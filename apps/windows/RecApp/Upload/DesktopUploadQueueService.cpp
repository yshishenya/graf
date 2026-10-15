#include "DesktopUploadQueueService.h"
#include "DesktopHttpTransport.h"

#include "../Storage/AtomicFileStore.h"
#include "../Contracts/JsonString.h"
#include "../Contracts/JsonReader.h"

#include <cctype>
#include <charconv>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <system_error>
#include <utility>

namespace graf::windows {
namespace {

std::size_t objectEnd(std::string_view json, std::size_t start, const std::atomic<bool>* cancellation) {
    if (start >= json.size() || json[start] != '{') return std::string_view::npos;
    std::size_t depth = 0;
    bool quoted = false;
    bool escaped = false;
    for (std::size_t index = start; index < json.size(); ++index) {
        if (((index - start) & 4095) == 0) json_detail::checkCancellation(cancellation);
        const auto character = json[index];
        if (escaped) { escaped = false; continue; }
        if (quoted && character == '\\') { escaped = true; continue; }
        if (character == '"') { quoted = !quoted; continue; }
        if (quoted) continue;
        if (character == '{') ++depth;
        if (character == '}' && depth > 0 && --depth == 0) return index;
    }
    return std::string_view::npos;
}

template<class String, class Fields>
std::optional<String> stringField(const Fields& fields, std::string_view key, const std::atomic<bool>* cancellation) {
    const auto field = fields.find(key);
    if (field == fields.end() || field->second.size() > 4 * 1024 * 1024) return std::nullopt;
    json_detail::checkCancellation(cancellation);
    String result;
    result.reserve(field->second.size());
    std::size_t emitted = 0;
    if (!json_detail::decodeString(field->second, 4 * 1024 * 1024, false,
                                  [&](char c) {
        if ((emitted++ & 4095) == 0) json_detail::checkCancellation(cancellation);
        result += c;
    })) return std::nullopt;
    return result;
}

std::optional<std::uint64_t> unsignedToken(std::string_view token) {
    std::uint64_t value = 0;
    const auto parsed = std::from_chars(token.data(), token.data() + token.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != token.data() + token.size()) return std::nullopt;
    return value;
}

template<class Fields>
std::optional<std::uint64_t> numberField(const Fields& fields, std::string_view key) {
    const auto field = fields.find(key);
    return field == fields.end() ? std::nullopt : unsignedToken(field->second);
}

template<template<class> class Allocator, class String, class Fields>
std::optional<std::array<std::uint64_t, 3>> acceptedField(const Fields& fields, const std::atomic<bool>* cancellation) {
    const auto field = fields.find("accepted_bytes");
    if (field == fields.end()) return std::nullopt;
    json_detail::JsonReader<Allocator, String> reader(field->second, 32, false, cancellation);
    const auto values = reader.readArray();
    if (!values || values->size() != 3) return std::nullopt;
    std::array<std::uint64_t, 3> result{};
    for (std::size_t index = 0; index < result.size(); ++index) {
        const auto value = unsignedToken((*values)[index]);
        if (!value) return std::nullopt;
        result[index] = *value;
    }
    return result;
}

} // namespace

namespace {

constexpr std::array<std::uint64_t, 4> kDeletionRetryDelayMs = {5000, 15000, 30000, 60000};

template<class Item>
bool retryableStatus(const Item& item) noexcept {
    return !DesktopUploadQueueService::isPermanentUploadReason(item.safeReason) &&
        (item.status == UploadQueueStatus::pending || item.status == UploadQueueStatus::retry ||
         item.status == UploadQueueStatus::needsAuth || item.status == UploadQueueStatus::blocked);
}

template<class Operation, class Receipt>
bool deletionReceiptMatches(const Operation& record, const Receipt& receipt) {
    if (!receipt.accepted() || !DesktopApiClient::accountId(receipt.requestId)) return false;
    if (record.target == DeletionTarget::ownOrigin)
        return receipt.localRecordingId == record.targetId &&
            (receipt.receiptType == "origin_cancellation" ||
             (receipt.receiptType == "meeting_deletion" && !receipt.meetingId.empty()));
    return record.target == DeletionTarget::meeting && receipt.receiptType == "meeting_deletion" &&
        receipt.meetingId == record.targetId;
}

std::uint64_t deletionRetryAt(std::uint64_t now, std::uint64_t delay) noexcept {
    return now + std::min(delay, std::numeric_limits<std::uint64_t>::max() - now);
}

template<class Operation>
bool markDeletionPhaseValue(Operation& record, DeletionOperationPhase phase, std::string_view reason,
    std::uint64_t now) {
    if (now < record.updatedAtMs ||
        phase == DeletionOperationPhase::accepted || record.phase == DeletionOperationPhase::verified ||
        (deletionPhaseIsAccepted(record.phase) && phase != DeletionOperationPhase::verified) ||
        (phase == DeletionOperationPhase::verified && record.phase != DeletionOperationPhase::accepted)) return false;
    record.phase = phase; record.updatedAtMs = now; record.safeReason = reason;
    record.nextAttemptAtMs = 0;
    if (phase == DeletionOperationPhase::sending) {
        if (record.attemptCount < std::numeric_limits<std::uint32_t>::max()) ++record.attemptCount;
    } else if (phase == DeletionOperationPhase::resolving) {
        const auto attempts = record.attemptCount == 0 ? std::size_t{0} : record.attemptCount - 1;
        record.nextAttemptAtMs = deletionRetryAt(now,
            kDeletionRetryDelayMs[std::min(attempts, kDeletionRetryDelayMs.size() - 1)]);
    }
    return true;
}

template<class Operation, class Receipt>
bool acceptDeletionValue(Operation& record, const Receipt& receipt, std::uint64_t now) {
    if (!deletionReceiptMatches(record, receipt) ||
        (!record.receiptRequestId.empty() && record.receiptRequestId != receipt.requestId)) return false;
    if (record.phase == DeletionOperationPhase::verified) return true;
    if (now < record.updatedAtMs) return false;
    record.phase = DeletionOperationPhase::accepted;
    record.receiptRequestId = receipt.requestId;
    record.updatedAtMs = now; record.nextAttemptAtMs = 0; record.safeReason.clear();
    return true;
}

// Domain transformation only. Callers own the private candidate and publish the
// complete attempt/receipt/identity once; no intermediate sending ledger exists.
template<class Operation, class Items, class String>
bool applyDeletionAnswerValue(Operation& record, Items& items, const BasicDeletionWireResult<String>& wire,
    std::uint64_t now, const std::atomic<bool>* cancellation, bool (*validReason)(std::string_view) noexcept) {
    json_detail::checkCancellation(cancellation);
    if (wire.body.size() > 2 * 1024 * 1024 ||
        !validReason(wire.waitReason) ||
        !markDeletionPhaseValue(record, DeletionOperationPhase::sending, "attempt", now)) return false;
    if (wire.accepted()) {
        const auto receipt = DesktopApiClient::decodeDeletionReceipt<String>(wire.body, cancellation);
        if (receipt && acceptDeletionValue(record, *receipt, now)) {
            if (record.target == DeletionTarget::ownOrigin && !receipt->meetingId.empty()) {
                for (auto& item : items) {
                    json_detail::checkCancellation(cancellation);
                    if (item.ownerUserId != record.actorUserId || item.ownerWorkspaceId != record.workspaceId ||
                        item.directoryId != record.targetId || item.meetingId == receipt->meetingId) continue;
                    item.meetingId = receipt->meetingId; item.updatedAtMs = now;
                }
            }
            return true;
        }
        return markDeletionPhaseValue(record, DeletionOperationPhase::resolving, "unreadable_receipt", now);
    }
    if (!wire.waitReason.empty())
        return markDeletionPhaseValue(record, DeletionOperationPhase::resolving, wire.waitReason, now);
    if (wire.status == 403 && wire.body.find("deletion_forbidden") != String::npos)
        return markDeletionPhaseValue(record, DeletionOperationPhase::rejected, "deletion_forbidden", now);
    std::string_view reason = "connection";
    if (wire.status == 401) reason = "authentication";
    else if (wire.status == 404 || wire.status == 426) reason = "server_update";
    else if (wire.status == 429) reason = "rate_limit";
    if (!markDeletionPhaseValue(record, DeletionOperationPhase::resolving, reason, now)) return false;
    if (wire.retryAfterSeconds != 0) record.nextAttemptAtMs = deletionRetryAt(now,
        std::min<std::uint64_t>(static_cast<std::uint64_t>(wire.retryAfterSeconds) * 1000, 24ULL * 60 * 60 * 1000));
    json_detail::checkCancellation(cancellation);
    return true;
}

template<class Items, class Item>
bool enqueueValue(Items& items, Item item, std::uint64_t now, const std::atomic<bool>* cancellation,
    bool (*validReason)(std::string_view) noexcept) {
    json_detail::checkCancellation(cancellation);
    if (!DesktopUploadQueueService::validIdentity(item.localRecordingId) ||
        !DesktopUploadQueueService::validIdentity(item.directoryId) ||
        !DesktopUploadQueueService::validIdentity(item.sessionId) ||
        !validReason(item.safeReason) ||
        static_cast<unsigned>(item.status) > static_cast<unsigned>(UploadQueueStatus::blocked) ||
        item.ownerUserId.empty() != item.ownerWorkspaceId.empty() ||
        (!item.ownerUserId.empty() && (!DesktopApiClient::accountId(item.ownerUserId) ||
                                     !DesktopApiClient::accountId(item.ownerWorkspaceId)))) return false;
    std::size_t scanned = 0;
    for (const auto& old : items) {
        if ((scanned++ & 255) == 0) json_detail::checkCancellation(cancellation);
        if (old.localRecordingId == item.localRecordingId) return false;
    }
    json_detail::checkCancellation(cancellation);
    item.updatedAtMs = now;
    items.push_back(std::move(item));
    return true;
}

[[nodiscard]] const char* deletionTargetName(DeletionTarget target) noexcept {
    return target == DeletionTarget::ownOrigin ? "own_origin" : "meeting";
}

template<class Operations>
bool requestDeletionValue(Operations& operations, DeletionTarget target, std::string_view targetId,
    std::string_view user, std::string_view workspace, std::string_view origin, std::uint64_t now,
    std::string& operationId, bool& changed, const std::atomic<bool>* cancellation) {
    operationId.clear(); changed = false;
    json_detail::checkCancellation(cancellation);
    if (!DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace) ||
        !DesktopUploadQueueService::validServerOrigin(origin) ||
        (target != DeletionTarget::ownOrigin && target != DeletionTarget::meeting) ||
        (target == DeletionTarget::ownOrigin ? !DesktopUploadQueueService::validIdentity(targetId) :
            !DesktopApiClient::accountId(targetId))) return false;
    const auto derived = DesktopApiClient::deletionOperationId(
        DeletionScope{std::string(user), std::string(workspace)}, target, targetId);
    if (!DesktopApiClient::accountId(derived)) return false;
    for (const auto& existing : operations) {
        json_detail::checkCancellation(cancellation);
        if (std::string_view(existing.operationId) != derived) continue;
        if (std::string_view(existing.actorUserId) != user || std::string_view(existing.workspaceId) != workspace ||
            existing.target != target || std::string_view(existing.targetId) != targetId ||
            std::string_view(existing.serverOrigin) != origin) return false;
        operationId = derived; // Preserve receipt, phase, timestamps and retry budget.
        return true;
    }
    typename Operations::value_type record;
    record.operationId.assign(derived.begin(), derived.end()); record.target = target;
    record.targetId.assign(targetId.begin(), targetId.end()); record.actorUserId.assign(user.begin(), user.end());
    record.workspaceId.assign(workspace.begin(), workspace.end()); record.serverOrigin.assign(origin.begin(), origin.end());
    record.requestedAtMs = record.updatedAtMs = now;
    json_detail::checkCancellation(cancellation);
    operationId = derived;
    operations.push_back(std::move(record));
    changed = true;
    return true;
}

template<class Items, class Operations, class Targets, class Plan>
bool planDeletionSelectionValue(Items& items, Operations& operations, const Targets& targets,
    std::string_view user, std::string_view workspace, std::string_view origin, std::uint64_t now,
    Plan& plan, bool& changed, const std::atomic<bool>* cancellation) {
    changed = false; plan = {};
    json_detail::checkCancellation(cancellation);
    if (targets.empty() || targets.size() > 100 || !DesktopApiClient::accountId(user) ||
        !DesktopApiClient::accountId(workspace) || !DesktopUploadQueueService::validServerOrigin(origin)) return false;
    using String = typename std::decay_t<decltype(plan.operationIds)>::value_type;
    // Resolve the complete bounded input before creating any intent. All callers
    // mutate only a private candidate, including local tombstones.
    for (const auto& target : targets) {
        json_detail::checkCancellation(cancellation);
        auto resolvedTarget = target.target;
        std::string_view resolvedId = target.targetId;
        if (target.target == DeletionTarget::ownOrigin) {
            if (!DesktopUploadQueueService::validIdentity(target.targetId)) return false;
            auto found = items.end();
            for (auto it = items.begin(); it != items.end(); ++it) {
                json_detail::checkCancellation(cancellation);
                if (it->directoryId != target.targetId) continue;
                if (found != items.end()) return false; // Ambiguous directory is not one selected recording.
                found = it;
            }
            if (found == items.end() || std::string_view(found->ownerUserId) != user ||
                std::string_view(found->ownerWorkspaceId) != workspace || found->status == UploadQueueStatus::uploading)
                return false;
            if (!hasUploadServerIdentity(*found)) {
                if (std::find(plan.localOnly.begin(), plan.localOnly.end(), found->localRecordingId) == plan.localOnly.end())
                    plan.localOnly.push_back(found->localRecordingId);
                continue;
            }
            if (!found->meetingId.empty()) { resolvedTarget = DeletionTarget::meeting; resolvedId = found->meetingId; }
        } else if (target.target != DeletionTarget::meeting) return false;
        if (resolvedTarget == DeletionTarget::meeting && !DesktopApiClient::accountId(resolvedId)) return false;
        if (std::any_of(plan.requests.begin(), plan.requests.end(), [&](const auto& entry) {
            return entry.target == resolvedTarget && std::string_view(entry.targetId) == resolvedId;
        })) continue;
        typename std::decay_t<decltype(plan.requests)>::value_type entry;
        entry.target = resolvedTarget; entry.targetId = resolvedId;
        plan.requests.push_back(std::move(entry));
    }
    for (auto& entry : plan.requests) {
        std::string operationId; bool inserted = false;
        if (!requestDeletionValue(operations, entry.target, entry.targetId, user, workspace, origin, now,
            operationId, inserted, cancellation)) return false;
        changed = changed || inserted;
        entry.operationId = std::string_view(operationId); plan.operationIds.push_back(entry.operationId);
        entry.path = entry.target == DeletionTarget::meeting ? DesktopApiClient::meetingDeletionPath<String>(entry.targetId) :
            DesktopApiClient::ownOriginDeletionPath<String>(entry.targetId);
        entry.body = entry.target == DeletionTarget::meeting ? DesktopApiClient::meetingDeletionBody<String>() :
            DesktopApiClient::originCancellationBody<String>(entry.operationId);
        if (entry.path.empty() || entry.body.empty()) return false;
    }
    for (const auto& id : plan.localOnly) for (auto& row : items) {
        json_detail::checkCancellation(cancellation);
        if (row.localRecordingId != id || row.safeReason == "local_delete_pending") continue;
        if (now < row.updatedAtMs) return false;
        row.status = UploadQueueStatus::quarantined; row.safeReason = "local_delete_pending"; row.updatedAtMs = now;
        changed = true;
    }
    plan.requests.erase(std::remove_if(plan.requests.begin(), plan.requests.end(), [&](const auto& entry) {
        json_detail::checkCancellation(cancellation);
        const auto found = std::find_if(operations.begin(), operations.end(), [&](const auto& operation) {
            return operation.operationId == entry.operationId;
        });
        return found == operations.end() || deletionPhaseIsAccepted(found->phase) ||
            found->phase == DeletionOperationPhase::rejected || found->nextAttemptAtMs > now;
    }), plan.requests.end());
    json_detail::checkCancellation(cancellation);
    return !plan.operationIds.empty() || !plan.localOnly.empty();
}

template<class Items, class Stamp>
bool requeueNeedsAuthValues(Items& items, Stamp stamp, const std::atomic<bool>* cancellation) {
    bool changed = false;
    std::size_t scanned = 0;
    json_detail::checkCancellation(cancellation);
    for (auto& item : items) {
        if ((scanned++ & 255) == 0) json_detail::checkCancellation(cancellation);
        if (item.status != UploadQueueStatus::needsAuth) continue;
        item.status = UploadQueueStatus::retry;
        item.safeReason = "auth_recovered";
        stamp(item);
        changed = true;
    }
    json_detail::checkCancellation(cancellation); // Includes an empty/no-change scan.
    return changed;
}

template<class Item, class Truth>
void applyServerTruthValue(Item& item, const Truth& truth, bool (*validSafeReason)(std::string_view)) {
    item.acceptedBytes = truth.acceptedBytes;
    if (item.meetingId.empty() && !truth.meetingId.empty() && DesktopUploadQueueService::validIdentity(truth.meetingId))
        item.meetingId = truth.meetingId;
    const auto adopt = [](auto& field, const auto& value, bool (*valid)(std::string_view)) {
        if (!value.empty() && valid(value)) field = value;
    };
    adopt(item.mediaRevisionId, truth.mediaRevisionId, DesktopUploadQueueService::validIdentity);
    adopt(item.uploadSessionId, truth.uploadSessionId, DesktopUploadQueueService::validIdentity);
    adopt(item.serverStatus, truth.serverStatus, validSafeReason);
    adopt(item.processingStatus, truth.processingStatus, validSafeReason);
    adopt(item.mediaRevisionStatus, truth.mediaRevisionStatus, validSafeReason);
    if (truth.finalized) item.status = UploadQueueStatus::uploaded;
    else if (truth.uploadSessionExists) item.status = UploadQueueStatus::uploading;
}

template<class Operation, class Item>
bool deletionTargetsRow(const Operation& operation, const Item& row) noexcept {
    return (operation.target == DeletionTarget::meeting && operation.targetId == row.meetingId) ||
        (operation.target == DeletionTarget::ownOrigin && operation.targetId == row.directoryId);
}

template<class Item, class Result>
bool applyUploadResultValue(Item& item, const Result& result, bool (*validSafeReason)(std::string_view)) {
    if (static_cast<unsigned>(result.status) > static_cast<unsigned>(DesktopTransportStatus::unsupportedPlatform) ||
        (result.status == DesktopTransportStatus::authRequired &&
         !validSafeReason(result.safeReason))) return false;
    if (result.serverTruth && std::string_view(result.serverTruth->localRecordingId) == std::string_view(item.localRecordingId))
        applyServerTruthValue(item, *result.serverTruth, validSafeReason);
    const auto retry = [&](const char* reason, bool spendAttempt = true) {
        item.status = UploadQueueStatus::retry;
        item.safeReason = reason;
        if (spendAttempt && item.attempts < std::numeric_limits<std::uint32_t>::max()) ++item.attempts;
    };
    switch (result.status) {
    case DesktopTransportStatus::uploaded:
        item.status = UploadQueueStatus::uploaded;
        break;
    case DesktopTransportStatus::authRequired:
        item.status = UploadQueueStatus::needsAuth;
        if (result.safeReason.empty()) item.safeReason = "auth_required";
        else item.safeReason = result.safeReason;
        break;
    case DesktopTransportStatus::invalidPackage:
        item.status = UploadQueueStatus::quarantined;
        item.safeReason = "invalid_package";
        break;
    case DesktopTransportStatus::serverRejected:
        if (result.retryClass == "not_retryable") {
            item.status = UploadQueueStatus::blocked;
            if (DesktopUploadQueueService::isPermanentUploadReason(result.safeReason)) item.safeReason = result.safeReason;
            else item.safeReason = "not_retryable";
        } else if (result.retryClass == "paused_until_user_action") {
            item.status = UploadQueueStatus::needsAuth;
            item.safeReason = "auth_required";
        } else if (result.retryClass == "paused_until_admin_action") {
            item.status = UploadQueueStatus::blocked;
            item.safeReason = "needs_admin";
        } else if (result.retryClass == "terminal") {
            item.status = UploadQueueStatus::quarantined;
            item.safeReason = "terminal_undelivered";
        } else retry("server_rejected");
        break;
    case DesktopTransportStatus::unsupportedPlatform:
        retry("unsupported_platform");
        break;
    case DesktopTransportStatus::retryableFailure:
        retry(result.retryAfterSeconds ? "rate_limited" : "transport_unavailable", !result.retryAfterSeconds);
        break;
    }
    return true;
}

struct QueueSerializationLimit {};

// One field/order/escaping implementation for the existing filesystem-path
// ledger and charged UTF-8 values. Protected output never converts a native path
// or creates an uncharged string/numeric scratch allocation.
template<class Output, class Items, class Operations, class Acknowledgements>
void serializeQueueLedger(Output& json, const Items& items, const Operations& operations,
    const Acknowledgements& acknowledgements, std::uint64_t updatedAtMs,
    const std::atomic<bool>* cancellation, std::size_t limit) {
    const auto append = [&](std::string_view bytes) {
        if (bytes.size() > limit - json.size()) throw QueueSerializationLimit{};
        while (!bytes.empty()) {
            json_detail::checkCancellation(cancellation);
            const auto count = std::min<std::size_t>(4096, bytes.size());
            json.insert(json.end(), bytes.begin(), bytes.begin() + count);
            bytes.remove_prefix(count);
        }
    };
    const auto number = [&](std::uint64_t value) {
        std::array<char, 20> buffer{};
        const auto converted = std::to_chars(buffer.data(), buffer.data() + buffer.size(), value);
        append({buffer.data(), static_cast<std::size_t>(converted.ptr - buffer.data())});
    };
    const auto quote = [&](std::string_view value) {
        append("\"");
        std::size_t start = 0;
        for (std::size_t index = 0; index < value.size(); ++index) {
            if ((index & 4095) == 0) json_detail::checkCancellation(cancellation);
            const auto c = static_cast<unsigned char>(value[index]);
            if (c >= 32 && c != '"' && c != '\\') continue;
            append(value.substr(start, index - start));
            switch (c) {
            case '\\': append("\\\\"); break;
            case '"': append("\\\""); break;
            case '\n': append("\\n"); break;
            case '\r': append("\\r"); break;
            case '\t': append("\\t"); break;
            case '\b': append("\\b"); break;
            case '\f': append("\\f"); break;
            default: {
                constexpr char hex[] = "0123456789abcdef";
                const std::array<char, 6> escaped{'\\', 'u', '0', '0', hex[c >> 4], hex[c & 15]};
                append({escaped.data(), escaped.size()});
                break;
            }
            }
            start = index + 1;
        }
        append(value.substr(start));
        append("\"");
    };
    const auto textField = [&](std::string_view key, std::string_view value) { append(key); quote(value); };
    const auto numberField = [&](std::string_view key, std::uint64_t value) { append(key); number(value); };
    static_assert(kQueueSchemaVersion == "desktop-upload-queue.v3");
    json_detail::checkCancellation(cancellation);
    append(R"({"schema_version":"desktop-upload-queue.v3","items":[)");
    for (std::size_t index = 0; index < items.size(); ++index) {
        json_detail::checkCancellation(cancellation);
        const auto& row = items[index];
        if (index) append(",");
        textField("{\"local_recording_id\":", row.localRecordingId);
        textField(",\"directory_id\":", row.directoryId);
        textField(",\"session_id\":", row.sessionId);
        append(",\"package_directory\":");
        if constexpr (std::is_same_v<std::decay_t<decltype(row.packageDirectory)>, std::filesystem::path>)
            quote(row.packageDirectory.string()); // Legacy caller only.
        else quote(row.packageDirectory);
        numberField(",\"status\":", static_cast<unsigned>(row.status));
        append(",\"accepted_bytes\":["); number(row.acceptedBytes[0]);
        append(","); number(row.acceptedBytes[1]); append(","); number(row.acceptedBytes[2]); append("]");
        numberField(",\"attempts\":", row.attempts);
        textField(",\"safe_reason\":", row.safeReason);
        textField(",\"owner_user_id\":", row.ownerUserId);
        textField(",\"owner_workspace_id\":", row.ownerWorkspaceId);
        textField(",\"meeting_id\":", row.meetingId);
        textField(",\"media_revision_id\":", row.mediaRevisionId);
        textField(",\"upload_session_id\":", row.uploadSessionId);
        textField(",\"server_status\":", row.serverStatus);
        textField(",\"processing_status\":", row.processingStatus);
        textField(",\"media_revision_status\":", row.mediaRevisionStatus);
        numberField(",\"updated_at_ms\":", row.updatedAtMs); append("}");
    }
    append("],\"updated_at_ms\":"); number(updatedAtMs); append(",\"deletion_operations\":[");
    for (std::size_t index = 0; index < operations.size(); ++index) {
        json_detail::checkCancellation(cancellation);
        const auto& row = operations[index];
        if (index) append(",");
        textField("{\"operation_id\":", row.operationId);
        textField(",\"target\":", deletionTargetName(row.target));
        textField(",\"target_id\":", row.targetId);
        textField(",\"actor_user_id\":", row.actorUserId);
        textField(",\"workspace_id\":", row.workspaceId);
        textField(",\"server_origin\":", row.serverOrigin);
        numberField(",\"phase\":", static_cast<unsigned>(row.phase));
        numberField(",\"requested_at_ms\":", row.requestedAtMs);
        numberField(",\"updated_at_ms\":", row.updatedAtMs);
        numberField(",\"attempts\":", row.attemptCount);
        numberField(",\"next_attempt_at_ms\":", row.nextAttemptAtMs);
        textField(",\"receipt_request_id\":", row.receiptRequestId);
        textField(",\"safe_reason\":", row.safeReason); append("}");
    }
    append("],\"purge_acknowledgements\":[");
    for (std::size_t index = 0; index < acknowledgements.size(); ++index) {
        json_detail::checkCancellation(cancellation);
        const auto& row = acknowledgements[index];
        if (index) append(",");
        textField("{\"task_id\":", row.taskId);
        textField(",\"meeting_id\":", row.meetingId);
        numberField(",\"acknowledged_at_ms\":", row.acknowledgedAtMs); append("}");
    }
    append("]}");
    json_detail::checkCancellation(cancellation);
}

[[nodiscard]] std::optional<DeletionTarget> deletionTargetFromName(std::string_view name) {
    if (name == "own_origin") return DeletionTarget::ownOrigin;
    if (name == "meeting") return DeletionTarget::meeting;
    return std::nullopt;
}

[[nodiscard]] bool isDeletionOperationId(std::string_view value) {
    return DesktopApiClient::accountId(value);
}

} // namespace

