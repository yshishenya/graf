#include "ProtectedCustodyMetadata.h"
#include "ProtectedCustodyPrimitives.h"
#include "ProtectedCustodyWriter.h"
#include "ProtectedPackedCustodyTree.h"
#include "ProtectedCustodyReader.h"
#include "Sha256.h"
#include "AtomicFileStore.h"
#include "../Upload/DesktopUploadQueueService.h"
#include "../Recording/LocalRecordingPackage.h"
#include <algorithm>
#include <limits>
#include <mutex>
#include <charconv>
#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#endif

namespace graf::windows {
namespace {
constexpr std::array<std::string_view, 5> packagePhases{"capturing", "finalizing", "sealed_normal", "sealed_degraded", "discard_pending"};
constexpr std::array<std::string_view, 5> packageRoles{"canonical", "media", "playback", "manifest", "recovery"};
constexpr std::size_t packageLimit = 65536;
#ifdef _WIN32
// Shared logical metadata read path. Physical/BOTH-slot selection stays in Files;
// semantic expectations come from the independently held native owner.
CustodyFileResult<CustodyBytes> readMetadataValue(ProtectedCustodyFiles& files,
    const CustodyContext& context, const CustodyIndex& index,
    const std::shared_ptr<const std::atomic<bool>>& cancellation) {
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<CustodyBytes> {
        return {std::nullopt, error, native};
    };
    const auto block = ProtectedCustodyCodec::blockBytes;
    if (!index.logicalLength || index.logicalLength > ProtectedCustodyCodec::logicalLimit(context.role) ||
        index.entries.size() != (index.logicalLength + block - 1) / block ||
        std::any_of(index.entries.begin(), index.entries.end(), [](const auto& entry) { return entry.flags != 0; }))
        return reject(CustodyFileError::invalidContent);
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyBytes bytes(static_cast<std::size_t>(index.logicalLength));
    struct Wipe {
        CustodyBytes& value;
        ~Wipe() { if (!value.empty()) SecureZeroMemory(value.data(), value.size()); }
    } wipe{bytes};
    for (std::size_t position = 0, offset = 0; position < index.entries.size(); ++position) {
        if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        const auto count = static_cast<std::uint32_t>(std::min<std::size_t>(block, bytes.size() - offset));
        const auto& entry = index.entries[position];
        auto cipher = files.readBlock(position, entry.version, count, entry.envelopeBytes);
        if (!cipher.ok()) return reject(cipher.error, cipher.nativeError);
        if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        auto plain = ProtectedCustodyCodec::openBlock(context, position, entry.version, count, *cipher.value);
        if (!plain.ok()) return reject(codecFileError(plain.error), plain.nativeError);
        Wipe plainWipe{*plain.value};
        if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        std::copy(plain.value->begin(), plain.value->end(), bytes.begin() + offset);
        offset += count;
    }
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return {std::move(bytes), CustodyFileError::none, 0};
}
#endif
constexpr std::array<std::string_view, 5> migrationStages{"prepared","copied_verified","switched","cleanup_pending","complete"};
constexpr std::array<std::string_view, 6> migrationSources{"ledger","manifest","canonical","media","playback","recovery"};
constexpr std::array<CustodyRole, 6> migrationRoles{CustodyRole::queue,CustodyRole::manifest,CustodyRole::canonical,CustodyRole::media,CustodyRole::playback,CustodyRole::recovery};
std::string_view text(const std::array<char, 301>& value) noexcept {
    return {value.data(), static_cast<std::size_t>(std::find(value.begin(), value.end(), '\0') - value.begin())};
}
bool identity(std::string_view value) noexcept {
    return !value.empty() && value.size() <= 300 && std::all_of(value.begin(), value.end(), [](char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
    });
}
std::string_view directory(const CustodyPackageValue& v) noexcept {
    const auto end = std::find(v.directory.begin(), v.directory.end(), '\0');
    return {v.directory.data(), static_cast<std::size_t>(end - v.directory.begin())};
}
std::string_view directory(const CustodyBootstrapValue& v) noexcept {
    if (!v.directory) return {};
    const auto end = std::find(v.directory->begin(), v.directory->end(), '\0');
    return {v.directory->data(), static_cast<std::size_t>(end - v.directory->begin())};
}
bool bootstrapShape(const CustodyBootstrapValue& v, const CustodyContext& own,
    std::uint64_t generation, const CustodyId& queue) noexcept {
    if (v.schema != 1 || own.role != CustodyRole::bootstrap || v.context.role != own.role ||
        v.context.storeId != own.storeId || v.context.objectId != own.objectId ||
        !generation || v.generation != generation || v.queueObjectId != queue) return false;
    if (v.mode == CustodyBootstrapMode::protectedStore) return !v.transactionId && !v.subject && !v.directory;
    if (v.mode != CustodyBootstrapMode::migrating || !v.transactionId || !v.subject) return false;
    if (*v.subject == CustodyMigrationSubject::queue) return !v.directory;
    return *v.subject == CustodyMigrationSubject::package && v.directory && identity(directory(v));
}
bool migrationShape(const CustodyMigrationValue& v, const CustodyContext& own, std::uint64_t generation,
    const CustodyId& transaction, CustodyMigrationSubject subject, std::string_view name) noexcept {
    const auto stage = static_cast<unsigned>(v.stage);
    if ((v.schema != 1 && v.schema != 2) || own.role != CustodyRole::migrationIntent || v.context.role != own.role ||
        v.context.storeId != own.storeId || v.context.objectId != own.objectId || !generation || v.generation != generation ||
        v.transactionId != transaction || v.subject != subject || stage >= migrationStages.size() ||
        !v.sourceCount || v.sourceCount > v.sources.size()) return false;
    if (subject == CustodyMigrationSubject::queue) { if (!name.empty() || v.directory || v.sourceCount != 1) return false; }
    else if (subject != CustodyMigrationSubject::package || !identity(name) || !v.directory || text(*v.directory) != name) return false;
    if (v.anchor.objectId.has_value() != v.anchor.generation.has_value() || (v.anchor.generation && !*v.anchor.generation) ||
        v.anchor.length > ProtectedCustodyCodec::logicalLimit(CustodyRole::queue) ||
        (subject == CustodyMigrationSubject::package && !v.anchor.objectId)) return false;
    if (generation == 1 && (v.stage != CustodyMigrationStage::prepared || v.barrier || v.authorization)) return false;
    unsigned kinds = 0;
    for (std::size_t i = 0; i < v.sourceCount; ++i) {
        const auto& s = v.sources[i]; const auto kind = static_cast<unsigned>(s.kind);
        if (kind >= migrationSources.size() || (kinds & (1U << kind)) ||
            s.length > ProtectedCustodyCodec::logicalLimit(migrationRoles[kind])) return false;
        kinds |= 1U << kind;
        if (subject == CustodyMigrationSubject::queue) {
            if (s.kind != CustodyMigrationSourceKind::ledger || s.length != v.anchor.length || s.sha256 != v.anchor.sha256) return false;
        } else if (s.kind == CustodyMigrationSourceKind::ledger) return false;
        if (v.stage == CustodyMigrationStage::prepared) {
            if (s.destinationGeneration || s.destinationLength || s.destinationSha256) return false;
        } else if (!s.destinationGeneration || !*s.destinationGeneration || !s.destinationLength ||
            *s.destinationLength != s.length || !s.destinationSha256 || *s.destinationSha256 != s.sha256) return false;
        if (!s.destinationPacked) {
            if (s.destinationContainerId || s.destinationCommittedExtent || s.destinationRootRef) return false;
        } else {
            if (v.schema != 2 || subject != CustodyMigrationSubject::package ||
                kind < static_cast<unsigned>(CustodyMigrationSourceKind::canonical) ||
                kind > static_cast<unsigned>(CustodyMigrationSourceKind::playback) || !s.destinationContainerId) return false;
            if (v.stage == CustodyMigrationStage::prepared) {
                if (s.destinationCommittedExtent || s.destinationRootRef) return false;
            } else {
                if (!s.destinationCommittedExtent || !s.destinationRootRef) return false;
                if (*s.destinationGeneration == 1 && (s.length != 0 ||
                    *s.destinationCommittedExtent != ProtectedPackedCustodyFormat::appendOffset)) return false;
                if (!ProtectedPackedCustodyFormat::decodeReference(s.destinationRootRef->data(), s.destinationRootRef->size(),
                    {s.length ? PackedRecordKind::nodeL2 : PackedRecordKind::empty, 0, *s.destinationGeneration,
                     *s.destinationCommittedExtent, *s.destinationCommittedExtent})) return false;
            }
        }
    }
    if (stage >= static_cast<unsigned>(CustodyMigrationStage::switched) && !v.barrier) return false;
    if (v.barrier && (v.barrier->objectId != own.objectId || v.barrier->generation != 1 || !v.barrier->blockVersion ||
        v.barrier->envelopeBytes <= 16 || v.barrier->envelopeBytes > ProtectedCustodyCodec::blockEnvelopeLimit(packageLimit))) return false;
    if (stage >= static_cast<unsigned>(CustodyMigrationStage::cleanupPending) && !v.authorization) return false;
    if (v.authorization) {
        const auto& a = *v.authorization;
        if ((a.kind != CustodyCleanupKind::ownerConfirmation && a.kind != CustodyCleanupKind::deletePurge) ||
            !a.queueGeneration || !identity(text(a.operationId)) || !identity(text(a.actorUserId)) || !identity(text(a.workspaceId))) return false;
        if (a.kind == CustodyCleanupKind::ownerConfirmation) {
            std::array<char, 32> id{};
            for (std::size_t i = 0; i < transaction.size(); ++i) { id[i*2] = "0123456789abcdef"[transaction[i] >> 4]; id[i*2+1] = "0123456789abcdef"[transaction[i] & 15]; }
            if (text(a.operationId) != std::string_view(id.data(), id.size())) return false;
        }
    }
    return true;
}
bool sameMigrationIdentity(const CustodyMigrationValue& a, const CustodyMigrationValue& b) noexcept {
    if (a.schema != b.schema || a.context.storeId != b.context.storeId || a.context.objectId != b.context.objectId ||
        a.context.role != b.context.role || a.transactionId != b.transactionId || a.subject != b.subject || a.directory != b.directory ||
        a.anchor.objectId != b.anchor.objectId || a.anchor.generation != b.anchor.generation ||
        a.anchor.length != b.anchor.length || a.anchor.sha256 != b.anchor.sha256 || a.sourceCount != b.sourceCount) return false;
    for (std::size_t i = 0; i < a.sourceCount; ++i) {
        const auto& source = a.sources[i];
        const auto end = b.sources.begin() + b.sourceCount;
        const auto found = std::find_if(b.sources.begin(), end, [&](const auto& s) { return s.kind == source.kind; });
        if (found == end || source.length != found->length || source.sha256 != found->sha256 ||
            source.destinationObjectId != found->destinationObjectId || source.destinationPacked != found->destinationPacked ||
            source.destinationContainerId != found->destinationContainerId) return false;
    }
    return true;
}
#ifdef _WIN32
bool migrationProgress(const CustodyMigrationValue& older, const CustodyMigrationValue& newer) noexcept {
    if (!sameMigrationIdentity(older, newer) || newer.stage < older.stage) return false;
    for (std::size_t i = 0; i < older.sourceCount; ++i) {
        const auto& s = older.sources[i];
        if (!s.destinationGeneration) continue;
        const auto& next = *std::find_if(newer.sources.begin(), newer.sources.begin() + newer.sourceCount,
            [&](const auto& v) { return v.kind == s.kind; }); // Exact kind set checked above.
        if (s.destinationGeneration != next.destinationGeneration || s.destinationLength != next.destinationLength ||
            s.destinationSha256 != next.destinationSha256 || s.destinationCommittedExtent != next.destinationCommittedExtent ||
            s.destinationRootRef != next.destinationRootRef) return false;
    }
    if (older.barrier) {
        if (!newer.barrier) return false;
        const auto& a = *older.barrier; const auto& b = *newer.barrier;
        if (a.objectId != b.objectId || a.generation != b.generation || a.blockVersion != b.blockVersion ||
            a.envelopeBytes != b.envelopeBytes || a.sha256 != b.sha256) return false;
    }
    if (older.authorization) {
        if (!newer.authorization) return false;
        const auto& a = *older.authorization; const auto& b = *newer.authorization;
        if (a.kind != b.kind || a.operationId != b.operationId || a.actorUserId != b.actorUserId || a.workspaceId != b.workspaceId ||
            a.queueObjectId != b.queueObjectId || a.queueGeneration != b.queueGeneration) return false;
    }
    return true;
}
#endif
std::optional<ReasonCode> packageReason(std::string_view text) noexcept {
    if (text.empty()) return ReasonCode::none;
    for (unsigned i = 1; i <= static_cast<unsigned>(ReasonCode::localPurgeUnverified); ++i) {
        const auto reason = static_cast<ReasonCode>(i);
        if (text == toString(reason)) return reason;
    }
    return std::nullopt;
}
bool packageShape(const CustodyPackageValue& v, const CustodyContext& own, std::uint64_t generation, std::string_view name) noexcept {
    if ((v.schema != 1 && v.schema != 2) || own.role != CustodyRole::packageState || v.context.role != own.role ||
        v.context.storeId != own.storeId || v.context.objectId != own.objectId || !generation || v.generation != generation ||
        !identity(name) || directory(v) != name || v.refCount > v.refs.size() ||
        static_cast<unsigned>(v.phase) >= packagePhases.size() || !packageReason(v.reason == ReasonCode::none ? "" : toString(v.reason))) return false;
    unsigned roles = 0, sealedRoles = 0;
    bool liveCanonical = false;
    const bool active = v.phase == CustodyPackagePhase::capturing || v.phase == CustodyPackagePhase::finalizing;
    for (std::size_t i = 0; i < v.refCount; ++i) {
        const auto& r = v.refs[i]; const auto role = static_cast<unsigned>(r.role);
        if (role < 1 || role > packageRoles.size() || (roles & (1U << role))) return false;
        roles |= 1U << role;
        if (r.sealed) {
            if (!r.generation || !*r.generation || !r.length || *r.length > ProtectedCustodyCodec::logicalLimit(r.role) || !r.sha256) return false;
            sealedRoles |= 1U << role;
        } else {
            if (!active || r.generation || r.length || r.sha256) return false;
            liveCanonical |= r.role == CustodyRole::canonical;
        }
        if (!r.packed) { if (r.containerId || r.committedExtent || r.rootRef) return false; }
        else {
            if (v.schema != 2 || role > static_cast<unsigned>(CustodyRole::playback) || !r.containerId) return false;
            if (!r.sealed) { if (r.committedExtent || r.rootRef) return false; }
            else {
                if (!r.committedExtent || !r.rootRef) return false;
                if (*r.generation == 1 && (*r.length != 0 || *r.committedExtent != ProtectedPackedCustodyFormat::appendOffset)) return false;
                if (!ProtectedPackedCustodyFormat::decodeReference(r.rootRef->data(), r.rootRef->size(),
                    {*r.length ? PackedRecordKind::nodeL2 : PackedRecordKind::empty, 0, *r.generation, *r.committedExtent, *r.committedExtent})) return false;
            }
        }
    }
    if (active) return liveCanonical && !v.shortRecordingDiscarded;
    if (v.phase == CustodyPackagePhase::sealedNormal) return v.reason == ReasonCode::none && !v.shortRecordingDiscarded &&
        (sealedRoles & 28U) == 28U; // media/playback/manifest.
    if (v.phase == CustodyPackagePhase::sealedDegraded) return v.reason != ReasonCode::none && !v.shortRecordingDiscarded;
    return v.shortRecordingDiscarded && v.reason == ReasonCode::none && (sealedRoles & (1U << static_cast<unsigned>(CustodyRole::manifest)));
}
// Closed metadata shapes: no heap DOM, retained input views, unknown-key
// skipping or recursive descent. Depth <=3, keys <=12, references <=6.
class PackageJson final {
public:
    explicit PackageJson(std::string_view input) noexcept : input_(input) {}
    ~PackageJson() { volatile char* bytes = token_.data(); for (std::size_t i = 0; i < token_.size(); ++i) bytes[i] = 0; }
    bool read(CustodyMigrationValue& v) noexcept {
        constexpr std::array<std::string_view, 12> keys{"schema","store_id","object_id","generation","transaction_id","subject","directory_id","stage","ledger_anchor","sources","barrier","cleanup_authorization"};
        std::array<unsigned, 6> sourceFields{};
        unsigned fields = 0;
        if (!object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: { const auto s = string(); if (!s) return false;
                if (*s == "graf.custody.migration.v1") v.schema = 1;
                else if (*s == "graf.custody.migration.v2") v.schema = 2; else return false; return true; }
            case 1: return hex(v.context.storeId);
            case 2: return hex(v.context.objectId);
            case 3: return number(v.generation);
            case 4: return hex(v.transactionId);
            case 5: { const auto s = string(); if (!s || (*s != "queue" && *s != "package")) return false;
                v.subject = *s == "queue" ? CustodyMigrationSubject::queue : CustodyMigrationSubject::package; return true; }
            case 6: return nullable(v.directory, [&](auto& value) { return identityString(value); });
            case 7: { const auto s = string(); if (!s) return false; const auto at = std::find(migrationStages.begin(), migrationStages.end(), *s);
                if (at == migrationStages.end()) return false; v.stage = static_cast<CustodyMigrationStage>(at-migrationStages.begin()); return true; }
            case 8: return migrationAnchor(v.anchor);
            case 9:
                if (!take('[')) return false;
                if (!take(']')) {
                    do { if (v.sourceCount == v.sources.size() || !migrationSource(v.sources[v.sourceCount], sourceFields[v.sourceCount])) return false; ++v.sourceCount; } while (take(','));
                    if (!take(']')) return false;
                }
                return true;
            case 10: return nullable(v.barrier, [&](auto& value) { return migrationBarrier(value); });
            case 11: return nullable(v.authorization, [&](auto& value) { return cleanupAuthorization(value); });
            }
            return false;
        }) || fields != 4095U) return false;
        whitespace(); if (cursor_ != input_.size()) return false;
        for (std::size_t i = 0; i < v.sourceCount; ++i) if (sourceFields[i] != (v.schema == 1 ? 127U : 2047U)) return false;
        return true;
    }
    bool read(CustodyBootstrapValue& v) noexcept {
        constexpr std::array<std::string_view, 9> keys{"schema","store_id","object_id","generation","mode","queue_object_id","transaction_id","subject","directory_id"};
        unsigned fields = 0;
        if (!object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: { const auto s = string(); return s && *s == "graf.custody.bootstrap.v1"; }
            case 1: return hex(v.context.storeId);
            case 2: return hex(v.context.objectId);
            case 3: return number(v.generation);
            case 4: { const auto s = string(); if (!s || (*s != "protected" && *s != "migrating")) return false;
                v.mode = *s == "protected" ? CustodyBootstrapMode::protectedStore : CustodyBootstrapMode::migrating; return true; }
            case 5: return hex(v.queueObjectId);
            case 6: return nullable(v.transactionId, [&](auto& value) { return hex(value); });
            case 7: return nullable(v.subject, [&](auto& value) {
                const auto s = string(); if (!s || (*s != "queue" && *s != "package")) return false;
                value = *s == "queue" ? CustodyMigrationSubject::queue : CustodyMigrationSubject::package; return true; });
            case 8: return nullable(v.directory, [&](auto& value) {
                const auto s = string(); if (!s || !identity(*s)) return false;
                std::copy(s->begin(), s->end(), value.begin()); return true; });
            }
            return false;
        }) || fields != 511U) return false;
        whitespace(); return cursor_ == input_.size();
    }
    bool read(CustodyPackageValue& v) noexcept {
        constexpr std::array<std::string_view, 9> keys{"schema","store_id","object_id","generation","directory_id","phase","reason","short_recording_discarded","refs"};
        std::array<unsigned, 5> refFields{};
        unsigned fields = 0;
        if (!object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: { const auto s = string(); if (!s) return false;
                if (*s == "graf.custody.package.v1") v.schema = 1;
                else if (*s == "graf.custody.package.v2") v.schema = 2; else return false; return true; }
            case 1: return hex(v.context.storeId);
            case 2: return hex(v.context.objectId);
            case 3: return number(v.generation);
            case 4: { const auto s = string(); if (!s || !identity(*s)) return false; std::copy(s->begin(), s->end(), v.directory.begin()); return true; }
            case 5: { const auto s = string(); if (!s) return false; const auto at = std::find(packagePhases.begin(), packagePhases.end(), *s);
                if (at == packagePhases.end()) return false; v.phase = static_cast<CustodyPackagePhase>(at - packagePhases.begin()); return true; }
            case 6: { const auto s = string(); if (!s) return false; const auto reason = packageReason(*s); if (!reason) return false; v.reason = *reason; return true; }
            case 7: if (literal("true")) { v.shortRecordingDiscarded = true; return true; } return literal("false");
            case 8:
                if (!take('[')) return false;
                if (!take(']')) {
                    do { if (v.refCount == v.refs.size() || !reference(v.refs[v.refCount], refFields[v.refCount])) return false; ++v.refCount; } while (take(','));
                    if (!take(']')) return false;
                }
                return true;
            }
            return false;
        }) || fields != 511U) return false;
        whitespace(); if (cursor_ != input_.size()) return false;
        for (std::size_t i = 0; i < v.refCount; ++i) if (refFields[i] != (v.schema == 1 ? 63U : 1023U)) return false;
        return true;
    }
private:
    bool identityString(std::array<char, 301>& out) noexcept {
        const auto s = string(); if (!s || !identity(*s)) return false;
        std::copy(s->begin(), s->end(), out.begin()); return true;
    }
    bool migrationAnchor(CustodyMigrationAnchor& v) noexcept {
        constexpr std::array<std::string_view, 4> keys{"object_id","generation","length","sha256"}; unsigned fields = 0;
        return object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: return nullable(v.objectId, [&](auto& x) { return hex(x); });
            case 1: return nullable(v.generation, [&](auto& x) { return number(x); });
            case 2: return number(v.length);
            case 3: return hex(v.sha256);
            } return false;
        }) && fields == 15U;
    }
    bool migrationSource(CustodyMigrationSource& v, unsigned& fields) noexcept {
        constexpr std::array<std::string_view, 11> keys{"source","source_length","source_sha256","destination_object_id","destination_generation","destination_length","destination_sha256",
            "destination_representation","destination_container_id","destination_committed_extent","destination_root_ref"};
        return object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: { const auto s = string(); if (!s) return false; const auto at = std::find(migrationSources.begin(), migrationSources.end(), *s);
                if (at == migrationSources.end()) return false; v.kind = static_cast<CustodyMigrationSourceKind>(at-migrationSources.begin()); return true; }
            case 1: return number(v.length);
            case 2: return hex(v.sha256);
            case 3: return hex(v.destinationObjectId);
            case 4: return nullable(v.destinationGeneration, [&](auto& x) { return number(x); });
            case 5: return nullable(v.destinationLength, [&](auto& x) { return number(x); });
            case 6: return nullable(v.destinationSha256, [&](auto& x) { return hex(x); });
            case 7: { const auto s = string(); if (!s || (*s != "flat_v1" && *s != "packed_v2")) return false;
                v.destinationPacked = *s == "packed_v2"; return true; }
            case 8: return nullable(v.destinationContainerId, [&](auto& x) { return hex(x); });
            case 9: return nullable(v.destinationCommittedExtent, [&](auto& x) { return number(x); });
            case 10: return nullable(v.destinationRootRef, [&](auto& x) { return hex(x); });
            } return false;
        });
    }
    bool migrationBarrier(CustodyMigrationBarrier& v) noexcept {
        constexpr std::array<std::string_view, 5> keys{"object_id","generation","block_version","envelope_bytes","sha256"}; unsigned fields = 0;
        return object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: return hex(v.objectId);
            case 1: return number(v.generation);
            case 2: return number(v.blockVersion);
            case 3: return number(v.envelopeBytes);
            case 4: return hex(v.sha256);
            } return false;
        }) && fields == 31U;
    }
    bool cleanupAuthorization(CustodyCleanupAuthorization& v) noexcept {
        constexpr std::array<std::string_view, 6> keys{"kind","operation_id","actor_user_id","workspace_id","queue_object_id","queue_generation"}; unsigned fields = 0;
        return object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: { const auto s = string(); if (!s || (*s != "owner_confirmation" && *s != "delete_purge")) return false;
                v.kind = *s == "owner_confirmation" ? CustodyCleanupKind::ownerConfirmation : CustodyCleanupKind::deletePurge; return true; }
            case 1: return identityString(v.operationId);
            case 2: return identityString(v.actorUserId);
            case 3: return identityString(v.workspaceId);
            case 4: return hex(v.queueObjectId);
            case 5: return number(v.queueGeneration);
            } return false;
        }) && fields == 63U;
    }
    void whitespace() noexcept { while (cursor_ < input_.size() && std::string_view(" \r\n\t").find(input_[cursor_]) != std::string_view::npos) ++cursor_; }
    bool take(char c) noexcept { whitespace(); if (cursor_ == input_.size() || input_[cursor_] != c) return false; ++cursor_; return true; }
    bool literal(std::string_view text) noexcept { whitespace(); if (input_.substr(cursor_, text.size()) != text) return false; cursor_ += text.size(); return true; }
    std::optional<std::string_view> string() noexcept {
        if (!take('"')) return std::nullopt;
        std::size_t size = 0;
        while (cursor_ < input_.size()) {
            auto c = static_cast<unsigned char>(input_[cursor_++]);
            if (c == '"') return std::string_view(token_.data(), size);
            if (c < 0x20 || c >= 0x80) return std::nullopt;
            if (c == '\\') {
                if (cursor_ == input_.size()) return std::nullopt;
                c = static_cast<unsigned char>(input_[cursor_++]);
                if (c == 'u') {
                    if (input_.size() - cursor_ < 4) return std::nullopt;
                    unsigned value = 0;
                    const auto parsed = std::from_chars(input_.data()+cursor_, input_.data()+cursor_+4, value, 16);
                    if (parsed.ec != std::errc{} || parsed.ptr != input_.data()+cursor_+4 || value >= 128) return std::nullopt;
                    cursor_ += 4; c = static_cast<unsigned char>(value);
                } else if (c == 'b') c = '\b'; else if (c == 'f') c = '\f'; else if (c == 'n') c = '\n';
                else if (c == 'r') c = '\r'; else if (c == 't') c = '\t';
                else if (c != '"' && c != '\\' && c != '/') return std::nullopt;
            }
            if (size == 300) return std::nullopt;
            token_[size++] = static_cast<char>(c);
        }
        return std::nullopt;
    }
    bool number(std::uint64_t& out) noexcept {
        whitespace(); const auto start = cursor_;
        while (cursor_ < input_.size() && input_[cursor_] >= '0' && input_[cursor_] <= '9') ++cursor_;
        if (start == cursor_ || (cursor_-start > 1 && input_[start] == '0')) return false;
        const auto result = std::from_chars(input_.data()+start, input_.data()+cursor_, out);
        return result.ec == std::errc{} && result.ptr == input_.data()+cursor_;
    }
    template<std::size_t N> bool hex(std::array<std::uint8_t, N>& out) noexcept {
        const auto text = string(); if (!text || text->size() != N*2) return false;
        const auto digit = [](char c) { return c >= '0' && c <= '9' ? c-'0' : c >= 'a' && c <= 'f' ? c-'a'+10 : -1; };
        for (std::size_t i = 0; i < N; ++i) { const auto a = digit((*text)[i*2]), b = digit((*text)[i*2+1]); if (a < 0 || b < 0) return false; out[i] = static_cast<std::uint8_t>(a*16+b); }
        return true;
    }
    template<class T, class Read> bool nullable(std::optional<T>& out, Read readValue) noexcept {
        if (literal("null")) { out.reset(); return true; } T value{}; if (!readValue(value)) return false; out = value; return true;
    }
    template<std::size_t N, class Field> bool object(const std::array<std::string_view, N>& keys, unsigned& fields, Field field) noexcept {
        if (!take('{')) return false; if (take('}')) return true;
        do {
            const auto key = string(); if (!key) return false;
            const auto at = std::find(keys.begin(), keys.end(), *key); if (at == keys.end()) return false;
            const auto index = static_cast<std::size_t>(at - keys.begin()); const unsigned bit = 1U << index;
            if ((fields & bit) || !take(':')) return false;
            fields |= bit; if (!field(index)) return false;
        } while (take(','));
        return take('}');
    }
    bool reference(CustodyPackageReference& r, unsigned& fields) noexcept {
        constexpr std::array<std::string_view, 10> keys{"role","object_id","binding","generation","length","sha256","representation","container_id","committed_extent","root_ref"};
        return object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: { const auto s = string(); if (!s) return false; const auto at = std::find(packageRoles.begin(), packageRoles.end(), *s);
                if (at == packageRoles.end()) return false; r.role = static_cast<CustodyRole>(at-packageRoles.begin()+1); return true; }
            case 1: return hex(r.objectId);
            case 2: { const auto s = string(); if (!s || (*s != "live" && *s != "sealed")) return false; r.sealed = *s == "sealed"; return true; }
            case 3: return nullable(r.generation, [&](auto& value) { return number(value); });
            case 4: return nullable(r.length, [&](auto& value) { return number(value); });
            case 5: return nullable(r.sha256, [&](auto& value) { return hex(value); });
            case 6: { const auto s = string(); if (!s || (*s != "flat_v1" && *s != "packed_v2")) return false; r.packed = *s == "packed_v2"; return true; }
            case 7: return nullable(r.containerId, [&](auto& value) { return hex(value); });
            case 8: return nullable(r.committedExtent, [&](auto& value) { return number(value); });
            case 9: return nullable(r.rootRef, [&](auto& value) { return hex(value); });
            }
            return false;
        });
    }
    std::string_view input_; std::size_t cursor_ = 0;
    std::array<char, 300> token_{};
};
} // namespace

