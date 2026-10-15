#include "ProtectedCustodyMetadata.h"
#include "ProtectedCustodyPrimitives.h"
#include "ProtectedCustodyWriter.h"
#include "ProtectedPackedCustodyTree.h"
#include "ProtectedCustodyReader.h"
#include "Sha256.h"
#include "../Upload/DesktopUploadQueueService.h"
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
CustodyFileResult<std::shared_ptr<const ProtectedCustodyMigrationPair>> ProtectedCustodyMigrationPair::readImpl(
    const std::filesystem::path& root, CustodyContext own, const CustodyId& transaction,
    CustodyMigrationSubject subject, std::string_view name, std::shared_ptr<const std::atomic<bool>> cancellation,
    std::shared_ptr<const ProtectedCustodyBootstrapPair> bootstrap) try {
    using Proof = std::shared_ptr<const ProtectedCustodyMigrationPair>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Proof> {
        return {std::nullopt, error, native};
    };
    if (own.role != CustodyRole::migrationIntent || !cancellation ||
        (subject == CustodyMigrationSubject::queue ? !name.empty() :
         subject != CustodyMigrationSubject::package || !identity(name))) return reject(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)root; (void)transaction; (void)bootstrap; return reject(CustodyFileError::unsupportedPlatform);
#else
    const auto cancelled = [&] { return cancellation->load(); };
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    CustodyNativeJob job;
    auto held = std::move(bootstrap); // Failure closes parent leases before job admission releases.
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyPin pin;
    if (!pin) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    auto opened = held ? ProtectedCustodyFiles::discover(root, CustodyRole::migrationIntent, name)
        : ProtectedCustodyFiles::open(root, name, own, CustodyFileAccess::writeExisting);
    if (!opened.ok()) return reject(opened.error, opened.nativeError);
    auto lease = std::move(*opened.value);
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    if (held) {
        own = lease->context();
        if (own.storeId != held->current().context.storeId) return reject(CustodyFileError::identityMismatch);
    }
    auto pair = lease->readValidatedMetadataPair();
    if (!pair.ok()) return reject(pair.error, pair.nativeError);
    std::array<CustodyMigrationValue, 2> values{};
    struct WipeValues {
        std::array<CustodyMigrationValue, 2>& values;
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
        auto parsed = readCustodyMigration({reinterpret_cast<const char*>(plain.value->data()), plain.value->size()},
            own, index.generation, transaction, subject, name);
        if (!parsed.ok()) return reject(codecFileError(parsed.error), parsed.nativeError);
        values[slot] = *parsed.value;
        SecureZeroMemory(&*parsed.value, sizeof(CustodyMigrationValue));
        if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        if (held && (subject == CustodyMigrationSubject::queue
            ? values[slot].sources[0].destinationObjectId != held->current().queueObjectId
            : !values[slot].anchor.objectId || *values[slot].anchor.objectId != held->current().queueObjectId))
            return reject(CustodyFileError::invalidContent);
        if (values[slot].barrier) {
            const auto& ref = *values[slot].barrier;
            auto envelope = lease->readMigrationBirthEnvelope(ref.blockVersion, static_cast<std::uint32_t>(ref.envelopeBytes));
            if (!envelope.ok()) return reject(envelope.error, envelope.nativeError);
            if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            auto birth = readCustodyMigrationBirth(*envelope.value, own, values[slot], transaction, subject, name);
            if (!birth.ok()) return reject(codecFileError(birth.error), birth.nativeError);
            SecureZeroMemory(&*birth.value, sizeof(CustodyMigrationValue));
        }
    }
    const auto selected = pair.value->selectedSlot;
    if (!migrationProgress(values[1U - selected], values[selected])) return reject(CustodyFileError::conflict);
    if (cancelled()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    lease->blockWrites();
    CustodyAllocator<ProtectedCustodyMigrationPair> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedCustodyMigrationPair(std::move(pin), std::move(held), std::move(lease), std::move(*pair.value), values); }
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

CustodyFileResult<bool> ProtectedCustodyStoreOwner::purgeLocalPackage(std::string_view localId,
    std::uint64_t expectedGeneration, ProtectedUploadQueueValue& candidate, std::uint64_t now,
    std::shared_ptr<const std::atomic<bool>> cancellation, const BasicLocalPurgeTask<CustodyString>* serverTask,
    std::string_view user, std::string_view workspace) try {
    if (!cancellation || !identity(localId)) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (serverTask && (!validLocalBufferPurgeTask(*serverTask) || !DesktopApiClient::accountId(user) ||
        !DesktopApiClient::accountId(workspace))) return {false, CustodyFileError::none, 0};
    const bool userScoped = !user.empty() || !workspace.empty();
    if (userScoped && (!DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace)))
        return {false, CustodyFileError::none, 0};
    if (failed_) return {std::nullopt, CustodyFileError::recoveryRequired, 0};
#ifndef _WIN32
    (void)expectedGeneration; (void)candidate; (void)now;
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
        {
            // Validate BOTH actual member closures; metadata alone is not proof.
            auto readers = openProtectedCustodyReaders(rootPath(), pair, cancellation);
            if (!readers.ok()) return {std::nullopt, readers.error, readers.nativeError};
        }
        // Open while genuine package leases still exclude rename/replacement.
        // Keep this object's identity alive across Shell's source/destination
        // checks. SHARE_DELETE is NOT an adversarial same-SID race barrier;
        // the sole GRAF worker has already drained and fenced all its writers.
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
        pair.reset(); // Only this guard survives; no native member/readers may remain.
        CustodyNativeJob job;
        if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
        if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
        if (!DesktopLocalPurgeService::recycle(path, 0, reinterpret_cast<std::uintptr_t>(guard.value)))
            return {false, CustodyFileError::none, 0};
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
    return ProtectedCustodyPackagePair::readImpl(root_->trustedRoot(), name, own, std::move(cancellation), std::move(held),
        ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly);
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<bool> ProtectedCustodyStoreOwner::revalidatePackage(
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
    {
        CustodyNativeJob job; // Cover current store/queue validation, not the nested pair's own admission.
        if (!job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
        auto checked = validate(cancellation);
        if (!checked.ok()) return checked;
    }
    const auto name = directory(held->current());
    // Re-read BOTH indices, referenced blocks and semantic payloads through the
    // SAME native lease. Never release/reopen identity or adopt a newer state.
    auto fresh = ProtectedCustodyPackagePair::readImpl(root_->trustedRoot(), name, own, cancellation, files,
        ProtectedCustodyPackagePair::LeaseOrigin::isolatedReadOnly);
    if (!fresh.ok()) return {std::nullopt, fresh.error, fresh.nativeError};
    const auto& actual = **fresh.value;
    if (held->selectedSlot() != actual.selectedSlot()) return {std::nullopt, CustodyFileError::conflict, 0};
    for (unsigned slot = 0; slot < 2; ++slot) {
        const auto& before = held->indices().indices[slot];
        const auto& after = actual.indices().indices[slot];
        if (before.generation != after.generation || before.logicalLength != after.logicalLength ||
            before.entries.size() != after.entries.size() ||
            !std::equal(before.entries.begin(), before.entries.end(), after.entries.begin(), [](const auto& a, const auto& b) {
                return a.version == b.version && a.envelopeBytes == b.envelopeBytes && a.flags == b.flags;
            })) return {std::nullopt, CustodyFileError::conflict, 0};
        // Reuse the closed canonical codec rather than comparing struct padding
        // or duplicating its fields. CustodyAllocator wipes both retiring buffers.
        auto expected = writeCustodyPackage(held->slots()[slot], own, before.generation, name);
        if (!expected.ok()) return {std::nullopt, codecFileError(expected.error), expected.nativeError};
        auto observed = writeCustodyPackage(actual.slots()[slot], own, after.generation, name);
        if (!observed.ok()) return {std::nullopt, codecFileError(observed.error), observed.nativeError};
        if (*expected.value != *observed.value) return {std::nullopt, CustodyFileError::conflict, 0};
    }
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
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
    if (failed_) return reject(CustodyFileError::recoveryRequired);
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
    auto directory = ProtectedCustodyFiles::createPackageRoot(raw->root_, name, raw->cancellation_, &raw->packageRoot_);
    if (!directory.ok()) return reject(directory.error, directory.nativeError);
    raw->packageRoot_ = std::move(*directory.value);
    auto state = ProtectedCustodyFiles::createPackageRole(raw->packageRoot_, CustodyRole::packageState, &raw->state_);
    if (!state.ok()) return reject(state.error, state.nativeError);
    raw->state_ = std::move(*state.value);
    raw->context_ = raw->state_->context();
    if (raw->context_.objectId == queueContext_.objectId || raw->context_.objectId == bootstrap_->context().objectId)
        return reject(CustodyFileError::identityMismatch);
    for (unsigned index = 0; index < raw->roles_.size(); ++index) {
        auto role = ProtectedCustodyFiles::createPackageRole(raw->packageRoot_, static_cast<CustodyRole>(index + 1), &raw->roles_[index]);
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

ProtectedCustodyStoreOwner::ProtectedCustodyStoreOwner(CustodyPin&& pin) {
    pin_.emplace(std::move(pin));
}
ProtectedCustodyStoreOwner::~ProtectedCustodyStoreOwner() = default;

CustodyFileResult<bool> ProtectedCustodyStoreOwner::validate(
    std::shared_ptr<const std::atomic<bool>> cancellation,
    std::shared_ptr<const ProtectedUploadQueueValue>* selectedValue) {
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
    (void)selectedValue;
    return reject(CustodyFileError::unsupportedPlatform);
#else
    auto inventory = root_->validateStoreInventory(false, cancellation);
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
        // This first regular-store owner deliberately does not resolve migration
        // histories/tombstones. Those roots remain closed for the T117 owner.
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
        if (selectedValue && slot == queue.value->selectedSlot) selected = std::move(*decoded.value);
    }
    const auto generation = queue.value->indices[queue.value->selectedSlot].generation;
    if (queueGeneration_ && queueGeneration_ != generation) return reject(CustodyFileError::conflict);
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
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
    auto validated = owner->validate(cancellation);
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
    if (owner->failed_ || base != owner->queueGeneration_) {
        rejected.error = owner->failed_ ? CustodyFileError::recoveryRequired : CustodyFileError::conflict;
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