DesktopUploadQueueService::DesktopUploadQueueService(
    std::filesystem::path ledgerPath,
    std::filesystem::path custodyRoot,
    LedgerWriter ledgerWriter)
    : ledgerWriter_(std::move(ledgerWriter)), ledgerPath_(std::move(ledgerPath)),
      custodyRoot_(custodyRoot.empty() ? ledgerPath_.parent_path() : std::move(custodyRoot)) {}

bool DesktopUploadQueueService::load() {
    const auto failure = [this] { quarantined_ = true; return false; };
    const auto quarantine = [this, &failure] {
        failure();
        std::error_code error;
        std::filesystem::rename(ledgerPath_, ledgerPath_.string() + ".quarantine", error);
        return false;
    };
    try {
        std::string json;
        {
            // Check the size before allocating; an exact read must also reject
            // truncation or growth. Close the input before any atomic rewrite.
            std::ifstream input(ledgerPath_, std::ios::binary | std::ios::ate);
            if (!input) {
                std::error_code error;
                const bool exists = std::filesystem::exists(ledgerPath_, error);
                if (exists || error || ledgerKnown_ || quarantined_ || !items_.empty() ||
                    !deletionOperations_.empty() || !purgeAcknowledgements_.empty()) return failure();
                const bool isolated = std::filesystem::exists(ledgerPath_.string() + ".quarantine", error);
                return isolated || error ? failure() : true;
            }
            const auto length = input.tellg();
            if (length < 0) return failure();
            if (length > 4 * 1024 * 1024) {
                input.close();
                return quarantine();
            }
            json.resize(static_cast<std::size_t>(length));
            input.seekg(0, std::ios::beg);
            if (!input) return failure();
            if (!json.empty()) {
                input.read(json.data(), static_cast<std::streamsize>(json.size()));
                if (!input || input.gcount() != static_cast<std::streamsize>(json.size())) return failure();
            }
            char extra = 0;
            if (input.get(extra) || !input.eof() || input.bad()) return failure();
        }

        DesktopUploadQueueService candidate(ledgerPath_, custodyRoot_, ledgerWriter_);
        candidate.clock_ = clock_;
        bool legacy = false;
        if (!candidate.decodeLedger(json, legacy)) return quarantine();
        for (const auto& item : candidate.items_) {
            if (!AtomicFileStore::isWithinRoot(custodyRoot_, item.packageDirectory)) return quarantine();
        }

        // The previous process has no upload worker. Recovery and upgrade only
        // touch the candidate until their required rewrite is acknowledged.
        bool recovered = false;
        for (auto& item : candidate.items_) {
            if (item.status != UploadQueueStatus::uploading) continue;
            item.status = UploadQueueStatus::retry;
            item.safeReason = "upload_interrupted";
            candidate.stamp(item);
            recovered = true;
        }
        if (legacy) {
            for (auto& item : candidate.items_) {
                if (item.updatedAtMs == 0) candidate.stamp(item);
            }
        }
        if ((legacy || recovered) && !candidate.persist()) return failure();
        items_.swap(candidate.items_);
        deletionOperations_.swap(candidate.deletionOperations_);
        purgeAcknowledgements_.swap(candidate.purgeAcknowledgements_);
        updatedAtMs_ = candidate.updatedAtMs_;
        ledgerKnown_ = true;
        quarantined_ = false;
        return true;
    } catch (...) {
        // Allocation, I/O or writer failure is not evidence of malformed bytes.
        // Keep both the source file and the previous projection intact.
        return failure();
    }
}