CustodyCodecResult<CustodyMigrationValue> readCustodyMigration(std::string_view json,
    const CustodyContext& own, std::uint64_t generation, const CustodyId& transaction,
    CustodyMigrationSubject subject, std::string_view name) noexcept {
    CustodyMigrationValue value;
    if (json.empty() || json.size() > packageLimit || !PackageJson(json).read(value) ||
        !migrationShape(value, own, generation, transaction, subject, name)) return {std::nullopt, CustodyCodecError::invalidPlaintext, 0};
    return {value, CustodyCodecError::none, 0};
}
CustodyCodecResult<CustodyMigrationValue> readCustodyMigrationBirth(
    const CustodyBytes& envelope, const CustodyContext& own, const CustodyMigrationValue& current,
    const CustodyId& transaction, CustodyMigrationSubject subject, std::string_view name) try {
    const auto reject = [](CustodyCodecError e, std::uint32_t native = 0) -> CustodyCodecResult<CustodyMigrationValue> {
        return {std::nullopt, e, native};
    };
    if (!migrationShape(current, own, current.generation, transaction, subject, name) || !current.barrier)
        return reject(CustodyCodecError::invalidInput);
    const auto& ref = *current.barrier;
    if (envelope.size() != ref.envelopeBytes) return reject(CustodyCodecError::invalidEnvelope);
    const auto hash = custody_detail::digest(envelope.data(), envelope.size());
    if (!hash) return reject(CustodyCodecError::hashFailed);
    if (*hash != ref.sha256) return reject(CustodyCodecError::invalidEnvelope);
    auto plain = ProtectedCustodyCodec::openMigrationBirthBlock(own, ref.blockVersion, envelope);
    if (!plain.ok()) return reject(plain.error, plain.nativeError);
    auto parsed = readCustodyMigration({reinterpret_cast<const char*>(plain.value->data()), plain.value->size()},
        own, ref.generation, transaction, subject, name);
    if (!parsed.ok()) return parsed;
    struct Wipe {
        CustodyMigrationValue& value;
        ~Wipe() { volatile auto* bytes = reinterpret_cast<volatile std::uint8_t*>(&value);
            for (std::size_t i=0; i<sizeof(value); ++i) bytes[i]=0; }
    } wipe{*parsed.value};
    const auto& birth = *parsed.value;
    if (!sameMigrationIdentity(birth, current)) return reject(CustodyCodecError::invalidPlaintext);
    return {birth, CustodyCodecError::none, 0};
} catch (const std::bad_alloc&) {
    return {std::nullopt, CustodyCodecError::allocationFailed, 0};
}

ProtectedCustodyMigrationPair::ProtectedCustodyMigrationPair(CustodyPin&& pin,
    std::shared_ptr<const ProtectedCustodyBootstrapPair>&& bootstrap,
    std::unique_ptr<ProtectedCustodyFiles>&& lease, CustodyMetadataIndices&& indices,
    const std::array<CustodyMigrationValue, 2>& values)
    : indices_(std::move(indices)), values_(values) {
    // Finish throwing index/proxy moves before transferring native ownership.
    pin_.emplace(std::move(pin)); bootstrap_ = std::move(bootstrap); lease_ = std::move(lease);
}
ProtectedCustodyMigrationPair::~ProtectedCustodyMigrationPair() {
    static_assert(std::is_trivially_copyable_v<CustodyMigrationValue>);
    volatile auto* bytes = reinterpret_cast<volatile std::uint8_t*>(values_.data());
    for (std::size_t i = 0; i < sizeof(values_); ++i) bytes[i] = 0;
}
CustodyFileResult<std::shared_ptr<const ProtectedCustodyMigrationPair>> ProtectedCustodyMigrationPair::read(
    std::shared_ptr<const ProtectedCustodyBootstrapPair> bootstrap,
    std::shared_ptr<const std::atomic<bool>> cancellation) {
    if (!bootstrap || !cancellation || !bootstrap->queueLease_)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
#ifndef _WIN32
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    const auto& selected = bootstrap->current();
    if (selected.mode == CustodyBootstrapMode::protectedStore) {
        for (const auto& peer : bootstrap->slots()) {
            if (peer.mode != CustodyBootstrapMode::protectedStore || peer.transactionId || peer.subject || peer.directory)
                return {std::nullopt, CustodyFileError::invalidInput, 0};
        }
        const auto& root = bootstrap->lease_->trustedRoot();
        // Completed root history has no bootstrap transaction selector. Only
        // independently authenticated direct Birth may supply that expectation.
        return readImpl(root, CustodyContext{{}, {}, CustodyRole::migrationIntent}, std::nullopt,
            CustodyMigrationSubject::queue, {}, std::move(cancellation), std::move(bootstrap));
    }
    if (selected.mode != CustodyBootstrapMode::migrating)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    for (const auto& peer : bootstrap->slots()) {
        if (peer.mode == CustodyBootstrapMode::migrating &&
            (peer.transactionId != selected.transactionId || peer.subject != selected.subject ||
             directory(peer) != directory(selected))) return {std::nullopt, CustodyFileError::conflict, 0};
    }
    const auto& root = bootstrap->lease_->trustedRoot();
    // The references remain with the parent moved into readImpl, not a caller path.
    return readImpl(root, CustodyContext{{}, {}, CustodyRole::migrationIntent}, *selected.transactionId,
        *selected.subject, directory(selected), std::move(cancellation), std::move(bootstrap));
#endif
}
CustodyFileResult<std::shared_ptr<const ProtectedCustodyMigrationPair>> ProtectedCustodyMigrationPair::read(
    const std::filesystem::path& root, const CustodyContext& own, const CustodyId& transaction,
    CustodyMigrationSubject subject, std::string_view name, std::shared_ptr<const std::atomic<bool>> cancellation) {
    return readImpl(root, own, transaction, subject, name, std::move(cancellation), {});
}
CustodyFileResult<bool> ProtectedCustodyMigrationPair::readValues(ProtectedCustodyFiles& lease,
    const CustodyContext& own, std::optional<CustodyId> transaction, CustodyMigrationSubject subject,
    std::string_view name, const std::shared_ptr<const std::atomic<bool>>& cancellation,
    const ProtectedCustodyBootstrapPair* bootstrap, bool preparing, CustodyMetadataIndices& indices,
    std::array<CustodyMigrationValue,2>& values) {
#ifndef _WIN32
    (void)lease; (void)own; (void)transaction; (void)subject; (void)name;
    (void)cancellation; (void)bootstrap; (void)preparing; (void)indices; (void)values;
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    const auto cancelled = [&] { return cancellation->load(); };
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<bool> {
        return {std::nullopt, error, native};
    };
    auto pair = lease.readValidatedMetadataPair();
    if (!pair.ok()) return reject(pair.error, pair.nativeError);
    struct WipeValues {
        std::array<CustodyMigrationValue, 2>& values;
        ~WipeValues() { SecureZeroMemory(values.data(), sizeof(values)); }
    };
    for (unsigned slot = 0; slot < 2; ++slot) {
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        const auto& index = pair.value->indices[slot];
        if (!index.logicalLength || index.logicalLength > packageLimit || index.entries.size() != 1 || index.entries[0].flags != 0)
            return reject(CustodyFileError::invalidContent);
        const auto& entry = index.entries[0];
        auto cipher = lease.readBlock(0, entry.version, static_cast<std::uint32_t>(index.logicalLength), entry.envelopeBytes);
        if (!cipher.ok()) return reject(cipher.error, cipher.nativeError);
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        auto plain = ProtectedCustodyCodec::openBlock(own, 0, entry.version, static_cast<std::uint32_t>(index.logicalLength), *cipher.value);
        if (!plain.ok()) return reject(codecFileError(plain.error), plain.nativeError);
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        const std::string_view json{reinterpret_cast<const char*>(plain.value->data()), plain.value->size()};
        auto expectedTransaction = transaction;
        if (preparing && !expectedTransaction && index.generation == 1) {
            // Pre-fence restart has no bootstrap tuple yet. Authenticate the
            // fixed native Birth independently before deriving strict expectations.
            auto birthPlain = ProtectedCustodyCodec::openMigrationBirthBlock(own, entry.version, *cipher.value);
            if (!birthPlain.ok()) return reject(codecFileError(birthPlain.error), birthPlain.nativeError);
            std::array<CustodyMigrationValue,2> provisional{}; WipeValues wipeProvisional{provisional};
            if (!PackageJson({reinterpret_cast<const char*>(birthPlain.value->data()), birthPlain.value->size()}).read(provisional[0]))
                return reject(CustodyFileError::invalidContent);
            expectedTransaction = provisional[0].transactionId;
        }
        if (!expectedTransaction) {
            std::array<CustodyMigrationValue, 2> provisional{};
            WipeValues wipeProvisional{provisional};
            // Locator only: no semantic expectation or path is taken from this
            // current JSON. Fixed role/position and native context stay on lease.
            if (!PackageJson(json).read(provisional[0]) || !provisional[0].barrier)
                return reject(CustodyFileError::invalidContent);
            const auto& ref = *provisional[0].barrier;
            if (ref.objectId != own.objectId || ref.generation != 1 || !ref.blockVersion ||
                ref.envelopeBytes <= 16 || ref.envelopeBytes > ProtectedCustodyCodec::blockEnvelopeLimit(packageLimit))
                return reject(CustodyFileError::invalidContent);
            auto envelope = lease.readMigrationBirthEnvelope(ref.blockVersion, static_cast<std::uint32_t>(ref.envelopeBytes));
            if (!envelope.ok()) return reject(envelope.error, envelope.nativeError);
            if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            if (envelope.value->size() != ref.envelopeBytes) return reject(CustodyFileError::invalidContent);
            const auto hash = custody_detail::digest(envelope.value->data(), envelope.value->size());
            if (!hash) return reject(codecFileError(CustodyCodecError::hashFailed));
            if (*hash != ref.sha256) return reject(CustodyFileError::invalidContent);
            if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            auto birthPlain = ProtectedCustodyCodec::openMigrationBirthBlock(own, ref.blockVersion, *envelope.value);
            if (!birthPlain.ok()) return reject(codecFileError(birthPlain.error), birthPlain.nativeError);
            if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            if (!PackageJson({reinterpret_cast<const char*>(birthPlain.value->data()), birthPlain.value->size()}).read(provisional[1]))
                return reject(CustodyFileError::invalidContent);
            expectedTransaction = provisional[1].transactionId;
        }
        auto parsed = readCustodyMigration(json, own, index.generation, *expectedTransaction, subject, name);
        if (!parsed.ok()) return reject(codecFileError(parsed.error), parsed.nativeError);
        values[slot] = *parsed.value;
        SecureZeroMemory(&*parsed.value, sizeof(CustodyMigrationValue));
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        if (bootstrap && (subject == CustodyMigrationSubject::queue
            ? values[slot].sources[0].destinationObjectId != bootstrap->current().queueObjectId
            : !values[slot].anchor.objectId || *values[slot].anchor.objectId != bootstrap->current().queueObjectId))
            return reject(CustodyFileError::invalidContent);
        if (values[slot].barrier) {
            const auto& ref = *values[slot].barrier;
            auto envelope = lease.readMigrationBirthEnvelope(ref.blockVersion, static_cast<std::uint32_t>(ref.envelopeBytes));
            if (!envelope.ok()) return reject(envelope.error, envelope.nativeError);
            if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            auto birth = readCustodyMigrationBirth(*envelope.value, own, values[slot], values[slot].transactionId, subject, name);
            if (!birth.ok()) return reject(codecFileError(birth.error), birth.nativeError);
            SecureZeroMemory(&*birth.value, sizeof(CustodyMigrationValue));
        }
    }
    const auto selected = pair.value->selectedSlot;
    if (!migrationProgress(values[1U - selected], values[selected])) return reject(CustodyFileError::conflict);
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    indices = std::move(*pair.value);
    return {true, CustodyFileError::none, 0};
#endif
}

CustodyFileResult<std::shared_ptr<const ProtectedCustodyMigrationPair>> ProtectedCustodyMigrationPair::readImpl(
    const std::filesystem::path& root, CustodyContext own, std::optional<CustodyId> transaction,
    CustodyMigrationSubject subject, std::string_view name, std::shared_ptr<const std::atomic<bool>> cancellation,
    std::shared_ptr<const ProtectedCustodyBootstrapPair> bootstrap, std::unique_ptr<ProtectedCustodyFiles> prepared) try {
    using Proof = std::shared_ptr<const ProtectedCustodyMigrationPair>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Proof> {
        return {std::nullopt, error, native};
    };
    if (own.role != CustodyRole::migrationIntent || !cancellation ||
        (!transaction && !prepared && (!bootstrap || subject != CustodyMigrationSubject::queue)) ||
        (subject == CustodyMigrationSubject::queue ? !name.empty() :
         subject != CustodyMigrationSubject::package || !identity(name))) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)root; (void)transaction; (void)bootstrap; (void)prepared; return reject(CustodyFileError::unsupportedPlatform);