namespace {
template<template<class> class Allocator, class String, class Items, class Operations, class Acknowledgements>
bool decodeQueueLedger(std::string_view json, Items& items_, Operations& deletionOperations_,
    Acknowledgements& purgeAcknowledgements_, std::uint64_t& updatedAtMs_, bool& legacy,
    bool (*validSafeReason)(std::string_view) noexcept, const std::atomic<bool>* cancellation = nullptr) {
    using Item = typename Items::value_type;
    using Operation = typename Operations::value_type;
    using Acknowledgement = typename Acknowledgements::value_type;
    const auto contains = [&](const auto& records, std::string_view id, auto member) {
        std::size_t scanned = 0;
        for (const auto& record : records) {
            if ((scanned++ & 255) == 0) json_detail::checkCancellation(cancellation);
            if (std::string_view(record.*member) == id) return true;
        }
        return false;
    };
    json_detail::checkCancellation(cancellation);
    constexpr std::string_view prefix = R"({"schema_version":"desktop-upload-queue.v3","items":[)";
    static_assert(kQueueSchemaVersion == "desktop-upload-queue.v3");
    constexpr std::string_view legacyPrefix = R"({"schema_version":"desktop-upload-queue.v2","items":[)";
    static_assert(kQueueSchemaVersionV2 == "desktop-upload-queue.v2");
    if (json.size() > 4 * 1024 * 1024 ||
        (json.rfind(prefix, 0) != 0 && json.rfind(legacyPrefix, 0) != 0)) return false;
    legacy = json.rfind(legacyPrefix, 0) == 0;
    std::size_t cursor = legacy ? legacyPrefix.size() : prefix.size();
    while (cursor < json.size()) {
        json_detail::checkCancellation(cancellation);
        if (json[cursor] == ']') { ++cursor; break; }
        if (json[cursor] == ',') {
            ++cursor;
            if (cursor >= json.size() || json[cursor] == ']' || json[cursor] != '{') return false;
        }
        if (json[cursor] != '{') return false;
        const auto end = objectEnd(json, cursor, cancellation);
        if (end == std::string_view::npos) return false;
        const auto object = std::string_view(json).substr(cursor, end - cursor + 1);
        json_detail::JsonReader<Allocator, String> reader(object, 32, false, cancellation);
        const auto fields = reader.read();
        if (!fields) return false;
        const auto user = fields->find("owner_user_id");
        const auto workspace = fields->find("owner_workspace_id");
        String ownerUser, ownerWorkspace;
        if (user != fields->end() || workspace != fields->end()) {
            if (user == fields->end() || workspace == fields->end()) return false;
            const auto ownerField = [](std::string_view value, String& output) {
                if (value.size() < 2 || value.front() != '"' || value.back() != '"') return false;
                value.remove_prefix(1); value.remove_suffix(1);
                if (!value.empty() && !DesktopApiClient::accountId(value)) return false;
                output = value;
                return true;
            };
            if (!ownerField(user->second, ownerUser) || !ownerField(workspace->second, ownerWorkspace) ||
                ownerUser.empty() != ownerWorkspace.empty()) return false;
        }
        const auto id = stringField<String>(*fields, "local_recording_id", cancellation);
        const auto directoryId = stringField<String>(*fields, "directory_id", cancellation);
        const auto sessionId = stringField<String>(*fields, "session_id", cancellation);
        const auto packageDirectory = stringField<String>(*fields, "package_directory", cancellation);
        const auto status = numberField(*fields, "status");
        const auto attempts = numberField(*fields, "attempts");
        const auto safeReason = stringField<String>(*fields, "safe_reason", cancellation);
        const auto accepted = acceptedField<Allocator, String>(*fields, cancellation);
        // Written only after the server names the meeting, so an absent field is
        // the ordinary state of a row that has not been accepted yet.
        const auto meetingId = stringField<String>(*fields, "meeting_id", cancellation);
        if (meetingId && !meetingId->empty() && !DesktopUploadQueueService::validIdentity(*meetingId)) return false;
        // Written from version 3 on, once the server named them. An absent field
        // is the ordinary state of a row the server has not accepted yet.
        const auto mediaRevisionId = stringField<String>(*fields, "media_revision_id", cancellation);
        const auto uploadSessionId = stringField<String>(*fields, "upload_session_id", cancellation);
        const auto serverStatus = stringField<String>(*fields, "server_status", cancellation);
        const auto processingStatus = stringField<String>(*fields, "processing_status", cancellation);
        if (mediaRevisionId && !mediaRevisionId->empty() && !DesktopUploadQueueService::validIdentity(*mediaRevisionId)) return false;
        if (uploadSessionId && !uploadSessionId->empty() && !DesktopUploadQueueService::validIdentity(*uploadSessionId)) return false;
        if (serverStatus && !serverStatus->empty() && !validSafeReason(*serverStatus)) return false;
        if (processingStatus && !processingStatus->empty() && !validSafeReason(*processingStatus)) return false;
        // Written only from version 3 on; an older ledger has no timestamps, and
        // a row without one is read as "never stamped" rather than as an error.
        const auto updatedAt = numberField(*fields, "updated_at_ms");
        const auto revisionStatus = stringField<String>(*fields, "media_revision_status", cancellation);
        if ((fields->count("meeting_id") && !meetingId) ||
            (fields->count("media_revision_id") && !mediaRevisionId) ||
            (fields->count("upload_session_id") && !uploadSessionId) ||
            (fields->count("server_status") && !serverStatus) ||
            (fields->count("processing_status") && !processingStatus) ||
            (fields->count("media_revision_status") && !revisionStatus) ||
            (fields->count("updated_at_ms") && !updatedAt)) return false;
        if (!id || !directoryId || !sessionId || !packageDirectory || !status || !attempts || !safeReason || !accepted ||
            !DesktopUploadQueueService::validIdentity(*id) || !DesktopUploadQueueService::validIdentity(*directoryId) || !DesktopUploadQueueService::validIdentity(*sessionId) || *status > 6 ||
            *attempts > std::numeric_limits<std::uint32_t>::max() || !validSafeReason(*safeReason) ||
            packageDirectory->size() > 4096 || packageDirectory->find_first_of("\r\n\t") != std::string::npos ||
            contains(items_, *id, &Item::localRecordingId)) return false;
        Item item;
        item.localRecordingId = *id; item.directoryId = *directoryId; item.sessionId = *sessionId;
        item.packageDirectory = *packageDirectory; item.status = static_cast<UploadQueueStatus>(*status);
        item.acceptedBytes = *accepted; item.attempts = static_cast<std::uint32_t>(*attempts); item.safeReason = *safeReason;
        item.ownerUserId = std::move(ownerUser); item.ownerWorkspaceId = std::move(ownerWorkspace);
        if (meetingId) item.meetingId = *meetingId;
        if (mediaRevisionId) item.mediaRevisionId = *mediaRevisionId;
        if (uploadSessionId) item.uploadSessionId = *uploadSessionId;
        if (serverStatus) item.serverStatus = *serverStatus;
        if (processingStatus) item.processingStatus = *processingStatus;
        if (revisionStatus) {
            if (!revisionStatus->empty() && !validSafeReason(*revisionStatus)) return false;
            item.mediaRevisionStatus = *revisionStatus;
        }
        if (updatedAt) item.updatedAtMs = *updatedAt;
        items_.push_back(std::move(item)); cursor = end + 1;
    }
    while (cursor < json.size() && std::isspace(static_cast<unsigned char>(json[cursor]))) {
        if ((cursor & 4095) == 0) json_detail::checkCancellation(cancellation);
        ++cursor;
    }
    if (legacy) {
        if (cursor + 1 != json.size() || json[cursor] != '}') return false;
    } else {
        // The tail of a current ledger: the document stamp and the durable
        // deletion requests, in the order this writer always emits them.
        constexpr std::string_view tail = "\"updated_at_ms\":";
        if (json.compare(cursor, 1, ",") != 0) return false;
        ++cursor;
        if (json.compare(cursor, tail.size(), tail) != 0) return false;
        cursor += tail.size();
        auto stampEnd = cursor;
        while (stampEnd < json.size() && json[stampEnd] >= '0' && json[stampEnd] <= '9') {
            if ((stampEnd & 4095) == 0) json_detail::checkCancellation(cancellation);
            ++stampEnd;
        }
        if (stampEnd == cursor || stampEnd == json.size() || stampEnd - cursor > 18) return false;
        const auto stamp = unsignedToken(json.substr(cursor, stampEnd - cursor));
        if (!stamp) return false;
        updatedAtMs_ = *stamp;
        cursor = stampEnd;
        constexpr std::string_view operationsKey = ",\"deletion_operations\":[";
        if (json.compare(cursor, operationsKey.size(), operationsKey) != 0) return false;
        cursor += operationsKey.size();
        while (cursor < json.size()) {
            json_detail::checkCancellation(cancellation);
            if (json[cursor] == ']') { ++cursor; break; }
            if (json[cursor] == ',') {
                ++cursor;
                if (cursor >= json.size() || json[cursor] != '{') return false;
            }
            if (json[cursor] != '{') return false;
            const auto end = objectEnd(json, cursor, cancellation);
            if (end == std::string_view::npos) return false;
            const auto object = std::string_view(json).substr(cursor, end - cursor + 1);
            json_detail::JsonReader<Allocator, String> reader(object, 32, false, cancellation);
            const auto fields = reader.read();
            if (!fields) return false;
            const auto operationId = stringField<String>(*fields, "operation_id", cancellation);
            const auto targetName = stringField<String>(*fields, "target", cancellation);
            const auto targetId = stringField<String>(*fields, "target_id", cancellation);
            const auto actorUserId = stringField<String>(*fields, "actor_user_id", cancellation);
            const auto workspaceId = stringField<String>(*fields, "workspace_id", cancellation);
            const auto serverOrigin = stringField<String>(*fields, "server_origin", cancellation);
            const auto phase = numberField(*fields, "phase");
            const auto requestedAt = numberField(*fields, "requested_at_ms");
            const auto operationUpdatedAt = numberField(*fields, "updated_at_ms");
            const auto attemptCount = numberField(*fields, "attempts");
            const auto nextAttemptAt = numberField(*fields, "next_attempt_at_ms");
            const auto receiptRequestId = stringField<String>(*fields, "receipt_request_id", cancellation);
            const auto operationReason = stringField<String>(*fields, "safe_reason", cancellation);
            const auto target = targetName ? deletionTargetFromName(*targetName) : std::nullopt;
            if (!operationId || !target || !targetId || !actorUserId || !workspaceId || !serverOrigin || !phase ||
                !requestedAt || !operationUpdatedAt || !attemptCount || !nextAttemptAt || !receiptRequestId ||
                !operationReason || !isDeletionOperationId(*operationId) ||
                !DesktopApiClient::accountId(*actorUserId) || !DesktopApiClient::accountId(*workspaceId) ||
                !DesktopUploadQueueService::validServerOrigin(*serverOrigin) || *phase > static_cast<std::uint64_t>(DeletionOperationPhase::verified) ||
                *attemptCount > std::numeric_limits<std::uint32_t>::max() ||
                *operationUpdatedAt < *requestedAt || !validSafeReason(*operationReason) ||
                (*target == DeletionTarget::ownOrigin ? !DesktopUploadQueueService::validIdentity(*targetId)
                                                      : !DesktopApiClient::accountId(*targetId)) ||
                (*nextAttemptAt != 0 && *nextAttemptAt < *operationUpdatedAt) ||
                (!receiptRequestId->empty() && !DesktopApiClient::accountId(*receiptRequestId)) ||
                contains(deletionOperations_, *operationId, &Operation::operationId)) return false;
            Operation record;
            record.operationId = *operationId;
            record.target = *target;
            record.targetId = *targetId;
            record.actorUserId = *actorUserId;
            record.workspaceId = *workspaceId;
            record.serverOrigin = *serverOrigin;
            record.phase = static_cast<DeletionOperationPhase>(*phase);
            record.requestedAtMs = *requestedAt;
            record.updatedAtMs = *operationUpdatedAt;
            record.attemptCount = static_cast<std::uint32_t>(*attemptCount);
            record.nextAttemptAtMs = *nextAttemptAt;
            record.receiptRequestId = *receiptRequestId;
            record.safeReason = *operationReason;
            // Acceptance is only believable with the receipt that proved it, so
            // a hand-edited ledger cannot turn a rejection into a deletion. A
            // rejection without a reason is not a state this writer produces.
            if (deletionPhaseIsAccepted(record.phase) && record.receiptRequestId.empty()) return false;
            if (record.phase == DeletionOperationPhase::rejected && record.safeReason.empty()) return false;
            deletionOperations_.push_back(std::move(record));
            cursor = end + 1;
        }
        // The acknowledged purge tasks are the last field of a current ledger and
        // absent from the one this writer produced before them.
        constexpr std::string_view purgeKey = ",\"purge_acknowledgements\":[";
        if (json.compare(cursor, purgeKey.size(), purgeKey) == 0) {
            cursor += purgeKey.size();
            while (cursor < json.size()) {
                json_detail::checkCancellation(cancellation);
                if (json[cursor] == ']') { ++cursor; break; }
                if (json[cursor] == ',') {
                    ++cursor;
                    if (cursor >= json.size() || json[cursor] != '{') return false;
                }
                if (json[cursor] != '{') return false;
                const auto end = objectEnd(json, cursor, cancellation);
                if (end == std::string_view::npos) return false;
                const auto object = std::string_view(json).substr(cursor, end - cursor + 1);
                json_detail::JsonReader<Allocator, String> reader(object, 32, false, cancellation);
                const auto fields = reader.read();
                if (!fields) return false;
                const auto taskId = stringField<String>(*fields, "task_id", cancellation);
                const auto meetingId = stringField<String>(*fields, "meeting_id", cancellation);
                const auto acknowledgedAt = numberField(*fields, "acknowledged_at_ms");
                if (!taskId || !meetingId || !acknowledgedAt || !DesktopApiClient::accountId(*taskId) ||
                    !DesktopApiClient::accountId(*meetingId) || contains(purgeAcknowledgements_, *taskId, &Acknowledgement::taskId)) {
                    return false;
                }
                Acknowledgement record;
                record.taskId = *taskId;
                record.meetingId = *meetingId;
                record.acknowledgedAtMs = *acknowledgedAt;
                purgeAcknowledgements_.push_back(std::move(record));
                cursor = end + 1;
            }
        }
        while (cursor < json.size() && std::isspace(static_cast<unsigned char>(json[cursor]))) {
            if ((cursor & 4095) == 0) json_detail::checkCancellation(cancellation);
            ++cursor;
        }
        if (cursor + 1 != json.size() || json[cursor] != '}') return false;
    }
    json_detail::checkCancellation(cancellation);
    return true;
}

} // namespace

CustodyFileResult<bool> ProtectedCustodyStoreOwner::validateQueueValue(
    std::string_view json, const std::atomic<bool>* cancellation) {
    auto decoded = ProtectedUploadQueueValue::decode(json, cancellation);
    if (!decoded.ok()) return {std::nullopt, decoded.error, decoded.nativeError};
    return {true, CustodyFileError::none, 0};
}

CustodyFileResult<std::shared_ptr<const ProtectedUploadQueueValue>> ProtectedUploadQueueValue::decode(
    std::string_view json, const std::atomic<bool>* cancellation) try {
    if (!cancellation) return {std::nullopt, CustodyFileError::invalidInput, 0};
    json_detail::checkCancellation(cancellation);
    CustodyAllocator<ProtectedUploadQueueValue> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedUploadQueueValue(); }
    catch (...) { allocator.deallocate(raw, 1); throw; }
    std::shared_ptr<const ProtectedUploadQueueValue> value{raw, [](const ProtectedUploadQueueValue* p) {
        p->~ProtectedUploadQueueValue();
        CustodyAllocator<ProtectedUploadQueueValue>{}.deallocate(const_cast<ProtectedUploadQueueValue*>(p), 1);
    }, allocator};
    if (!decodeQueueLedger<CustodyAllocator, CustodyString>(json, raw->items_, raw->operations_, raw->acknowledgements_,
        raw->updatedAtMs_, raw->legacy_, DesktopUploadQueueService::validSafeReason, cancellation))
        return {std::nullopt, CustodyFileError::invalidContent, 0};
    json_detail::checkCancellation(cancellation);
    return {std::move(value), CustodyFileError::none, 0};
} catch (const json_detail::ParseCancelled&) {
    return {std::nullopt, CustodyFileError::ioFailed, 995}; // ERROR_OPERATION_ABORTED, also portable.
} catch (const std::bad_alloc&) {
    return {std::nullopt, CustodyFileError::allocationFailed, 0};
}

bool ProtectedUploadQueueValue::requeueNeedsAuth(std::uint64_t nowMs, const std::atomic<bool>* cancellation) {
    const bool changed = requeueNeedsAuthValues(items_, [nowMs](auto& item) { item.updatedAtMs = nowMs; }, cancellation);
    if (changed) updatedAtMs_ = nowMs;
    json_detail::checkCancellation(cancellation);
    return changed;
}

bool ProtectedUploadQueueValue::enqueue(Item item, std::uint64_t now, const std::atomic<bool>* cancellation) {
    if (!cancellation || item.packageDirectory.empty() || item.packageDirectory.size() > 4096 ||
        item.packageDirectory.find_first_of("\r\n\t") != CustodyString::npos ||
        !item.meetingId.empty() || !item.mediaRevisionId.empty() || !item.uploadSessionId.empty() ||
        !item.serverStatus.empty() || !item.processingStatus.empty() || !item.mediaRevisionStatus.empty() ||
        item.attempts || item.acceptedBytes != std::array<std::uint64_t, 3>{}) return false;
    if (!enqueueValue(items_, std::move(item), now, cancellation, DesktopUploadQueueService::validSafeReason)) return false;
    updatedAtMs_ = now;
    return true;
}