#else
    const auto cancelled = [&] { return cancellation->load(); };
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyNativeJob job;
    auto held = std::move(bootstrap); // Failure closes parent leases before job admission releases.
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyPin pin;
    if (!pin) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    auto lease = std::move(prepared);
    if (lease) {
        const auto native = lease->context();
        if (lease->trustedRoot() != root || native.storeId != own.storeId || native.objectId != own.objectId || native.role != own.role)
            return reject(CustodyFileError::identityMismatch);
    } else {
        auto opened = held ? ProtectedCustodyFiles::discover(root, CustodyRole::migrationIntent, name)
            : ProtectedCustodyFiles::open(root, name, own, CustodyFileAccess::writeExisting);
        if (!opened.ok()) return reject(opened.error, opened.nativeError);
        lease = std::move(*opened.value);
    }
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    if (held) {
        own = lease->context();
        if (own.storeId != held->current().context.storeId) return reject(CustodyFileError::identityMismatch);
    }
    CustodyMetadataIndices indices;
    std::array<CustodyMigrationValue, 2> values{};
    struct WipeValues {
        std::array<CustodyMigrationValue, 2>& values;
        ~WipeValues() { SecureZeroMemory(values.data(), sizeof(values)); }
    } wipe{values};
    auto checked = readValues(*lease, own, transaction, subject, name, cancellation, held.get(), false, indices, values);
    if (!checked.ok()) return reject(checked.error, checked.nativeError);
    lease->blockWrites();
    CustodyAllocator<ProtectedCustodyMigrationPair> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedCustodyMigrationPair(std::move(pin), std::move(held), std::move(lease), std::move(indices), values); }
    catch (...) { allocator.deallocate(raw, 1); throw; }
    Proof proof{raw, [](const ProtectedCustodyMigrationPair* p) {
        p->~ProtectedCustodyMigrationPair();
        CustodyAllocator<ProtectedCustodyMigrationPair>{}.deallocate(const_cast<ProtectedCustodyMigrationPair*>(p), 1);
    }, allocator};
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return {std::move(proof), CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyCodecResult<CustodyBytes> writeCustodyMigration(const CustodyMigrationValue& value,
    const CustodyContext& own, std::uint64_t generation, const CustodyId& transaction,
    CustodyMigrationSubject subject, std::string_view name) try {
    if (!migrationShape(value, own, generation, transaction, subject, name)) return {std::nullopt, CustodyCodecError::invalidInput, 0};
    CustodyBytes out; out.reserve(packageLimit);
    const auto emit = [&](std::string_view s) { if (s.size() > packageLimit-out.size()) throw std::length_error("migration bound"); out.insert(out.end(), s.begin(), s.end()); };
    const auto quoted = [&](std::string_view s) { emit("\""); emit(s); emit("\""); };
    const auto hex = [&](const auto& bytes) { emit("\""); for (auto b : bytes) { const char chars[2]{"0123456789abcdef"[b >> 4], "0123456789abcdef"[b & 15]}; emit({chars, 2}); } emit("\""); };
    const auto number = [&](std::uint64_t n) { char chars[20]; const auto encoded = std::to_chars(chars, chars+20, n); emit({chars, static_cast<std::size_t>(encoded.ptr-chars)}); };
    emit("{\"schema\":"); quoted(value.schema == 1 ? "graf.custody.migration.v1" : "graf.custody.migration.v2");
    emit(",\"store_id\":"); hex(value.context.storeId);
    emit(",\"object_id\":"); hex(value.context.objectId); emit(",\"generation\":"); number(value.generation);
    emit(",\"transaction_id\":"); hex(value.transactionId); emit(",\"subject\":"); quoted(subject == CustodyMigrationSubject::queue ? "queue" : "package");
    emit(",\"directory_id\":"); if (value.directory) quoted(text(*value.directory)); else emit("null");
    emit(",\"stage\":"); quoted(migrationStages[static_cast<unsigned>(value.stage)]);
    emit(",\"ledger_anchor\":{\"object_id\":"); if (value.anchor.objectId) hex(*value.anchor.objectId); else emit("null");
    emit(",\"generation\":"); if (value.anchor.generation) number(*value.anchor.generation); else emit("null");
    emit(",\"length\":"); number(value.anchor.length); emit(",\"sha256\":"); hex(value.anchor.sha256); emit("},\"sources\":[");
    bool first = true;
    for (unsigned kind = 0; kind < migrationSources.size(); ++kind) for (std::size_t i = 0; i < value.sourceCount; ++i) {
        const auto& s = value.sources[i]; if (static_cast<unsigned>(s.kind) != kind) continue;
        if (!first) emit(","); first = false;
        emit("{\"source\":"); quoted(migrationSources[kind]); emit(",\"source_length\":"); number(s.length);
        emit(",\"source_sha256\":"); hex(s.sha256); emit(",\"destination_object_id\":"); hex(s.destinationObjectId);
        emit(",\"destination_generation\":"); if (s.destinationGeneration) number(*s.destinationGeneration); else emit("null");
        emit(",\"destination_length\":"); if (s.destinationLength) number(*s.destinationLength); else emit("null");
        emit(",\"destination_sha256\":"); if (s.destinationSha256) hex(*s.destinationSha256); else emit("null");
        if (value.schema == 2) {
            emit(",\"destination_representation\":"); quoted(s.destinationPacked ? "packed_v2" : "flat_v1");
            emit(",\"destination_container_id\":"); if (s.destinationContainerId) hex(*s.destinationContainerId); else emit("null");
            emit(",\"destination_committed_extent\":"); if (s.destinationCommittedExtent) number(*s.destinationCommittedExtent); else emit("null");
            emit(",\"destination_root_ref\":"); if (s.destinationRootRef) hex(*s.destinationRootRef); else emit("null");
        }
        emit("}");
    }
    emit("],\"barrier\":");
    if (!value.barrier) emit("null");
    else {
        const auto& b = *value.barrier; emit("{\"object_id\":"); hex(b.objectId); emit(",\"generation\":"); number(b.generation);
        emit(",\"block_version\":"); number(b.blockVersion); emit(",\"envelope_bytes\":"); number(b.envelopeBytes); emit(",\"sha256\":"); hex(b.sha256); emit("}");
    }
    emit(",\"cleanup_authorization\":");
    if (!value.authorization) emit("null");
    else {
        const auto& a = *value.authorization;
        emit("{\"kind\":"); quoted(a.kind == CustodyCleanupKind::ownerConfirmation ? "owner_confirmation" : "delete_purge");
        emit(",\"operation_id\":"); quoted(text(a.operationId)); emit(",\"actor_user_id\":"); quoted(text(a.actorUserId));
        emit(",\"workspace_id\":"); quoted(text(a.workspaceId)); emit(",\"queue_object_id\":"); hex(a.queueObjectId);
        emit(",\"queue_generation\":"); number(a.queueGeneration); emit("}");
    }
    emit("}"); return {std::move(out), CustodyCodecError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyCodecError::allocationFailed, 0}; }
  catch (const std::length_error&) { return {std::nullopt, CustodyCodecError::invalidInput, 0}; }

CustodyCodecResult<CustodyBootstrapValue> readCustodyBootstrap(std::string_view json,
    const CustodyContext& own, std::uint64_t generation, const CustodyId& queue) noexcept {
    CustodyBootstrapValue value;
    if (json.empty() || json.size() > packageLimit || !PackageJson(json).read(value) ||
        !bootstrapShape(value, own, generation, queue)) return {std::nullopt, CustodyCodecError::invalidPlaintext, 0};
    return {value, CustodyCodecError::none, 0};
}
CustodyCodecResult<CustodyBytes> writeCustodyBootstrap(const CustodyBootstrapValue& value,
    const CustodyContext& own, std::uint64_t generation, const CustodyId& queue) try {
    if (!bootstrapShape(value, own, generation, queue)) return {std::nullopt, CustodyCodecError::invalidInput, 0};
    CustodyBytes out;
    out.reserve(packageLimit); // Charged before plaintext; no unwiped growth buffer.
    const auto emit = [&](std::string_view text) { if (text.size() > packageLimit-out.size()) throw std::length_error("bootstrap bound"); out.insert(out.end(), text.begin(), text.end()); };
    const auto quoted = [&](std::string_view text) { emit("\""); emit(text); emit("\""); };
    const auto hex = [&](const auto& bytes) { emit("\""); for (auto b : bytes) { const char chars[2]{"0123456789abcdef"[b >> 4], "0123456789abcdef"[b & 15]}; emit({chars, 2}); } emit("\""); };
    const auto number = [&](std::uint64_t n) { char chars[20]; const auto encoded = std::to_chars(chars, chars+20, n); emit({chars, static_cast<std::size_t>(encoded.ptr-chars)}); };
    emit("{\"schema\":\"graf.custody.bootstrap.v1\",\"store_id\":"); hex(value.context.storeId);
    emit(",\"object_id\":"); hex(value.context.objectId); emit(",\"generation\":"); number(value.generation);
    emit(",\"mode\":"); quoted(value.mode == CustodyBootstrapMode::protectedStore ? "protected" : "migrating");
    emit(",\"queue_object_id\":"); hex(value.queueObjectId);
    emit(",\"transaction_id\":"); if (value.transactionId) hex(*value.transactionId); else emit("null");
    emit(",\"subject\":"); if (value.subject) quoted(*value.subject == CustodyMigrationSubject::queue ? "queue" : "package"); else emit("null");
    emit(",\"directory_id\":"); if (value.directory) quoted(directory(value)); else emit("null");
    emit("}"); return {std::move(out), CustodyCodecError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyCodecError::allocationFailed, 0}; }
  catch (const std::length_error&) { return {std::nullopt, CustodyCodecError::invalidInput, 0}; }

CustodyCodecResult<CustodyPackageValue> readCustodyPackage(std::string_view json, const CustodyContext& own,
    std::uint64_t generation, std::string_view name) noexcept {
    CustodyPackageValue value;
    if (json.empty() || json.size() > packageLimit || !PackageJson(json).read(value) || !packageShape(value, own, generation, name))
        return {std::nullopt, CustodyCodecError::invalidPlaintext, 0};
    return {value, CustodyCodecError::none, 0};
}
CustodyCodecResult<CustodyBytes> writeCustodyPackage(const CustodyPackageValue& value, const CustodyContext& own,
    std::uint64_t generation, std::string_view name) try {
    if (!packageShape(value, own, generation, name)) return {std::nullopt, CustodyCodecError::invalidInput, 0};
    CustodyBytes out;
    // Admit the fixed payload cap before plaintext; no vector growth can free
    // an unwiped previous plaintext buffer. All capacity is charged as usual.
    out.reserve(packageLimit);
    const auto emit = [&](std::string_view text) { if (text.size() > packageLimit-out.size()) throw std::length_error("package bound"); out.insert(out.end(), text.begin(), text.end()); };
    const auto quoted = [&](std::string_view text) { emit("\""); emit(text); emit("\""); }; // Validated closed ASCII grammar; no escapes required.
    const auto hex = [&](const auto& bytes) { emit("\""); for (auto b : bytes) { const char chars[2]{"0123456789abcdef"[b >> 4], "0123456789abcdef"[b & 15]}; emit({chars, 2}); } emit("\""); };
    const auto number = [&](std::uint64_t n) { char chars[20]; const auto encoded = std::to_chars(chars, chars+20, n); emit({chars, static_cast<std::size_t>(encoded.ptr-chars)}); };
    emit("{\"schema\":"); quoted(value.schema == 1 ? "graf.custody.package.v1" : "graf.custody.package.v2");
    emit(",\"store_id\":"); hex(value.context.storeId); emit(",\"object_id\":"); hex(value.context.objectId);
    emit(",\"generation\":"); number(value.generation); emit(",\"directory_id\":"); quoted(name);
    emit(",\"phase\":"); quoted(packagePhases[static_cast<unsigned>(value.phase)]);
    emit(",\"reason\":"); quoted(value.reason == ReasonCode::none ? "" : toString(value.reason));
    emit(",\"short_recording_discarded\":"); emit(value.shortRecordingDiscarded ? "true" : "false"); emit(",\"refs\":[");
    bool first = true;
    for (unsigned role = 1; role <= packageRoles.size(); ++role) for (std::size_t i = 0; i < value.refCount; ++i) {
        const auto& r = value.refs[i]; if (static_cast<unsigned>(r.role) != role) continue;
        if (!first) emit(","); first = false;
        emit("{\"role\":"); quoted(packageRoles[role-1]); emit(",\"object_id\":"); hex(r.objectId);
        emit(",\"binding\":"); quoted(r.sealed ? "sealed" : "live"); emit(",\"generation\":"); if (r.generation) number(*r.generation); else emit("null");
        emit(",\"length\":"); if (r.length) number(*r.length); else emit("null"); emit(",\"sha256\":"); if (r.sha256) hex(*r.sha256); else emit("null");
        if (value.schema == 2) {
            emit(",\"representation\":"); quoted(r.packed ? "packed_v2" : "flat_v1"); emit(",\"container_id\":"); if (r.containerId) hex(*r.containerId); else emit("null");
            emit(",\"committed_extent\":"); if (r.committedExtent) number(*r.committedExtent); else emit("null"); emit(",\"root_ref\":"); if (r.rootRef) hex(*r.rootRef); else emit("null");
        }
        emit("}");
    }
    emit("]}"); return {std::move(out), CustodyCodecError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyCodecError::allocationFailed, 0}; }
  catch (const std::length_error&) { return {std::nullopt, CustodyCodecError::invalidInput, 0}; }

ProtectedCustodyBootstrapPair::ProtectedCustodyBootstrapPair(CustodyPin&& pin,
    std::unique_ptr<ProtectedCustodyFiles>&& lease, std::unique_ptr<ProtectedCustodyFiles>&& queueLease,
    CustodyMetadataIndices&& indices,
    const std::array<CustodyBootstrapValue, 2>& values)
    : indices_(std::move(indices)), values_(values) {
    pin_.emplace(std::move(pin)); lease_ = std::move(lease); queueLease_ = std::move(queueLease);
}
ProtectedCustodyBootstrapPair::~ProtectedCustodyBootstrapPair() {
    static_assert(std::is_trivially_copyable_v<CustodyBootstrapValue>);
    volatile auto* bytes = reinterpret_cast<volatile std::uint8_t*>(values_.data());
    for (std::size_t i = 0; i < sizeof(values_); ++i) bytes[i] = 0;
}
CustodyFileResult<std::shared_ptr<const ProtectedCustodyBootstrapPair>> ProtectedCustodyBootstrapPair::read(
    const std::filesystem::path& root, std::shared_ptr<const std::atomic<bool>> cancellation) {
    return readImpl(root, CustodyContext{{}, {}, CustodyRole::bootstrap}, {}, true, std::move(cancellation));
}
CustodyFileResult<std::shared_ptr<const ProtectedCustodyBootstrapPair>> ProtectedCustodyBootstrapPair::read(
    const std::filesystem::path& root, const CustodyContext& own, const CustodyId& queue,
    std::shared_ptr<const std::atomic<bool>> cancellation) {
    return readImpl(root, own, queue, false, std::move(cancellation));
}
CustodyFileResult<std::shared_ptr<const ProtectedCustodyBootstrapPair>> ProtectedCustodyBootstrapPair::readImpl(
    const std::filesystem::path& root, CustodyContext own, CustodyId queue, bool discover,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Proof = std::shared_ptr<const ProtectedCustodyBootstrapPair>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Proof> {
        return {std::nullopt, error, native};
    };
    if (own.role != CustodyRole::bootstrap || !cancellation) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)root; (void)queue; (void)discover; return reject(CustodyFileError::unsupportedPlatform);
#else
    const auto cancelled = [&] { return cancellation->load(); };
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyNativeJob job;
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyPin pin;
    if (!pin) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    auto opened = discover ? ProtectedCustodyFiles::discover(root, CustodyRole::bootstrap)
        : ProtectedCustodyFiles::open(root, "", own, CustodyFileAccess::writeExisting);
    if (!opened.ok()) return reject(opened.error, opened.nativeError);
    auto lease = std::move(*opened.value);
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    std::unique_ptr<ProtectedCustodyFiles> queueLease;
    if (discover) {
        auto reserved = ProtectedCustodyFiles::discover(root, CustodyRole::queue);
        if (!reserved.ok()) return reject(reserved.error, reserved.nativeError);
        queueLease = std::move(*reserved.value);
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        own = lease->context();
        if (queueLease->context().storeId != own.storeId) return reject(CustodyFileError::identityMismatch);
        queue = queueLease->context().objectId;
    }
    auto pair = lease->readValidatedMetadataPair();
    if (!pair.ok()) return reject(pair.error, pair.nativeError);
    std::array<CustodyBootstrapValue, 2> values{};
    struct WipeValues {
        std::array<CustodyBootstrapValue, 2>& values;
        ~WipeValues() { SecureZeroMemory(values.data(), sizeof(values)); }
    } wipe{values};
    for (unsigned slot = 0; slot < 2; ++slot) {
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        const auto& index = pair.value->indices[slot];
        if (!index.logicalLength || index.logicalLength > packageLimit || index.entries.size() != 1 || index.entries[0].flags != 0)
            return reject(CustodyFileError::invalidContent);
        const auto& entry = index.entries[0];
        auto cipher = lease->readBlock(0, entry.version, static_cast<std::uint32_t>(index.logicalLength), entry.envelopeBytes);
        if (!cipher.ok()) return reject(cipher.error, cipher.nativeError);
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        auto plain = ProtectedCustodyCodec::openBlock(own, 0, entry.version, static_cast<std::uint32_t>(index.logicalLength), *cipher.value);
        if (!plain.ok()) return reject(codecFileError(plain.error), plain.nativeError);
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        auto parsed = readCustodyBootstrap({reinterpret_cast<const char*>(plain.value->data()), plain.value->size()}, own, index.generation, queue);
        if (!parsed.ok()) return reject(codecFileError(parsed.error), parsed.nativeError);
        values[slot] = *parsed.value; SecureZeroMemory(&*parsed.value, sizeof(CustodyBootstrapValue));
    }
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    lease->blockWrites();
    CustodyAllocator<ProtectedCustodyBootstrapPair> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedCustodyBootstrapPair(std::move(pin), std::move(lease), std::move(queueLease), std::move(*pair.value), values); }
    catch (...) { allocator.deallocate(raw, 1); throw; }
    Proof proof{raw, [](const ProtectedCustodyBootstrapPair* p) {
        p->~ProtectedCustodyBootstrapPair();
        CustodyAllocator<ProtectedCustodyBootstrapPair>{}.deallocate(const_cast<ProtectedCustodyBootstrapPair*>(p), 1);
    }, allocator};
    return {std::move(proof), CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

ProtectedCustodyQueueInput::ProtectedCustodyQueueInput(CustodyPin&& pin,
    std::shared_ptr<const ProtectedCustodyBootstrapPair>&& bootstrap,
    CustodyMetadataIndices&& indices, std::array<CustodyBytes, 2>&& payloads)
    : indices_(std::move(indices)), payloads_(std::move(payloads)) {
    // Finish throwing Debug proxy transfers before releasing caller admission.
    pin_.emplace(std::move(pin)); bootstrap_ = std::move(bootstrap);
}
CustodyFileResult<std::shared_ptr<const ProtectedCustodyQueueInput>> ProtectedCustodyQueueInput::read(
    std::shared_ptr<const ProtectedCustodyBootstrapPair> bootstrap,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Input = std::shared_ptr<const ProtectedCustodyQueueInput>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Input> {
        return {std::nullopt, error, native};
    };
    if (!bootstrap || !cancellation || !bootstrap->queueLease_) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    return reject(CustodyFileError::unsupportedPlatform);
#else
    const auto cancelled = [&] { return cancellation->load(); };
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyNativeJob job;
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    auto held = std::move(bootstrap); // Last input release after mutex unlock, before job admission.
    CustodyPin pin;
    if (!pin) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    std::unique_lock<std::mutex> lock(held->queueRead_, std::try_to_lock);
    if (!lock.owns_lock()) return reject(CustodyFileError::conflict, ERROR_BUSY);
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    const CustodyContext context{held->current().context.storeId, held->current().queueObjectId, CustodyRole::queue};
    auto& files = *held->queueLease_;
    auto pair = files.readValidatedMetadataPair();
    if (!pair.ok()) return reject(pair.error, pair.nativeError);
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    std::array<CustodyBytes, 2> payloads;
    for (unsigned slot = 0; slot < 2; ++slot) {
        auto value = readMetadataValue(files, context, pair.value->indices[slot], cancellation);
        if (!value.ok()) return reject(value.error, value.nativeError);
        payloads[slot] = std::move(*value.value);
    }
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyAllocator<ProtectedCustodyQueueInput> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedCustodyQueueInput(std::move(pin), std::shared_ptr<const ProtectedCustodyBootstrapPair>(held), std::move(*pair.value), std::move(payloads)); }
    catch (...) { allocator.deallocate(raw, 1); throw; }
    Input input{raw, [](const ProtectedCustodyQueueInput* p) {
        p->~ProtectedCustodyQueueInput(); CustodyAllocator<ProtectedCustodyQueueInput>{}.deallocate(const_cast<ProtectedCustodyQueueInput*>(p), 1);
    }, allocator};
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return {std::move(input), CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

ProtectedCustodyPackagePair::ProtectedCustodyPackagePair(CustodyPin&& pin,
    std::unique_ptr<ProtectedCustodyFiles>&& lease, CustodyMetadataIndices&& indices,
    const std::array<CustodyPackageValue, 2>& values, std::shared_ptr<const std::atomic<bool>> cancellation, LeaseOrigin origin)
    : indices_(std::move(indices)), values_(values), cancellation_(std::move(cancellation)), origin_(origin) {
    // Finish all throwing index/proxy transfers while caller still owns lease.
    pin_.emplace(std::move(pin)); lease_ = std::move(lease);
}
ProtectedCustodyPackagePair::~ProtectedCustodyPackagePair() {
    static_assert(std::is_trivially_copyable_v<CustodyPackageValue>);
    volatile auto* bytes = reinterpret_cast<volatile std::uint8_t*>(values_.data());
    for (std::size_t i = 0; i < sizeof(values_); ++i) bytes[i] = 0;
}
CustodyFileResult<std::shared_ptr<const ProtectedCustodyPackagePair>> ProtectedCustodyPackagePair::read(
    const std::filesystem::path& root, std::string_view directory, const CustodyContext& own,
    std::shared_ptr<const std::atomic<bool>> cancellation) {
    return readImpl(root, directory, own, std::move(cancellation), {}, LeaseOrigin::isolatedReadOnly);
}
CustodyFileResult<std::shared_ptr<const ProtectedCustodyPackagePair>> ProtectedCustodyPackagePair::readImpl(
    const std::filesystem::path& root, std::string_view directory, const CustodyContext& own,
    std::shared_ptr<const std::atomic<bool>> cancellation, std::shared_ptr<ProtectedCustodyFiles> retained, LeaseOrigin origin) try {
    using Proof = std::shared_ptr<const ProtectedCustodyPackagePair>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Proof> {
        return {std::nullopt, error, native};
    };
    if (own.role != CustodyRole::packageState || !identity(directory) || !cancellation)
        return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)root; (void)retained; (void)origin; return reject(CustodyFileError::unsupportedPlatform);
#else
    const auto cancelled = [&] { return cancellation->load(); };
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyNativeJob job;
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyPin pin;
    if (!pin) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    // Existing identity HANDLE excludes another protocol writer. No create,
    // publication or repair; private blocked lease never exposes write rights.
    std::unique_ptr<ProtectedCustodyFiles> lease;
    if (!retained) {
        auto opened = ProtectedCustodyFiles::open(root, directory, own, CustodyFileAccess::writeExisting);
        if (!opened.ok()) return reject(opened.error, opened.nativeError);
        lease = std::move(*opened.value);
    }
    auto* files = retained ? retained.get() : lease.get();
    if (files->context().storeId != own.storeId || files->context().objectId != own.objectId || files->context().role != own.role)
        return reject(CustodyFileError::identityMismatch);
    auto pair = files->readValidatedMetadataPair();
    if (!pair.ok()) return reject(pair.error, pair.nativeError);
    std::array<CustodyPackageValue, 2> values{};
    struct WipeValues {
        std::array<CustodyPackageValue, 2>& values;
        ~WipeValues() { SecureZeroMemory(values.data(), sizeof(values)); }
    } wipe{values};
    for (unsigned slot = 0; slot < 2; ++slot) {
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        const auto& index = pair.value->indices[slot];
        if (!index.logicalLength || index.logicalLength > packageLimit || index.entries.size() != 1 || index.entries[0].flags != 0)
            return reject(CustodyFileError::invalidContent);
        const auto& entry = index.entries[0];
        auto cipher = files->readBlock(0, entry.version, static_cast<std::uint32_t>(index.logicalLength), entry.envelopeBytes);
        if (!cipher.ok()) return reject(cipher.error, cipher.nativeError);
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        auto plain = ProtectedCustodyCodec::openBlock(own, 0, entry.version, static_cast<std::uint32_t>(index.logicalLength), *cipher.value);
        if (!plain.ok()) return reject(codecFileError(plain.error), plain.nativeError);
        auto parsed = readCustodyPackage({reinterpret_cast<const char*>(plain.value->data()), plain.value->size()}, own, index.generation, directory);
        if (!parsed.ok()) return reject(codecFileError(parsed.error), parsed.nativeError);
        values[slot] = *parsed.value;
        SecureZeroMemory(&*parsed.value, sizeof(CustodyPackageValue));
    }
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    if (lease) lease->blockWrites(); // A borrowed writer retains its capability; no release/reopen or upgrade.
    CustodyAllocator<ProtectedCustodyPackagePair> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedCustodyPackagePair(std::move(pin), std::move(lease), std::move(*pair.value), values, cancellation, origin); }
    catch (...) { allocator.deallocate(raw, 1); throw; }
    Proof proof{raw, [](const ProtectedCustodyPackagePair* p) {
        p->~ProtectedCustodyPackagePair();
        CustodyAllocator<ProtectedCustodyPackagePair>{}.deallocate(const_cast<ProtectedCustodyPackagePair*>(p), 1);
    }, allocator};
    raw->retainedLease_ = std::move(retained);
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return {std::move(proof), CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

ProtectedCustodyRecordingPackage::~ProtectedCustodyRecordingPackage() {
#ifdef _WIN32
    SecureZeroMemory(&current_, sizeof(current_));
#endif
}

std::filesystem::path ProtectedCustodyRecordingPackage::path() const {
#ifdef _WIN32
    return packageRoot_->packagePath(); // Actual held package/.custody-v1 parent, not a caller path.
#else
    return {};
#endif
}

#ifdef _WIN32
// Reject every identity/path alias, including rows belonging to another user.
bool recordingReservationConflict(const ProtectedUploadQueueValue& value,
    const std::filesystem::path& path, const ProtectedUploadQueueValue::Item* own) {
    const auto equal = [](const std::filesystem::path& a, const std::filesystem::path& b) {
        return CompareStringOrdinal(a.c_str(), -1, b.c_str(), -1, TRUE) == CSTR_EQUAL;
    };
    const auto directory = path.filename();
    for (const auto& row : value.items()) {
        if (&row == own) continue;
        std::error_code error;
        const auto other = std::filesystem::weakly_canonical(
            std::filesystem::u8path(row.packageDirectory.begin(), row.packageDirectory.end()), error);
        if (error || equal(other, path) ||
            equal(std::filesystem::u8path(row.directoryId.begin(), row.directoryId.end()), directory) ||
            equal(std::filesystem::u8path(row.localRecordingId.begin(), row.localRecordingId.end()), directory) ||
            equal(std::filesystem::u8path(row.sessionId.begin(), row.sessionId.end()), directory)) return true;
    }
    for (const auto& operation : value.deletionOperations())
        if (operation.phase != DeletionOperationPhase::rejected &&
            equal(std::filesystem::u8path(operation.targetId.begin(), operation.targetId.end()), directory)) return true;
    return own && value.deletionBlocks(*own);
}
#endif

CustodyFileResult<bool> ProtectedCustodyStoreOwner::prepareRecordingReservation(ProtectedUploadQueueValue& candidate,
    std::string_view name, std::string_view user, std::string_view workspace, bool ownerKnown,
    std::uint64_t now, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!cancellation || !DesktopApiClient::accountId(name) ||
        (ownerKnown ? (!user.empty() || !workspace.empty()) &&
            (!DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace)) :
            !user.empty() || !workspace.empty())) return {std::nullopt, CustodyFileError::invalidInput, 0};
    auto current = readQueueValue(cancellation);
    if (!current.ok()) return {std::nullopt, current.error, current.nativeError};
    auto durable = (*current.value)->serialize(cancellation), proposed = candidate.serialize(cancellation);
    if (!durable.ok()) return {std::nullopt, durable.error, durable.nativeError};
    if (!proposed.ok()) return {std::nullopt, proposed.error, proposed.nativeError};
    if (*durable.value != *proposed.value || now < candidate.updatedAtMs())
        return {std::nullopt, CustodyFileError::conflict, 0};
#ifndef _WIN32
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    const auto path = rootPath() / std::filesystem::u8path(name.begin(), name.end());
    if (recordingReservationConflict(candidate, path)) return {std::nullopt, CustodyFileError::conflict, 0};
    const auto attributes = GetFileAttributesW(path.c_str());
    const auto error = attributes == INVALID_FILE_ATTRIBUTES ? GetLastError() : ERROR_ALREADY_EXISTS;
    if (attributes != INVALID_FILE_ATTRIBUTES || (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND))
        return {std::nullopt, CustodyFileError::conflict, error};
    const auto encoded = path.u8string();
    ProtectedUploadQueueValue::Item row;
    row.localRecordingId.assign(name.begin(), name.end());
    row.directoryId = row.sessionId = row.localRecordingId;
    row.packageDirectory.assign(encoded.begin(), encoded.end());
    row.ownerUserId.assign(user.begin(), user.end()); row.ownerWorkspaceId.assign(workspace.begin(), workspace.end());
    row.status = UploadQueueStatus::quarantined;
    row.safeReason = ownerKnown ? "capture_prepared" : "capture_owner_unknown";
    if (!candidate.enqueue(std::move(row), now, cancellation.get())) return {std::nullopt, CustodyFileError::conflict, 0};
    return {true, CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (...) { return {std::nullopt, CustodyFileError::ioFailed, 0}; }

CustodyFileResult<bool> ProtectedCustodyStoreOwner::finishRecordingReservation(ProtectedUploadQueueValue& candidate,
    const ProtectedUploadQueueValue& reservation, std::string_view name, const V5WriterResult& result,
    std::uint64_t now, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!cancellation || !DesktopApiClient::accountId(name)) return {std::nullopt, CustodyFileError::invalidInput, 0};
    auto current = readQueueValue(cancellation);
    if (!current.ok()) return {std::nullopt, current.error, current.nativeError};
    auto durable = (*current.value)->serialize(cancellation), proposed = candidate.serialize(cancellation);
    if (!durable.ok()) return {std::nullopt, durable.error, durable.nativeError};
    if (!proposed.ok()) return {std::nullopt, proposed.error, proposed.nativeError};
    if (*durable.value != *proposed.value || now < candidate.updatedAtMs())
        return {std::nullopt, CustodyFileError::conflict, 0};
#ifndef _WIN32
    (void)reservation; (void)result;
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    auto found = std::find_if(candidate.items_.begin(), candidate.items_.end(),
        [&](const auto& row) { return std::string_view(row.localRecordingId) == name; });
    const auto expected = std::find_if(reservation.items().begin(), reservation.items().end(),
        [&](const auto& row) { return std::string_view(row.localRecordingId) == name; });
    const auto path = rootPath() / std::filesystem::u8path(name.begin(), name.end());
    if (found == candidate.items_.end() || expected == reservation.items().end() ||
        !sameUploadIdentity(*found, *expected) || found->safeReason != expected->safeReason ||
        found->updatedAtMs != expected->updatedAtMs || hasUploadServerIdentity(*expected) ||
        found->directoryId != found->localRecordingId ||
        found->sessionId != found->localRecordingId || std::string_view(found->packageDirectory) != path.u8string() ||
        found->status != UploadQueueStatus::quarantined || hasUploadServerIdentity(*found) ||
        (found->safeReason != "capture_prepared" && found->safeReason != "capture_owner_unknown") ||
        (!result.packageDirectory.empty() && result.packageDirectory != path) ||
        recordingReservationConflict(candidate, path, &*found)) return {std::nullopt, CustodyFileError::conflict, 0};
    if (result.shortRecordingDiscarded) {
        // The writer and all consumers must already be drained by the caller.
        auto opened = readPackage(name, cancellation);
        if (!opened.ok()) return {std::nullopt, opened.error, opened.nativeError};
        const auto& state = (*opened.value)->current();
        if (state.context.storeId != result.packageContext.storeId || state.context.objectId != result.packageContext.objectId ||
            state.context.role != result.packageContext.role || state.generation != result.packageGeneration ||
            state.phase != CustodyPackagePhase::discardPending || !state.shortRecordingDiscarded || state.reason != ReasonCode::none)
            return {std::nullopt, CustodyFileError::conflict, 0};
        auto inspected = LocalRecordingPackage::inspectProtected(rootPath(), *opened.value, name, cancellation);
        if (!inspected.ok()) return {std::nullopt, inspected.error, inspected.nativeError};
        if ((*inspected.value)->evidence().integrity != PackageIntegrity::discardPending)
            return {std::nullopt, CustodyFileError::conflict, 0};
        candidate.items_.erase(found); // No deletion operations/acknowledgements are changed.
    } else {
        const bool owned = !found->ownerUserId.empty() && !found->ownerWorkspaceId.empty();
        if (result.keepablePackage() && owned && found->safeReason == "capture_prepared") {
            found->status = UploadQueueStatus::pending; found->safeReason.clear();
        } // No-login and unknown retain their original marker, even on success.
        found->updatedAtMs = now;
    }
    candidate.updatedAtMs_ = now;
    return {true, CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (...) { return {std::nullopt, CustodyFileError::ioFailed, 0}; }

CustodyFileResult<bool> ProtectedCustodyStoreOwner::recoverRecordingReservation(ProtectedUploadQueueValue& candidate,
    const ProtectedUploadQueueValue& reservation, std::string_view name,
    std::shared_ptr<const ProtectedCustodyPackagePair> pair, std::uint64_t now,
    std::shared_ptr<const std::atomic<bool>> cancellation, std::string_view claimUser, std::string_view claimWorkspace) try {
    const bool claim = !claimUser.empty() || !claimWorkspace.empty();
    if (!cancellation || !DesktopApiClient::accountId(name) || !pair ||
        (claim && (!DesktopApiClient::accountId(claimUser) || !DesktopApiClient::accountId(claimWorkspace))))
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    auto current = readQueueValue(cancellation);
    if (!current.ok()) return {std::nullopt, current.error, current.nativeError};
    auto durable = (*current.value)->serialize(cancellation), proposed = candidate.serialize(cancellation);
    if (!durable.ok()) return {std::nullopt, durable.error, durable.nativeError};
    if (!proposed.ok()) return {std::nullopt, proposed.error, proposed.nativeError};
    if (*durable.value != *proposed.value || now < candidate.updatedAtMs())
        return {std::nullopt, CustodyFileError::conflict, 0};
#ifndef _WIN32
    (void)reservation;
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    auto found = std::find_if(candidate.items_.begin(), candidate.items_.end(),
        [&](const auto& row) { return std::string_view(row.localRecordingId) == name; });
    const auto expected = std::find_if(reservation.items().begin(), reservation.items().end(),
        [&](const auto& row) { return std::string_view(row.localRecordingId) == name; });
    const auto path = rootPath() / std::filesystem::u8path(name.begin(), name.end());
    if (found == candidate.items_.end() || expected == reservation.items().end() ||
        !sameUploadIdentity(*found, *expected) || found->safeReason != expected->safeReason ||
        found->updatedAtMs != expected->updatedAtMs || hasUploadServerIdentity(*expected) ||
        found->status != UploadQueueStatus::quarantined || found->safeReason != "capture_prepared" ||
        (claim ? !isPreparedUnownedRecording(*found) : !isPreparedOwnedRecording(*found)) ||
        hasUploadServerIdentity(*found) || found->directoryId != found->localRecordingId ||
        found->sessionId != found->localRecordingId || std::string_view(found->packageDirectory) != path.u8string() ||
        directory(pair->current()) != name || pair->current().phase != CustodyPackagePhase::sealedNormal ||
        recordingReservationConflict(candidate, path, &*found))
        return {std::nullopt, CustodyFileError::conflict, 0};
    auto checked = revalidatePackage(std::move(pair), cancellation);
    if (!checked.ok() || !*checked.value) return checked;
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    if (claim) return {candidate.prepareManualSend(static_cast<std::size_t>(found - candidate.items_.begin()),
        claimUser, claimWorkspace, true, now, cancellation.get()), CustodyFileError::none, 0};
    found->status = UploadQueueStatus::pending; found->safeReason.clear();
    found->updatedAtMs = candidate.updatedAtMs_ = now;
    return {true, CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (...) { return {std::nullopt, CustodyFileError::ioFailed, 0}; }

CustodyFileResult<bool> ProtectedCustodyStoreOwner::discardShortRecording(std::string_view name,
    const CustodyContext& expected, std::uint64_t generation,
    std::shared_ptr<const std::atomic<bool>> cancellation) {
    bool effectAttempted = false;
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<bool> {
        return {std::nullopt, effectAttempted ? CustodyFileError::recoveryRequired : error, native};
    };
    try {
    if (!cancellation || !identity(name) || !generation || expected.role != CustodyRole::packageState)
        return reject(CustodyFileError::invalidInput);
    if (shortDiscard_) {
        if (!shortDiscard_->attempted) shortDiscard_.reset();
        else {
            effectAttempted = true;
            if (std::string_view(shortDiscard_->directory) != name || shortDiscard_->generation != generation ||
                shortDiscard_->context.storeId != expected.storeId || shortDiscard_->context.objectId != expected.objectId ||
                shortDiscard_->context.role != expected.role)
                return {std::nullopt, CustodyFileError::recoveryRequired, 0};
        }
    }
    if (failed_ && !effectAttempted) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
#ifndef _WIN32
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    if (expected.storeId != queueContext_.storeId) return {std::nullopt, CustodyFileError::identityMismatch, 0};
    std::shared_ptr<const ProtectedUploadQueueValue> queue;
    {
    CustodyNativeJob job;
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    if (effectAttempted && failed_) {
        // Retire only failed metadata readers, NEVER the continuously held root
        // or this authenticated operation. Existing-only factories cannot birth
        // an empty ledger; independently retained identities must still match.
        bootstrap_.reset(); queue_.reset();
        auto reopenedQueue = ProtectedCustodyFiles::openStoreObject(root_, CustodyRole::queue, false);
        if (!reopenedQueue.ok()) return reject(reopenedQueue.error, reopenedQueue.nativeError);
        const auto actualQueue = (*reopenedQueue.value)->context();
        if (actualQueue.storeId != queueContext_.storeId || actualQueue.objectId != queueContext_.objectId)
            return reject(CustodyFileError::identityMismatch);
        queue_ = std::move(*reopenedQueue.value);
        auto bootstrap = ProtectedCustodyFiles::openStoreObject(root_, CustodyRole::bootstrap, false);
        if (!bootstrap.ok()) return reject(bootstrap.error, bootstrap.nativeError);
        const auto actualBootstrap = (*bootstrap.value)->context();
        if (actualBootstrap.storeId != shortDiscard_->bootstrapContext.storeId ||
            actualBootstrap.objectId != shortDiscard_->bootstrapContext.objectId)
            return reject(CustodyFileError::identityMismatch);
        bootstrap_ = std::move(*bootstrap.value);
    }
        auto checked = validate(cancellation, &queue);
        if (!checked.ok()) return reject(checked.error, checked.nativeError);
        // This slot was established while healthy and fences every mutator.
        // A later read-only validation error may recover only after this full
        // fresh BOTH/root validation, never by clearing an ambiguous write.
        if (effectAttempted) failed_ = false;
    }
    const auto path = rootPath() / std::filesystem::u8path(name.begin(), name.end());
    for (const auto& row : queue->items()) {
        std::error_code error;
        const auto other = std::filesystem::weakly_canonical(
            std::filesystem::u8path(row.packageDirectory.begin(), row.packageDirectory.end()), error);
        const auto otherName = std::filesystem::u8path(row.directoryId.begin(), row.directoryId.end()).native();
        if (error || std::string_view(row.localRecordingId) == name || std::string_view(row.sessionId) == name ||
            CompareStringOrdinal(other.c_str(), -1, path.c_str(), -1, TRUE) == CSTR_EQUAL ||
            CompareStringOrdinal(otherName.c_str(), -1, path.filename().c_str(), -1, TRUE) == CSTR_EQUAL)
            return effectAttempted ? reject(CustodyFileError::recoveryRequired) : CustodyFileResult<bool>{false, CustodyFileError::none, 0};
    }
    if (effectAttempted) {
        // Explicit recovery is read-only. Only this same genuine root owner
        // knows the preceding authenticated intent/attempt; a fresh missing
        // path can never enter this branch.
        if (!DesktopLocalPurgeService(rootPath()).isSafePackageDirectory(path, true))
            return {std::nullopt, CustodyFileError::recoveryRequired, 0};
        const auto attributes = GetFileAttributesW(path.c_str());
        if (attributes == INVALID_FILE_ATTRIBUTES) {
            const auto error = GetLastError();
            if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND)
                return {std::nullopt, CustodyFileError::recoveryRequired, error};
            if (cancellation->load())
                return {std::nullopt, CustodyFileError::recoveryRequired, ERROR_OPERATION_ABORTED};
            shortDiscard_.reset();
            return {true, CustodyFileError::none, 0};
        }
        struct Guard { HANDLE value; ~Guard() { if (value != INVALID_HANDLE_VALUE) CloseHandle(value); } } guard{
            CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr,
                OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr)};
        FILE_ID_INFO id{};
        if (guard.value == INVALID_HANDLE_VALUE || (attributes & FILE_ATTRIBUTE_REPARSE_POINT) ||
            !GetFileInformationByHandleEx(guard.value, FileIdInfo, &id, sizeof(id)) ||
            id.VolumeSerialNumber != shortDiscard_->volume ||
            std::memcmp(id.FileId.Identifier, shortDiscard_->fileId.data(), shortDiscard_->fileId.size()) != 0)
            return {std::nullopt, CustodyFileError::recoveryRequired, 0};
    }
    auto opened = readPackage(name, cancellation);
    if (!opened.ok()) return reject(opened.error, opened.nativeError);
    auto pair = std::move(*opened.value);
    const auto& actual = pair->current();
    if (actual.context.storeId != expected.storeId || actual.context.objectId != expected.objectId ||
        actual.context.role != expected.role || actual.generation != generation)
        return reject(CustodyFileError::conflict);
    if (actual.phase != CustodyPackagePhase::discardPending || !actual.shortRecordingDiscarded || actual.reason != ReasonCode::none)
        return {false, CustodyFileError::none, 0};
    {
        // Reuse the v5 validator: positive marker alone is not proof of the
        // exact short duration, session, format and BOTH authenticated closures.
        auto inspected = LocalRecordingPackage::inspectProtected(rootPath(), pair, name, cancellation);
        if (!inspected.ok()) return reject(inspected.error, inspected.nativeError);
        if ((*inspected.value)->evidence().integrity != PackageIntegrity::discardPending)
            return {false, CustodyFileError::none, 0};
    } // Real decoder/readers retire before any Shell operation.
    if (effectAttempted) {
        // Still the exact intact package. A later explicit attempt may retry;
        // this reconciliation itself never repeats the Shell effect.
        shortDiscard_.reset();
        return {false, CustodyFileError::none, 0};
    }
    shortDiscard_.emplace();
    shortDiscard_->directory.assign(name.begin(), name.end());
    shortDiscard_->context = actual.context;
    shortDiscard_->bootstrapContext = bootstrap_->context();
    shortDiscard_->generation = actual.generation;
    auto removed = recyclePackage(std::move(pair), cancellation, &effectAttempted);
    if (effectAttempted && (!removed.ok() || !*removed.value))
        return {std::nullopt, CustodyFileError::recoveryRequired, removed.nativeError};
    if (!removed.ok() || !*removed.value) return removed;
    CustodyNativeJob job;
    if (!job) return {std::nullopt, CustodyFileError::recoveryRequired, ERROR_NOT_ENOUGH_QUOTA};
    auto checked = validate(cancellation);
    if (!checked.ok()) return {std::nullopt, CustodyFileError::recoveryRequired, checked.nativeError};
    shortDiscard_.reset();
    return {true, CustodyFileError::none, 0}; // No queue row or synthetic commit was created.
#endif
    } catch (const std::bad_alloc&) {
        return {std::nullopt, effectAttempted ? CustodyFileError::recoveryRequired : CustodyFileError::allocationFailed, 0};
    } catch (const std::system_error& error) {
        return {std::nullopt, effectAttempted ? CustodyFileError::recoveryRequired : CustodyFileError::ioFailed,
            static_cast<std::uint32_t>(error.code().value())};
    }
}

#ifdef _WIN32
CustodyFileResult<bool> ProtectedCustodyStoreOwner::recyclePackage(
    std::shared_ptr<const ProtectedCustodyPackagePair> pair, std::shared_ptr<const std::atomic<bool>> cancellation,
    bool* effectAttempted) {
    if (!pair || !pair->retainedLease_ || pair->origin_ != ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly ||
        !cancellation || pair->cancellation_.get() != cancellation.get())
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    const auto name = directory(pair->current());
    const auto path = rootPath() / std::filesystem::u8path(name.begin(), name.end());
    if (pair->retainedLease_->trustedRoot() != rootPath() || pair->retainedLease_->packagePath().parent_path() != path ||
        !DesktopLocalPurgeService(rootPath()).isSafePackageDirectory(path))
        return {std::nullopt, CustodyFileError::identityMismatch, 0};
    auto revalidated = revalidatePackage(pair, cancellation);
    if (!revalidated.ok() || !*revalidated.value) return revalidated;
    {
        auto readers = openProtectedCustodyReaders(rootPath(), pair, cancellation);
        if (!readers.ok()) return {std::nullopt, readers.error, readers.nativeError};
    }
    // Retain the exact directory identity while retiring our own member leases.
    // SHARE_DELETE is not an adversarial same-SID race barrier; the worker has
    // already fenced its writers. Unknown external readers still block Shell.
    CustodyPin pin;
    if (!pin) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    struct Guard { HANDLE value; ~Guard() { if (value != INVALID_HANDLE_VALUE) CloseHandle(value); } } guard{
        CreateFileW(path.c_str(), FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_DELETE, nullptr,
            OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr)};
    FILE_ID_INFO id{}; FILE_ATTRIBUTE_TAG_INFO attributes{};
    if (guard.value == INVALID_HANDLE_VALUE ||
        !GetFileInformationByHandleEx(guard.value, FileIdInfo, &id, sizeof(id)) ||
        !GetFileInformationByHandleEx(guard.value, FileAttributeTagInfo, &attributes, sizeof(attributes)) ||
        !(attributes.FileAttributes & FILE_ATTRIBUTE_DIRECTORY) || (attributes.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT))
        return {false, CustodyFileError::none, 0};
    pair.reset();
    CustodyNativeJob job;
    if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    if (effectAttempted && shortDiscard_) {
        shortDiscard_->volume = id.VolumeSerialNumber;
        std::memcpy(shortDiscard_->fileId.data(), id.FileId.Identifier, shortDiscard_->fileId.size());
        shortDiscard_->attempted = true;
    }
    if (effectAttempted) *effectAttempted = true;
    return {DesktopLocalPurgeService::recycle(path, 0, reinterpret_cast<std::uintptr_t>(guard.value)), CustodyFileError::none, 0};
}
#endif

CustodyFileResult<bool> ProtectedCustodyStoreOwner::purgeLocalPackage(std::string_view localId,
    std::uint64_t expectedGeneration, ProtectedUploadQueueValue& candidate, std::uint64_t now,
    std::shared_ptr<const std::atomic<bool>> cancellation, const BasicLocalPurgeTask<CustodyString>* serverTask,
    std::string_view user, std::string_view workspace, std::string_view origin) try {
    if (!cancellation || !identity(localId)) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (serverTask && (!validLocalBufferPurgeTask(*serverTask) || !DesktopApiClient::accountId(user) ||
        !DesktopApiClient::accountId(workspace))) return {false, CustodyFileError::none, 0};
    const bool userScoped = !user.empty() || !workspace.empty();
    if (userScoped && (!DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace)))
        return {false, CustodyFileError::none, 0};
    if (failed_ || (shortDiscard_ && shortDiscard_->attempted))
        return {std::nullopt, CustodyFileError::recoveryRequired, 0};
#ifndef _WIN32
    (void)expectedGeneration; (void)candidate; (void)now; (void)origin;
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    std::shared_ptr<const ProtectedUploadQueueValue> current;
    CustodyFileResult<bool> checked;
    {
        CustodyNativeJob job;
        if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
        checked = validate(cancellation, &current); // BOTH bootstrap/queue slots, including migration barriers.
    }
    if (!checked.ok()) return checked;
    if (expectedGeneration != queueGeneration_ || !current || candidate.items_.size() != current->items().size())
        return {std::nullopt, CustodyFileError::conflict, 0};
    const auto& rows = current->items();
    const auto found = std::find_if(rows.begin(), rows.end(), [&](const auto& row) { return row.localRecordingId == localId; });
    if (found == rows.end() || found->safeReason != "local_delete_pending" ||
        !identity(found->directoryId) || now < found->updatedAtMs)
        return {false, CustodyFileError::none, 0};
    if (serverTask ? (found->status != UploadQueueStatus::uploaded || found->meetingId != serverTask->meetingId ||
            std::string_view(found->ownerUserId) != user || std::string_view(found->ownerWorkspaceId) != workspace) :
        (found->status != UploadQueueStatus::quarantined || (userScoped ?
            std::string_view(found->ownerUserId) != user || std::string_view(found->ownerWorkspaceId) != workspace :
            hasUploadServerIdentity(*found))))
        return {false, CustodyFileError::none, 0};
    const auto index = static_cast<std::size_t>(found - rows.begin());
    {
        // The whole private candidate must still be the durable value. In
        // particular sameUploadIdentity alone omits meetingId and other rows.
        const auto durable = current->serialize(cancellation), proposed = candidate.serialize(cancellation);
        if (!durable.ok()) return {std::nullopt, durable.error, durable.nativeError};
        if (!proposed.ok()) return {std::nullopt, proposed.error, proposed.nativeError};
        if (*durable.value != *proposed.value) return {std::nullopt, CustodyFileError::conflict, 0};
    }
    std::optional<ProtectedUploadQueueValue::PurgeAcknowledgement> proof;
    if (serverTask) {
        bool recorded = false;
        for (const auto& ack : current->purgeAcknowledgements()) if (ack.taskId == serverTask->taskId) {
            if (ack.meetingId != serverTask->meetingId) return {false, CustodyFileError::none, 0};
            recorded = true;
        }
        const bool last = std::none_of(rows.begin(), rows.end(), [&](const auto& row) {
            return &row != &*found && row.meetingId == serverTask->meetingId;
        }); // Unfinished and foreign rows also block all-copies-gone proof.
        if (last && !recorded) {
            proof.emplace(); proof->taskId = serverTask->taskId; proof->meetingId = serverTask->meetingId;
            proof->acknowledgedAtMs = now;
            candidate.acknowledgements_.reserve(candidate.acknowledgements_.size() + 1);
        } // Allocate before any OS effect; the last row and proof share one commit.
    }
    const auto path = rootPath() / std::filesystem::u8path(found->directoryId.begin(), found->directoryId.end());
    const auto encoded = path.u8string();
    if (std::string_view(found->packageDirectory) != encoded) return {false, CustodyFileError::none, 0};
    for (const auto& row : rows) {
        if (&row == &*found) continue;
        std::error_code aliasError;
        const auto other = std::filesystem::weakly_canonical(
            std::filesystem::u8path(row.packageDirectory.begin(), row.packageDirectory.end()), aliasError);
        const auto otherName = std::filesystem::u8path(row.directoryId.begin(), row.directoryId.end()).native();
        const auto ownName = path.filename().native();
        // Windows names are case-insensitive; textual inequality is not proof
        // that another queue owner refers to a different physical package.
        if (aliasError || CompareStringOrdinal(other.c_str(), -1, path.c_str(), -1, TRUE) == CSTR_EQUAL ||
            CompareStringOrdinal(otherName.c_str(), -1, ownName.c_str(), -1, TRUE) == CSTR_EQUAL)
            return {false, CustodyFileError::none, 0};
    }
    const DesktopLocalPurgeService purge(rootPath());
    if (!purge.isSafePackageDirectory(path, true)) return {false, CustodyFileError::none, 0};
    if (serverTask) {
        CustodyId transaction{}; bool needsCleanup = false;
        {
            CustodyNativeJob job;
            if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
            std::optional<CustodyVector<CustodyString>> scopes;
            checked = root_->validateStoreInventory(false, cancellation, false, &scopes);
            if (!checked.ok()) return checked;
            if (scopes && std::any_of(scopes->begin(), scopes->end(), [](const auto& scope) { return scope.empty(); })) {
                // Independent fixed-role Birth/BOTH discovery, not transaction
                // from the current JSON. Retire this history lease before cleanup.
                auto opened = ProtectedCustodyFiles::openStoreObject(root_, CustodyRole::migrationIntent, false, {}, true);
                if (!opened.ok()) return {std::nullopt, opened.error, opened.nativeError};
                auto intent = std::move(*opened.value);
                CustodyMetadataIndices indices; std::array<CustodyMigrationValue, 2> values{};
                struct Wipe { std::array<CustodyMigrationValue, 2>& value; ~Wipe() { SecureZeroMemory(value.data(), sizeof(value)); } } wipe{values};
                auto read = ProtectedCustodyMigrationPair::readValues(*intent, intent->context(), std::nullopt,
                    CustodyMigrationSubject::queue, {}, cancellation, nullptr, false, indices, values);
                if (!read.ok()) return read;
                transaction = values[indices.selectedSlot].transactionId;
                needsCleanup = std::any_of(values.begin(), values.end(), [](const auto& value) {
                    return value.stage != CustodyMigrationStage::complete;
                });
            }
        } // Discovery job and history lease are gone before cleanup.
        // BOTH complete already proved absence in validate(); never replace
        // that authorization with a later package's operation or task.
        if (needsCleanup) {
            auto cleaned = cleanupMigrationOriginals({}, transaction, user, workspace,
                expectedGeneration, cancellation, serverTask, origin);
            if (!cleaned.ok()) return cleaned;
        } // No cleanup/history/member lease survives into recyclePackage.
    }
    std::error_code error;
    auto status = std::filesystem::symlink_status(path, error);
    const auto absent = [&] {
        return status.type() == std::filesystem::file_type::not_found &&
            (!error || error == std::errc::no_such_file_or_directory);
    };
    if (!absent()) {
        if (error) return {false, CustodyFileError::none, 0};
        auto opened = readPackage(found->directoryId, cancellation);
        if (!opened.ok()) return {std::nullopt, opened.error, opened.nativeError};
        auto pair = std::move(*opened.value);
        // This lease is package-state, one role below package/.custody-v1.
        if (!pair->retainedLease_ || pair->retainedLease_->packagePath().parent_path() != path)
            return {std::nullopt, CustodyFileError::identityMismatch, 0};
        auto recycled = recyclePackage(std::move(pair), cancellation);
        if (!recycled.ok() || !*recycled.value) return recycled;
    }
    status = std::filesystem::symlink_status(path, error);
    if (!absent()) return {false, CustodyFileError::none, 0};
    {
        CustodyNativeJob job;
        if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
        checked = validate(cancellation); // Continuously held root and current durable intent.
    }
    if (!checked.ok()) return checked;
    candidate.items_.erase(candidate.items_.begin() + index);
    if (proof) {
        candidate.acknowledgements_.push_back(std::move(*proof));
        if (candidate.acknowledgements_.size() > DesktopApiClient::purgeTaskListLimit)
            candidate.acknowledgements_.erase(candidate.acknowledgements_.begin());
    }
    candidate.updatedAtMs_ = now;
    return {true, CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<std::shared_ptr<const ProtectedCustodyPackagePair>> ProtectedCustodyStoreOwner::readPackage(
    std::string_view name, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Pair = std::shared_ptr<const ProtectedCustodyPackagePair>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Pair> {
        return {std::nullopt, error, native};
    };
    if (!cancellation || !identity(name)) return reject(CustodyFileError::invalidInput);
    if (failed_) return reject(CustodyFileError::recoveryRequired);
#ifndef _WIN32
    return reject(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyNativeJob job; // Covers validation/discovery before the existing pair's own job admission.
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    auto checked = validate(cancellation);
    if (!checked.ok()) return reject(checked.error, checked.nativeError);
    auto opened = ProtectedCustodyFiles::openPackageState(root_, name, cancellation);
    if (!opened.ok()) return reject(opened.error, opened.nativeError);
    const auto own = (*opened.value)->context();
    if (own.storeId != queueContext_.storeId || own.objectId == CustodyId{} || own.objectId == own.storeId ||
        own.objectId == queueContext_.objectId || own.objectId == bootstrap_->context().objectId)
        return reject(CustodyFileError::identityMismatch);
    auto held = std::shared_ptr<ProtectedCustodyFiles>(opened.value->release(),
        [](ProtectedCustodyFiles* p) { delete p; }, CustodyAllocator<ProtectedCustodyFiles>{});
    auto pair = ProtectedCustodyPackagePair::readImpl(root_->trustedRoot(), name, own, cancellation, std::move(held),
        ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly);
    if (!pair.ok()) return pair;
    auto complete = validateMigrationPackageHistory(*pair.value, cancellation);
    if (!complete.ok()) return reject(complete.error, complete.nativeError);
    return pair;
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<bool> ProtectedCustodyStoreOwner::revalidatePackage(
    std::shared_ptr<const ProtectedCustodyPackagePair> held, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!held || !root_ || !cancellation || !held->retainedLease_ || held->cancellation_.get()!=cancellation.get() ||
        held->origin_!=ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly)
        return {std::nullopt,CustodyFileError::invalidInput,0};
    if (failed_) return {std::nullopt,CustodyFileError::recoveryRequired,0};
#ifndef _WIN32
    return {std::nullopt,CustodyFileError::unsupportedPlatform,0};
#else
    {
        CustodyNativeJob job; if (!job) return {std::nullopt,CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA};
        auto checked=validate(cancellation); if (!checked.ok()) return checked;
    }
    auto checked=revalidatePackageState(held,cancellation); if (!checked.ok()) return checked;
    return validateMigrationPackageHistory(std::move(held),std::move(cancellation));
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::system_error& error) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<bool> ProtectedCustodyStoreOwner::revalidatePackageState(
    std::shared_ptr<const ProtectedCustodyPackagePair> held, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!held || !held->retainedLease_ || !cancellation || held->cancellation_.get() != cancellation.get() ||
        held->origin_ != ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (failed_) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
#ifndef _WIN32
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    const auto& files = held->retainedLease_;
    const auto& own = held->current().context;
    if (!files || files->trustedRoot() != root_->trustedRoot() || own.storeId != queueContext_.storeId)
        return {std::nullopt, CustodyFileError::identityMismatch, 0};
    const auto name = directory(held->current());
    // Re-read BOTH indices, referenced blocks and semantic payloads through the
    // SAME native lease. Never release/reopen identity or adopt a newer state.
    CustodyNativeJob job;
    if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    auto fresh = files->readValidatedMetadataPair();
    if (!fresh.ok()) return {std::nullopt, fresh.error, fresh.nativeError};
    if (held->selectedSlot() != fresh.value->selectedSlot) return {std::nullopt, CustodyFileError::conflict, 0};
    for (unsigned slot = 0; slot < 2; ++slot) {
        if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
        const auto& before = held->indices().indices[slot];
        const auto& after = fresh.value->indices[slot];
        if (before.generation != after.generation || before.logicalLength != after.logicalLength ||
            before.entries.size() != after.entries.size() ||
            !std::equal(before.entries.begin(), before.entries.end(), after.entries.begin(), [](const auto& a, const auto& b) {
                return a.version == b.version && a.envelopeBytes == b.envelopeBytes && a.flags == b.flags;
            })) return {std::nullopt, CustodyFileError::conflict, 0};
        if (!after.logicalLength || after.logicalLength > packageLimit || after.entries.size() != 1 || after.entries[0].flags != 0)
            return {std::nullopt, CustodyFileError::invalidContent, 0};
        // Reuse the retained lease, not a second pinned proof just to compare
        // local metadata. Live recording/inspection/MF readers share 32 pins.
        auto bytes = readMetadataValue(*files, own, after, cancellation);
        if (!bytes.ok()) return {std::nullopt, bytes.error, bytes.nativeError};
        auto parsed = readCustodyPackage({reinterpret_cast<const char*>(bytes.value->data()), bytes.value->size()},
            own, after.generation, name);
        if (!parsed.ok()) return {std::nullopt, codecFileError(parsed.error), parsed.nativeError};
        struct Wipe {
            CustodyPackageValue& value;
            ~Wipe() { SecureZeroMemory(&value, sizeof(value)); }
        } wipe{*parsed.value};
        // Reuse the closed canonical codec rather than comparing struct padding
        // or duplicating its fields. CustodyAllocator wipes both retiring buffers.
        auto expected = writeCustodyPackage(held->slots()[slot], own, before.generation, name);
        if (!expected.ok()) return {std::nullopt, codecFileError(expected.error), expected.nativeError};
        auto observed = writeCustodyPackage(*parsed.value, own, after.generation, name);
        if (!observed.ok()) return {std::nullopt, codecFileError(observed.error), observed.nativeError};
        if (*expected.value != *observed.value) return {std::nullopt, CustodyFileError::conflict, 0};
    }
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    return {true,CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<bool> ProtectedCustodyStoreOwner::cleanupMigrationOriginals(std::string_view name,
    const CustodyId& transaction,std::string_view user,std::string_view workspace,
    std::uint64_t expectedGeneration,std::shared_ptr<const std::atomic<bool>> cancellation,
    const BasicLocalPurgeTask<CustodyString>* serverTask,std::string_view origin) try {
    const auto reject=[](CustodyFileError error,std::uint32_t native=0)->CustodyFileResult<bool> { return {std::nullopt,error,native}; };
    if (!root_ || !cancellation || (!name.empty() && !identity(name)) ||
        !DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace) || !expectedGeneration ||
        !std::any_of(transaction.begin(),transaction.end(),[](auto b) { return b!=0; })) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)serverTask; (void)origin;
    return reject(CustodyFileError::unsupportedPlatform);
#else
    if (failed_ || shortDiscard_ || cancellation->load()) return reject(CustodyFileError::recoveryRequired);
    if (serverTask && (!name.empty() || !validLocalBufferPurgeTask(*serverTask) ||
        !DesktopUploadQueueService::validServerOrigin(origin))) return reject(CustodyFileError::invalidInput);
    std::shared_ptr<const ProtectedUploadQueueValue> current;
    {
        CustodyNativeJob job; if (!job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
        if (!name.empty()) {
            // Refuse a busy target before cold validation; release this temporary
            // lease before the unchanged full closure/authority checks below.
            auto available=ProtectedCustodyFiles::openPackageState(root_,name,cancellation);
            if (!available.ok()) return reject(available.error,available.nativeError);
        }
        auto checked=validate(cancellation,&current,true); if (!checked.ok()) return checked;
    } // Full cold closure refuses any active incompatible consumer before authorization.
    if (!current || queueGeneration_!=expectedGeneration) return reject(CustodyFileError::conflict);
    const ProtectedUploadQueueValue::Operation* purgeOperation = nullptr;
    const auto covers = [](const auto& operation, const auto& row) {
        return (operation.target == DeletionTarget::meeting && operation.targetId == row.meetingId) ||
            (operation.target == DeletionTarget::ownOrigin && operation.targetId == row.directoryId);
    };
    const auto allowed=[&](const ProtectedUploadQueueValue& value,bool historical)->bool {
        bool found=name.empty();
        for (const auto& row:value.items()) {
            if (!name.empty() && std::string_view(row.directoryId)!=name) continue;
            found=true;
            // Current login never claims an unknown historical/current owner.
            if (std::string_view(row.ownerUserId)!=user || std::string_view(row.ownerWorkspaceId)!=workspace)
                return false;
            if (serverTask) {
                if (!purgeOperation || (historical && !covers(*purgeOperation, row))) return false;
                if (!historical && (row.status == UploadQueueStatus::uploading || row.safeReason == "capture_prepared")) return false;
                if (!historical && (value.deletionBlocks(row) || row.safeReason == "local_delete_pending") &&
                    (!covers(*purgeOperation, row) || row.meetingId != serverTask->meetingId ||
                     row.status != UploadQueueStatus::uploaded || row.safeReason != "local_delete_pending")) return false;
            } else {
                if (!historical && (row.status==UploadQueueStatus::uploading || value.deletionBlocks(row) ||
                    row.safeReason=="capture_prepared" || row.safeReason=="local_delete_pending")) return false;
            }
            const auto path=std::filesystem::u8path(row.packageDirectory.begin(),row.packageDirectory.end());
            const auto expected=root_->trustedRoot()/std::filesystem::u8path(row.directoryId.begin(),row.directoryId.end());
            if (path!=expected || !AtomicFileStore::isWithinRoot(root_->trustedRoot(),path)) return false;
        }
        return found;
    };
    if (!serverTask && !allowed(*current,false)) return reject(CustodyFileError::conflict);
    std::shared_ptr<const ProtectedCustodyPackagePair> package;
    std::optional<CustodyPackageReaders> readers;
    if (!name.empty()) {
        auto opened=readPackage(name,cancellation); if (!opened.ok()) return reject(opened.error,opened.nativeError);
        package=std::move(*opened.value);
        auto openedReaders=openProtectedCustodyReaders(root_->trustedRoot(),package,cancellation);
        if (!openedReaders.ok()) return reject(openedReaders.error,openedReaders.nativeError);
        readers.emplace(std::move(*openedReaders.value));
    } // These exact readonly state/member leases survive every cleanup effect.
    const auto subject=name.empty() ? CustodyMigrationSubject::queue : CustodyMigrationSubject::package;
    auto opened=ProtectedCustodyFiles::openStoreObject(root_,CustodyRole::migrationIntent,false,name,true);
    if (!opened.ok()) return reject(opened.error,opened.nativeError);
    auto intent=std::move(*opened.value); const auto own=intent->context();
    CustodyMetadataIndices indices; std::array<CustodyMigrationValue,2> values{};
    struct Wipe { std::array<CustodyMigrationValue,2>& value; ~Wipe() { SecureZeroMemory(value.data(),sizeof(value)); } } wipe{values};
    const auto readIntent=[&]()->CustodyFileResult<bool> {
        CustodyNativeJob job; if (!job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
        return ProtectedCustodyMigrationPair::readValues(*intent,own,transaction,subject,name,cancellation,nullptr,false,indices,values);
    };
    auto checked=readIntent(); if (!checked.ok()) return checked;
    for (const auto& value:values) if (value.stage<CustodyMigrationStage::switched || !value.barrier)
        return reject(CustodyFileError::recoveryRequired);
    const auto& selected=values[indices.selectedSlot];
    CustodyBytes legacy;
    checked=intent->validateMigrationFiles(selected,values[1U-indices.selectedSlot],cancellation,false,name.empty() ? &legacy : nullptr);
    if (!checked.ok()) return checked;
    std::shared_ptr<const ProtectedUploadQueueValue> historical;
    if (name.empty()) {
        if (legacy.empty()) {
            if (!selected.authorization || selected.stage<CustodyMigrationStage::cleanupPending) return reject(CustodyFileError::recoveryRequired);
        } else {
            auto old=decodeMigrationQueue({reinterpret_cast<const char*>(legacy.data()),legacy.size()},cancellation.get());
            if (!old.ok()) return reject(old.error,old.nativeError);
            historical=std::move(*old.value);
        }
    }
    const auto validOperation = [&](const auto& operation) {
        if (!serverTask || !deletionPhaseIsAccepted(operation.phase) || operation.receiptRequestId.empty() ||
            std::string_view(operation.actorUserId) != user || std::string_view(operation.workspaceId) != workspace ||
            std::string_view(operation.serverOrigin) != origin) return false;
        // The server task is a continuation selector, never the operation ID.
        return std::any_of(current->items().begin(), current->items().end(), [&](const auto& row) {
            return row.meetingId == serverTask->meetingId && row.status == UploadQueueStatus::uploaded &&
                row.safeReason == "local_delete_pending" && std::string_view(row.ownerUserId) == user &&
                std::string_view(row.ownerWorkspaceId) == workspace && covers(operation, row);
        });
    };
    if (serverTask) {
        const auto found = std::find_if(current->deletionOperations().begin(), current->deletionOperations().end(), [&](const auto& operation) {
            if (!validOperation(operation)) return false;
            if (selected.authorization && (selected.authorization->kind != CustodyCleanupKind::deletePurge ||
                text(selected.authorization->operationId) != std::string_view(operation.operationId))) return false;
            // A partial-unlink retry has no original bytes left: only its exact
            // already durable authorization may supply the previous scope proof.
            return historical ? std::all_of(historical->items().begin(), historical->items().end(), [&](const auto& row) {
                return std::string_view(row.ownerUserId) == user && std::string_view(row.ownerWorkspaceId) == workspace && covers(operation, row);
            }) : selected.authorization.has_value();
        });
        if (found == current->deletionOperations().end()) return reject(CustodyFileError::conflict);
        purgeOperation = &*found;
        if (!allowed(*current,false)) return reject(CustodyFileError::conflict);
    }
    std::array<char,32> operation{};
    for (std::size_t i=0;i<transaction.size();++i) {
        operation[i*2]="0123456789abcdef"[transaction[i]>>4]; operation[i*2+1]="0123456789abcdef"[transaction[i]&15];
    }
    const std::string_view operationId = serverTask ? std::string_view(purgeOperation->operationId) :
        std::string_view(operation.data(),operation.size());
    const auto matches=[&](const CustodyCleanupAuthorization& a) {
        return a.kind==(serverTask ? CustodyCleanupKind::deletePurge : CustodyCleanupKind::ownerConfirmation) &&
            text(a.operationId)==operationId && text(a.actorUserId)==user && text(a.workspaceId)==workspace &&
            a.queueObjectId==queueContext_.objectId && a.queueGeneration<=expectedGeneration;
    };
    for (const auto& value:values) if (value.authorization && !matches(*value.authorization)) return reject(CustodyFileError::conflict);
    if (historical) {
        if (!allowed(*historical,true)) return reject(CustodyFileError::conflict); // ALL original ledger rows.
        for (const auto& row:historical->items()) {
            const auto now=std::find_if(current->items().begin(),current->items().end(),[&](const auto& item) {
                return row.localRecordingId==item.localRecordingId;
            });
            if (now==current->items().end()) {
                if (!serverTask) return reject(CustodyFileError::conflict);
            } else if (row.directoryId!=now->directoryId || row.sessionId!=now->sessionId || row.packageDirectory!=now->packageDirectory ||
                row.ownerUserId!=now->ownerUserId || row.ownerWorkspaceId!=now->ownerWorkspaceId ||
                (serverTask && !row.meetingId.empty() && row.meetingId!=now->meetingId)) return reject(CustodyFileError::conflict);
        }
    }
    std::optional<std::array<std::uint8_t,32>> queueHash;
    const auto fresh=[&]()->CustodyFileResult<bool> {
        if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
        {
            CustodyNativeJob job; if (!job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
            auto bootstrap=bootstrap_->readValidatedMetadataPair(); if (!bootstrap.ok()) return reject(bootstrap.error,bootstrap.nativeError);
            for (const auto& index:bootstrap.value->indices) {
                auto bytes=readMetadataValue(*bootstrap_,bootstrap_->context(),index,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
                auto value=readCustodyBootstrap({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},bootstrap_->context(),index.generation,queueContext_.objectId);
                if (!value.ok()) return reject(codecFileError(value.error),value.nativeError);
                const bool normal=value.value->mode==CustodyBootstrapMode::protectedStore;
                SecureZeroMemory(&*value.value,sizeof(CustodyBootstrapValue));
                if (!normal) return reject(CustodyFileError::recoveryRequired);
            }
            auto pair=queue_->readValidatedMetadataPair(); if (!pair.ok()) return reject(pair.error,pair.nativeError);
            if (pair.value->indices[pair.value->selectedSlot].generation!=expectedGeneration) return reject(CustodyFileError::conflict);
            for (unsigned slot=0;slot<2;++slot) {
                const auto& index=pair.value->indices[slot];
                auto bytes=readMetadataValue(*queue_,queueContext_,index,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
                auto decoded=decodeMigrationQueue({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},cancellation.get());
                if (!decoded.ok()) return reject(decoded.error,decoded.nativeError);
                if (slot!=pair.value->selectedSlot) continue;
                if (serverTask) {
                    const auto& operations=(*decoded.value)->deletionOperations();
                    const auto found=std::find_if(operations.begin(),operations.end(),[&](const auto& operation) { return std::string_view(operation.operationId)==operationId; });
                    if (found==operations.end() || !validOperation(*found) || found->target!=purgeOperation->target ||
                        found->targetId!=purgeOperation->targetId || found->receiptRequestId!=purgeOperation->receiptRequestId)
                        return reject(CustodyFileError::conflict);
                }
                if (!allowed(**decoded.value,false)) return reject(CustodyFileError::conflict);
                const auto hash=custody_detail::digest(bytes.value->data(),bytes.value->size());
                if (!hash) return reject(CustodyFileError::hashFailed);
                if (queueHash && *queueHash!=*hash) return reject(CustodyFileError::conflict);
                queueHash=*hash;
            }
        }
        if (package) {
            auto state=revalidatePackageState(package,cancellation); if (!state.ok()) return state;
            for (const auto& slots:*readers) for (const auto& reader:slots) if (reader.stream) {
                STATSTG stat{}; const auto status=reader.stream->Stat(&stat,STATFLAG_NONAME);
                if (FAILED(status)) return reject(CustodyFileError::invalidContent,static_cast<std::uint32_t>(status));
            }
        }
        return {true,CustodyFileError::none,0};
    };
    checked=fresh(); if (!checked.ok()) return checked;
    const auto save=[&](CustodyMigrationValue value)->CustodyFileResult<bool> {
        auto valid=fresh(); if (!valid.ok()) return valid;
        const auto generation=values[indices.selectedSlot].generation;
        if (generation==(std::numeric_limits<std::uint64_t>::max)()) return reject(CustodyFileError::invalidContent);
        value.generation=generation+1;
        auto bytes=writeCustodyMigration(value,own,value.generation,transaction,subject,name);
        SecureZeroMemory(&value,sizeof(value));
        if (!bytes.ok()) return reject(codecFileError(bytes.error),bytes.nativeError);
        {
            auto committed=CustodyMetadataCommit::commitImpl(root_->trustedRoot(),name,own,generation,*bytes.value,cancellation,intent.get());
            if (committed.state!=CustodyCommitState::committed) {
                failed_=true;
                return reject(committed.state==CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : committed.error,committed.nativeError);
            }
        }
        valid=readIntent(); if (!valid.ok()) { failed_=true; return valid; }
        return fresh();
    };
    if (values[indices.selectedSlot].stage==CustodyMigrationStage::switched) {
        auto next=values[indices.selectedSlot]; next.stage=CustodyMigrationStage::cleanupPending;
        next.authorization.emplace(); auto& authorization=*next.authorization;
        authorization.kind=serverTask ? CustodyCleanupKind::deletePurge : CustodyCleanupKind::ownerConfirmation;
        std::copy(operationId.begin(),operationId.end(),authorization.operationId.begin());
        std::copy(user.begin(),user.end(),authorization.actorUserId.begin());
        std::copy(workspace.begin(),workspace.end(),authorization.workspaceId.begin());
        authorization.queueObjectId=queueContext_.objectId; authorization.queueGeneration=expectedGeneration;
        checked=save(next); SecureZeroMemory(&next,sizeof(next)); if (!checked.ok()) return checked;
    }
    if (values[indices.selectedSlot].stage==CustodyMigrationStage::cleanupPending) {
        // Both physical records carry the SAME durable confirmation before any unlink.
        if (values[1U-indices.selectedSlot].stage!=CustodyMigrationStage::cleanupPending) {
            checked=save(values[indices.selectedSlot]); if (!checked.ok()) return checked;
        }
        checked=fresh(); if (!checked.ok()) return checked;
        checked=intent->validateMigrationFiles(values[indices.selectedSlot],values[1U-indices.selectedSlot],cancellation,true);
        if (!checked.ok()) { failed_=true; return checked; }
        checked=fresh(); if (!checked.ok()) { failed_=true; return checked; }
        auto next=values[indices.selectedSlot]; next.stage=CustodyMigrationStage::complete;
        checked=save(next); SecureZeroMemory(&next,sizeof(next)); if (!checked.ok()) return checked;
    }
    if (values[indices.selectedSlot].stage!=CustodyMigrationStage::complete) return reject(CustodyFileError::recoveryRequired);
    if (values[1U-indices.selectedSlot].stage!=CustodyMigrationStage::complete) {
        checked=save(values[indices.selectedSlot]); if (!checked.ok()) return checked;
    }
    checked=intent->validateMigrationFiles(values[indices.selectedSlot],values[1U-indices.selectedSlot],cancellation);
    if (!checked.ok()) { failed_=true; return checked; }
    return fresh(); // Current ledger/projection unchanged; root gate/sentinel remain.
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::filesystem::filesystem_error&) { return {std::nullopt,CustodyFileError::unsafePath,0}; }
  catch (const std::system_error& error) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<bool> ProtectedCustodyStoreOwner::validateMigrationPackageHistory(
    std::shared_ptr<const ProtectedCustodyPackagePair> held, std::shared_ptr<const std::atomic<bool>> cancellation,
    std::shared_ptr<const ProtectedCustodyMigrationPair> history) {
    if (!bootstrap_) return {std::nullopt, CustodyFileError::invalidInput, 0};
    return validateMigrationPackageHistoryImpl(root_, queueContext_, bootstrap_->context(), queueGeneration_,
        std::move(held), std::move(cancellation), std::move(history));
}

CustodyFileResult<bool> ProtectedCustodyStoreOwner::validateMigrationPackageHistoryImpl(
    const std::shared_ptr<ProtectedCustodyFiles>& root, const CustodyContext& queueContext,
    const CustodyContext& bootstrapContext, std::uint64_t queueGeneration,
    std::shared_ptr<const ProtectedCustodyPackagePair> held, std::shared_ptr<const std::atomic<bool>> cancellation,
    std::shared_ptr<const ProtectedCustodyMigrationPair> history) try {
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<bool> {
        return {std::nullopt, error, native};
    };
    if (!held || !root || !cancellation || !held->retainedLease_ || held->cancellation_.get() != cancellation.get() ||
        held->origin_ != ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly)
        return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)history; (void)queueContext; (void)bootstrapContext; (void)queueGeneration;
    return reject(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    const auto name = directory(held->current());
    const auto& identity = held->current().context;
    if (held->retainedLease_->trustedRoot() != root->trustedRoot() || identity.storeId != queueContext.storeId ||
        held->retainedLease_->packagePath().parent_path() != root->trustedRoot() / std::filesystem::u8path(name.begin(), name.end()))
        return reject(CustodyFileError::identityMismatch);
    if (!history) {
        // Structural absence of ALL fixed history surfaces preserves ordinary v5
        // behavior. A filename alone never admits a completed migration.
        std::optional<CustodyVector<CustodyString>> scopes;
        auto inventory = root->validateStoreInventory(false, cancellation, false, &scopes);
        if (!inventory.ok()) return reject(inventory.error, inventory.nativeError);
        if (!scopes || std::none_of(scopes->begin(), scopes->end(), [&](const auto& scope) { return std::string_view(scope) == name; }))
            return {true, CustodyFileError::none, 0};
        auto opened = ProtectedCustodyFiles::openStoreObject(root, CustodyRole::migrationIntent, false, name);
        if (!opened.ok()) return reject(opened.error, opened.nativeError);
        const auto context = (*opened.value)->context();
        if (context.storeId != queueContext.storeId || context.objectId == context.storeId ||
            context.objectId == queueContext.objectId || context.objectId == bootstrapContext.objectId || context.objectId == identity.objectId)
            return reject(CustodyFileError::identityMismatch);
        auto checked = ProtectedCustodyMigrationPair::readImpl(root->trustedRoot(), context, std::nullopt,
            CustodyMigrationSubject::package, name, cancellation, {}, std::move(*opened.value));
        if (!checked.ok()) return reject(checked.error, checked.nativeError);
        history = std::move(*checked.value);
    }
    const auto& current = history->current();
    if (current.subject != CustodyMigrationSubject::package || !current.directory || text(*current.directory) != name ||
        current.context.storeId != identity.storeId || !history->lease_ || history->lease_->trustedRoot() != root->trustedRoot())
        return reject(CustodyFileError::identityMismatch);
    for (const auto& record : history->slots()) {
        if (record.stage < CustodyMigrationStage::switched || !record.barrier ||
            (record.stage==CustodyMigrationStage::switched ? record.authorization.has_value() : !record.authorization))
            return reject(CustodyFileError::recoveryRequired);
        if (!record.anchor.objectId || *record.anchor.objectId != queueContext.objectId || !record.anchor.generation)
            return reject(CustodyFileError::identityMismatch);
        // Cold validate has not adopted queueGeneration yet. The caller checked
        // the actual current pair before handing over this same history proof.
        if (queueGeneration && *record.anchor.generation > queueGeneration) return reject(CustodyFileError::conflict);
        if (record.authorization && (record.authorization->queueObjectId!=queueContext.objectId ||
            (queueGeneration && record.authorization->queueGeneration>queueGeneration))) return reject(CustodyFileError::conflict);
    }
    const auto& receipt = history->current();
    constexpr std::array<CustodyRole, 6> roles{CustodyRole::queue, CustodyRole::manifest,
        CustodyRole::canonical, CustodyRole::media, CustodyRole::playback, CustodyRole::recovery};
    for (const auto& value : held->slots()) {
        if ((value.phase != CustodyPackagePhase::sealedNormal && value.phase != CustodyPackagePhase::sealedDegraded &&
             value.phase != CustodyPackagePhase::discardPending) || value.refCount != receipt.sourceCount) return reject(CustodyFileError::recoveryRequired);
        for (std::size_t i = 0; i < receipt.sourceCount; ++i) {
            const auto& source = receipt.sources[i];
            const auto role = roles[static_cast<unsigned>(source.kind)];
            const auto end = value.refs.begin() + value.refCount;
            const auto ref = std::find_if(value.refs.begin(), end, [&](const auto& item) { return item.role == role; });
            if (ref == end || !ref->sealed || ref->objectId != source.destinationObjectId ||
                ref->generation != source.destinationGeneration || ref->length != source.destinationLength ||
                ref->sha256 != source.destinationSha256 || ref->packed != source.destinationPacked ||
                ref->containerId != source.destinationContainerId || ref->committedExtent != source.destinationCommittedExtent ||
                ref->rootRef != source.destinationRootRef) return reject(CustodyFileError::invalidContent);
        }
    }
    // Do not reopen member identities here: revalidation also runs while the
    // actual inspection/playback group is alive. Cold admission retains the
    // existing whole-group closure below; consumers and recycle keep their
    // existing member/retained-root guards before any effect.
    auto files = history->lease_->validateMigrationFiles(current, history->slots()[1U-history->selectedSlot()], cancellation);
    if (!files.ok()) return reject(files.error, files.nativeError);
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return {true, CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<std::shared_ptr<ProtectedCustodyRecordingPackage>> ProtectedCustodyStoreOwner::createPackage(
    std::string_view name, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Package = std::shared_ptr<ProtectedCustodyRecordingPackage>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Package> {
        return {std::nullopt, error, native};
    };
    if (!cancellation || !identity(name)) return reject(CustodyFileError::invalidInput);
    if (failed_ || (shortDiscard_ && shortDiscard_->attempted)) return reject(CustodyFileError::recoveryRequired);
#ifndef _WIN32
    return reject(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    std::optional<CustodyNativeJob> job(std::in_place);
    if (!*job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    auto checked = validate(cancellation);
    if (!checked.ok()) return reject(checked.error, checked.nativeError);
    CustodyAllocator<ProtectedCustodyRecordingPackage> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedCustodyRecordingPackage(); }
    catch (...) { allocator.deallocate(raw, 1); throw; }
    Package package(raw, [](ProtectedCustodyRecordingPackage* p) {
        p->~ProtectedCustodyRecordingPackage(); CustodyAllocator<ProtectedCustodyRecordingPackage>{}.deallocate(p, 1);
    }, allocator);
    raw->pin_.emplace();
    if (!*raw->pin_) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    raw->root_ = root_; raw->cancellation_ = std::move(cancellation);
    raw->directoryLength_ = name.size(); std::copy(name.begin(), name.end(), raw->directory_.begin());
    failedPackage_ = package; // Preserve every partial native birth until the storage worker releases/reconciles.
    failed_ = true;
    auto directory = ProtectedCustodyFiles::openPackageRoot(raw->root_, name, raw->cancellation_, &raw->packageRoot_, CustodyFileAccess::createNew);
    if (!directory.ok()) return reject(directory.error, directory.nativeError);
    raw->packageRoot_ = std::move(*directory.value);
    auto state = ProtectedCustodyFiles::openPackageRole(raw->packageRoot_, CustodyRole::packageState, &raw->state_, CustodyFileAccess::createNew);
    if (!state.ok()) return reject(state.error, state.nativeError);
    raw->state_ = std::move(*state.value);
    raw->context_ = raw->state_->context();
    if (raw->context_.objectId == queueContext_.objectId || raw->context_.objectId == bootstrap_->context().objectId)
        return reject(CustodyFileError::identityMismatch);
    for (unsigned index = 0; index < raw->roles_.size(); ++index) {
        auto role = ProtectedCustodyFiles::openPackageRole(raw->packageRoot_, static_cast<CustodyRole>(index + 1), &raw->roles_[index], CustodyFileAccess::createNew);
        if (!role.ok()) return reject(role.error, role.nativeError);
        raw->roles_[index] = std::move(*role.value);
        raw->contexts_[index] = raw->roles_[index]->context();
        const auto id = raw->contexts_[index].objectId;
        if (id == raw->context_.objectId || id == queueContext_.objectId || id == bootstrap_->context().objectId)
            return reject(CustodyFileError::identityMismatch);
        for (unsigned previous = 0; previous < index; ++previous)
            if (id == raw->contexts_[previous].objectId) return reject(CustodyFileError::identityMismatch);
    }
    for (unsigned index = 0; index < raw->containers_.size(); ++index) {
        const auto rng = BCryptGenRandom(nullptr, raw->containers_[index].data(), 16, BCRYPT_USE_SYSTEM_PREFERRED_RNG);
        if (rng < 0) return reject(CustodyFileError::ioFailed, static_cast<std::uint32_t>(rng));
        const auto id = raw->containers_[index];
        if (id == CustodyId{} || id == raw->context_.storeId || id == raw->context_.objectId ||
            id == queueContext_.objectId || id == bootstrap_->context().objectId)
            return reject(CustodyFileError::identityMismatch);
        for (const auto& own : raw->contexts_) if (id == own.objectId) return reject(CustodyFileError::identityMismatch);
        for (unsigned previous = 0; previous < index; ++previous)
            if (id == raw->containers_[previous]) return reject(CustodyFileError::identityMismatch);
    }
    CustodyPackageValue birth;
    birth.schema = 2; birth.context = raw->context_; birth.generation = 1;
    birth.directory = raw->directory_; birth.phase = CustodyPackagePhase::capturing;
    birth.refCount = 1; birth.refs[0].role = CustodyRole::canonical;
    birth.refs[0].objectId = raw->contexts_[0].objectId;
    birth.refs[0].packed = true; birth.refs[0].containerId = raw->containers_[0];
    // Native creation is complete; commit admits its own IO and paired readback.
    // Keep all partial-birth leases, but do not charge nested jobs twice.
    job.reset();
    auto committed = raw->commit(birth); // BOTH semantic g1 ACK before any packed content birth/audio.
    if (committed.state != CustodyCommitState::committed) return reject(committed.error, committed.nativeError);
    failedPackage_.reset(); failed_ = false;
    return {std::move(package), CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<ReasonCode> ProtectedCustodyStoreOwner::recoveryReason(
    std::string_view name, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    const auto reject=[](CustodyFileError error=CustodyFileError::invalidContent,std::uint32_t native=0)->CustodyFileResult<ReasonCode> {
        return {std::nullopt,error,native};
    };
#ifndef _WIN32
    (void)name; (void)cancellation; return reject(CustodyFileError::unsupportedPlatform);
#else
    // No audio owner is opened here. All temporary readonly leases retire on
    // return, before prepareRecovery acquires fresh content ownership.
    auto pair=readPackage(name,cancellation);
    if (!pair.ok()) return reject(pair.error,pair.nativeError);
    const CustodyPackageReference* selected=nullptr;
    std::optional<CustodyId> canonicalId, containerId, manifestId;
    for (unsigned slot=0;slot<2;++slot) {
        const auto& value=(*pair.value)->slots()[slot];
        if (value.phase!=CustodyPackagePhase::capturing && value.phase!=CustodyPackagePhase::finalizing) return reject();
        bool canonical=false;
        for (std::size_t i=0;i<value.refCount;++i) {
            const auto& ref=value.refs[i];
            if (ref.role==CustodyRole::canonical && ref.packed && !ref.sealed && ref.containerId) {
                if ((canonicalId && *canonicalId!=ref.objectId) || (containerId && containerId!=ref.containerId)) return reject();
                canonicalId=ref.objectId; containerId=ref.containerId; canonical=true;
            } else if (ref.role==CustodyRole::manifest && ref.sealed && !ref.packed && ref.generation &&
                ref.length && *ref.length && *ref.length<=packageLimit && ref.sha256) {
                if (manifestId && *manifestId!=ref.objectId) return reject();
                manifestId=ref.objectId;
                if (slot==(*pair.value)->selectedSlot()) selected=&ref;
            } else return reject();
        }
        if (!canonical) return reject();
    }
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    if (!manifestId) return {ReasonCode::none,CustodyFileError::none,0};
    if (!selected) return reject();
    CustodyNativeJob job; // readPackage already retired its own admission.
    if (!job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
    const CustodyContext context{(*pair.value)->current().context.storeId,*manifestId,CustodyRole::manifest};
    auto member=ProtectedCustodyFiles::openPackageMember((*pair.value)->retainedLease_,context,cancellation);
    if (!member.ok()) return reject(member.error,member.nativeError);
    auto indices=(*member.value)->readValidatedMetadataPair();
    if (!indices.ok()) return reject(indices.error,indices.nativeError);
    if (selected->generation!=indices.value->indices[indices.value->selectedSlot].generation) return reject();
    std::array<CustodyBytes,2> bytes;
    std::array<std::array<std::uint8_t,32>,2> hashes{};
    for (unsigned slot=0;slot<2;++slot) {
        auto read=readMetadataValue(**member.value,context,indices.value->indices[slot],cancellation);
        if (!read.ok()) return reject(read.error,read.nativeError);
        auto hash=custody_detail::digest(read.value->data(),read.value->size());
        if (!hash) return reject(CustodyFileError::hashFailed);
        hashes[slot]=*hash; bytes[slot]=std::move(*read.value);
    }
    std::array<bool,2> bound{};
    for (const auto& value:(*pair.value)->slots()) for (std::size_t i=0;i<value.refCount;++i) {
        const auto& ref=value.refs[i];
        if (ref.role!=CustodyRole::manifest) continue;
        bool matched=false;
        for (unsigned slot=0;slot<2;++slot) if (ref.generation==indices.value->indices[slot].generation) {
            if (ref.length!=bytes[slot].size() || ref.sha256!=hashes[slot]) return reject();
            bound[slot]=true; matched=true;
        }
        if (!matched) return reject();
    }
    auto reason=LocalRecordingPackage::classifyRecoveryManifest(bytes,indices.value->selectedSlot,bound,name);
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    return reason;
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::system_error& e) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(e.code().value())}; }

CustodyFileResult<std::shared_ptr<ProtectedCustodyRecordingPackage>> ProtectedCustodyStoreOwner::openUnfinished(
    std::string_view name, std::shared_ptr<const std::atomic<bool>> cancellation, CustodyRecoveryLayout layout) try {
    using Package = std::shared_ptr<ProtectedCustodyRecordingPackage>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Package> {
        return {std::nullopt,error,native};
    };
    if (!cancellation || !identity(name)) return reject(CustodyFileError::invalidInput);
    if (failed_ || (shortDiscard_ && shortDiscard_->attempted)) return reject(CustodyFileError::recoveryRequired);
#ifndef _WIN32
    (void)layout;
    return reject(CustodyFileError::unsupportedPlatform);
#else
    const bool playbackStarted=layout==CustodyRecoveryLayout::playbackStarted;
    const bool terminalUnused=layout==CustodyRecoveryLayout::terminalRecoveryUnused;
    const bool completed=layout==CustodyRecoveryLayout::completed,
        wavReady=layout==CustodyRecoveryLayout::wavReady || playbackStarted;
    const bool ready=completed || terminalUnused;
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    std::optional<CustodyNativeJob> job(std::in_place);
    if (!*job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
    auto checked = validate(cancellation);
    if (!checked.ok()) return reject(checked.error,checked.nativeError);
    CustodyAllocator<ProtectedCustodyRecordingPackage> allocator;
    auto* raw = allocator.allocate(1);
    try { new(raw) ProtectedCustodyRecordingPackage(); }
    catch (...) { allocator.deallocate(raw,1); throw; }
    Package package(raw,[](ProtectedCustodyRecordingPackage* p) {
        p->~ProtectedCustodyRecordingPackage(); CustodyAllocator<ProtectedCustodyRecordingPackage>{}.deallocate(p,1);
    },allocator);
    raw->pin_.emplace();
    if (!*raw->pin_) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
    raw->root_=root_; raw->cancellation_=cancellation; raw->recoveryLayout_=layout;
    raw->directoryLength_=name.size(); std::copy(name.begin(),name.end(),raw->directory_.begin());
    auto directory=ProtectedCustodyFiles::openPackageRoot(root_,name,cancellation,&raw->packageRoot_,CustodyFileAccess::writeExisting);
    if (!directory.ok()) return reject(directory.error,directory.nativeError);
    raw->packageRoot_=std::move(*directory.value);
    auto state=ProtectedCustodyFiles::openPackageRole(raw->packageRoot_,CustodyRole::packageState,&raw->state_,CustodyFileAccess::writeExisting);
    if (!state.ok()) return reject(state.error,state.nativeError);
    raw->state_=std::move(*state.value); raw->context_=raw->state_->context();
    if (raw->context_.objectId==queueContext_.objectId || raw->context_.objectId==bootstrap_->context().objectId)
        return reject(CustodyFileError::identityMismatch);
    for (unsigned i=0;i<5;++i) {
        auto role=ProtectedCustodyFiles::openPackageRole(raw->packageRoot_,static_cast<CustodyRole>(i+1),&raw->roles_[i],
            i==0 || completed || (terminalUnused && i<4) || (wavReady && i==1) ? CustodyFileAccess::readExisting : CustodyFileAccess::writeExisting);
        if (!role.ok()) return reject(role.error,role.nativeError);
        raw->roles_[i]=std::move(*role.value); raw->contexts_[i]=raw->roles_[i]->context();
        const auto id=raw->contexts_[i].objectId;
        if (id==CustodyId{} || id==raw->context_.storeId || id==raw->context_.objectId ||
            id==queueContext_.objectId || id==bootstrap_->context().objectId) return reject(CustodyFileError::identityMismatch);
        for (unsigned previous=0;previous<i;++previous)
            if (id==raw->contexts_[previous].objectId) return reject(CustodyFileError::identityMismatch);
    }
    job.reset(); // Pair and packed readers admit their own IO.
    auto pair=raw->readPair();
    if (!pair.ok()) return reject(pair.error,pair.nativeError);
    raw->current_=(*pair.value)->current();
    if ((ready || wavReady) && raw->current_.phase!=CustodyPackagePhase::finalizing) return reject(CustodyFileError::invalidInput);
    const CustodyPackageReference* manifest=nullptr;
    bool manifestSeen=false, canonicalSeen=false;
    for (const auto& value:(*pair.value)->slots()) {
        if (value.phase!=CustodyPackagePhase::capturing && value.phase!=CustodyPackagePhase::finalizing)
            return reject(CustodyFileError::invalidInput);
        bool canonical=false;
        for (std::size_t n=0;n<value.refCount;++n) {
            const auto& ref=value.refs[n];
            const auto i=static_cast<unsigned>(ref.role)-1;
            if (i>=5 || ref.objectId!=raw->contexts_[i].objectId) return reject(CustodyFileError::identityMismatch);
            if (ref.role==CustodyRole::canonical) {
                if (!ref.packed || ref.sealed || !ref.containerId ||
                    (canonicalSeen && raw->containers_[0]!=*ref.containerId)) return reject(CustodyFileError::invalidContent);
                raw->containers_[0]=*ref.containerId; canonicalSeen=true; canonical=true;
            } else if (ref.role==CustodyRole::manifest && ref.sealed && !ref.packed) manifestSeen=true;
            else return reject(CustodyFileError::recoveryRequired); // Started outputs are NOT unused.
        }
        if (!canonical) return reject(CustodyFileError::invalidContent);
    }
    for (std::size_t n=0;n<raw->current_.refCount;++n)
        if(raw->current_.refs[n].role==CustodyRole::manifest) manifest=&raw->current_.refs[n];
    if (manifestSeen && !manifest) return reject(CustodyFileError::recoveryRequired);
    if ((ready || wavReady) && !manifest) return reject(CustodyFileError::recoveryRequired);
    {
        CustodyNativeJob inventory;
        if (!inventory) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
        for (unsigned i=(ready || wavReady) ? 0U : 1U;i<5;++i) {
            if ((i==3 && manifest) || (completed && i==4)) {
                auto metadata=raw->roles_[i]->readValidatedMetadataPair();
                if (!metadata.ok()) return reject(metadata.error,metadata.nativeError);
                const auto generation=metadata.value->indices[metadata.value->selectedSlot].generation;
                if ((i==3 && manifest->generation!=std::optional<std::uint64_t>{generation}) ||
                    (i==4 && generation!=1)) return reject(CustodyFileError::recoveryRequired);
                raw->metadataGenerations_[i]=generation;
                if (ready || wavReady) {
                    checked=raw->roles_[i]->completedPackageRole(&*metadata.value);
                    if (!checked.ok()) return reject(checked.error,checked.nativeError);
                }
            } else {
                checked=(ready && i<4) || (completed && i==4) || (wavReady && i<(playbackStarted ? 3U : 2U))
                    ? raw->roles_[i]->completedPackageRole() : raw->roles_[i]->unusedPackageRole();
                if (!checked.ok()) return reject(checked.error,checked.nativeError);
            }
        }
        if (!ready) for (unsigned i=playbackStarted ? 3U : wavReady ? 2U : 1U;i<3;++i) {
            const auto rng=BCryptGenRandom(nullptr,raw->containers_[i].data(),16,BCRYPT_USE_SYSTEM_PREFERRED_RNG);
            if (rng<0) return reject(CustodyFileError::ioFailed,static_cast<std::uint32_t>(rng));
        }
    }
    for (unsigned i=0;i<((ready || playbackStarted) ? 3U : wavReady ? 2U : 1U);++i) {
        auto packed=ProtectedPackedCustodyOwner::openImpl(root_->trustedRoot(),name,
            {raw->contexts_[i],raw->containers_[i]},playbackStarted && i==2 ? CustodyFileAccess::writeExisting : CustodyFileAccess::readExisting,
            &raw->roles_[i],nullptr,
            i ? &raw->containers_[i] : nullptr);
        if (!packed.ok()) return reject(packed.error,packed.nativeError);
        raw->packed_[i]=std::move(*packed.value);
    }
    for (unsigned i=0;i<3;++i) {
        const auto id=raw->containers_[i];
        if (id==CustodyId{} || id==raw->context_.storeId || id==raw->context_.objectId ||
            id==queueContext_.objectId || id==bootstrap_->context().objectId) return reject(CustodyFileError::identityMismatch);
        for (const auto& own:raw->contexts_) if (id==own.objectId) return reject(CustodyFileError::identityMismatch);
        for (unsigned previous=0;previous<i;++previous)
            if (id==raw->containers_[previous]) return reject(CustodyFileError::identityMismatch);
    }
    for (const auto& value:(*pair.value)->slots()) {
        checked=raw->validateRefs(value);
        if (!checked.ok()) return reject(checked.error,checked.nativeError);
    }
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    return {std::move(package),CustodyFileError::none,0}; // No content or metadata has been changed.
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::system_error& e) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(e.code().value())}; }

CustodyFileResult<std::array<CustodyBytes,2>> ProtectedCustodyRecordingPackage::completedMetadata(
    CustodyRole role, CustodyPackageReference& reference, unsigned& selectedSlot) try {
#ifndef _WIN32
    (void)role; (void)reference; (void)selectedSlot; return {std::nullopt,CustodyFileError::unsupportedPlatform,0};
#else
    if ((recoveryLayout_!=CustodyRecoveryLayout::completed && recoveryLayout_!=CustodyRecoveryLayout::terminalRecoveryUnused) ||
        failed_ || current_.phase!=CustodyPackagePhase::finalizing ||
        (role!=CustodyRole::manifest && role!=CustodyRole::recovery)) return {std::nullopt,CustodyFileError::invalidInput,0};
    CustodyNativeJob job;
    if (!job) return {std::nullopt,CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA};
    const auto i=static_cast<unsigned>(role)-1;
    auto pair=roles_[i]->readValidatedMetadataPair();
    if (!pair.ok()) return {std::nullopt,pair.error,pair.nativeError};
    auto inventory=roles_[i]->completedPackageRole(&*pair.value);
    if (!inventory.ok()) return {std::nullopt,inventory.error,inventory.nativeError};
    const auto& selected=pair.value->indices[pair.value->selectedSlot];
    if (selected.generation!=metadataGenerations_[i] || (role==CustodyRole::recovery && selected.generation!=1))
        return {std::nullopt,CustodyFileError::recoveryRequired,0};
    std::array<CustodyBytes,2> bytes;
    for (unsigned slot=0;slot<2;++slot) {
        auto read=readMetadataValue(*roles_[i],contexts_[i],pair.value->indices[slot],cancellation_);
        if (!read.ok()) return {std::nullopt,read.error,read.nativeError};
        bytes[slot]=std::move(*read.value);
    }
    auto hash=custody_detail::digest(bytes[pair.value->selectedSlot].data(),bytes[pair.value->selectedSlot].size());
    if (!hash) return {std::nullopt,CustodyFileError::hashFailed,0};
    reference={}; reference.role=role; reference.objectId=contexts_[i].objectId; reference.sealed=true;
    reference.generation=selected.generation; reference.length=selected.logicalLength; reference.sha256=*hash;
    selectedSlot=pair.value->selectedSlot;
    return {std::move(bytes),CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }

CustodyFileResult<CustodyPackageReference> ProtectedCustodyRecordingPackage::reference(CustodyRole role) const {
    const auto index = static_cast<unsigned>(role);
    if (!index || index > contexts_.size()) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (failed_) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
    CustodyPackageReference value;
    value.role = role; value.objectId = contexts_[index - 1].objectId;
    value.packed = index <= packed_.size();
    if (value.packed) value.containerId = containers_[index - 1];
    return {value, CustodyFileError::none, 0}; // Identity only, not a sealed ref/stamp or effect capability.
}

CustodyFileResult<std::shared_ptr<ProtectedCustodyWriter>> ProtectedCustodyRecordingPackage::createWriter(CustodyRole role) try {
    const auto index = static_cast<unsigned>(role);
    if (!index || index > packed_.size()) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (failed_ || !current_.generation) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
    if (current_.phase != CustodyPackagePhase::capturing && current_.phase != CustodyPackagePhase::finalizing)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (packed_[index - 1] || !roles_[index - 1]) return {std::nullopt, CustodyFileError::conflict, 0};
#ifndef _WIN32
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    using Writer = std::shared_ptr<ProtectedCustodyWriter>;
    if (cancellation_->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    CustodyNativeJob job;
    if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    failed_ = true; // Any partial role/content factory stays closed, never retries CREATE_NEW.
    auto owner = ProtectedPackedCustodyOwner::openImpl(root_->trustedRoot(), directory(),
        {contexts_[index - 1], containers_[index - 1]}, CustodyFileAccess::createNew,
        &roles_[index - 1], &packed_[index - 1]);
    if (!owner.ok()) return {std::nullopt, owner.error, owner.nativeError};
    packed_[index - 1] = std::move(*owner.value);
    auto proof = ProtectedPackedCustodyTree::verify(packed_[index - 1]);
    if (!proof.ok()) return {std::nullopt, proof.error, proof.nativeError};
    auto writer = ProtectedCustodyWriter::open(std::move(*proof.value), cancellation_);
    if (!writer.ok()) return {std::nullopt, writer.error, writer.nativeError};
    Writer result(writer.value->release(), [](ProtectedCustodyWriter* p) { delete p; }, CustodyAllocator<ProtectedCustodyWriter>{});
    if (cancellation_->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    failed_ = false;
    return {std::move(result), CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { failed_ = true; return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { failed_ = true; return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<std::shared_ptr<const ProtectedCustodyPackagePair>> ProtectedCustodyRecordingPackage::readPair() {
    if (failed_ || !state_) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
#ifndef _WIN32
    return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    return ProtectedCustodyPackagePair::readImpl(root_->trustedRoot(), directory(), context_, cancellation_,
        std::shared_ptr<ProtectedCustodyFiles>(shared_from_this(), state_.get()), ProtectedCustodyPackagePair::LeaseOrigin::borrowedWriter);
#endif
}

CustodyMetadataCommit ProtectedCustodyRecordingPackage::commitMetadata(CustodyRole role, const CustodyBytes& bytes) {
    CustodyMetadataCommit rejected;
    rejected.error = CustodyFileError::invalidInput;
    if (role != CustodyRole::manifest && role != CustodyRole::recovery) return rejected;
    const auto index = static_cast<unsigned>(role) - 1;
    rejected.context = contexts_[index]; rejected.baseGeneration = metadataGenerations_[index];
    if (failed_) { rejected.error = CustodyFileError::recoveryRequired; return rejected; }
    const bool capturing = current_.phase == CustodyPackagePhase::capturing;
    if ((!capturing && current_.phase != CustodyPackagePhase::finalizing) ||
        (capturing && role != CustodyRole::manifest) || bytes.empty() || bytes.size() > packageLimit) return rejected;
    const auto end = current_.refs.begin() + current_.refCount;
    const auto previous = std::find_if(current_.refs.begin(), end, [&](const auto& ref) { return ref.role == role; });
    const bool bindManifest = role == CustodyRole::manifest && (capturing || previous != end);
    if (bindManifest && ((previous != end && (!previous->sealed || previous->generation != metadataGenerations_[index])) ||
        (previous == end && metadataGenerations_[index]) ||
        metadataGenerations_[index] == (std::numeric_limits<std::uint64_t>::max)() ||
        current_.generation > (std::numeric_limits<std::uint64_t>::max)() - (previous != end ? 2 : 1))) return rejected;
#ifndef _WIN32
    rejected.error = CustodyFileError::unsupportedPlatform; return rejected;
#else
    bool attempted = false;
    try {
        auto held = shared_from_this();
        rejected.package_ = held; // Exception/ambiguous results retain the SAME native ownership too.
        std::optional<std::array<std::uint8_t, 32>> hash;
        if (bindManifest) {
            hash = custody_detail::digest(bytes.data(), bytes.size());
            if (!hash) { rejected.error = CustodyFileError::hashFailed; return rejected; }
            if (previous != end) {
                // Retire the older package ref BEFORE its metadata index is
                // reused. Both package slots then retain the current manifest.
                auto retained = current_; ++retained.generation;
                const auto saved = commitImpl(retained, true);
                if (saved.state != CustodyCommitState::committed) {
                    rejected.state = saved.state; rejected.error = saved.error;
                    rejected.nativeError = saved.nativeError; return rejected;
                }
            }
        }
        std::optional<CustodyNativeJob> job(std::in_place);
        if (!*job) { rejected.error = CustodyFileError::allocationFailed; return rejected; }
        attempted = true;
        auto result = CustodyMetadataCommit::commitImpl(root_->trustedRoot(), directory(), contexts_[index],
            metadataGenerations_[index], bytes, cancellation_, roles_[index].get());
        result.package_ = std::move(held);
        if (result.state != CustodyCommitState::committed) { failed_ = true; return result; }
        metadataGenerations_[index] = result.targetGeneration;
        job.reset(); // Package publication admits its own IO; no nested job charge.
        if (bindManifest) {
            auto value = current_; ++value.generation;
            std::size_t slot = 0;
            while (slot != value.refCount && value.refs[slot].role != role) ++slot;
            if (slot == value.refCount) ++value.refCount;
            CustodyPackageReference reference;
            reference.role = role; reference.objectId = contexts_[index].objectId; reference.sealed = true;
            reference.generation = result.targetGeneration; reference.length = bytes.size(); reference.sha256 = *hash;
            value.refs[slot] = reference;
            const auto published = commitImpl(value, true);
            if (published.state != CustodyCommitState::committed) {
                // Metadata changed, but the package ACK is not proven. Keep
                // the prior manifest and owner; no retry/effects on this lease.
                failed_ = true; result.state = CustodyCommitState::ambiguous;
                result.snapshot.reset(); result.error = published.error; result.nativeError = published.nativeError;
            }
        }
        return result;
    } catch (const std::bad_alloc&) {
        failed_ = true; rejected.error = CustodyFileError::allocationFailed;
        if (attempted) rejected.state = CustodyCommitState::ambiguous;
        return rejected;
    } catch (const std::system_error& error) {
        failed_ = true; rejected.error = CustodyFileError::ioFailed;
        rejected.nativeError = static_cast<std::uint32_t>(error.code().value());
        if (attempted) rejected.state = CustodyCommitState::ambiguous;
        return rejected;
    }
#endif
}

CustodyFileResult<bool> ProtectedCustodyRecordingPackage::validateRefs(const CustodyPackageValue& value) {
#ifndef _WIN32
    (void)value; return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    for (std::size_t i = 0; i < value.refCount; ++i) {
        if (cancellation_->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
        const auto& ref = value.refs[i];
        const auto index = static_cast<unsigned>(ref.role) - 1;
        if (index >= contexts_.size() || ref.objectId != contexts_[index].objectId || ref.packed != (index < packed_.size()))
            return {std::nullopt, CustodyFileError::identityMismatch, 0};
        if (ref.packed && ref.containerId != std::optional<CustodyId>{containers_[index]})
            return {std::nullopt, CustodyFileError::identityMismatch, 0};
        if (!ref.sealed) continue; // Capturing birth has reserved IDs, not fabricated empty roots.
        if (ref.packed) {
            if (!packed_[index]) return {std::nullopt, CustodyFileError::invalidContent, 0};
            const auto root = ProtectedPackedCustodyFormat::decodeReference(ref.rootRef->data(), ref.rootRef->size(),
                {*ref.length ? PackedRecordKind::nodeL2 : PackedRecordKind::empty, 0,
                    *ref.generation, *ref.committedExtent, *ref.committedExtent});
            if (!root) return {std::nullopt, CustodyFileError::invalidContent, 0};
            const PackedRootDescriptor stamp{*ref.generation, *ref.length, *ref.committedExtent,
                static_cast<std::uint32_t>((*ref.length + ProtectedCustodyCodec::blockBytes - 1) / ProtectedCustodyCodec::blockBytes), *root};
            auto proof = ProtectedPackedCustodyTree::verifyRetained(packed_[index], {contexts_[index], containers_[index]}, stamp);
            if (!proof.ok()) return {std::nullopt, proof.error, proof.nativeError};
            auto reader = openProtectedCustodyReader(std::move(*proof.value), cancellation_);
            if (!reader.ok()) return {std::nullopt, reader.error, reader.nativeError};
            auto hash = sha256ProtectedStream(reader.value->stream.Get(), *ref.length, cancellation_);
            if (!hash.ok()) return {std::nullopt, hash.error, hash.nativeError};
            if (*hash.value != *ref.sha256) return {std::nullopt, CustodyFileError::invalidContent, 0};
        } else {
            CustodyNativeJob job; // Flat metadata IO has no packed Guard.
            if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
            auto pair = roles_[index]->readValidatedMetadataPair();
            if (!pair.ok()) return {std::nullopt, pair.error, pair.nativeError};
            bool matched = false;
            for (const auto& entry : pair.value->indices) {
                auto bytes = readMetadataValue(*roles_[index], contexts_[index], entry, cancellation_);
                if (!bytes.ok()) return {std::nullopt, bytes.error, bytes.nativeError};
                if (entry.generation != *ref.generation) continue;
                auto hash = custody_detail::digest(bytes.value->data(), bytes.value->size());
                if (!hash) return {std::nullopt, CustodyFileError::hashFailed, 0};
                if (entry.logicalLength != *ref.length || *hash != *ref.sha256)
                    return {std::nullopt, CustodyFileError::invalidContent, 0};
                matched = true;
            }
            if (!matched) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
        }
    }
    return {true, CustodyFileError::none, 0};
#endif
}

CustodyMetadataCommit ProtectedCustodyRecordingPackage::commit(const CustodyPackageValue& value) {
    return commitImpl(value, false);
}

CustodyMetadataCommit ProtectedCustodyRecordingPackage::commitImpl(const CustodyPackageValue& value, bool metadataCheckpoint) {
    CustodyMetadataCommit rejected;
    rejected.context = context_; rejected.baseGeneration = current_.generation;
    rejected.error = CustodyFileError::invalidInput;
    if (failed_ || !state_) { rejected.error = CustodyFileError::recoveryRequired; return rejected; }
    if (current_.generation == (std::numeric_limits<std::uint64_t>::max)() || value.generation != current_.generation + 1 ||
        value.schema != 2 || !packageShape(value, context_, value.generation, directory())) return rejected;
    const bool transition = !current_.generation ? value.phase == CustodyPackagePhase::capturing :
        current_.phase == CustodyPackagePhase::capturing ? value.phase == CustodyPackagePhase::finalizing ||
            (metadataCheckpoint && value.phase == CustodyPackagePhase::capturing) :
        current_.phase == CustodyPackagePhase::finalizing ? value.phase != CustodyPackagePhase::capturing :
        value.phase == current_.phase && value.reason == current_.reason && value.shortRecordingDiscarded == current_.shortRecordingDiscarded;
    if (!transition) { rejected.error = CustodyFileError::conflict; return rejected; }
#ifndef _WIN32
    rejected.error = CustodyFileError::unsupportedPlatform; return rejected;
#else
    bool attempted = false;
    try {
        auto held = shared_from_this();
        rejected.package_ = held;
        auto refs = validateRefs(value);
        if (!refs.ok()) { rejected.error = refs.error; rejected.nativeError = refs.nativeError; return rejected; }
        if (current_.generation) {
            auto pair = readPair();
            if (!pair.ok()) { failed_ = true; rejected.error = pair.error; rejected.nativeError = pair.nativeError; return rejected; }
            if ((*pair.value)->current().generation != current_.generation) { failed_ = true; rejected.error = CustodyFileError::conflict; return rejected; }
            if (metadataCheckpoint) for (const auto& existing : (*pair.value)->slots()) {
                auto valid = validateRefs(existing);
                if (!valid.ok()) {
                    failed_ = true; rejected.error = valid.error; rejected.nativeError = valid.nativeError; return rejected;
                }
            }
        }
        // Reads and member hashes admit their own jobs. Reserve only the
        // subsequent metadata publication and physical paired readback.
        CustodyNativeJob job;
        if (!job) { rejected.error = CustodyFileError::allocationFailed; return rejected; }
        auto bytes = writeCustodyPackage(value, context_, value.generation, directory());
        if (!bytes.ok()) { rejected.error = codecFileError(bytes.error); rejected.nativeError = bytes.nativeError; return rejected; }
        attempted = true;
        auto result = CustodyMetadataCommit::commitImpl(root_->trustedRoot(), directory(), context_, current_.generation,
            *bytes.value, cancellation_, state_.get());
        result.package_ = std::move(held);
        if (result.state != CustodyCommitState::committed) { failed_ = true; return result; }
        // Postpublication must finish BOTH semantic readback even if UI cancelled.
        auto finish = std::allocate_shared<std::atomic<bool>>(CustodyAllocator<std::atomic<bool>>{}, false);
        auto pair = ProtectedCustodyPackagePair::readImpl(root_->trustedRoot(), directory(), context_, finish,
            std::shared_ptr<ProtectedCustodyFiles>(shared_from_this(), state_.get()), ProtectedCustodyPackagePair::LeaseOrigin::borrowedWriter);
        if (!pair.ok() || (*pair.value)->current().generation != value.generation) {
            failed_ = true; result.state = CustodyCommitState::ambiguous;
            result.error = pair.ok() ? CustodyFileError::conflict : pair.error;
            result.nativeError = pair.nativeError; return result;
        }
        current_ = (*pair.value)->current();
        return result;
    } catch (const std::bad_alloc&) {
        failed_ = attempted; rejected.error = CustodyFileError::allocationFailed;
        if (attempted) rejected.state = CustodyCommitState::ambiguous;
        return rejected;
    } catch (const std::system_error& error) {
        failed_ = attempted; rejected.error = CustodyFileError::ioFailed; rejected.nativeError = static_cast<std::uint32_t>(error.code().value());
        if (attempted) rejected.state = CustodyCommitState::ambiguous;
        return rejected;
    }
#endif
}

ProtectedCustodyQueueMigration::~ProtectedCustodyQueueMigration() {
#ifdef _WIN32
    SecureZeroMemory(values_.data(), sizeof(values_));
#endif
}

CustodyFileResult<std::shared_ptr<const ProtectedUploadQueueValue>> ProtectedCustodyStoreOwner::decodeMigrationQueue(
    std::string_view bytes, const std::atomic<bool>* cancellation) {
    return ProtectedUploadQueueValue::decode(bytes,cancellation);
}

CustodyFileResult<std::shared_ptr<ProtectedCustodyQueueMigration>> ProtectedCustodyQueueMigration::prepare(
    const std::filesystem::path& path, std::shared_ptr<const std::atomic<bool>> cancellation) {
    return openImpl(path,std::move(cancellation),false);
}
CustodyFileResult<std::shared_ptr<ProtectedCustodyQueueMigration>> ProtectedCustodyQueueMigration::openImpl(
    const std::filesystem::path& path, std::shared_ptr<const std::atomic<bool>> cancellation, bool copyAndSwitch) try {
    using Owner = std::shared_ptr<ProtectedCustodyQueueMigration>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Owner> {
        return {std::nullopt, error, native};
    };
    if (!cancellation) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)path; (void)copyAndSwitch; return reject(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyNativeJob job;
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyPin pin;
    if (!pin) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyAllocator<ProtectedCustodyQueueMigration> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedCustodyQueueMigration(); }
    catch (...) { allocator.deallocate(raw,1); throw; }
    Owner owner(raw, [](ProtectedCustodyQueueMigration* p) {
        p->~ProtectedCustodyQueueMigration(); CustodyAllocator<ProtectedCustodyQueueMigration>{}.deallocate(p,1);
    }, allocator);
    owner->pin_.emplace(std::move(pin)); owner->cancellation_ = cancellation;
    unsigned roles = 0; bool envelopes = false;
    auto locked = ProtectedCustodyFiles::lockQueueMigrationRoot(path, cancellation, owner->source_, roles, envelopes);
    if (!locked.ok()) return reject(locked.error, locked.nativeError);
    owner->root_ = std::shared_ptr<ProtectedCustodyFiles>(locked.value->release(),
        [](ProtectedCustodyFiles* p) { delete p; }, CustodyAllocator<ProtectedCustodyFiles>{});
    const auto openRole = [&](CustodyRole role, unsigned bit) {
        return ProtectedCustodyFiles::openStoreObject(owner->root_, role, !(roles & bit), {}, true);
    };
    auto queue = openRole(CustodyRole::queue,1); if (!queue.ok()) return reject(queue.error,queue.nativeError);
    owner->queue_ = std::move(*queue.value);
    auto intent = openRole(CustodyRole::migrationIntent,2); if (!intent.ok()) return reject(intent.error,intent.nativeError);
    owner->intent_ = std::move(*intent.value);
    const auto own = owner->intent_->context(), queueContext = owner->queue_->context();
    if (own.storeId != queueContext.storeId || own.objectId == own.storeId || own.objectId == queueContext.objectId ||
        queueContext.objectId == queueContext.storeId) return reject(CustodyFileError::identityMismatch);
    // Existing identities are checked before the first intent publication.
    if (roles & 4) {
        auto bootstrap = openRole(CustodyRole::bootstrap,4);
        if (!bootstrap.ok()) return reject(bootstrap.error,bootstrap.nativeError);
        owner->bootstrap_ = std::move(*bootstrap.value);
        const auto context = owner->bootstrap_->context();
        if (context.storeId != own.storeId || context.objectId == context.storeId ||
            context.objectId == own.objectId || context.objectId == queueContext.objectId)
            return reject(CustodyFileError::identityMismatch);
    }
    const auto sourceHash = custody_detail::digest(owner->source_.data(), owner->source_.size());
    if (!sourceHash) return reject(CustodyFileError::hashFailed);
    const auto revalidateSource = [&]() -> CustodyFileResult<bool> {
        auto bytes = owner->root_->readMigrationQueue();
        if (!bytes.ok()) return {std::nullopt,bytes.error,bytes.nativeError};
        if (*bytes.value != owner->source_) return {std::nullopt,CustodyFileError::conflict,0};
        return {true,CustodyFileError::none,0};
    };
    const auto readIntent = [&](std::optional<CustodyId> transaction) {
        return ProtectedCustodyMigrationPair::readValues(*owner->intent_, own, transaction,
            CustodyMigrationSubject::queue, {}, cancellation, nullptr, true, owner->indices_, owner->values_);
    };
    const auto saveIntent = [&](const CustodyMigrationValue& value) -> CustodyFileResult<bool> {
        auto checked = revalidateSource(); if (!checked.ok()) return checked;
        auto bytes = writeCustodyMigration(value, own, value.generation, value.transactionId, CustodyMigrationSubject::queue, {});
        if (!bytes.ok()) return {std::nullopt,codecFileError(bytes.error),bytes.nativeError};
        auto committed = CustodyMetadataCommit::commitImpl(path, {}, own, value.generation - 1, *bytes.value, cancellation, owner->intent_.get());
        if (committed.state != CustodyCommitState::committed) return {std::nullopt,
            committed.state == CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : committed.error,committed.nativeError};
        return readIntent(value.transactionId); // BOTH semantic ACK on the same writable owner.
    };
    const auto unused = owner->intent_->unusedPackageRole();
    if (unused.ok()) {
        if (envelopes) return reject(CustodyFileError::recoveryRequired); // No intent birth over a bootstrap/partial envelope.
        CustodyMigrationValue value; value.context = own; value.generation = 1;
        value.subject = CustodyMigrationSubject::queue; value.stage = CustodyMigrationStage::prepared;
        const auto rng = BCryptGenRandom(nullptr,value.transactionId.data(),16,BCRYPT_USE_SYSTEM_PREFERRED_RNG);
        if (rng < 0) return reject(CustodyFileError::ioFailed,static_cast<std::uint32_t>(rng));
        value.anchor.length = owner->source_.size(); value.anchor.sha256 = *sourceHash;
        value.sourceCount = 1; value.sources[0].kind = CustodyMigrationSourceKind::ledger;
        value.sources[0].length = value.anchor.length; value.sources[0].sha256 = *sourceHash;
        value.sources[0].destinationObjectId = queueContext.objectId;
        auto saved = saveIntent(value); SecureZeroMemory(&value,sizeof(value));
        if (!saved.ok()) return reject(saved.error,saved.nativeError);
    } else {
        auto read = readIntent(std::nullopt); if (!read.ok()) return reject(read.error,read.nativeError);
    }
    for (const auto& value : owner->values_) {
        if ((!copyAndSwitch && value.stage != CustodyMigrationStage::prepared) || value.stage > CustodyMigrationStage::switched ||
            value.authorization || value.anchor.objectId || value.anchor.generation ||
            value.anchor.length != owner->source_.size() || value.anchor.sha256 != *sourceHash ||
            value.sourceCount != 1 || value.sources[0].destinationObjectId != queueContext.objectId ||
            value.sources[0].length != owner->source_.size() || value.sources[0].sha256 != *sourceHash)
            return reject(CustodyFileError::conflict);
    }
    if (owner->current().stage>CustodyMigrationStage::prepared && !owner->bootstrap_) return reject(CustodyFileError::recoveryRequired);
    bool packageFence=false;
    std::optional<CustodyBootstrapValue> pendingPackage;
    const auto validateFence = [&]() -> CustodyFileResult<bool> {
        if (!owner->bootstrap_ || !owner->current().barrier) return {std::nullopt,CustodyFileError::recoveryRequired,0};
        const auto context = owner->bootstrap_->context();
    auto pair = owner->bootstrap_->readValidatedMetadataPair(); if (!pair.ok()) return {std::nullopt,pair.error,pair.nativeError};
    std::array<CustodyBootstrapMode,2> modes{};
    for (unsigned slot = 0; slot < 2; ++slot) {
        const auto& index = pair.value->indices[slot];
        auto bytes = readMetadataValue(*owner->bootstrap_,context,index,cancellation);
        if (!bytes.ok()) return {std::nullopt,bytes.error,bytes.nativeError};
        auto value = readCustodyBootstrap({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},context,index.generation,queueContext.objectId);
        if (!value.ok()) return {std::nullopt,codecFileError(value.error),value.nativeError};
        bool deferred=false;
        if (copyAndSwitch && owner->current().stage==CustodyMigrationStage::switched &&
            owner->values_[1U-owner->indices_.selectedSlot].stage==CustodyMigrationStage::switched &&
            value.value->mode==CustodyBootstrapMode::migrating && value.value->subject==CustodyMigrationSubject::package && value.value->directory) {
            if (pendingPackage && (pendingPackage->directory!=value.value->directory || pendingPackage->transactionId!=value.value->transactionId))
                return {std::nullopt,CustodyFileError::conflict,0};
            pendingPackage=*value.value; packageFence=true; deferred=true;
        }
        const bool matches = deferred || (value.value->mode == CustodyBootstrapMode::migrating &&
            value.value->transactionId == owner->current().transactionId && value.value->subject == CustodyMigrationSubject::queue && !value.value->directory) ||
            (copyAndSwitch && owner->current().stage >= CustodyMigrationStage::copiedVerified &&
             value.value->mode == CustodyBootstrapMode::protectedStore);
        modes[slot] = value.value->mode;
        SecureZeroMemory(&*value.value,sizeof(CustodyBootstrapValue));
        if (!matches) return {std::nullopt,CustodyFileError::conflict,0};
    }
    if (!packageFence && modes[pair.value->selectedSlot] == CustodyBootstrapMode::migrating &&
        modes[1U - pair.value->selectedSlot] != CustodyBootstrapMode::migrating)
        return {std::nullopt,CustodyFileError::conflict,0};
        return {true,CustodyFileError::none,0};
    };
    // A singleton/invalid bootstrap is never followed by a repair/prepared write.
    if (owner->bootstrap_ && !owner->bootstrap_->unusedPackageRole().ok()) {
        auto valid = validateFence(); if (!valid.ok()) return reject(valid.error,valid.nativeError);
    }
    // Even a known native intent does not authorize an arbitrary existing quarantine.
    auto gatePresent = owner->root_->migrationQueueGatePresent();
    if (!gatePresent.ok()) return reject(gatePresent.error,gatePresent.nativeError);
    if (*gatePresent.value && !owner->current().barrier) return reject(CustodyFileError::recoveryRequired);
    if (owner->current().barrier) {
        const auto& ref = *owner->current().barrier;
        auto birth = owner->intent_->readMigrationBirthEnvelope(ref.blockVersion,static_cast<std::uint32_t>(ref.envelopeBytes));
        if (!birth.ok()) return reject(birth.error,birth.nativeError);
        auto copies = owner->root_->installQueueMigrationBarriers(owner->current(),*birth.value,cancellation,false);
        if (!copies.ok()) return reject(copies.error,copies.nativeError);
    }
    if (!owner->current().barrier) {
        const auto& index = owner->indices_.indices[owner->indices_.selectedSlot];
        if (index.generation != 1) return reject(CustodyFileError::recoveryRequired);
        const auto& entry = index.entries[0];
        auto envelope = owner->intent_->readMigrationBirthEnvelope(entry.version,entry.envelopeBytes);
        if (!envelope.ok()) return reject(envelope.error,envelope.nativeError);
        const auto cipherHash = custody_detail::digest(envelope.value->data(),envelope.value->size());
        if (!cipherHash) return reject(CustodyFileError::hashFailed);
        auto next = owner->current(); ++next.generation;
        next.barrier = CustodyMigrationBarrier{own.objectId,1,entry.version,envelope.value->size(),*cipherHash};
        auto saved = saveIntent(next); SecureZeroMemory(&next,sizeof(next));
        if (!saved.ok()) return reject(saved.error,saved.nativeError);
    }
    auto checked = revalidateSource(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
    // Initial closing fence follows the durable prepared/Birth reference and
    // reserved queue identity. No queue indices or destination content exist.
    if (!owner->bootstrap_) {
        auto bootstrap = openRole(CustodyRole::bootstrap,4);
        if (!bootstrap.ok()) return reject(bootstrap.error,bootstrap.nativeError);
        owner->bootstrap_ = std::move(*bootstrap.value);
    }
    const auto context = owner->bootstrap_->context();
    if (context.storeId != own.storeId || context.objectId == context.storeId || context.objectId == own.objectId ||
        context.objectId == queueContext.objectId) return reject(CustodyFileError::identityMismatch);
    if (owner->bootstrap_->unusedPackageRole().ok()) {
        CustodyBootstrapValue fence; fence.context = context; fence.generation = 1;
        fence.queueObjectId = queueContext.objectId; fence.mode = CustodyBootstrapMode::migrating;
        fence.transactionId = owner->current().transactionId; fence.subject = CustodyMigrationSubject::queue;
        auto bytes = writeCustodyBootstrap(fence,context,1,queueContext.objectId); SecureZeroMemory(&fence,sizeof(fence));
        if (!bytes.ok()) return reject(codecFileError(bytes.error),bytes.nativeError);
        auto committed = CustodyMetadataCommit::commitImpl(path,{},context,0,*bytes.value,cancellation,owner->bootstrap_.get());
        if (committed.state != CustodyCommitState::committed) return reject(
            committed.state == CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : committed.error,committed.nativeError);
    }
    checked = validateFence(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
    checked = revalidateSource(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
    if (!copyAndSwitch) return {std::move(owner),CustodyFileError::none,0};
    const auto& ref = *owner->current().barrier;
    auto birth = owner->intent_->readMigrationBirthEnvelope(ref.blockVersion,static_cast<std::uint32_t>(ref.envelopeBytes));
    if (!birth.ok()) return reject(birth.error,birth.nativeError);
    // Existing fixed copies are authenticated before any destination/intent write.
    checked = owner->root_->installQueueMigrationBarriers(owner->current(),*birth.value,cancellation,false);
    if (!checked.ok()) return reject(checked.error,checked.nativeError);
    // An interrupted metadata birth with one slot is retained, never completed.
    if (owner->queue_->unusedPackageRole().ok()) {
        if (owner->current().stage != CustodyMigrationStage::prepared) return reject(CustodyFileError::recoveryRequired);
        checked = revalidateSource(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
        auto copied = CustodyMetadataCommit::commitImpl(path,{},queueContext,0,owner->source_,cancellation,owner->queue_.get());
        if (copied.state != CustodyCommitState::committed) return reject(
            copied.state == CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : copied.error,copied.nativeError);
    }
    auto destination = owner->queue_->readValidatedMetadataPair();
    if (!destination.ok()) return reject(destination.error,destination.nativeError);
    const auto copiedGeneration = destination.value->indices[destination.value->selectedSlot].generation;
    for (const auto& index : destination.value->indices) {
        auto bytes = readMetadataValue(*owner->queue_,queueContext,index,cancellation);
        if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
        if (owner->current().stage < CustodyMigrationStage::switched) {
            if (index.generation != 1 || *bytes.value != owner->source_) return reject(CustodyFileError::conflict);
        } else {
            // Posthandoff queue legitimately evolves; only the original receipt is immutable.
            auto decoded = ProtectedCustodyStoreOwner::decodeMigrationQueue({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},cancellation.get());
            if (!decoded.ok()) return reject(decoded.error,decoded.nativeError);
        }
    }
    if (owner->current().stage == CustodyMigrationStage::prepared) {
        auto next = owner->current(); ++next.generation; next.stage = CustodyMigrationStage::copiedVerified;
        auto& source = next.sources[0]; source.destinationGeneration = copiedGeneration;
        source.destinationLength = source.length; source.destinationSha256 = source.sha256;
        auto saved = saveIntent(next); SecureZeroMemory(&next,sizeof(next));
        if (!saved.ok()) return reject(saved.error,saved.nativeError);
    }
    if (owner->current().sources[0].destinationGeneration != 1 ||
        owner->current().sources[0].destinationLength != owner->source_.size() ||
        owner->current().sources[0].destinationSha256 != sourceHash) return reject(CustodyFileError::conflict);
    checked = revalidateSource(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
    checked = owner->root_->installQueueMigrationBarriers(owner->current(),*birth.value,cancellation,true);
    if (!checked.ok()) return reject(checked.error,checked.nativeError);
    if (packageFence) {
        // Structural closed worker only. The exact package intent/closure is still owed before admission.
        checked=revalidateSource(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
        return {std::move(owner),CustodyFileError::none,0};
    }
    const auto protectBootstrap = [&]() -> CustodyFileResult<bool> {
        auto pair = owner->bootstrap_->readValidatedMetadataPair(); if (!pair.ok()) return {std::nullopt,pair.error,pair.nativeError};
        const auto selected = pair.value->selectedSlot;
        auto bytes = readMetadataValue(*owner->bootstrap_,context,pair.value->indices[selected],cancellation);
        if (!bytes.ok()) return {std::nullopt,bytes.error,bytes.nativeError};
        auto current = readCustodyBootstrap({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},context,
            pair.value->indices[selected].generation,queueContext.objectId);
        if (!current.ok()) return {std::nullopt,codecFileError(current.error),current.nativeError};
        const bool already = current.value->mode == CustodyBootstrapMode::protectedStore;
        SecureZeroMemory(&*current.value,sizeof(CustodyBootstrapValue));
        if (already) return {true,CustodyFileError::none,0};
        auto fresh = revalidateSource(); if (!fresh.ok()) return fresh;
        CustodyBootstrapValue next; next.context = context; next.generation = pair.value->indices[selected].generation + 1;
        next.queueObjectId = queueContext.objectId; next.mode = CustodyBootstrapMode::protectedStore;
        auto encoded = writeCustodyBootstrap(next,context,next.generation,queueContext.objectId);
        SecureZeroMemory(&next,sizeof(next));
        if (!encoded.ok()) return {std::nullopt,codecFileError(encoded.error),encoded.nativeError};
        auto committed = CustodyMetadataCommit::commitImpl(path,{},context,pair.value->indices[selected].generation,*encoded.value,cancellation,owner->bootstrap_.get());
        if (committed.state != CustodyCommitState::committed) return {std::nullopt,
            committed.state == CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : committed.error,committed.nativeError};
        return {true,CustodyFileError::none,0};
    };
    checked = protectBootstrap(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
    if (owner->current().stage == CustodyMigrationStage::copiedVerified) {
        auto next = owner->current(); ++next.generation; next.stage = CustodyMigrationStage::switched;
        auto saved = saveIntent(next); SecureZeroMemory(&next,sizeof(next));
        if (!saved.ok()) return reject(saved.error,saved.nativeError);
    }
    // Retire a possible migrating peer via a real subsequent protected commit.
    auto protectedPair = owner->bootstrap_->readValidatedMetadataPair();
    if (!protectedPair.ok()) return reject(protectedPair.error,protectedPair.nativeError);
    bool bothProtected = true;
    for (const auto& index : protectedPair.value->indices) {
        auto bytes = readMetadataValue(*owner->bootstrap_,context,index,cancellation);
        if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
        auto value = readCustodyBootstrap({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},context,index.generation,queueContext.objectId);
        if (!value.ok()) return reject(codecFileError(value.error),value.nativeError);
        bothProtected = bothProtected && value.value->mode == CustodyBootstrapMode::protectedStore;
        SecureZeroMemory(&*value.value,sizeof(CustodyBootstrapValue));
    }
    if (!bothProtected) {
        checked = revalidateSource(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
        CustodyBootstrapValue next; next.context = context;
        next.generation = protectedPair.value->indices[protectedPair.value->selectedSlot].generation + 1;
        next.queueObjectId = queueContext.objectId; next.mode = CustodyBootstrapMode::protectedStore;
        auto bytes = writeCustodyBootstrap(next,context,next.generation,queueContext.objectId); SecureZeroMemory(&next,sizeof(next));
        if (!bytes.ok()) return reject(codecFileError(bytes.error),bytes.nativeError);
        auto committed = CustodyMetadataCommit::commitImpl(path,{},context,
            protectedPair.value->indices[protectedPair.value->selectedSlot].generation,*bytes.value,cancellation,owner->bootstrap_.get());
        if (committed.state != CustodyCommitState::committed) return reject(
            committed.state == CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : committed.error,committed.nativeError);
    }
    // Both intent slots must carry switched receipts before regular cold admission.
    if (owner->values_[1U - owner->indices_.selectedSlot].stage != CustodyMigrationStage::switched) {
        auto next = owner->current(); ++next.generation;
        auto saved = saveIntent(next); SecureZeroMemory(&next,sizeof(next));
        if (!saved.ok()) return reject(saved.error,saved.nativeError);
    }
    checked = validateFence(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
    checked = revalidateSource(); if (!checked.ok()) return reject(checked.error,checked.nativeError);
    return {std::move(owner),CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::system_error& error) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<std::shared_ptr<ProtectedCustodyQueueMigration>> ProtectedCustodyQueueMigration::openProtected(
    const std::filesystem::path& path, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Owner=std::shared_ptr<ProtectedCustodyQueueMigration>;
    const auto reject=[](CustodyFileError error,std::uint32_t native=0)->CustodyFileResult<Owner> { return {std::nullopt,error,native}; };
    if (!cancellation) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)path; return reject(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    CustodyNativeJob job; if (!job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
    CustodyPin pin; if (!pin) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
    bool birth=false;
    auto root=ProtectedCustodyFiles::lockStoreRoot(path,cancellation,birth,true);
    if (!root.ok()) return reject(root.error,root.nativeError);
    if (birth) return reject(CustodyFileError::conflict);
    CustodyAllocator<ProtectedCustodyQueueMigration> allocator; auto* raw=allocator.allocate(1);
    try { new(raw) ProtectedCustodyQueueMigration(); }
    catch (...) { allocator.deallocate(raw,1); throw; }
    Owner owner(raw,[](ProtectedCustodyQueueMigration* p) {
        p->~ProtectedCustodyQueueMigration(); CustodyAllocator<ProtectedCustodyQueueMigration>{}.deallocate(p,1);
    },allocator);
    owner->pin_.emplace(std::move(pin)); owner->cancellation_=cancellation;
    owner->root_=std::shared_ptr<ProtectedCustodyFiles>(root.value->release(),
        [](ProtectedCustodyFiles* p) { delete p; },CustodyAllocator<ProtectedCustodyFiles>{});
    auto queue=ProtectedCustodyFiles::openStoreObject(owner->root_,CustodyRole::queue,false);
    if (!queue.ok()) return reject(queue.error,queue.nativeError);
    owner->queue_=std::move(*queue.value);
    auto bootstrap=ProtectedCustodyFiles::openStoreObject(owner->root_,CustodyRole::bootstrap,false);
    if (!bootstrap.ok()) return reject(bootstrap.error,bootstrap.nativeError);
    owner->bootstrap_=std::move(*bootstrap.value);
    const auto q=owner->queue_->context(), b=owner->bootstrap_->context();
    if (q.storeId!=b.storeId || q.objectId==q.storeId || b.objectId==b.storeId || q.objectId==b.objectId)
        return reject(CustodyFileError::identityMismatch);
    if (owner->bootstrap_->unusedPackageRole().ok()) return reject(CustodyFileError::recoveryRequired);
    auto pair=owner->bootstrap_->readValidatedMetadataPair(); if (!pair.ok()) return reject(pair.error,pair.nativeError);
    std::optional<CustodyBootstrapValue> pending;
    struct Wipe { std::optional<CustodyBootstrapValue>& value; ~Wipe() { if (value) SecureZeroMemory(&*value,sizeof(*value)); } } wipe{pending};
    for (const auto& index:pair.value->indices) {
        auto bytes=readMetadataValue(*owner->bootstrap_,b,index,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
        auto value=readCustodyBootstrap({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},b,index.generation,q.objectId);
        if (!value.ok()) return reject(codecFileError(value.error),value.nativeError);
        if (value.value->mode==CustodyBootstrapMode::migrating) {
            if (value.value->subject==CustodyMigrationSubject::queue && !value.value->directory)
                return reject(CustodyFileError::recoveryRequired); // Exact root source/copy reconciliation owns this fence.
            if (value.value->subject!=CustodyMigrationSubject::package || !value.value->directory)
                return reject(CustodyFileError::conflict);
            if (pending && (pending->directory!=value.value->directory || pending->transactionId!=value.value->transactionId))
                return reject(CustodyFileError::conflict);
            pending=*value.value;
        }
        SecureZeroMemory(&*value.value,sizeof(CustodyBootstrapValue));
    }
    // Structural inventory is never admission: every root history surface must
    // independently authenticate Birth/progression, BOTH current queue values and
    // ALL fixed barrier/original/absence proofs before any package preparation.
    auto queuePair=owner->queue_->readValidatedMetadataPair(); if (!queuePair.ok()) return reject(queuePair.error,queuePair.nativeError);
    const auto queueGeneration=queuePair.value->indices[queuePair.value->selectedSlot].generation;
    for (unsigned slot=0;slot<2;++slot) {
        const auto& index=queuePair.value->indices[slot];
        auto bytes=readMetadataValue(*owner->queue_,q,index,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
        auto decoded=ProtectedCustodyStoreOwner::decodeMigrationQueue({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},cancellation.get());
        if (!decoded.ok()) return reject(decoded.error,decoded.nativeError);
        if (slot==queuePair.value->selectedSlot) {
            // Volatile inventory only; independently authenticated history below
            // remains mandatory before any package preparation/effect.
            auto absent=owner->root_->captureMigrationAbsences(**decoded.value,cancellation);
            if (!absent.ok()) return reject(absent.error,absent.nativeError);
        }
    }
    std::optional<CustodyVector<CustodyString>> scopes;
    auto inventory=owner->root_->validateStoreInventory(false,cancellation,false,&scopes,true);
    if (!inventory.ok()) return reject(inventory.error,inventory.nativeError);
    if (scopes && std::any_of(scopes->begin(),scopes->end(),[](const auto& name) { return name.empty(); })) {
        auto intent=ProtectedCustodyFiles::openStoreObject(owner->root_,CustodyRole::migrationIntent,false);
        if (!intent.ok()) return reject(intent.error,intent.nativeError);
        owner->intent_=std::move(*intent.value); const auto own=owner->intent_->context();
        if (own.objectId==q.objectId || own.objectId==b.objectId || own.objectId==own.storeId) return reject(CustodyFileError::identityMismatch);
        auto read=ProtectedCustodyMigrationPair::readValues(*owner->intent_,own,std::nullopt,CustodyMigrationSubject::queue,{},
            cancellation,nullptr,false,owner->indices_,owner->values_);
        if (!read.ok()) return reject(read.error,read.nativeError);
        for (const auto& value:owner->values_) {
            if (value.stage<CustodyMigrationStage::switched) return reject(CustodyFileError::recoveryRequired);
            if (!value.barrier || value.sourceCount!=1 || value.sources[0].destinationObjectId!=q.objectId ||
                !value.sources[0].destinationGeneration || *value.sources[0].destinationGeneration>queueGeneration ||
                (value.authorization && (value.authorization->queueObjectId!=q.objectId || value.authorization->queueGeneration>queueGeneration)))
                return reject(CustodyFileError::invalidContent);
        }
        auto files=owner->intent_->validateMigrationFiles(owner->current(),owner->values_[1U-owner->indices_.selectedSlot],cancellation);
        if (!files.ok()) return reject(files.error,files.nativeError);
    }
    auto absent=owner->root_->validateMigrationAbsences();
    if (!absent.ok()) return reject(absent.error,absent.nativeError);
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    return {std::move(owner),CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::system_error& error) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<std::shared_ptr<ProtectedCustodyStoreOwner>> ProtectedCustodyMigration::open(
    const std::filesystem::path& path,std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Owner=std::shared_ptr<ProtectedCustodyStoreOwner>;
    const auto reject=[](CustodyFileError error,std::uint32_t native=0)->CustodyFileResult<Owner> { return {std::nullopt,error,native}; };
    if (!cancellation) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)path; return reject(CustodyFileError::unsupportedPlatform);
#else
    // Existing normal/virgin admission stays first and keeps all of its guards.
    auto ordinary=ProtectedCustodyStoreOwner::open(path,cancellation);
    if (ordinary.ok()) return ordinary;
    // An observed appearance ends this pass; a fresh fallback must not forget it.
    if (ordinary.error==CustodyFileError::conflict && ordinary.nativeError==ERROR_ALREADY_EXISTS) return ordinary;
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    if (ordinary.error==CustodyFileError::allocationFailed || ordinary.error==CustodyFileError::unsafePath ||
        ordinary.error==CustodyFileError::unsafeFile || ordinary.error==CustodyFileError::protectionFailed ||
        ordinary.error==CustodyFileError::unsupportedPlatform) return ordinary;
    // A protected queue may need only package migration. This private structural
    // acquisition grants no ordinary owner. Completed root history is freshly
    // proved; an active root queue fence uses the exact legacy migration path.
    auto migration=ProtectedCustodyQueueMigration::openProtected(path,cancellation);
    if (!migration.ok() && migration.error==CustodyFileError::recoveryRequired)
        migration=ProtectedCustodyQueueMigration::openImpl(path,cancellation,true);
    if (!migration.ok()) return reject(migration.error,migration.nativeError);
    auto worker=std::move(*migration.value);
    CustodyBytes ledger; std::uint64_t generation=0;
    std::shared_ptr<const ProtectedUploadQueueValue> queue;
    CustodyVector<CustodyString> packages;
    {
        CustodyNativeJob job; if (!job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
        const auto context=worker->queue_->context();
        auto pair=worker->queue_->readValidatedMetadataPair(); if (!pair.ok()) return reject(pair.error,pair.nativeError);
        for (unsigned slot=0;slot<2;++slot) {
            const auto& index=pair.value->indices[slot];
            auto bytes=readMetadataValue(*worker->queue_,context,index,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
            auto decoded=ProtectedCustodyStoreOwner::decodeMigrationQueue({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},cancellation.get());
            if (!decoded.ok()) return reject(decoded.error,decoded.nativeError);
            if (slot==pair.value->selectedSlot) { generation=index.generation; ledger=std::move(*bytes.value); queue=std::move(*decoded.value); }
        }
        auto inventory=worker->root_->migrationPackages(); if (!inventory.ok()) return reject(inventory.error,inventory.nativeError);
        packages=std::move(*inventory.value);
        auto bootstrap=worker->bootstrap_->readValidatedMetadataPair(); if (!bootstrap.ok()) return reject(bootstrap.error,bootstrap.nativeError);
        for (const auto& index:bootstrap.value->indices) {
            auto bytes=readMetadataValue(*worker->bootstrap_,worker->bootstrap_->context(),index,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
            auto value=readCustodyBootstrap({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},worker->bootstrap_->context(),index.generation,context.objectId);
            if (!value.ok()) return reject(codecFileError(value.error),value.nativeError);
            if (value.value->mode==CustodyBootstrapMode::migrating) {
                if (value.value->subject!=CustodyMigrationSubject::package || !value.value->directory) return reject(CustodyFileError::conflict);
                const auto pending=text(*value.value->directory);
                const auto found=std::find_if(packages.begin(),packages.end(),[&](const CustodyString& id) { return std::string_view(id)==pending; });
                if (found==packages.end()) return reject(CustodyFileError::recoveryRequired);
                std::rotate(packages.begin(),found,found+1); // Retire the sole active selected/peer transaction before any other package.
            }
            SecureZeroMemory(&*value.value,sizeof(CustodyBootstrapValue));
        }
    }
    for (const auto& name:packages) {
        if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
        auto absent=worker->root_->validateMigrationAbsences(); if (!absent.ok()) return reject(absent.error,absent.nativeError);
        std::string_view session;
        for (const auto& item:queue->items()) if (std::string_view(item.directoryId)==std::string_view(name)) {
            if (!session.empty() && session!=std::string_view(item.sessionId)) return reject(CustodyFileError::conflict);
            session=item.sessionId;
        }
        if (session.empty()) return reject(CustodyFileError::recoveryRequired); // Unknown source is retained; no guessed session/owner.
        auto migrated=migratePackage(*worker,name,session,ledger,generation);
        if (!migrated.ok()) return reject(migrated.error,migrated.nativeError);
        absent=worker->root_->validateMigrationAbsences(); if (!absent.ok()) return reject(absent.error,absent.nativeError);
    }
    // No legacy reader or migration writer survives admission. The same root,
    // queue and bootstrap identities transfer to the ordinary owner; cold history,
    // BOTH closures/retained roots and every barrier/original are freshly proved.
    auto absent=worker->root_->validateMigrationAbsences(); if (!absent.ok()) return reject(absent.error,absent.nativeError);
    worker->root_->retireMigrationQueueSource();
    absent=worker->root_->validateMigrationAbsences(); if (!absent.ok()) return reject(absent.error,absent.nativeError);
    worker->intent_.reset();
    CustodyPin pin; if (!pin) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
    CustodyAllocator<ProtectedCustodyStoreOwner> allocator; auto* raw=allocator.allocate(1);
    try { new(raw) ProtectedCustodyStoreOwner(std::move(pin)); }
    catch (...) { allocator.deallocate(raw,1); throw; }
    Owner owner(raw,[](ProtectedCustodyStoreOwner* p) {
        p->~ProtectedCustodyStoreOwner(); CustodyAllocator<ProtectedCustodyStoreOwner>{}.deallocate(p,1);
    },allocator);
    owner->root_=std::move(worker->root_); owner->queue_=std::move(worker->queue_); owner->bootstrap_=std::move(worker->bootstrap_);
    owner->queueContext_=owner->queue_->context();
    {
        CustodyNativeJob job; if (!job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
        auto admitted=owner->validate(cancellation,nullptr,true); if (!admitted.ok()) return reject(admitted.error,admitted.nativeError);
    }
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    absent=owner->root_->validateMigrationAbsences(); if (!absent.ok()) return reject(absent.error,absent.nativeError);
    absent=owner->root_->releaseMigrationAbsences(); if (!absent.ok()) return reject(absent.error,absent.nativeError);
    return {std::move(owner),CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::system_error& error) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<bool> ProtectedCustodyMigration::migratePackage(
    ProtectedCustodyQueueMigration& worker,std::string_view name,std::string_view session,
    const CustodyBytes& ledger,std::uint64_t queueGeneration) try {
    const auto reject=[](CustodyFileError error,std::uint32_t native=0)->CustodyFileResult<bool> { return {std::nullopt,error,native}; };
#ifndef _WIN32
    (void)worker; (void)name; (void)session; (void)ledger; (void)queueGeneration; return reject(CustodyFileError::unsupportedPlatform);
#else
    const auto cancellation=worker.cancellation_;
    if (!identity(name) || !identity(session) || !queueGeneration || !cancellation) return reject(CustodyFileError::invalidInput);
    CustodyNativeJob job; if (!job) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
    CustodyPin pin; if (!pin) return reject(CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA);
    const auto root=worker.root_; const auto queueContext=worker.queue_->context(), bootstrapContext=worker.bootstrap_->context();
    const auto path=root->trustedRoot();
    std::unique_ptr<ProtectedCustodyFiles> intent;
    CustodyContext own{}; CustodyMetadataIndices indices; std::array<CustodyMigrationValue,2> values{};
    struct Wipe { std::array<CustodyMigrationValue,2>& values; ~Wipe() { SecureZeroMemory(values.data(),sizeof(values)); } } wipe{values};
    const auto readIntent=[&](std::optional<CustodyId> transaction) {
        return ProtectedCustodyMigrationPair::readValues(*intent,own,transaction,CustodyMigrationSubject::package,name,
            cancellation,nullptr,true,indices,values);
    };
    auto existing=ProtectedCustodyFiles::openStoreObject(root,CustodyRole::migrationIntent,false,name,true);
    bool hasHistory=false;
    if (existing.ok()) {
        intent=std::move(*existing.value); own=intent->context();
        if (!intent->unusedPackageRole().ok()) {
            auto read=readIntent(std::nullopt); if (!read.ok()) return read;
            hasHistory=true;
        }
    } else if (existing.nativeError!=ERROR_FILE_NOT_FOUND && existing.nativeError!=ERROR_PATH_NOT_FOUND) return reject(existing.error,existing.nativeError);
    // Read BOTH bootstrap values and qualify only this exact transaction/directory.
    const auto readBootstrap=[&](std::array<CustodyBootstrapValue,2>& parsed,CustodyMetadataIndices& pair)->CustodyFileResult<bool> {
        auto nativePair=worker.bootstrap_->readValidatedMetadataPair(); if (!nativePair.ok()) return reject(nativePair.error,nativePair.nativeError);
        for (unsigned slot=0;slot<2;++slot) {
            const auto& index=nativePair.value->indices[slot];
            auto bytes=readMetadataValue(*worker.bootstrap_,bootstrapContext,index,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
            auto value=readCustodyBootstrap({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},bootstrapContext,index.generation,queueContext.objectId);
            if (!value.ok()) return reject(codecFileError(value.error),value.nativeError);
            parsed[slot]=*value.value; SecureZeroMemory(&*value.value,sizeof(CustodyBootstrapValue));
            if (parsed[slot].mode==CustodyBootstrapMode::migrating &&
                (parsed[slot].transactionId!=values[indices.selectedSlot].transactionId || parsed[slot].subject!=CustodyMigrationSubject::package ||
                 parsed[slot].directory!=values[indices.selectedSlot].directory)) return reject(CustodyFileError::conflict);
        }
        pair=std::move(*nativePair.value); return {true,CustodyFileError::none,0};
    };
    std::array<CustodyBootstrapValue,2> beforeBootstrap{}; CustodyMetadataIndices beforeBootstrapPair;
    auto preflight=readBootstrap(beforeBootstrap,beforeBootstrapPair); if (!preflight.ok()) return preflight;
    for (const auto& record:beforeBootstrap) if (record.mode==CustodyBootstrapMode::migrating && !hasHistory)
        return reject(CustodyFileError::recoveryRequired); // Required intent must preexist its fence; never invent a replacement transaction.
    if (hasHistory && std::all_of(values.begin(),values.end(),[](const auto& value) {
            return value.stage>=CustodyMigrationStage::switched;
        }) && std::all_of(beforeBootstrap.begin(),beforeBootstrap.end(),[](const auto& value) {
            return value.mode==CustodyBootstrapMode::protectedStore;
        })) {
        // Completed A is an independently authenticated readonly history, never
        // B's active selector or a reason to reopen/rewrite A's legacy originals.
        auto history=ProtectedCustodyMigrationPair::readImpl(path,own,std::nullopt,CustodyMigrationSubject::package,
            name,cancellation,{},std::move(intent));
        if (!history.ok()) return reject(history.error,history.nativeError);
        auto state=ProtectedCustodyFiles::openPackageState(root,name,cancellation);
        if (!state.ok()) return reject(state.error,state.nativeError);
        const auto stateContext=(*state.value)->context();
        if (stateContext.storeId!=queueContext.storeId || stateContext.objectId==stateContext.storeId ||
            stateContext.objectId==queueContext.objectId || stateContext.objectId==bootstrapContext.objectId || stateContext.objectId==own.objectId)
            return reject(CustodyFileError::identityMismatch);
        auto retained=std::shared_ptr<ProtectedCustodyFiles>(state.value->release(),
            [](ProtectedCustodyFiles* files) { delete files; },CustodyAllocator<ProtectedCustodyFiles>{});
        auto pair=ProtectedCustodyPackagePair::readImpl(path,name,stateContext,cancellation,std::move(retained),
            ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly);
        if (!pair.ok()) return reject(pair.error,pair.nativeError);
        auto readers=openProtectedCustodyReaders(path,*pair.value,cancellation);
        if (!readers.ok()) return reject(readers.error,readers.nativeError);
        return ProtectedCustodyStoreOwner::validateMigrationPackageHistoryImpl(root,queueContext,bootstrapContext,
            queueGeneration,*pair.value,cancellation,*history.value);
    }
    CustodyMigrationValue captured; captured.schema=2; captured.subject=CustodyMigrationSubject::package;
    captured.directory.emplace(); std::copy(name.begin(),name.end(),captured.directory->begin());
    unsigned roles=0;
    auto native=ProtectedCustodyFiles::lockMigrationPackageRoot(root,name,cancellation,captured,roles,
        hasHistory ? &values[indices.selectedSlot] : nullptr);
    if (!native.ok()) return reject(native.error,native.nativeError);
    auto packageRoot=std::move(*native.value);
    CustodyBytes manifest,recovery;
    for (std::size_t source=0;source<captured.sourceCount;++source) {
        const auto& item=captured.sources[source];
        if (item.kind!=CustodyMigrationSourceKind::manifest && item.kind!=CustodyMigrationSourceKind::recovery) continue;
        auto bytes=packageRoot->readMigrationPackageSource(static_cast<unsigned>(item.kind),0,static_cast<std::uint32_t>(item.length));
        if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
        (item.kind==CustodyMigrationSourceKind::manifest ? manifest : recovery)=std::move(*bytes.value);
    }
    CustodyPackageValue stateValue; stateValue.schema=2; stateValue.generation=1;
    std::copy(name.begin(),name.end(),stateValue.directory.begin());
    auto classified=LocalRecordingPackage::classifyMigrationContent(stateValue,manifest,recovery,session);
    if (!classified.ok()) return classified;
    if (hasHistory) {
        const auto& current=values[indices.selectedSlot];
        if (current.stage>CustodyMigrationStage::switched || current.authorization || current.schema!=2 ||
            current.sourceCount!=captured.sourceCount || current.anchor.objectId!=queueContext.objectId) return reject(CustodyFileError::recoveryRequired);
        for (std::size_t i=0;i<captured.sourceCount;++i) {
            const auto& a=captured.sources[i]; const auto& b=current.sources[i];
            if (a.kind!=b.kind || a.length!=b.length || a.sha256!=b.sha256) return reject(CustodyFileError::conflict);
        }
    }
    if (hasHistory) {
        if (!(roles&1)) return reject(CustodyFileError::recoveryRequired);
        for (std::size_t i=0;i<captured.sourceCount;++i)
            if (!(roles&(1U<<(static_cast<unsigned>(captured.sources[i].kind)+1)))) return reject(CustodyFileError::recoveryRequired);
    }
    auto checked=packageRoot->createMigrationPackageCustody(); if (!checked.ok()) return checked;
    std::unique_ptr<ProtectedCustodyFiles> state;
    auto openedState=ProtectedCustodyFiles::openPackageRole(packageRoot,CustodyRole::packageState,&state,
        roles&1 ? CustodyFileAccess::writeExisting : CustodyFileAccess::createNew);
    if (!openedState.ok()) return reject(openedState.error,openedState.nativeError);
    state=std::move(*openedState.value); stateValue.context=state->context();
    std::array<std::unique_ptr<ProtectedCustodyFiles>,5> files;
    std::array<CustodyContext,5> contexts{};
    std::array<CustodyId,3> containers{};
    constexpr std::array<CustodyRole,6> mapping{CustodyRole::queue,CustodyRole::manifest,CustodyRole::canonical,CustodyRole::media,CustodyRole::playback,CustodyRole::recovery};
    for (std::size_t i=0;i<captured.sourceCount;++i) {
        auto& source=captured.sources[i]; const auto kind=static_cast<unsigned>(source.kind);
        const auto role=mapping[kind]; const auto index=static_cast<unsigned>(role)-1;
        auto member=ProtectedCustodyFiles::openPackageRole(packageRoot,role,&files[index],
            roles&(1U<<(kind+1)) ? CustodyFileAccess::writeExisting : CustodyFileAccess::createNew);
        if (!member.ok()) return reject(member.error,member.nativeError);
        files[index]=std::move(*member.value); contexts[index]=files[index]->context(); source.destinationObjectId=contexts[index].objectId;
        if (hasHistory && source.destinationObjectId!=values[indices.selectedSlot].sources[i].destinationObjectId) return reject(CustodyFileError::identityMismatch);
        if (index<containers.size()) {
            source.destinationPacked=true;
            if (hasHistory) {
                if (!values[indices.selectedSlot].sources[i].destinationContainerId) return reject(CustodyFileError::invalidContent);
                containers[index]=*values[indices.selectedSlot].sources[i].destinationContainerId;
            } else {
                if (!files[index]->unusedPackageRole().ok()) return reject(CustodyFileError::recoveryRequired);
                const auto status=BCryptGenRandom(nullptr,containers[index].data(),16,BCRYPT_USE_SYSTEM_PREFERRED_RNG);
                if (status<0) return reject(CustodyFileError::ioFailed,static_cast<std::uint32_t>(status));
            }
            source.destinationContainerId=containers[index];
        }
    }
    if (!intent) {
        auto created=ProtectedCustodyFiles::openStoreObject(root,CustodyRole::migrationIntent,true,name,true);
        if (!created.ok()) return reject(created.error,created.nativeError);
        intent=std::move(*created.value); own=intent->context();
    }
    std::array<CustodyId,9> ids{}; std::size_t used=0;
    for (const auto id:{queueContext.objectId,bootstrapContext.objectId,own.objectId,stateValue.context.objectId}) ids[used++]=id;
    for (const auto& member:files) if (member) ids[used++]=member->context().objectId;
    for (std::size_t i=0;i<used;++i) {
        if (ids[i]==CustodyId{} || ids[i]==own.storeId) return reject(CustodyFileError::identityMismatch);
        for (std::size_t j=0;j<i;++j) if (ids[i]==ids[j]) return reject(CustodyFileError::identityMismatch);
    }
    const auto ledgerHash=custody_detail::digest(ledger.data(),ledger.size()); if (!ledgerHash) return reject(CustodyFileError::hashFailed);
    const auto queueStamp=[&](const CustodyMigrationValue& value)->CustodyFileResult<bool> {
        auto absent=worker.root_->validateMigrationAbsences(); if (!absent.ok()) return absent;
        auto pair=worker.queue_->readValidatedMetadataPair(); if (!pair.ok()) return reject(pair.error,pair.nativeError);
        const auto& selected=pair.value->indices[pair.value->selectedSlot];
        auto bytes=readMetadataValue(*worker.queue_,queueContext,selected,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
        const auto hash=custody_detail::digest(bytes.value->data(),bytes.value->size()); if (!hash) return reject(CustodyFileError::hashFailed);
        return value.anchor.objectId==queueContext.objectId && value.anchor.generation==selected.generation &&
            value.anchor.length==bytes.value->size() && value.anchor.sha256==*hash ? CustodyFileResult<bool>{true,CustodyFileError::none,0} : reject(CustodyFileError::conflict);
    };
    const auto saveIntent=[&](const CustodyMigrationValue& value)->CustodyFileResult<bool> {
        auto sources=packageRoot->verifyMigrationPackageSources(value); if (!sources.ok()) return sources;
        auto stamp=queueStamp(value); if (!stamp.ok()) return stamp;
        auto bytes=writeCustodyMigration(value,own,value.generation,value.transactionId,CustodyMigrationSubject::package,name);
        if (!bytes.ok()) return reject(codecFileError(bytes.error),bytes.nativeError);
        auto result=CustodyMetadataCommit::commitImpl(path,name,own,value.generation-1,*bytes.value,cancellation,intent.get());
        if (result.state!=CustodyCommitState::committed) return reject(result.state==CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : result.error,result.nativeError);
        return readIntent(value.transactionId);
    };
    if (!hasHistory) {
        if (!intent->unusedPackageRole().ok() || !state->unusedPackageRole().ok() || (roles&0x80000000U)) return reject(CustodyFileError::recoveryRequired);
        captured.context=own; captured.generation=1; captured.stage=CustodyMigrationStage::prepared;
        captured.anchor={queueContext.objectId,queueGeneration,ledger.size(),*ledgerHash};
        const auto status=BCryptGenRandom(nullptr,captured.transactionId.data(),16,BCRYPT_USE_SYSTEM_PREFERRED_RNG);
        if (status<0) return reject(CustodyFileError::ioFailed,static_cast<std::uint32_t>(status));
        auto saved=saveIntent(captured); if (!saved.ok()) return saved;
    }
    auto& current=values[indices.selectedSlot];
    // No new write can turn an unexplained old-name barrier/original into a valid history.
    if (!current.barrier && (roles&0x80000000U)) return reject(CustodyFileError::recoveryRequired);
    if (!current.barrier) {
        const auto& selected=indices.indices[indices.selectedSlot];
        if (selected.generation!=1) return reject(CustodyFileError::recoveryRequired);
        const auto& entry=selected.entries[0];
        auto birth=intent->readMigrationBirthEnvelope(entry.version,entry.envelopeBytes); if (!birth.ok()) return reject(birth.error,birth.nativeError);
        const auto hash=custody_detail::digest(birth.value->data(),birth.value->size()); if (!hash) return reject(CustodyFileError::hashFailed);
        auto next=current; ++next.generation; next.barrier=CustodyMigrationBarrier{own.objectId,1,entry.version,birth.value->size(),*hash};
        auto saved=saveIntent(next); SecureZeroMemory(&next,sizeof(next)); if (!saved.ok()) return saved;
    }
    const auto& barrier=*values[indices.selectedSlot].barrier;
    auto birth=intent->readMigrationBirthEnvelope(barrier.blockVersion,static_cast<std::uint32_t>(barrier.envelopeBytes));
    if (!birth.ok()) return reject(birth.error,birth.nativeError);
    checked=packageRoot->installPackageMigrationBarriers(values[indices.selectedSlot],*birth.value,false); if (!checked.ok()) return checked;
    const auto publishBootstrap=[&](bool migrating)->CustodyFileResult<bool> {
        std::array<CustodyBootstrapValue,2> parsed{}; CustodyMetadataIndices pair;
        auto read=readBootstrap(parsed,pair); if (!read.ok()) return read;
        auto stamp=queueStamp(values[indices.selectedSlot]); if (!stamp.ok()) return stamp;
        auto sources=packageRoot->verifyMigrationPackageSources(values[indices.selectedSlot]); if (!sources.ok()) return sources;
        CustodyBootstrapValue next; next.context=bootstrapContext; next.generation=pair.indices[pair.selectedSlot].generation+1;
        next.queueObjectId=queueContext.objectId; next.mode=migrating ? CustodyBootstrapMode::migrating : CustodyBootstrapMode::protectedStore;
        if (migrating) { next.transactionId=values[indices.selectedSlot].transactionId; next.subject=CustodyMigrationSubject::package; next.directory=values[indices.selectedSlot].directory; }
        auto bytes=writeCustodyBootstrap(next,bootstrapContext,next.generation,queueContext.objectId); SecureZeroMemory(&next,sizeof(next));
        if (!bytes.ok()) return reject(codecFileError(bytes.error),bytes.nativeError);
        auto result=CustodyMetadataCommit::commitImpl(path,{},bootstrapContext,pair.indices[pair.selectedSlot].generation,*bytes.value,cancellation,worker.bootstrap_.get());
        if (result.state!=CustodyCommitState::committed) return reject(result.state==CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : result.error,result.nativeError);
        return readBootstrap(parsed,pair);
    };
    std::array<CustodyBootstrapValue,2> bootstrap{}; CustodyMetadataIndices bootstrapPair;
    checked=readBootstrap(bootstrap,bootstrapPair); if (!checked.ok()) return checked;
    const auto selectedMode=bootstrap[bootstrapPair.selectedSlot].mode;
    if (selectedMode==CustodyBootstrapMode::protectedStore && values[indices.selectedSlot].stage==CustodyMigrationStage::prepared) {
        if (bootstrap[1U-bootstrapPair.selectedSlot].mode!=CustodyBootstrapMode::protectedStore) return reject(CustodyFileError::conflict);
        checked=publishBootstrap(true); if (!checked.ok()) return checked;
    } else if (selectedMode==CustodyBootstrapMode::protectedStore && values[indices.selectedSlot].stage==CustodyMigrationStage::copiedVerified)
        return reject(CustodyFileError::conflict);
    if (values[indices.selectedSlot].stage<CustodyMigrationStage::switched || selectedMode==CustodyBootstrapMode::migrating) {
        checked=queueStamp(values[indices.selectedSlot]); if (!checked.ok()) return checked;
    }
    std::array<std::shared_ptr<ProtectedPackedCustodyOwner>,3> packed;
    std::array<std::shared_ptr<const ProtectedPackedCustodyTree>,3> trees;
    auto copied=values[indices.selectedSlot];
    for (std::size_t i=0;i<copied.sourceCount;++i) {
        auto& source=copied.sources[i]; const auto kind=static_cast<unsigned>(source.kind);
        const auto role=mapping[kind]; const auto index=static_cast<unsigned>(role)-1;
        checked=packageRoot->verifyMigrationPackageSources(values[indices.selectedSlot]); if (!checked.ok()) return checked;
        std::uint64_t generation=0; std::optional<std::uint64_t> extent; std::optional<ProtectedPackedCustodyFormat::Reference> rootRef;
        if (source.destinationPacked) {
            const bool unused=files[index]->unusedPackageRole().ok();
            if (unused && values[indices.selectedSlot].stage!=CustodyMigrationStage::prepared) return reject(CustodyFileError::recoveryRequired);
            auto owner=ProtectedPackedCustodyOwner::openImpl(path,name,{contexts[index],containers[index]},
                unused ? CustodyFileAccess::createNew : CustodyFileAccess::writeExisting,&files[index],&packed[index],nullptr,packageRoot.get());
            if (!owner.ok()) return reject(owner.error,owner.nativeError);
            packed[index]=std::move(*owner.value);
            auto tree=ProtectedPackedCustodyTree::verify(packed[index]); if (!tree.ok()) return reject(tree.error,tree.nativeError);
            trees[index]=std::move(*tree.value); // BOTH current HEAD closures remain independently required.
            if (values[indices.selectedSlot].stage!=CustodyMigrationStage::prepared) {
                if (!source.destinationGeneration || !source.destinationLength || !source.destinationCommittedExtent || !source.destinationRootRef ||
                    source.destinationLength!=source.length || source.destinationSha256!=source.sha256)
                    return reject(CustodyFileError::invalidContent);
                const auto rootReference=ProtectedPackedCustodyFormat::decodeReference(source.destinationRootRef->data(),source.destinationRootRef->size(),
                    {source.length ? PackedRecordKind::nodeL2 : PackedRecordKind::empty,0,
                        *source.destinationGeneration,*source.destinationCommittedExtent,*source.destinationCommittedExtent});
                if (!rootReference) return reject(CustodyFileError::invalidContent);
                const PackedRootDescriptor stamp{*source.destinationGeneration,source.length,*source.destinationCommittedExtent,
                    static_cast<std::uint32_t>((source.length+ProtectedCustodyCodec::blockBytes-1)/ProtectedCustodyCodec::blockBytes),*rootReference};
                auto historical=ProtectedPackedCustodyTree::verifyRetained(packed[index],{contexts[index],containers[index]},stamp);
                if (!historical.ok()) return reject(historical.error,historical.nativeError);
                trees[index]=std::move(*historical.value); // Receipt root may be absent from BOTH current HEADs.
            }
            if (trees[index]->logicalBytes()>source.length) return reject(CustodyFileError::conflict);
            for (std::uint64_t position=0,at=0;at<trees[index]->logicalBytes();++position) {
                auto block=trees[index]->readBlock(position); if (!block.ok()) return reject(block.error,block.nativeError);
                auto original=packageRoot->readMigrationPackageSource(kind,at,static_cast<std::uint32_t>(block.value->bytes.size()));
                if (!original.ok()) return reject(original.error,original.nativeError);
                if (*original.value!=block.value->bytes) return reject(CustodyFileError::conflict);
                at+=block.value->bytes.size();
            }
            if (trees[index]->logicalBytes()!=source.length && trees[index]->logicalBytes()%ProtectedCustodyCodec::blockBytes)
                return reject(CustodyFileError::conflict);
            if (values[indices.selectedSlot].stage!=CustodyMigrationStage::prepared && trees[index]->logicalBytes()!=source.length)
                return reject(CustodyFileError::conflict);
            while (trees[index]->logicalBytes()<source.length) {
                const auto at=trees[index]->logicalBytes();
                auto original=packageRoot->readMigrationPackageSource(kind,at,static_cast<std::uint32_t>((std::min)(std::uint64_t{ProtectedCustodyCodec::blockBytes},source.length-at)));
                if (!original.ok()) return reject(original.error,original.nativeError);
                auto result=trees[index]->appendBlock(*original.value);
                if (result.state!=CustodyCommitState::committed) return reject(result.state==CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : result.error,result.nativeError);
                trees[index]=std::move(result.snapshot);
            }
            const auto& descriptor=trees[index]->descriptor(); generation=descriptor.generation; extent=descriptor.committedExtent;
            rootRef=ProtectedPackedCustodyFormat::encodeReference(descriptor.root); if (!rootRef) return reject(CustodyFileError::invalidContent);
            auto reader=openProtectedCustodyReader(trees[index],cancellation); if (!reader.ok()) return reject(reader.error,reader.nativeError);
            auto hash=sha256ProtectedStream(reader.value->stream.Get(),source.length,cancellation);
            if (!hash.ok()) return reject(hash.error,hash.nativeError);
            if (*hash.value!=source.sha256) return reject(CustodyFileError::conflict);
        } else {
            if (files[index]->unusedPackageRole().ok()) {
                if (values[indices.selectedSlot].stage!=CustodyMigrationStage::prepared) return reject(CustodyFileError::recoveryRequired);
                const auto& bytes=kind==1 ? manifest : recovery;
                auto result=CustodyMetadataCommit::commitImpl(path,name,contexts[index],0,bytes,cancellation,files[index].get());
                if (result.state!=CustodyCommitState::committed) return reject(result.state==CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : result.error,result.nativeError);
            }
            auto pair=files[index]->readValidatedMetadataPair(); if (!pair.ok()) return reject(pair.error,pair.nativeError);
            generation=pair.value->indices[pair.value->selectedSlot].generation;
            for (const auto& head:pair.value->indices) {
                auto bytes=readMetadataValue(*files[index],contexts[index],head,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
                const auto hash=custody_detail::digest(bytes.value->data(),bytes.value->size());
                if (!hash) return reject(CustodyFileError::hashFailed);
                if (head.generation!=1 || bytes.value->size()!=source.length || *hash!=source.sha256) return reject(CustodyFileError::conflict);
            }
        }
        if (values[indices.selectedSlot].stage!=CustodyMigrationStage::prepared && source.destinationGeneration!=generation)
            return reject(CustodyFileError::conflict);
        source.destinationGeneration=generation; source.destinationLength=source.length; source.destinationSha256=source.sha256;
        source.destinationCommittedExtent=extent; source.destinationRootRef=rootRef;
        auto& reference=stateValue.refs[stateValue.refCount++]; reference.role=role; reference.objectId=source.destinationObjectId; reference.sealed=true;
        reference.packed=source.destinationPacked; reference.generation=generation; reference.length=source.length; reference.sha256=source.sha256;
        reference.containerId=source.destinationContainerId; reference.committedExtent=extent; reference.rootRef=rootRef;
    }
    {
        std::array<CustodyReader,3> readers; std::array<IStream*,3> streams{};
        for (unsigned i=0;i<trees.size();++i) if (trees[i]) {
            auto reader=openProtectedCustodyReader(trees[i],cancellation); if (!reader.ok()) return reject(reader.error,reader.nativeError);
            readers[i]=std::move(*reader.value); streams[i]=readers[i].stream.Get();
        }
        auto evidence=LocalRecordingPackage::validateProtectedContent(stateValue,streams,manifest,recovery,session,cancellation);
        if (!evidence.ok()) return reject(evidence.error,evidence.nativeError);
    }
    if (values[indices.selectedSlot].stage==CustodyMigrationStage::prepared) {
        copied.stage=CustodyMigrationStage::copiedVerified; ++copied.generation;
        auto saved=saveIntent(copied); if (!saved.ok()) return saved;
    }
    checked=packageRoot->installPackageMigrationBarriers(values[indices.selectedSlot],*birth.value,true); if (!checked.ok()) return checked;
    const auto verifyState=[&]()->CustodyFileResult<bool> {
        auto pair=state->readValidatedMetadataPair(); if (!pair.ok()) return reject(pair.error,pair.nativeError);
        for (const auto& head:pair.value->indices) {
            auto bytes=readMetadataValue(*state,stateValue.context,head,cancellation); if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
            auto value=readCustodyPackage({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},stateValue.context,head.generation,name);
            if (!value.ok()) return reject(codecFileError(value.error),value.nativeError);
            auto expected=stateValue; expected.generation=head.generation;
            auto encoding=writeCustodyPackage(expected,expected.context,head.generation,name);
            auto actual=writeCustodyPackage(*value.value,stateValue.context,head.generation,name);
            SecureZeroMemory(&*value.value,sizeof(CustodyPackageValue));
            if (!encoding.ok() || !actual.ok()) return reject(CustodyFileError::invalidContent);
            if (*encoding.value!=*actual.value) return reject(CustodyFileError::conflict);
        }
        return {true,CustodyFileError::none,0};
    };
    if (state->unusedPackageRole().ok()) {
        if (values[indices.selectedSlot].stage!=CustodyMigrationStage::copiedVerified) return reject(CustodyFileError::recoveryRequired);
        checked=packageRoot->verifyMigrationPackageSources(values[indices.selectedSlot]); if (!checked.ok()) return checked;
        checked=queueStamp(values[indices.selectedSlot]); if (!checked.ok()) return checked;
        auto bytes=writeCustodyPackage(stateValue,stateValue.context,1,name); if (!bytes.ok()) return reject(codecFileError(bytes.error),bytes.nativeError);
        auto result=CustodyMetadataCommit::commitImpl(path,name,stateValue.context,0,*bytes.value,cancellation,state.get());
        if (result.state!=CustodyCommitState::committed) return reject(result.state==CustodyCommitState::ambiguous ? CustodyFileError::recoveryRequired : result.error,result.nativeError);
    }
    checked=verifyState(); if (!checked.ok()) return checked;
    if (values[indices.selectedSlot].stage==CustodyMigrationStage::copiedVerified) {
        auto next=values[indices.selectedSlot]; ++next.generation; next.stage=CustodyMigrationStage::switched;
        auto saved=saveIntent(next); SecureZeroMemory(&next,sizeof(next)); if (!saved.ok()) return saved;
    }
    checked=readBootstrap(bootstrap,bootstrapPair); if (!checked.ok()) return checked;
    if (bootstrap[bootstrapPair.selectedSlot].mode==CustodyBootstrapMode::migrating) {
        checked=publishBootstrap(false); if (!checked.ok()) return checked;
        checked=readBootstrap(bootstrap,bootstrapPair); if (!checked.ok()) return checked;
    }
    if (bootstrap[1U-bootstrapPair.selectedSlot].mode==CustodyBootstrapMode::migrating) {
        checked=publishBootstrap(false); if (!checked.ok()) return checked;
    }
    if (values[1U-indices.selectedSlot].stage!=CustodyMigrationStage::switched) {
        auto next=values[indices.selectedSlot]; ++next.generation;
        auto saved=saveIntent(next); SecureZeroMemory(&next,sizeof(next)); if (!saved.ok()) return saved;
    }
    checked=verifyState(); if (!checked.ok()) return checked;
    checked=packageRoot->verifyMigrationPackageSources(values[indices.selectedSlot]); if (!checked.ok()) return checked;
    // Readers/writers are retired before the later full ordinary cold-admission proof.
    packageRoot->retireMigrationPackageSources();
    return {true,CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::system_error& error) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(error.code().value())}; }

ProtectedCustodyStoreOwner::ProtectedCustodyStoreOwner(CustodyPin&& pin) {
    pin_.emplace(std::move(pin));
}
ProtectedCustodyStoreOwner::~ProtectedCustodyStoreOwner() = default;

CustodyFileResult<bool> ProtectedCustodyStoreOwner::validate(
    std::shared_ptr<const std::atomic<bool>> cancellation,
    std::shared_ptr<const ProtectedUploadQueueValue>* selectedValue, bool coldAdmission) {
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<bool> {
        // Validation never writes. Refused memory or actual caller cancellation
        // requires a fresh full read, not recovery of otherwise healthy files.
        if (error != CustodyFileError::allocationFailed && !(error == CustodyFileError::ioFailed &&
            native == 995 && cancellation && cancellation->load())) failed_ = true;
        return {std::nullopt, error, native};
    };
    try {
    if (!cancellation || !root_ || !bootstrap_ || !queue_) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)selectedValue; (void)coldAdmission;
    return reject(CustodyFileError::unsupportedPlatform);
#else
    std::optional<CustodyVector<CustodyString>> migrationScopes;
    auto inventory = root_->validateStoreInventory(false, cancellation, false, &migrationScopes);
    if (!inventory.ok()) return reject(inventory.error, inventory.nativeError);
    const auto own = bootstrap_->context();
    if (own.storeId != queueContext_.storeId || own.objectId == queueContext_.objectId ||
        queue_->context().storeId != queueContext_.storeId || queue_->context().objectId != queueContext_.objectId)
        return reject(CustodyFileError::identityMismatch);
    auto bootstrap = bootstrap_->readValidatedMetadataPair();
    if (!bootstrap.ok()) return reject(bootstrap.error, bootstrap.nativeError);
    for (unsigned slot = 0; slot < 2; ++slot) {
        auto bytes = readMetadataValue(*bootstrap_, own, bootstrap.value->indices[slot], cancellation);
        if (!bytes.ok()) return reject(bytes.error, bytes.nativeError);
        struct Wipe {
            CustodyBytes& value;
            ~Wipe() { if (!value.empty()) SecureZeroMemory(value.data(), value.size()); }
        } wipe{*bytes.value};
        auto parsed = readCustodyBootstrap({reinterpret_cast<const char*>(bytes.value->data()), bytes.value->size()},
            own, bootstrap.value->indices[slot].generation, queueContext_.objectId);
        if (!parsed.ok()) return reject(codecFileError(parsed.error), parsed.nativeError);
        const bool protectedMode = parsed.value->mode == CustodyBootstrapMode::protectedStore;
        SecureZeroMemory(&*parsed.value, sizeof(CustodyBootstrapValue));
        // BOTH protected/null are required before any completed-history admission.
        // A migrating peer still belongs exclusively to migration recovery.
        if (!protectedMode) return reject(CustodyFileError::recoveryRequired);
    }
    auto queue = queue_->readValidatedMetadataPair();
    if (!queue.ok()) return reject(queue.error, queue.nativeError);
    std::shared_ptr<const ProtectedUploadQueueValue> selected;
    for (unsigned slot = 0; slot < 2; ++slot) {
        auto bytes = readMetadataValue(*queue_, queueContext_, queue.value->indices[slot], cancellation);
        if (!bytes.ok()) return reject(bytes.error, bytes.nativeError);
        struct Wipe {
            CustodyBytes& value;
            ~Wipe() { if (!value.empty()) SecureZeroMemory(value.data(), value.size()); }
        } wipe{*bytes.value};
        auto decoded = ProtectedUploadQueueValue::decode(
            {reinterpret_cast<const char*>(bytes.value->data()), bytes.value->size()}, cancellation.get());
        if (!decoded.ok()) return reject(decoded.error, decoded.nativeError);
        if ((selectedValue || coldAdmission) && slot == queue.value->selectedSlot) selected = std::move(*decoded.value);
    }
    const auto generation = queue.value->indices[queue.value->selectedSlot].generation;
    if (queueGeneration_ && queueGeneration_ != generation) return reject(CustodyFileError::conflict);
    CustodyVector<CustodyString> absentPackages;
    if (coldAdmission) {
        auto absent=root_->validateQueuePackages(*selected,cancellation,false,absentPackages);
        if (!absent.ok()) return reject(absent.error,absent.nativeError);
    }
    if (migrationScopes) for (const auto& directory : *migrationScopes) {
        if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        const std::string_view name(directory);
        // Root queue admission does not reopen an active package-state owner.
        // Every package consumer/effect checks its actual retained Pair below.
        if (!coldAdmission && !name.empty()) continue;
        const auto subject = name.empty() ? CustodyMigrationSubject::queue : CustodyMigrationSubject::package;
        auto opened = ProtectedCustodyFiles::openStoreObject(root_, CustodyRole::migrationIntent, false, name);
        if (!opened.ok()) return reject(opened.error, opened.nativeError);
        const auto context = (*opened.value)->context();
        if (context.storeId != queueContext_.storeId || context.objectId == context.storeId ||
            context.objectId == queueContext_.objectId || context.objectId == own.objectId)
            return reject(CustodyFileError::identityMismatch);
        // Same root and intent lease from locator through independently authenticated
        // Birth, strict current BOTH records, progression and every later file proof.
        auto history = ProtectedCustodyMigrationPair::readImpl(root_->trustedRoot(), context, std::nullopt,
            subject, name, cancellation, {}, std::move(*opened.value));
        if (!history.ok()) return reject(history.error, history.nativeError);
        for (const auto& record : (*history.value)->slots()) {
            if (record.stage < CustodyMigrationStage::switched || !record.barrier ||
            (record.stage==CustodyMigrationStage::switched ? record.authorization.has_value() : !record.authorization))
                return reject(CustodyFileError::recoveryRequired);
            if (subject == CustodyMigrationSubject::queue) {
                const auto& source = record.sources[0];
                if (source.destinationObjectId != queueContext_.objectId || !source.destinationGeneration ||
                    *source.destinationGeneration > generation)
                    return reject(CustodyFileError::invalidContent);
                // An authenticated historical copy receipt is not today's mutable
                // queue snapshot; BOTH current queue payloads were strictly decoded above.
            } else if (!record.anchor.objectId || *record.anchor.objectId != queueContext_.objectId ||
                !record.anchor.generation || *record.anchor.generation > generation)
                return reject(CustodyFileError::invalidContent);
            if (record.authorization && (record.authorization->queueObjectId!=queueContext_.objectId ||
                record.authorization->queueGeneration>generation)) return reject(CustodyFileError::conflict);
        }
        if (coldAdmission && subject == CustodyMigrationSubject::package) {
            auto state = ProtectedCustodyFiles::openPackageState(root_, name, cancellation);
            if (!state.ok()) return reject(state.error, state.nativeError);
            const auto identity = (*state.value)->context();
            if (identity.storeId != queueContext_.storeId || identity.objectId == identity.storeId ||
                identity.objectId == queueContext_.objectId || identity.objectId == own.objectId || identity.objectId == context.objectId)
                return reject(CustodyFileError::identityMismatch);
            auto retained = std::shared_ptr<ProtectedCustodyFiles>(state.value->release(),
                [](ProtectedCustodyFiles* files) { delete files; }, CustodyAllocator<ProtectedCustodyFiles>{});
            auto pair = ProtectedCustodyPackagePair::readImpl(root_->trustedRoot(), name, identity, cancellation,
                std::move(retained), ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly);
            if (!pair.ok()) return reject(pair.error, pair.nativeError);
            // No consumer exists during cold admission. Verify BOTH closures,
            // including noncurrent retained roots, and hold all member leases
            // through history/barrier/original verification before exposing Owner.
            auto readers = openProtectedCustodyReaders(root_->trustedRoot(), *pair.value, cancellation);
            if (!readers.ok()) return reject(readers.error, readers.nativeError);
            auto complete = validateMigrationPackageHistory(*pair.value, cancellation, *history.value);
            if (!complete.ok()) return reject(complete.error, complete.nativeError);
        }
        if (subject == CustodyMigrationSubject::queue) {
            auto files = (*history.value)->lease_->validateMigrationFiles((*history.value)->current(), (*history.value)->slots()[1U-(*history.value)->selectedSlot()], cancellation);
            if (!files.ok()) return reject(files.error, files.nativeError);
        } // Cold package checks above retained readers through fixed-file validation.
    }
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    auto absent=root_->validateQueueAbsences(absentPackages,cancellation);
    if (!absent.ok()) return reject(absent.error,absent.nativeError);
    queueGeneration_ = generation;
    if (selectedValue) *selectedValue = std::move(selected);
    return {true, CustodyFileError::none, 0};
#endif
    } catch (const std::bad_alloc&) { return reject(CustodyFileError::allocationFailed); }
      catch (const std::system_error& error) { return reject(CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())); }
}

CustodyFileResult<std::shared_ptr<const ProtectedUploadQueueValue>> ProtectedCustodyStoreOwner::readQueueValue(
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Value = std::shared_ptr<const ProtectedUploadQueueValue>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Value> {
        return {std::nullopt, error, native};
    };
    if (!cancellation) return reject(CustodyFileError::invalidInput);
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, 995);
    if (failed_) return reject(CustodyFileError::recoveryRequired);
    CustodyNativeJob job;
    if (!job) return reject(CustodyFileError::allocationFailed);
    Value selected;
    auto checked = validate(cancellation, &selected);
    if (!checked.ok()) {
        return reject(checked.error, checked.nativeError);
    }
    if (cancellation->load()) {
        return reject(CustodyFileError::ioFailed, 995);
    }
    return {std::move(selected), CustodyFileError::none, 0};
} catch (const std::bad_alloc&) {
    return {std::nullopt, CustodyFileError::allocationFailed, 0};
}

CustodyFileResult<std::shared_ptr<ProtectedCustodyStoreOwner>> ProtectedCustodyStoreOwner::open(
    const std::filesystem::path& root, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Owner = std::shared_ptr<ProtectedCustodyStoreOwner>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Owner> {
        return {std::nullopt, error, native};
    };
    if (!cancellation) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)root;
    return reject(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyNativeJob job;
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyPin pin;
    if (!pin) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyAllocator<ProtectedCustodyStoreOwner> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedCustodyStoreOwner(std::move(pin)); }
    catch (...) { allocator.deallocate(raw, 1); throw; }
    Owner owner{raw, [](ProtectedCustodyStoreOwner* p) {
        p->~ProtectedCustodyStoreOwner(); CustodyAllocator<ProtectedCustodyStoreOwner>{}.deallocate(p, 1);
    }, allocator};
    bool birth = false;
    auto held = ProtectedCustodyFiles::lockStoreRoot(root, cancellation, birth);
    if (!held.ok()) return reject(held.error, held.nativeError);
    owner->root_ = std::shared_ptr<ProtectedCustodyFiles>(held.value->release(),
        [](ProtectedCustodyFiles* p) { delete p; }, CustodyAllocator<ProtectedCustodyFiles>{});
    auto queue = ProtectedCustodyFiles::openStoreObject(owner->root_, CustodyRole::queue, birth);
    if (!queue.ok()) return reject(queue.error, queue.nativeError);
    owner->queue_ = std::move(*queue.value);
    owner->queueContext_ = owner->queue_->context();
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    auto bootstrap = ProtectedCustodyFiles::openStoreObject(owner->root_, CustodyRole::bootstrap, birth);
    if (!bootstrap.ok()) return reject(bootstrap.error, bootstrap.nativeError);
    owner->bootstrap_ = std::move(*bootstrap.value);
    if (owner->bootstrap_->context().objectId == owner->queueContext_.objectId)
        return reject(CustodyFileError::identityMismatch);
    if (birth) {
        const auto json = DesktopUploadQueueService::emptyLedgerJson;
        CustodyBytes value(json.begin(), json.end());
        struct WipeBytes {
            CustodyBytes& value;
            ~WipeBytes() { if (!value.empty()) SecureZeroMemory(value.data(), value.size()); }
        } wipeValue{value};
        {
            auto saved = CustodyMetadataCommit::commitImpl(root, {}, owner->queueContext_, 0, value, cancellation, owner->queue_.get());
            if (saved.state != CustodyCommitState::committed) return reject(saved.error, saved.nativeError);
        } // Release snapshot/pin before the next independent birth.
        CustodyBootstrapValue state{};
        state.context = owner->bootstrap_->context(); state.generation = 1;
        state.mode = CustodyBootstrapMode::protectedStore; state.queueObjectId = owner->queueContext_.objectId;
        auto encoded = writeCustodyBootstrap(state, state.context, 1, state.queueObjectId);
        SecureZeroMemory(&state, sizeof(state));
        if (!encoded.ok()) return reject(codecFileError(encoded.error), encoded.nativeError);
        WipeBytes wipeBootstrap{*encoded.value};
        auto committed = CustodyMetadataCommit::commitImpl(root, {}, owner->bootstrap_->context(),
            0, *encoded.value, cancellation, owner->bootstrap_.get());
        if (committed.state != CustodyCommitState::committed) return reject(committed.error, committed.nativeError);
    }
    auto validated = owner->validate(cancellation, nullptr, true);
    if (!validated.ok()) return reject(validated.error, validated.nativeError);
    auto inventory = owner->root_->validateStoreInventory(false, cancellation, birth);
    if (!inventory.ok()) return reject(inventory.error, inventory.nativeError);
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return {std::move(owner), CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyMetadataCommit commitProtectedCustodyMetadata(std::shared_ptr<ProtectedCustodyStoreOwner> owner,
    const CustodyContext& expected, std::uint64_t base, const CustodyBytes& value,
    std::shared_ptr<const std::atomic<bool>> cancellation) {
    CustodyMetadataCommit rejected;
    rejected.context = expected; rejected.baseGeneration = base;
    if (!owner || !cancellation || !base || base == (std::numeric_limits<std::uint64_t>::max)() ||
        value.empty() || value.size() > ProtectedCustodyCodec::logicalLimit(CustodyRole::queue) || expected.role != CustodyRole::queue) {
        rejected.error = CustodyFileError::invalidInput;
        return rejected;
    }
#ifndef _WIN32
    rejected.error = CustodyFileError::unsupportedPlatform;
    return rejected;
#else
    if (cancellation->load()) {
        rejected.error = CustodyFileError::ioFailed; rejected.nativeError = ERROR_OPERATION_ABORTED;
        return rejected;
    }
    if (expected.storeId != owner->queueContext_.storeId || expected.objectId != owner->queueContext_.objectId) {
        rejected.error = CustodyFileError::identityMismatch;
        return rejected;
    }
    if (owner->failed_ || (owner->shortDiscard_ && owner->shortDiscard_->attempted) || base != owner->queueGeneration_) {
        rejected.error = owner->failed_ || (owner->shortDiscard_ && owner->shortDiscard_->attempted)
            ? CustodyFileError::recoveryRequired : CustodyFileError::conflict;
        return rejected;
    }
    CustodyNativeJob job;
    auto held = std::move(owner); // Last temporary owner closes before job admission.
    if (!job) {
        rejected.error = CustodyFileError::allocationFailed; rejected.nativeError = ERROR_NOT_ENOUGH_QUOTA;
        return rejected;
    }
    bool commitAttempted = false;
    try {
        auto decoded = held->validateQueueValue({reinterpret_cast<const char*>(value.data()), value.size()}, cancellation.get());
        if (!decoded.ok()) {
            rejected.error = decoded.error; rejected.nativeError = decoded.nativeError;
            return rejected;
        }
        // Actual BOTH semantic revalidation under the same native identities,
        // not a cached bool/readiness flag or a generation taken from JSON.
        auto current = held->validate(cancellation);
        if (!current.ok()) {
            rejected.error = current.error; rejected.nativeError = current.nativeError;
            return rejected;
        }
        if (held->queueGeneration_ != base) { rejected.error = CustodyFileError::conflict; return rejected; }
        commitAttempted = true;
        auto committed = CustodyMetadataCommit::commitImpl(held->rootPath(), {}, expected, base, value,
            cancellation, held->queue_.get());
        committed.owner_ = held;
        if (committed.state == CustodyCommitState::committed) held->queueGeneration_ = committed.targetGeneration;
        else held->failed_ = true; // Retain failed native writer; no bool fallback or lease reopening.
        return committed;
    } catch (const std::bad_alloc&) {
        held->failed_ = commitAttempted;
        rejected.error = CustodyFileError::allocationFailed;
        // Before commit even starts, allocation refusal is known notCommitted.
        // A throwing result move after it starts may follow actual publication.
        if (commitAttempted) rejected.state = CustodyCommitState::ambiguous;
        rejected.owner_ = std::move(held);
        return rejected;
    } catch (const std::system_error& error) {
        held->failed_ = commitAttempted;
        rejected.error = CustodyFileError::ioFailed; rejected.nativeError = static_cast<std::uint32_t>(error.code().value());
        if (commitAttempted) rejected.state = CustodyCommitState::ambiguous;
        rejected.owner_ = std::move(held);
        return rejected;
    }
#endif
}

CustodyMetadataCommit commitProtectedCustodyMetadata(const std::filesystem::path& root,
    std::string_view package, const CustodyContext& context, std::uint64_t base,
    const CustodyBytes& value, std::shared_ptr<const std::atomic<bool>> cancellation) {
    return CustodyMetadataCommit::commitImpl(root, package, context, base, value, std::move(cancellation), nullptr);
}

CustodyMetadataCommit CustodyMetadataCommit::commitImpl(const std::filesystem::path& root,
    std::string_view package, const CustodyContext& context, std::uint64_t base,
    const CustodyBytes& value, std::shared_ptr<const std::atomic<bool>> cancellation,
    ProtectedCustodyFiles* files) {
    CustodyMetadataCommit result;
    result.context = context; result.baseGeneration = base;
    bool publicationStarted = false;
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) {
        result.error = error; result.nativeError = native;
        if (publicationStarted) result.state = CustodyCommitState::ambiguous;
        result.snapshot.reset(); // Error return must not retry an allocating snapshot move.
        if (files) files->blockWrites();
        else result.pin_.reset(); // Failed factory/admission has no retained owner.
        return std::move(result);
    };
    const auto role = static_cast<unsigned>(context.role);
    if (role < static_cast<unsigned>(CustodyRole::manifest) || role > static_cast<unsigned>(CustodyRole::migrationIntent)
        || !cancellation || value.empty() || value.size() > ProtectedCustodyCodec::logicalLimit(context.role)
        || base == (std::numeric_limits<std::uint64_t>::max)()) return reject(CustodyFileError::invalidInput);
    result.targetGeneration = base + 1;
#ifndef _WIN32
    (void)root; (void)package;
    return reject(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    try {
        result.pin_.emplace();
        if (!*result.pin_) { result.pin_.reset(); return reject(CustodyFileError::allocationFailed); }
        // ponytail: serialize metadata staging (one 256KiB dirty block/process).
        // Split only on measured contention with equally bounded dirty admission.
        static std::mutex staging;
        std::lock_guard<std::mutex> lock(staging);
        if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        CustodyDirtySlot dirty;
        if (!dirty) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
        CustodyIndex candidate{base + 1, value.size(), {}};
        const auto count = (value.size() + ProtectedCustodyCodec::blockBytes - 1) / ProtectedCustodyCodec::blockBytes;
        candidate.entries.reserve(count);
        CustodyBytes chunk; chunk.reserve(std::min<std::size_t>(value.size(), ProtectedCustodyCodec::blockBytes));
        struct Wipe { CustodyBytes& bytes; ~Wipe() { if (!bytes.empty()) SecureZeroMemory(bytes.data(), bytes.size()); } } wipe{chunk};
        if (!files) {
            auto opened = ProtectedCustodyFiles::open(root, package, context,
                base ? CustodyFileAccess::writeExisting : CustodyFileAccess::createNew);
            if (!opened.ok()) return reject(opened.error, opened.nativeError);
            result.lease = std::move(*opened.value);
            files = result.lease.get();
        }
        auto group = files->lockWriteGroup(); // Same shared root exclusion as packed physical growth.
        if (base) {
            auto current = files->readValidatedSnapshot();
            if (!current.ok()) return reject(current.error, current.nativeError);
            if (current.value->state != CustodySnapshotState::verified || current.value->index.generation != base)
                return reject(CustodyFileError::conflict);
        }
        const auto indexCopies = base ? 1U : 2U;
        const auto peak = value.size() + count * 4096 + indexCopies * ProtectedCustodyCodec::indexEnvelopeLimit(context.role);
        auto reserved = files->checkWriteReserve(peak, static_cast<std::uint32_t>(count) + indexCopies);
        if (!reserved.ok()) return reject(reserved.error, reserved.nativeError);
        std::uint64_t position = 0;
        for (std::size_t offset = 0; offset < value.size(); offset += chunk.size(), ++position) {
            if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            const auto bytes = std::min<std::size_t>(ProtectedCustodyCodec::blockBytes, value.size() - offset);
            if (!chunk.empty()) SecureZeroMemory(chunk.data(), chunk.size());
            chunk.assign(value.begin() + offset, value.begin() + offset + bytes);
            auto version = files->nextBlockVersion(position);
            if (!version.ok()) return reject(version.error, version.nativeError);
            auto cipher = ProtectedCustodyCodec::sealBlock(context, position, *version.value, chunk);
            if (!cipher.ok()) return reject(codecFileError(cipher.error), cipher.nativeError);
            auto written = files->writeBlock(position, *version.value, static_cast<std::uint32_t>(bytes), *cipher.value);
            if (!written.ok()) return reject(written.error, written.nativeError);
            candidate.entries.push_back({*version.value, *written.value, 0});
        }
        if (!chunk.empty()) SecureZeroMemory(chunk.data(), chunk.size());
        CustodyBytes{}.swap(chunk);
        const auto slot = static_cast<std::uint32_t>(base % 2);
        std::array<CustodyBytes, 2> indices;
        for (unsigned copy = 0; copy < indexCopies; ++copy) {
            auto cipher = ProtectedCustodyCodec::sealIndex(context, base ? slot : copy, candidate);
            if (!cipher.ok()) return reject(codecFileError(cipher.error), cipher.nativeError);
            indices[copy] = std::move(*cipher.value);
        }
        if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        for (unsigned copy = 0; copy < indexCopies; ++copy) {
            // Cancellation no longer rolls back publication; finish both birth
            // slots/reopen even when UI/account capability becomes stale.
            publicationStarted = true;
            const auto published = files->publishIndex(base ? slot : copy, indices[copy]);
            if (published.state != CustodyPublishState::published) {
                if (copy == 0 && published.state == CustodyPublishState::notPublished) publicationStarted = false;
                return reject(published.error, published.nativeError);
            }
        }
        indices = {}; // Release writer cipher copies before independent reopen.
        auto reopened = files->readValidatedSnapshot();
        if (!reopened.ok()) return reject(reopened.error, reopened.nativeError);
        const auto& accepted = reopened.value->index;
        if (reopened.value->state != CustodySnapshotState::verified || accepted.generation != candidate.generation
            || accepted.logicalLength != candidate.logicalLength || accepted.entries.size() != candidate.entries.size()
            || !std::equal(accepted.entries.begin(), accepted.entries.end(), candidate.entries.begin(), [](const auto& a, const auto& b) {
                return a.version == b.version && a.envelopeBytes == b.envelopeBytes && a.flags == b.flags;
            })) return reject(CustodyFileError::conflict);
        result.snapshot = std::move(*reopened.value);
        result.state = CustodyCommitState::committed;
        return result;
    } catch (const std::bad_alloc&) { return reject(CustodyFileError::allocationFailed); }
      catch (const std::system_error& error) { return reject(CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())); }
#endif
}

} // namespace graf::windows