bool ProtectedUploadQueueValue::prepareLocalPurgeTask(const BasicLocalPurgeTask<CustodyString>& task,
    std::string_view user, std::string_view workspace, std::uint64_t now, bool& changed,
    const std::atomic<bool>* cancellation) {
    changed = false;
    if (!cancellation) return false;
    json_detail::checkCancellation(cancellation);
    if (!validLocalBufferPurgeTask(task) || !DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace)) return false;
    for (const auto& proof : acknowledgements_) {
        json_detail::checkCancellation(cancellation);
        if (proof.taskId == task.taskId && proof.meetingId != task.meetingId) return false;
    }
    for (auto& row : items_) {
        json_detail::checkCancellation(cancellation);
        if (row.meetingId != task.meetingId || std::string_view(row.ownerUserId) != user ||
            std::string_view(row.ownerWorkspaceId) != workspace || row.status != UploadQueueStatus::uploaded) continue;
        if (now < row.updatedAtMs) return false;
        if (row.safeReason == "local_delete_pending") continue;
        row.safeReason = "local_delete_pending"; row.updatedAtMs = now; changed = true;
    }
    json_detail::checkCancellation(cancellation);
    if (changed) updatedAtMs_ = now;
    return true;
}

bool ProtectedUploadQueueValue::canLocalRemoval(std::size_t index, std::string_view user,
    std::string_view workspace, bool resumeIntent) const noexcept {
    if (index >= items_.size() || !DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace)) return false;
    const auto& row = items_[index];
    if (std::string_view(row.ownerUserId) != user || std::string_view(row.ownerWorkspaceId) != workspace ||
        !DesktopUploadQueueService::validIdentity(row.localRecordingId) ||
        !DesktopUploadQueueService::validIdentity(row.directoryId) || row.status == UploadQueueStatus::uploading) return false;
    return resumeIntent ? row.status == UploadQueueStatus::quarantined && row.safeReason == "local_delete_pending" :
        row.safeReason != "local_delete_pending";
}

bool ProtectedUploadQueueValue::planLocalRemoval(std::size_t index, std::string_view user,
    std::string_view workspace, std::uint64_t now, ProtectedDeletionPlan& plan, bool& changed,
    const std::atomic<bool>* cancellation, bool resumeIntent) {
    changed = false; plan = {};
    if (!cancellation) return false;
    json_detail::checkCancellation(cancellation);
    if (!canLocalRemoval(index, user, workspace, resumeIntent) || now < updatedAtMs_ || now < items_[index].updatedAtMs) return false;
    auto& row = items_[index];
    plan.localOnly.push_back(row.localRecordingId);
    if (!resumeIntent) {
        row.status = UploadQueueStatus::quarantined; row.safeReason = "local_delete_pending";
        row.updatedAtMs = updatedAtMs_ = now; changed = true;
    }
    json_detail::checkCancellation(cancellation);
    return true;
}

bool ProtectedUploadQueueValue::canManualSend(std::size_t index, std::string_view user,
    std::string_view workspace, bool confirmUnowned) const noexcept {
    if (index >= items_.size() || !DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace)) return false;
    const auto& row = items_[index];
    if (!retryableStatus(row) || deletionBlocks(row)) return false;
    const bool unowned = row.ownerUserId.empty() && row.ownerWorkspaceId.empty();
    return unowned ? (confirmUnowned && !hasUploadServerIdentity(row)) :
        (std::string_view(row.ownerUserId) == user && std::string_view(row.ownerWorkspaceId) == workspace);
}

bool ProtectedUploadQueueValue::prepareManualSend(std::size_t index, std::string_view user,
    std::string_view workspace, bool confirmUnowned, std::uint64_t now, const std::atomic<bool>* cancellation) {
    if (!cancellation) return false;
    json_detail::checkCancellation(cancellation);
    if (!canManualSend(index, user, workspace, confirmUnowned)) return false;
    auto& row = items_[index];
    if (now < row.updatedAtMs || now < updatedAtMs_) return false;
    if (row.ownerUserId.empty()) { row.ownerUserId = user; row.ownerWorkspaceId = workspace; }
    row.status = UploadQueueStatus::retry; row.attempts = 0; row.safeReason = "manual_retry";
    row.updatedAtMs = updatedAtMs_ = now;
    json_detail::checkCancellation(cancellation); // A cancelled/throwing private copy must be discarded.
    return true;
}

bool ProtectedUploadQueueValue::localPurgeAcknowledged(const BasicLocalPurgeTask<CustodyString>& task) const noexcept {
    if (!validLocalBufferPurgeTask(task) || std::any_of(items_.begin(), items_.end(),
        [&](const auto& row) { return row.meetingId == task.meetingId; })) return false;
    return std::any_of(acknowledgements_.begin(), acknowledgements_.end(), [&](const auto& proof) {
        return proof.taskId == task.taskId && proof.meetingId == task.meetingId;
    });
}

CustodyVector<CustodyString> ProtectedUploadQueueValue::meetingsAwaitingLocalPurge(std::string_view user,
    std::string_view workspace, std::string_view origin, const std::atomic<bool>* cancellation) const {
    CustodyVector<CustodyString> meetings;
    if (!cancellation) return meetings;
    json_detail::checkCancellation(cancellation);
    if (!DesktopApiClient::accountId(user) || !DesktopApiClient::accountId(workspace) ||
        !DesktopUploadQueueService::validServerOrigin(origin)) return meetings;
    for (const auto& row : items_) {
        json_detail::checkCancellation(cancellation);
        if (!DesktopApiClient::accountId(row.meetingId) || std::string_view(row.ownerUserId) != user ||
            std::string_view(row.ownerWorkspaceId) != workspace) continue;
        const bool accepted = std::any_of(operations_.begin(), operations_.end(), [&](const auto& operation) {
            json_detail::checkCancellation(cancellation);
            return deletionPhaseIsAccepted(operation.phase) && operation.actorUserId == row.ownerUserId &&
                operation.workspaceId == row.ownerWorkspaceId && std::string_view(operation.serverOrigin) == origin &&
                deletionTargetsRow(operation, row);
        });
        if (accepted && std::find(meetings.begin(), meetings.end(), row.meetingId) == meetings.end()) meetings.push_back(row.meetingId);
    }
    json_detail::checkCancellation(cancellation);
    return meetings;
}

bool ProtectedUploadQueueValue::deletionBlocks(const Item& row) const noexcept {
    if (row.safeReason == "local_delete_pending") return true;
    return std::any_of(operations_.begin(), operations_.end(), [&](const auto& operation) {
        return operation.phase != DeletionOperationPhase::rejected && operation.actorUserId == row.ownerUserId &&
            operation.workspaceId == row.ownerWorkspaceId &&
            deletionTargetsRow(operation, row);
    });
}

bool ProtectedUploadQueueValue::planDeletionSelection(const ProtectedDeletionTargets& targets, std::string_view user,
    std::string_view workspace, std::string_view origin, std::uint64_t now, ProtectedDeletionPlan& plan,
    bool& changed, const std::atomic<bool>* cancellation) {
    changed = false;
    if (!cancellation) return false;
    if (!planDeletionSelectionValue(items_, operations_, targets, user, workspace, origin, now, plan, changed, cancellation))
        return false;
    if (changed) updatedAtMs_ = now;
    return true;
}

bool ProtectedUploadQueueValue::applyDeletionAnswer(const Operation& expected,
    const BasicDeletionWireResult<CustodyString>& wire, std::uint64_t now, bool& changed,
    const std::atomic<bool>* cancellation) {
    changed = false;
    if (!cancellation) return false;
    json_detail::checkCancellation(cancellation);
    for (auto& record : operations_) {
        json_detail::checkCancellation(cancellation);
        if (record.operationId != expected.operationId) continue;
        if (record.actorUserId != expected.actorUserId || record.workspaceId != expected.workspaceId ||
            record.serverOrigin != expected.serverOrigin || record.target != expected.target ||
            record.targetId != expected.targetId || record.phase != expected.phase ||
            record.receiptRequestId != expected.receiptRequestId || record.requestedAtMs != expected.requestedAtMs ||
            record.updatedAtMs != expected.updatedAtMs || record.attemptCount != expected.attemptCount ||
            record.nextAttemptAtMs != expected.nextAttemptAtMs || record.safeReason != expected.safeReason) return false;
        // A duplicate confirmation is a no-op, never another attempt or rollback.
        if (deletionPhaseIsAccepted(record.phase)) {
            if (!wire.accepted()) return false;
            const auto receipt = DesktopApiClient::decodeDeletionReceipt<CustodyString>(wire.body, cancellation);
            return receipt && deletionReceiptMatches(record, *receipt) && record.receiptRequestId == receipt->requestId;
        }
        if (record.phase == DeletionOperationPhase::rejected ||
            !applyDeletionAnswerValue(record, items_, wire, now, cancellation, DesktopUploadQueueService::validSafeReason)) return false;
        updatedAtMs_ = now; changed = true;
        json_detail::checkCancellation(cancellation);
        return true;
    }
    return false;
}

bool ProtectedUploadQueueValue::applyUploadResult(const Item& expected,
    const BasicDesktopTransportResult<CustodyString>& result, std::uint64_t now, const std::atomic<bool>* cancellation) {
    if (!cancellation) return false;
    json_detail::checkCancellation(cancellation);
    for (auto& row : items_) {
        json_detail::checkCancellation(cancellation);
        if (row.localRecordingId != expected.localRecordingId) continue;
        if (!sameUploadIdentity(row, expected)) return false;
        if (!applyUploadResultValue(row, result, DesktopUploadQueueService::validSafeReason)) return false;
        row.updatedAtMs = updatedAtMs_ = now;
        json_detail::checkCancellation(cancellation); // Caller discards a cancelled private candidate.
        return true;
    }
    return false;
}

CustodyVector<std::size_t> ProtectedUploadQueueValue::prepareUploads(bool authRecovered,
    std::uint32_t maxAttempts, std::uint64_t now, const std::atomic<bool>* cancellation) {
    CustodyVector<std::size_t> selected;
    if (!cancellation) return selected;
    if (authRecovered) (void)requeueNeedsAuth(now, cancellation);
    for (std::size_t index = 0; index < items_.size(); ++index) {
        json_detail::checkCancellation(cancellation);
        auto& row = items_[index];
        if (deletionBlocks(row)) continue;
        if (row.status != UploadQueueStatus::pending && row.status != UploadQueueStatus::retry &&
            row.status != UploadQueueStatus::uploading) continue;
        if (row.attempts >= maxAttempts) {
            if (row.safeReason != "retry_budget_exhausted") {
                row.status = UploadQueueStatus::retry; row.safeReason = "retry_budget_exhausted";
                if (row.attempts < std::numeric_limits<std::uint32_t>::max()) ++row.attempts;
                row.updatedAtMs = updatedAtMs_ = now;
            }
            continue;
        }
        selected.push_back(index);
        if (selected.size() == 32) break;
    }
    json_detail::checkCancellation(cancellation);
    return selected;
}

CustodyFileResult<CustodyBytes> ProtectedUploadQueueValue::serialize(
    std::shared_ptr<const std::atomic<bool>> cancellation) const try {
    if (!cancellation) return {std::nullopt, CustodyFileError::invalidInput, 0};
    json_detail::checkCancellation(cancellation.get());
    CustodyBytes bytes;
    serializeQueueLedger(bytes, items_, operations_, acknowledgements_, updatedAtMs_, cancellation.get(), 4 * 1024 * 1024);
    CustodyFileResult<CustodyBytes> result{std::move(bytes), CustodyFileError::none, 0};
    json_detail::checkCancellation(cancellation.get());
    return result;
} catch (const json_detail::ParseCancelled&) {
    return {std::nullopt, CustodyFileError::ioFailed, 995};
} catch (const QueueSerializationLimit&) {
    return {std::nullopt, CustodyFileError::invalidInput, 0};
} catch (const std::bad_alloc&) {
    return {std::nullopt, CustodyFileError::allocationFailed, 0};
}

bool DesktopUploadQueueService::decodeLedger(std::string_view json, bool& legacy) {
    return decodeQueueLedger<std::allocator, std::string>(json, items_, deletionOperations_,
        purgeAcknowledgements_, updatedAtMs_, legacy, validSafeReason);
}

bool DesktopUploadQueueService::enqueue(UploadCustodyItem item) {
    if (quarantined_ || item.packageDirectory.empty() ||
        !AtomicFileStore::isWithinRoot(custodyRoot_, item.packageDirectory) ||
        !enqueueValue(items_, std::move(item), nowMs(), nullptr, validSafeReason)) return false;
    return persist();
}

bool DesktopUploadQueueService::reconcile(const UploadServerTruth& truth) {
    auto* item = find(truth.localRecordingId);
    if (item == nullptr) return false;
    applyServerTruth(*item, truth);
    stamp(*item);
    return persist();
}

bool DesktopUploadQueueService::applyUploadResult(std::string_view id, const BasicDesktopTransportResult<std::string>& result) {
    auto* item = find(id);
    if (quarantined_ || !item || !applyUploadResultValue(*item, result, validSafeReason)) return false;
    stamp(*item);
    return persist();
}

void DesktopUploadQueueService::applyServerTruth(UploadCustodyItem& item, const UploadServerTruth& truth) {
    applyServerTruthValue(item, truth, validSafeReason);
}

bool DesktopUploadQueueService::markDeferred(std::string_view id, std::string reason) {
    auto* item = find(id); if (quarantined_ || !item || !validSafeReason(reason) || reason.empty()) return false;
    // The server asked the client to wait, so this is a pause and not a failed
    // attempt: the retry budget counts work the server could not accept, and
    // waiting longer must never be the reason a recording stops being sent.
    item->status = UploadQueueStatus::retry;
    item->safeReason = std::move(reason);
    stamp(*item);
    return persist();
}

bool DesktopUploadQueueService::markRetry(std::string_view id, std::string reason) {
    auto* item = find(id); if (quarantined_ || !item || !validSafeReason(reason) || reason.empty()) return false;
    item->status = UploadQueueStatus::retry;
    if (item->attempts < std::numeric_limits<std::uint32_t>::max()) ++item->attempts;
    item->safeReason = std::move(reason);
    stamp(*item);
    return persist();
}

bool DesktopUploadQueueService::requestRetry(std::string_view id) {
    auto* item = find(id);
    if (quarantined_ || !item || !canRetry(*item)) return false;
    const auto previous = *item;
    item->status = UploadQueueStatus::retry;
    item->attempts = 0;
    item->safeReason = "manual_retry";
    stamp(*item);
    if (persist()) return true;
    *item = previous;
    return false;
}

bool DesktopUploadQueueService::canRetry(const UploadCustodyItem& item) noexcept {
    return retryableStatus(item) &&
        DesktopApiClient::accountId(item.ownerUserId) && DesktopApiClient::accountId(item.ownerWorkspaceId);
}

bool DesktopUploadQueueService::markNeedsAuth(std::string_view id, std::string reason) {
    auto* item = find(id); if (quarantined_ || !item || reason.empty() || !validSafeReason(reason)) return false;
    item->status = UploadQueueStatus::needsAuth; item->safeReason = std::move(reason);
    stamp(*item);
    return persist();
}

bool DesktopUploadQueueService::assignOwner(std::string_view id, const DesktopAccountIdentity& identity) {
    auto* item = find(id);
    if (quarantined_ || !item || !item->ownerUserId.empty() || !item->ownerWorkspaceId.empty() ||
        item->status == UploadQueueStatus::quarantined || item->status == UploadQueueStatus::uploaded ||
        !DesktopApiClient::accountId(identity.userId) || !DesktopApiClient::accountId(identity.workspaceId)) return false;
    const auto previous = *item;
    item->ownerUserId = identity.userId;
    item->ownerWorkspaceId = identity.workspaceId;
    if (item->status == UploadQueueStatus::needsAuth) {
        item->status = UploadQueueStatus::pending;
        item->safeReason.clear();
    }
    stamp(*item);
    if (persist()) return true;
    *item = previous; // Failed durable claim is never usable by a worker.
    return false;
}

bool DesktopUploadQueueService::requeueNeedsAuth() {
    const bool changed = requeueNeedsAuthValues(items_, [this](auto& item) { stamp(item); }, nullptr);
    return !changed || persist();
}

bool DesktopUploadQueueService::markQuarantined(std::string_view id, std::string reason) {
    auto* item = find(id); if (!item || reason.empty() || !validSafeReason(reason)) return false;
    item->status = UploadQueueStatus::quarantined; item->safeReason = std::move(reason);
    stamp(*item);
    return persist();
}

bool DesktopUploadQueueService::markBlocked(std::string_view id, std::string reason, const UploadServerTruth* truth) {
    auto* item = find(id);
    if (quarantined_ || !item || reason.empty() || !validSafeReason(reason) ||
        (truth && truth->localRecordingId != id)) return false;
    if (truth) applyServerTruth(*item, *truth);
    item->status = UploadQueueStatus::blocked; item->safeReason = std::move(reason);
    stamp(*item);
    return persist();
}

bool DesktopUploadQueueService::markUploaded(std::string_view id) {
    auto* item = find(id); if (!item) return false;
    item->status = UploadQueueStatus::uploaded;
    stamp(*item);
    return persist();
}

LocalCopyRemovalResult DesktopUploadQueueService::removeLocalCopy(
    std::string_view id, LocalPurgeProof proof,
    const std::function<bool(const std::filesystem::path&)>& recycle) {
    // A local copy is removed for one of two reasons, and never for an unnamed
    // one: the user confirmed this copy, or a purge task the server created names
    // the meeting it belongs to.
    if (proof != LocalPurgeProof::userConfirmedLocalCopy && proof != LocalPurgeProof::serverRequestedPurge) {
        return LocalCopyRemovalResult::confirmationRequired;
    }
    if (quarantined_) return LocalCopyRemovalResult::ledgerFailure;
    const std::string localId(id);
    auto* item = find(localId);
    if (!item) return LocalCopyRemovalResult::unknownRecording;
    if (proof == LocalPurgeProof::serverRequestedPurge && item->status != UploadQueueStatus::uploaded)
        return LocalCopyRemovalResult::confirmationRequired;
    const auto package = item->packageDirectory;
    const DesktopLocalPurgeService purge(custodyRoot_);
    if (!purge.isSafePackageDirectory(package, true) || AtomicFileStore::isWithinRoot(package, ledgerPath_))
        return LocalCopyRemovalResult::unsafePath;
    std::error_code error;
    const auto target = std::filesystem::weakly_canonical(package, error);
    if (error) return LocalCopyRemovalResult::unsafePath;
    for (const auto& other : items_) {
        if (other.localRecordingId == localId) continue;
        const auto otherTarget = std::filesystem::weakly_canonical(other.packageDirectory, error);
        if (error || otherTarget == target) return LocalCopyRemovalResult::unsafePath;
    }
    // Persist the intent before invoking an OS operation. After a crash/recycle
    // success + ledger failure the intent remains. A server task must retain
    // the uploaded classification so a failed recycle can retry after restart;
    // the marker still excludes reads/uploads and user-confirmed recovery.
    if (proof == LocalPurgeProof::userConfirmedLocalCopy) item->status = UploadQueueStatus::quarantined;
    item->safeReason = "local_delete_pending";
    stamp(*item);
    if (!persist()) {
        quarantined_ = true;
        return LocalCopyRemovalResult::ledgerFailure;
    }
    const auto exists = std::filesystem::exists(package, error);
    if (error) return LocalCopyRemovalResult::recycleFailed;
    if (exists) {
        if (!purge.isSafePackageDirectory(package) || !recycle) return LocalCopyRemovalResult::recycleFailed;
        try {
            if (!recycle(package)) return LocalCopyRemovalResult::recycleFailed;
        } catch (...) {
            return LocalCopyRemovalResult::recycleFailed;
        }
    }
    const auto status = std::filesystem::symlink_status(package, error);
    if (status.type() != std::filesystem::file_type::not_found ||
        (error && error != std::errc::no_such_file_or_directory)) return LocalCopyRemovalResult::recycleFailed;
    auto retained = items_;
    items_.erase(std::remove_if(items_.begin(), items_.end(), [&](const auto& value) {
        return value.localRecordingId == localId;
    }), items_.end());
    if (!persist()) {
        items_ = std::move(retained);
        quarantined_ = true;
        return LocalCopyRemovalResult::ledgerFailure;
    }
    return LocalCopyRemovalResult::removed;
}

bool DesktopUploadQueueService::isShortRecordingMarked(const std::filesystem::path& packageDirectory) {
    if (packageDirectory.empty()) return false;
    std::ifstream input(packageDirectory / "manifest.json", std::ios::binary);
    if (!input) return false;
    const std::string text((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    if (text.empty() || text.size() > 8 * 1024 * 1024) return false;
    // Compare a compacted copy so a reformatted manifest cannot defeat the gate:
    // the marker must be a positive literal, never a missing or false field.
    std::string compact;
    compact.reserve(text.size());
    for (const char c : text) {
        if (c == ' ' || c == '\t' || c == '\r' || c == '\n') continue;
        compact += c;
    }
    return compact.find(std::string("\"") + std::string(kShortRecordingDiscardedField) + "\":true")
        != std::string::npos;
}

ShortRecordingDiscardResult DesktopUploadQueueService::discardShortRecording(
    const std::filesystem::path& packageDirectory) {
    if (quarantined_) return ShortRecordingDiscardResult::ledgerFailure;
    const DesktopLocalPurgeService purge(custodyRoot_);
    if (!purge.isSafePackageDirectory(packageDirectory) ||
        AtomicFileStore::isWithinRoot(packageDirectory, ledgerPath_)) {
        return ShortRecordingDiscardResult::unsafePath;
    }
    if (!isShortRecordingMarked(packageDirectory)) return ShortRecordingDiscardResult::notMarked;
    std::error_code error;
    const auto target = std::filesystem::weakly_canonical(packageDirectory, error);
    if (error) return ShortRecordingDiscardResult::unsafePath;
    // Drop the ledger row first. Even if the file cleanup below fails, a
    // discarded recording can never be selected for upload again, and the
    // on-disk marker lets the next sweep finish the job.
    auto retained = items_;
    items_.erase(std::remove_if(items_.begin(), items_.end(), [&](const auto& value) {
        std::error_code compareError;
        const auto other = std::filesystem::weakly_canonical(value.packageDirectory, compareError);
        return !compareError && other == target;
    }), items_.end());
    if (items_.size() != retained.size() && !persist()) {
        items_ = std::move(retained);
        quarantined_ = true;
        return ShortRecordingDiscardResult::ledgerFailure;
    }
    // Inspect every entry before deleting anything, so an unexpected or linked
    // entry aborts the discard instead of partially applying it.
    std::error_code scanError;
    std::vector<std::filesystem::path> children;
    for (const auto& entry : std::filesystem::directory_iterator(packageDirectory, scanError)) {
        if (scanError) return ShortRecordingDiscardResult::unsafePath;
        const auto status = entry.symlink_status(scanError);
        if (scanError || status.type() != std::filesystem::file_type::regular) {
            return ShortRecordingDiscardResult::unsafePath;
        }
        children.push_back(entry.path());
    }
    if (scanError) return ShortRecordingDiscardResult::unsafePath;
    for (const auto& child : children) {
        std::filesystem::remove(child, error);
        if (error) return ShortRecordingDiscardResult::unsafePath;
    }
    // Remove only a now-empty directory: anything created after inspection is
    // never removed recursively.
    std::error_code emptyError;
    if (!std::filesystem::is_empty(packageDirectory, emptyError) || emptyError) {
        return ShortRecordingDiscardResult::unsafePath;
    }
    std::filesystem::remove(packageDirectory, error);
    return error ? ShortRecordingDiscardResult::unsafePath : ShortRecordingDiscardResult::discarded;
}

std::size_t DesktopUploadQueueService::sweepDiscardedShortRecordings() {
    if (custodyRoot_.empty() || quarantined_) return 0;
    std::error_code error;
    std::vector<std::filesystem::path> candidates;
    for (const auto& entry : std::filesystem::directory_iterator(custodyRoot_, error)) {
        if (error) break;
        const auto status = entry.symlink_status(error);
        if (error) break;
        if (status.type() != std::filesystem::file_type::directory) continue;
        candidates.push_back(entry.path());
    }
    std::size_t discarded = 0;
    for (const auto& candidate : candidates) {
        if (!isShortRecordingMarked(candidate)) continue;
        if (discardShortRecording(candidate) == ShortRecordingDiscardResult::discarded) ++discarded;
    }
    return discarded;
}

std::optional<UploadCustodyItem> DesktopUploadQueueService::nextPending() const {
    if (quarantined_) return std::nullopt;
    for (const auto& item : items_) {
        if (item.status == UploadQueueStatus::pending || item.status == UploadQueueStatus::retry) return item;
    }
    return std::nullopt;
}

std::vector<UploadCustodyItem> DesktopUploadQueueService::pendingItems(std::size_t limit) const {
    std::vector<UploadCustodyItem> result;
    if (quarantined_) return result;
    result.reserve(std::min(limit, items_.size()));
    for (const auto& item : items_) {
        if (item.status != UploadQueueStatus::pending && item.status != UploadQueueStatus::retry) continue;
        result.push_back(item);
        if (result.size() >= limit) break;
    }
    return result;
}

bool DesktopUploadQueueService::requestDeletion(DeletionTarget target, std::string_view targetId,
                                               const DesktopAccountIdentity& owner, std::string_view serverOrigin,
                                               std::string& operationId) {
    operationId.clear();
    bool changed = false;
    if (quarantined_ || !requestDeletionValue(deletionOperations_, target, targetId, owner.userId,
        owner.workspaceId, serverOrigin, nowMs(), operationId, changed, nullptr)) return false;
    if (changed && !persist()) {
        deletionOperations_.pop_back();
        operationId.clear();
        return false;
    }
    return true;
}

bool DesktopUploadQueueService::markDeletionPhase(std::string_view operationId, DeletionOperationPhase phase,
                                                 std::string_view safeReason) {
    if (quarantined_ || !validSafeReason(safeReason)) return false;
    auto* record = findOperation(operationId);
    if (record == nullptr) return false;
    const auto previous = *record;
    if (!markDeletionPhaseValue(*record, phase, safeReason, nowMs())) return false;
    if (!persist()) {
        *record = previous;
        return false;
    }
    return true;
}

bool DesktopUploadQueueService::markDeletionAttempt(std::string_view operationId, std::uint64_t nextAttemptAtMs) {
    if (quarantined_) return false;
    auto* record = findOperation(operationId);
    if (record == nullptr || deletionPhaseIsAccepted(record->phase)) return false;
    const auto now = nowMs();
    if (now < record->updatedAtMs || nextAttemptAtMs < now) return false;
    const auto previous = *record;
    record->nextAttemptAtMs = nextAttemptAtMs;
    record->updatedAtMs = now;
    if (!persist()) {
        *record = previous;
        return false;
    }
    return true;
}

bool DesktopUploadQueueService::acceptDeletion(std::string_view operationId, const DeletionReceipt& receipt) {
    if (quarantined_ || !receipt.accepted() || !DesktopApiClient::accountId(receipt.requestId)) return false;
    auto* record = findOperation(operationId);
    if (record == nullptr) return false;
    const auto previous = *record;
    if (!acceptDeletionValue(*record, receipt, nowMs())) return false;
    if (previous.phase == DeletionOperationPhase::verified) return true;
    if (!persist()) {
        *record = previous;
        return false;
    }
    return true;
}

std::vector<DeletionOperationRecord> DesktopUploadQueueService::currentDeletionOperations(
    const DesktopAccountIdentity& owner) const {
    std::vector<DeletionOperationRecord> result;
    if (!DesktopApiClient::accountId(owner.userId) || !DesktopApiClient::accountId(owner.workspaceId)) return result;
    for (const auto& record : deletionOperations_) {
        if (record.actorUserId != owner.userId || record.workspaceId != owner.workspaceId) continue;
        result.push_back(record);
    }
    std::stable_sort(result.begin(), result.end(), [](const auto& left, const auto& right) {
        return left.requestedAtMs < right.requestedAtMs;
    });
    return result;
}

const DeletionOperationRecord* DesktopUploadQueueService::findDeletionOperation(
    std::string_view operationId) const noexcept {
    for (const auto& record : deletionOperations_) {
        if (record.operationId == operationId) return &record;
    }
    return nullptr;
}

bool DesktopUploadQueueService::hasServerIdentity(const UploadCustodyItem& item) noexcept {
    // A local session key is not a server identity: every recording has one from
    // the moment it is queued. What counts is that the server was actually told:
    // there is a meeting, an upload was attempted, or the upload already finished.
    return hasUploadServerIdentity(item);
}

LocalPurgeAckState DesktopUploadQueueService::localPurgeAckState(LocalPurgeVerification verification) noexcept {
    return verification == LocalPurgeVerification::deleted ? LocalPurgeAckState::acknowledged
                                                           : LocalPurgeAckState::failed;
}

std::string_view DesktopUploadQueueService::localPurgeReasonCode(LocalPurgeVerification verification) noexcept {
    switch (verification) {
    case LocalPurgeVerification::deleted: return "local_artifacts_deleted";
    case LocalPurgeVerification::failed: return "local_purge_failed";
    case LocalPurgeVerification::unverified: break;
    }
    return "local_purge_unverified";
}

std::vector<DesktopUploadQueueService::LocalPurgeCandidate> DesktopUploadQueueService::localPurgeCandidates(
    const LocalPurgeTask& task) const {
    std::vector<LocalPurgeCandidate> candidates;
    // The meeting the server itself returned is the only thing that can match a
    // task to a row. An empty identifier matches nothing, not everything.
    if (task.meetingId.empty()) return candidates;
    for (const auto& item : items_) {
        if (item.meetingId != task.meetingId) continue;
        // A copy that has not reached the server is not a buffer the server can
        // have deleted: removing it here would destroy an upload in flight.
        candidates.push_back({item.localRecordingId, item.status == UploadQueueStatus::uploaded});
    }
    return candidates;
}

DesktopUploadQueueService::LocalPurgeCompletion DesktopUploadQueueService::completeLocalPurgeTask(
    const LocalPurgeTask& task, const std::function<bool(const std::filesystem::path&)>& recycle) {
    LocalPurgeCompletion completion;
    // An unreadable ledger or a task this client cannot verify proves nothing.
    // Validate the task before consulting retained proof, not just before IO.
    if (quarantined_ || !validLocalBufferPurgeTask(task)) return completion;
    // A task this device already carried out is answered from the record: the rows
    // it named are gone, and looking for them again would turn a proven deletion
    // into "unverified" the second time the server asked.
    const auto recorded = std::find_if(purgeAcknowledgements_.begin(), purgeAcknowledgements_.end(),
        [&](const auto& record) { return record.taskId == task.taskId; });
    if (recorded != purgeAcknowledgements_.end()) {
        if (recorded->meetingId != task.meetingId) return completion;
        completion.verification = LocalPurgeVerification::deleted;
        completion.ack = LocalPurgeAckState::acknowledged;
        completion.reasonCode = std::string(localPurgeReasonCode(completion.verification));
        return completion;
    }
    const auto candidates = localPurgeCandidates(task);
    if (!candidates.empty()) {
        bool everyCopyGone = true;
        for (const auto& candidate : candidates) {
            if (!candidate.purgeable) {
                everyCopyGone = false;
                continue;
            }
            const auto removal = removeLocalCopy(candidate.localRecordingId,
                LocalPurgeProof::serverRequestedPurge, recycle);
            if (removal == LocalCopyRemovalResult::removed) ++completion.removed;
            else everyCopyGone = false;
        }
        completion.verification = everyCopyGone ? LocalPurgeVerification::deleted : LocalPurgeVerification::failed;
        if (completion.verification == LocalPurgeVerification::deleted) {
            // The proof is written before the answer is sent, so a lost answer
            // cannot turn a deletion this device performed into a failure.
            LocalPurgeAcknowledgement record;
            record.taskId = task.taskId;
            record.meetingId = task.meetingId;
            record.acknowledgedAtMs = nowMs();
            purgeAcknowledgements_.push_back(std::move(record));
            // The server bounds its own task list, so a device never has to
            // remember more answers than that; the oldest are the least useful.
            if (purgeAcknowledgements_.size() > DesktopApiClient::purgeTaskListLimit) {
                purgeAcknowledgements_.erase(purgeAcknowledgements_.begin());
            }
            if (!persist()) {
                purgeAcknowledgements_.pop_back();
                quarantined_ = true;
                completion.verification = LocalPurgeVerification::unverified;
                completion.removed = 0;
            }
        }
    }
    completion.ack = localPurgeAckState(completion.verification);
    completion.reasonCode = std::string(localPurgeReasonCode(completion.verification));
    return completion;
}

bool DesktopUploadQueueService::hasLocalPurgeAcknowledgement(std::string_view taskId) const {
    return std::any_of(purgeAcknowledgements_.begin(), purgeAcknowledgements_.end(),
        [taskId](const auto& record) { return record.taskId == taskId; });
}

std::vector<std::string> DesktopUploadQueueService::meetingsAwaitingLocalPurge() const {
    std::vector<std::string> meetings;
    if (quarantined_) return meetings;
    for (const auto& item : items_) {
        if (item.meetingId.empty()) continue;
        // The server creates the purge task from its own side, so the client asks
        // for it as soon as its own deletion request has been accepted. A refused
        // or still waiting request is not a deletion the server would purge.
        const bool deleted = std::any_of(deletionOperations_.begin(), deletionOperations_.end(),
            [&item](const auto& record) {
                if (!deletionPhaseIsAccepted(record.phase)) return false;
                return deletionTargetsRow(record, item);
            });
        if (!deleted) continue;
        if (std::find(meetings.begin(), meetings.end(), item.meetingId) == meetings.end()) {
            meetings.push_back(item.meetingId);
        }
    }
    return meetings;
}

DesktopUploadQueueService::DeletionPlan DesktopUploadQueueService::planDeletionSelection(
    const std::vector<DeletionTargetRequest>& targets, const DesktopAccountIdentity& owner,
    std::string_view serverOrigin) {
    if (quarantined_) return {};
    try {
        auto candidate = *this;
        DeletionPlan plan; bool changed = false;
        const auto now = nowMs();
        if (!planDeletionSelectionValue(candidate.items_, candidate.deletionOperations_, targets, owner.userId,
            owner.workspaceId, serverOrigin, now, plan, changed, nullptr)) return {};
        if (changed && !publishCandidate(candidate, now)) return {};
        plan.saved = true;
        return plan;
    } catch (...) { return {}; }
}

bool DesktopUploadQueueService::applyDeletionAnswer(const DeletionRequestPlan& request,
                                                   const DesktopAccountIdentity& owner,
                                                   std::string_view serverOrigin,
                                                   const DeletionWireResult& wire) {
    if (quarantined_) return false;
    const auto* stored = findDeletionOperation(request.operationId);
    // An answer about a request this ledger does not hold, of another account, or
    // of another server is not an answer this app may record.
    if (stored == nullptr || stored->actorUserId != owner.userId ||
        stored->workspaceId != owner.workspaceId || stored->serverOrigin != serverOrigin ||
        stored->target != request.target || stored->targetId != request.targetId) {
        return false;
    }
    if (deletionPhaseIsAccepted(stored->phase) || stored->phase == DeletionOperationPhase::rejected) return false;
    try {
        // Keep getters on this service unchanged even inside the durable writer.
        auto candidate = *this;
        const auto now = nowMs();
        auto* record = candidate.findOperation(request.operationId);
        if (!applyDeletionAnswerValue(*record, candidate.items_, wire, now, nullptr, validSafeReason)) return false;
        return publishCandidate(candidate, now);
    } catch (...) { return false; }
}

bool DesktopUploadQueueService::publishCandidate(DesktopUploadQueueService& candidate, std::uint64_t now) {
    bool publicationStarted = false;
    try {
        const auto json = serialize(candidate.items_, candidate.deletionOperations_, candidate.purgeAcknowledgements_, now);
        publicationStarted = true;
        const auto saved = ledgerWriter_ ? ledgerWriter_(custodyRoot_, ledgerPath_, json) :
            AtomicFileStore::writeWithinRoot(custodyRoot_, ledgerPath_, json, 4 * 1024 * 1024).ok();
        if (!saved) { quarantined_ = true; return false; }
        items_.swap(candidate.items_); deletionOperations_.swap(candidate.deletionOperations_);
        purgeAcknowledgements_.swap(candidate.purgeAcknowledgements_);
        updatedAtMs_ = now; ledgerKnown_ = true;
        return true;
    } catch (...) {
        if (publicationStarted) quarantined_ = true;
        return false;
    }
}

template<class String>
String DesktopUploadQueueService::deletionGateReason(const BasicDeletionWireResult<String>& context,
    const BasicDesktopAccountIdentity<String>& owner, const std::atomic<bool>* cancellation) {
    // A pass that could not read the server's declared support must not mutate: an
    // older server ignores the expected-account headers, and a receipt that failed
    // to decode would arrive after the recording was gone. macOS refuses the same
    // answers with `recording_deletion_update_required`, and refuses a context that
    // names another account with `recording_scope_changed`.
    if (!context.waitReason.empty()) return context.waitReason;
    if (context.transportFailed || context.status == 0) return "connection";
    if (context.status != 200) {
        if (context.status == 429) return "rate_limit";
        if (context.status == 401 || context.status == 403) return "authentication";
        return "server_update";
    }
    const auto declared = DesktopApiClient::decodeNotificationContext<String>(context.body, cancellation);
    if (!declared || declared->protocolVersion != 1) return "server_update";
    if (declared->userId != owner.userId || declared->workspaceId != owner.workspaceId) return "scope_changed";
    return {};
}

template<class String>
bool DesktopUploadQueueService::deletionFailureIsShared(const BasicDeletionWireResult<String>& wire) noexcept {
    // Only two answers are about this one target: the server refused it, or it no
    // longer has it. Both leave the rest of the batch worth asking, and both are
    // the same two answers macOS continues on.
    const bool answered = wire.answered();
    const bool refusedTarget = answered && wire.status == 403 &&
        wire.body.find("deletion_forbidden") != std::string::npos;
    const bool targetGone = answered && wire.status == 404 &&
        wire.body.find("meeting_not_found") != std::string::npos;
    if (refusedTarget || targetGone) return false;
    if (answered && wire.accepted()) return false;
    // Everything else — no network, an expired session, a rate limit, a server
    // update, an answer that cannot be read — says the same thing about every
    // request of this account.
    return true;
}

template std::string DesktopUploadQueueService::deletionGateReason<std::string>(const BasicDeletionWireResult<std::string>&, const BasicDesktopAccountIdentity<std::string>&, const std::atomic<bool>*);
template CustodyString DesktopUploadQueueService::deletionGateReason<CustodyString>(const BasicDeletionWireResult<CustodyString>&, const BasicDesktopAccountIdentity<CustodyString>&, const std::atomic<bool>*);
template bool DesktopUploadQueueService::deletionFailureIsShared<std::string>(const BasicDeletionWireResult<std::string>&) noexcept;
template bool DesktopUploadQueueService::deletionFailureIsShared<CustodyString>(const BasicDeletionWireResult<CustodyString>&) noexcept;

DesktopUploadQueueService::DeletionSelectionOutcome DesktopUploadQueueService::deletionSelectionOutcome(
    const DeletionPlan& plan) const {
    DeletionSelectionOutcome outcome;
    for (const auto& operationId : plan.operationIds) {
        const auto* stored = findDeletionOperation(operationId);
        if (stored == nullptr) {
            ++outcome.pending;
            continue;
        }
        if (deletionPhaseIsAccepted(stored->phase)) ++outcome.accepted;
        else if (stored->phase == DeletionOperationPhase::rejected) ++outcome.rejected;
        else ++outcome.pending;
    }
    return outcome;
}

std::optional<int> DesktopUploadQueueService::uploadProgressPercent(
    const UploadCustodyItem& item, const std::array<std::uint64_t, 3>& trackBytes) noexcept {
    std::uint64_t total = 0;
    for (const auto bytes : trackBytes) total += bytes;
    if (total == 0) return std::nullopt;
    std::uint64_t accepted = 0;
    for (std::size_t index = 0; index < trackBytes.size(); ++index) {
        // Сервер не может принять больше, чем дорожка весит: иначе прогресс
        // перескочил бы за сто процентов и строка выглядела бы сломанной.
        accepted += std::min(item.acceptedBytes[index], trackBytes[index]);
    }
    const auto percent = static_cast<int>((accepted * 100) / total);
    return std::clamp(percent, 0, 100);
}


bool DesktopUploadQueueService::localDeletionPending(const UploadCustodyItem& item) noexcept {
    // The mark is written before the Recycle Bin operation and removed together
    // with the row, so a row still carrying it is a deletion that did not finish.
    return item.safeReason == "local_delete_pending";
}

std::vector<std::string> DesktopUploadQueueService::pendingLocalDeletionIds() const {
    std::vector<std::string> ids;
    if (quarantined_) return ids;
    for (const auto& item : items_) {
        if (item.status == UploadQueueStatus::quarantined && localDeletionPending(item)) ids.push_back(item.localRecordingId);
    }
    return ids;
}

void DesktopUploadQueueService::setClock(std::function<std::uint64_t()> clock) {
    clock_ = std::move(clock);
}

std::uint64_t DesktopUploadQueueService::nowMs() const {
    if (clock_) {
        try {
            return clock_();
        } catch (...) {
            // A clock that cannot answer is not a reason to change the ledger.
        }
    }
    const auto now = std::chrono::system_clock::now().time_since_epoch();
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(now).count());
}

void DesktopUploadQueueService::stamp(UploadCustodyItem& item) const noexcept {
    item.updatedAtMs = nowMs();
}

bool DesktopUploadQueueService::persist() {
    if (quarantined_) return false;
    // The document stamp is the moment of the last change to the ledger as a
    // whole, so it is taken here rather than by each caller.
    updatedAtMs_ = nowMs();
    const auto json = serialize(items_, deletionOperations_, purgeAcknowledgements_, updatedAtMs_);
    const bool saved = ledgerWriter_ ? ledgerWriter_(custodyRoot_, ledgerPath_, json) :
        AtomicFileStore::writeWithinRoot(custodyRoot_, ledgerPath_, json, 4 * 1024 * 1024).ok();
    if (saved) { ledgerKnown_ = true; return true; }
    quarantined_ = true;
    return false;
}

std::string DesktopUploadQueueService::serialize(const std::vector<UploadCustodyItem>& items,
                                                 const std::vector<DeletionOperationRecord>& operations,
                                                 const std::vector<LocalPurgeAcknowledgement>& purgeAcknowledgements,
                                                 std::uint64_t updatedAtMs) {
    std::string json(std::size_t{0}, char{});
    serializeQueueLedger(json, items, operations, purgeAcknowledgements, updatedAtMs, nullptr, json.max_size());
    return json;
}

bool DesktopUploadQueueService::validServerOrigin(std::string_view value) noexcept {
    if (value.empty() || value.size() > 200) return false;
    const auto schemeEnd = value.find("://");
    if (schemeEnd == std::string_view::npos) return false;
    const auto scheme = value.substr(0, schemeEnd);
    const bool secure = scheme == "https";
    if (!secure && scheme != "http") return false;
    const auto authority = value.substr(schemeEnd + 3);
    // An origin, not a URL: no credentials, no path, no query, no fragment.
    if (authority.empty() || authority.find_first_of("/?#@") != std::string_view::npos) return false;
    for (const unsigned char c : authority) {
        if (!(std::isalnum(c) || c == '.' || c == '-' || c == ':' || c == '[' || c == ']')) return false;
    }
    if (!secure) {
        // Unencrypted is only acceptable towards a server on this computer, where
        // no session ever leaves the machine.
        const auto host = authority.substr(0, authority.find(':'));
        if (host != "127.0.0.1" && host != "localhost" && host != "[::1]") return false;
    }
    return true;
}

DeletionOperationRecord* DesktopUploadQueueService::findOperation(std::string_view operationId) noexcept {
    for (auto& record : deletionOperations_) if (record.operationId == operationId) return &record;
    return nullptr;
}

bool DesktopUploadQueueService::validIdentity(std::string_view value) noexcept {
    if (value.empty() || value.size() > 300) return false;
    for (const unsigned char c : value) if (!(std::isalnum(c) || c == '-' || c == '_')) return false;
    return true;
}

bool DesktopUploadQueueService::validSafeReason(std::string_view value) noexcept {
    if (value.size() > 64) return false;
    for (const unsigned char c : value) {
        if (!(std::islower(c) || std::isdigit(c) || c == '-' || c == '_')) return false;
    }
    return true;
}

UploadCustodyItem* DesktopUploadQueueService::find(std::string_view id) noexcept {
    for (auto& item : items_) if (item.localRecordingId == id) return &item;
    return nullptr;
}

CustodyFileResult<std::shared_ptr<const ProtectedUploadQueueCandidate>> ProtectedUploadQueueCandidate::read(
    std::shared_ptr<const ProtectedCustodyQueueInput> input,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Proof = std::shared_ptr<const ProtectedUploadQueueCandidate>;
    const auto reject = [](CustodyFileError error, std::uint32_t native = 0) -> CustodyFileResult<Proof> {
        return {std::nullopt, error, native};
    };
    if (!input || !cancellation) return reject(CustodyFileError::invalidInput);
    json_detail::checkCancellation(cancellation.get());
    CustodyNativeJob job;
    if (!job) return reject(CustodyFileError::allocationFailed);
    auto held = std::move(input); // Last input release remains inside actual job completion.
    const auto decode = [&](unsigned slot) {
        const auto& bytes = held->payloads()[slot];
        return ProtectedUploadQueueValue::decode(
            {reinterpret_cast<const char*>(bytes.data()), bytes.size()}, cancellation.get());
    };
    const auto selected = held->indices().selectedSlot;
    {
        auto previous = decode(1 - selected);
        if (!previous.ok()) return reject(previous.error, previous.nativeError);
    }
    json_detail::checkCancellation(cancellation.get());
    CustodyAllocator<ProtectedUploadQueueCandidate> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedUploadQueueCandidate(); }
    catch (...) { allocator.deallocate(raw, 1); throw; }
    Proof proof{raw, [](const ProtectedUploadQueueCandidate* p) {
        p->~ProtectedUploadQueueCandidate();
        CustodyAllocator<ProtectedUploadQueueCandidate>{}.deallocate(const_cast<ProtectedUploadQueueCandidate*>(p), 1);
    }, allocator};
    auto value = decode(selected);
    if (!value.ok()) return reject(value.error, value.nativeError);
    raw->value_ = std::move(*value.value);
    raw->input_ = std::move(held);
    json_detail::checkCancellation(cancellation.get());
    return {std::move(proof), CustodyFileError::none, 0};
} catch (const json_detail::ParseCancelled&) {
    return {std::nullopt, CustodyFileError::ioFailed, 995}; // ERROR_OPERATION_ABORTED, also portable.
} catch (const std::bad_alloc&) {
    return {std::nullopt, CustodyFileError::allocationFailed, 0};
}

} // namespace graf::windows
