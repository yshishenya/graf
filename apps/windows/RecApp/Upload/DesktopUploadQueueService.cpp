#include "DesktopUploadQueueService.h"
#include "DesktopApiClient.h"

#include "../Storage/AtomicFileStore.h"

#include <cctype>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iterator>
#include <limits>
#include <system_error>
#include <utility>

namespace graf::windows {
namespace {

std::string jsonEscape(std::string_view value) {
    std::string result;
    for (const char c : value) {
        switch (c) {
        case '\\': result += "\\\\"; break;
        case '"': result += "\\\""; break;
        case '\n': result += "\\n"; break;
        case '\r': result += "\\r"; break;
        case '\t': result += "\\t"; break;
        default: result += c; break;
        }
    }
    return result;
}

std::size_t objectEnd(std::string_view json, std::size_t start) {
    if (start >= json.size() || json[start] != '{') return std::string_view::npos;
    std::size_t depth = 0;
    bool quoted = false;
    bool escaped = false;
    for (std::size_t index = start; index < json.size(); ++index) {
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

std::optional<std::string> stringField(std::string_view object, std::string_view key) {
    const auto marker = std::string("\"") + std::string(key) + "\":\"";
    const auto start = object.find(marker);
    if (start == std::string_view::npos) return std::nullopt;
    std::string result;
    bool escaped = false;
    for (std::size_t index = start + marker.size(); index < object.size(); ++index) {
        const auto c = object[index];
        if (escaped) { result += c; escaped = false; continue; }
        if (c == '\\') { escaped = true; continue; }
        if (c == '"') return result;
        result += c;
    }
    return std::nullopt;
}

std::optional<std::uint64_t> numberField(std::string_view object, std::string_view key) {
    const auto marker = std::string("\"") + std::string(key) + "\":";
    const auto start = object.find(marker);
    if (start == std::string_view::npos) return std::nullopt;
    const auto valueStart = start + marker.size();
    const auto end = object.find_first_not_of("0123456789", valueStart);
    if (end == valueStart) return std::nullopt;
    const auto valueEnd = end == std::string_view::npos ? object.size() : end;
    try {
        auto delimiter = valueEnd;
        while (delimiter < object.size() && std::isspace(static_cast<unsigned char>(object[delimiter]))) ++delimiter;
        if (delimiter < object.size() && object[delimiter] != ',' && object[delimiter] != '}') return std::nullopt;
        return std::stoull(std::string(object.substr(valueStart, valueEnd - valueStart)));
    }
    catch (...) { return std::nullopt; }
}

std::optional<std::array<std::uint64_t, 3>> acceptedField(std::string_view object) {
    const auto marker = std::string("\"accepted_bytes\":[");
    const auto start = object.find(marker);
    if (start == std::string_view::npos) return std::nullopt;
    std::array<std::uint64_t, 3> result{};
    auto cursor = start + marker.size();
    for (std::size_t index = 0; index < result.size(); ++index) {
        auto& value = result[index];
        const auto end = object.find_first_not_of("0123456789", cursor);
        if (end == cursor) return std::nullopt;
        try { value = std::stoull(std::string(object.substr(cursor, end - cursor))); }
        catch (...) { return std::nullopt; }
        cursor = end;
        if (index + 1 == result.size()) {
            if (cursor >= object.size() || object[cursor] != ']') return std::nullopt;
        } else {
            if (cursor >= object.size() || object[cursor] != ',') return std::nullopt;
            ++cursor;
        }
    }
    return std::optional<std::array<std::uint64_t, 3>>(result);
}

} // namespace

namespace {

constexpr std::array<std::uint64_t, 4> kDeletionRetryDelayMs = {5000, 15000, 30000, 60000};

[[nodiscard]] const char* deletionTargetName(DeletionTarget target) noexcept {
    return target == DeletionTarget::ownOrigin ? "own_origin" : "meeting";
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
    std::filesystem::path custodyRoot)
    : ledgerPath_(std::move(ledgerPath)),
      custodyRoot_(custodyRoot.empty() ? ledgerPath_.parent_path() : std::move(custodyRoot)) {}

bool DesktopUploadQueueService::load() {
    items_.clear(); quarantined_ = false;
    deletionOperations_.clear();
    updatedAtMs_ = 0;
    std::string json;
    {
        std::ifstream input(ledgerPath_, std::ios::binary);
        if (!input) {
            std::error_code error;
            const bool exists = std::filesystem::exists(ledgerPath_, error);
            quarantined_ = exists || static_cast<bool>(error);
            if (!quarantined_) quarantined_ = std::filesystem::exists(ledgerPath_.string() + ".quarantine", error) || error;
            return !quarantined_;
        }
        json.assign(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    }
    const auto quarantine = [this] {
        std::error_code error;
        std::filesystem::rename(ledgerPath_, ledgerPath_.string() + ".quarantine", error);
        items_.clear();
        deletionOperations_.clear();
        quarantined_ = true;
        return false;
    };
    const auto prefix = std::string("{\"schema_version\":\"") + std::string(kQueueSchemaVersion) + "\",\"items\":[";
    const auto legacyPrefix = std::string("{\"schema_version\":\"") + std::string(kQueueSchemaVersionV2) + "\",\"items\":[";
    if (json.size() > 4 * 1024 * 1024 ||
        (json.rfind(prefix, 0) != 0 && json.rfind(legacyPrefix, 0) != 0)) return quarantine();
    const bool legacy = json.rfind(legacyPrefix, 0) == 0;
    std::size_t cursor = legacy ? legacyPrefix.size() : prefix.size();
    while (cursor < json.size()) {
        if (json[cursor] == ']') { ++cursor; break; }
        if (json[cursor] == ',') {
            ++cursor;
            if (cursor >= json.size() || json[cursor] == ']' || json[cursor] != '{') return quarantine();
        }
        if (json[cursor] != '{') return quarantine();
        const auto end = objectEnd(json, cursor);
        if (end == std::string_view::npos) return quarantine();
        const auto object = std::string_view(json).substr(cursor, end - cursor + 1);
        const auto fields = DesktopApiClient::jsonObjectFields(object);
        if (!fields) return quarantine();
        const auto user = fields->find("owner_user_id");
        const auto workspace = fields->find("owner_workspace_id");
        std::string ownerUser, ownerWorkspace;
        if (user != fields->end() || workspace != fields->end()) {
            if (user == fields->end() || workspace == fields->end()) return quarantine();
            const auto ownerField = [](std::string_view value, std::string& output) {
                if (value.size() < 2 || value.front() != '"' || value.back() != '"') return false;
                value.remove_prefix(1); value.remove_suffix(1);
                if (!value.empty() && !DesktopApiClient::accountId(value)) return false;
                output = value;
                return true;
            };
            if (!ownerField(user->second, ownerUser) || !ownerField(workspace->second, ownerWorkspace) ||
                ownerUser.empty() != ownerWorkspace.empty()) return quarantine();
        }
        const auto id = stringField(object, "local_recording_id");
        const auto directoryId = stringField(object, "directory_id");
        const auto sessionId = stringField(object, "session_id");
        const auto packageDirectory = stringField(object, "package_directory");
        const auto status = numberField(object, "status");
        const auto attempts = numberField(object, "attempts");
        const auto safeReason = stringField(object, "safe_reason");
        const auto accepted = acceptedField(object);
        // Written only after the server names the meeting, so an absent field is
        // the ordinary state of a row that has not been accepted yet.
        const auto meetingId = stringField(object, "meeting_id");
        if (meetingId && !meetingId->empty() && !validIdentity(*meetingId)) return quarantine();
        // Written from version 3 on, once the server named them. An absent field
        // is the ordinary state of a row the server has not accepted yet.
        const auto mediaRevisionId = stringField(object, "media_revision_id");
        const auto uploadSessionId = stringField(object, "upload_session_id");
        const auto serverStatus = stringField(object, "server_status");
        const auto processingStatus = stringField(object, "processing_status");
        if (mediaRevisionId && !mediaRevisionId->empty() && !validIdentity(*mediaRevisionId)) return quarantine();
        if (uploadSessionId && !uploadSessionId->empty() && !validIdentity(*uploadSessionId)) return quarantine();
        if (serverStatus && !serverStatus->empty() && !validSafeReason(*serverStatus)) return quarantine();
        if (processingStatus && !processingStatus->empty() && !validSafeReason(*processingStatus)) return quarantine();
        // Written only from version 3 on; an older ledger has no timestamps, and
        // a row without one is read as "never stamped" rather than as an error.
        const auto updatedAt = numberField(object, "updated_at_ms");
        if (!id || !directoryId || !sessionId || !packageDirectory || !status || !attempts || !safeReason || !accepted ||
            !validIdentity(*id) || !validIdentity(*directoryId) || !validIdentity(*sessionId) || *status > 6 ||
            *attempts > std::numeric_limits<std::uint32_t>::max() || !validSafeReason(*safeReason) ||
            packageDirectory->size() > 4096 || packageDirectory->find_first_of("\r\n\t") != std::string::npos ||
            !AtomicFileStore::isWithinRoot(custodyRoot_, *packageDirectory) ||
            find(*id) != nullptr) return quarantine();
        UploadCustodyItem item;
        item.localRecordingId = *id; item.directoryId = *directoryId; item.sessionId = *sessionId;
        item.packageDirectory = *packageDirectory; item.status = static_cast<UploadQueueStatus>(*status);
        item.acceptedBytes = *accepted; item.attempts = static_cast<std::uint32_t>(*attempts); item.safeReason = *safeReason;
        item.ownerUserId = std::move(ownerUser); item.ownerWorkspaceId = std::move(ownerWorkspace);
        if (meetingId) item.meetingId = *meetingId;
        if (mediaRevisionId) item.mediaRevisionId = *mediaRevisionId;
        if (uploadSessionId) item.uploadSessionId = *uploadSessionId;
        if (serverStatus) item.serverStatus = *serverStatus;
        if (processingStatus) item.processingStatus = *processingStatus;
        if (const auto revisionStatus = stringField(object, "media_revision_status")) {
            if (!revisionStatus->empty() && !validSafeReason(*revisionStatus)) return quarantine();
            item.mediaRevisionStatus = *revisionStatus;
        }
        if (updatedAt) item.updatedAtMs = *updatedAt;
        items_.push_back(std::move(item)); cursor = end + 1;
    }
    while (cursor < json.size() && std::isspace(static_cast<unsigned char>(json[cursor]))) ++cursor;
    if (legacy) {
        if (cursor + 1 != json.size() || json[cursor] != '}') return quarantine();
    } else {
        // The tail of a current ledger: the document stamp and the durable
        // deletion requests, in the order this writer always emits them.
        const auto tail = std::string("\"updated_at_ms\":");
        if (json.compare(cursor, 1, ",") != 0) return quarantine();
        ++cursor;
        if (json.compare(cursor, tail.size(), tail) != 0) return quarantine();
        cursor += tail.size();
        const auto stampEnd = json.find_first_not_of("0123456789", cursor);
        if (stampEnd == cursor) return quarantine();
        try {
            if (json.substr(cursor, stampEnd - cursor).size() > 18) return quarantine();
            updatedAtMs_ = std::stoull(json.substr(cursor, stampEnd - cursor));
        } catch (...) { return quarantine(); }
        cursor = stampEnd;
        const auto operationsKey = std::string(",\"deletion_operations\":[");
        if (json.compare(cursor, operationsKey.size(), operationsKey) != 0) return quarantine();
        cursor += operationsKey.size();
        while (cursor < json.size()) {
            if (json[cursor] == ']') { ++cursor; break; }
            if (json[cursor] == ',') {
                ++cursor;
                if (cursor >= json.size() || json[cursor] != '{') return quarantine();
            }
            if (json[cursor] != '{') return quarantine();
            const auto end = objectEnd(json, cursor);
            if (end == std::string_view::npos) return quarantine();
            const auto object = std::string_view(json).substr(cursor, end - cursor + 1);
            const auto fields = DesktopApiClient::jsonObjectFields(object);
            if (!fields) return quarantine();
            const auto operationId = stringField(object, "operation_id");
            const auto targetName = stringField(object, "target");
            const auto targetId = stringField(object, "target_id");
            const auto actorUserId = stringField(object, "actor_user_id");
            const auto workspaceId = stringField(object, "workspace_id");
            const auto serverOrigin = stringField(object, "server_origin");
            const auto phase = numberField(object, "phase");
            const auto requestedAt = numberField(object, "requested_at_ms");
            const auto operationUpdatedAt = numberField(object, "updated_at_ms");
            const auto attemptCount = numberField(object, "attempts");
            const auto nextAttemptAt = numberField(object, "next_attempt_at_ms");
            const auto receiptRequestId = stringField(object, "receipt_request_id");
            const auto operationReason = stringField(object, "safe_reason");
            const auto target = targetName ? deletionTargetFromName(*targetName) : std::nullopt;
            if (!operationId || !target || !targetId || !actorUserId || !workspaceId || !serverOrigin || !phase ||
                !requestedAt || !operationUpdatedAt || !attemptCount || !nextAttemptAt || !receiptRequestId ||
                !operationReason || !isDeletionOperationId(*operationId) ||
                !DesktopApiClient::accountId(*actorUserId) || !DesktopApiClient::accountId(*workspaceId) ||
                !validServerOrigin(*serverOrigin) || *phase > static_cast<std::uint64_t>(DeletionOperationPhase::verified) ||
                *attemptCount > std::numeric_limits<std::uint32_t>::max() ||
                *operationUpdatedAt < *requestedAt || !validSafeReason(*operationReason) ||
                (*target == DeletionTarget::ownOrigin ? !validIdentity(*targetId)
                                                      : !DesktopApiClient::accountId(*targetId)) ||
                (*nextAttemptAt != 0 && *nextAttemptAt < *operationUpdatedAt) ||
                (!receiptRequestId->empty() && !DesktopApiClient::accountId(*receiptRequestId)) ||
                findOperation(*operationId) != nullptr) return quarantine();
            DeletionOperationRecord record;
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
            if (deletionPhaseIsAccepted(record.phase) && record.receiptRequestId.empty()) return quarantine();
            if (record.phase == DeletionOperationPhase::rejected && record.safeReason.empty()) return quarantine();
            deletionOperations_.push_back(std::move(record));
            cursor = end + 1;
        }
        // The acknowledged purge tasks are the last field of a current ledger and
        // absent from the one this writer produced before them.
        const auto purgeKey = std::string(",\"purge_acknowledgements\":[");
        if (json.compare(cursor, purgeKey.size(), purgeKey) == 0) {
            cursor += purgeKey.size();
            while (cursor < json.size()) {
                if (json[cursor] == ']') { ++cursor; break; }
                if (json[cursor] == ',') {
                    ++cursor;
                    if (cursor >= json.size() || json[cursor] != '{') return quarantine();
                }
                if (json[cursor] != '{') return quarantine();
                const auto end = objectEnd(json, cursor);
                if (end == std::string_view::npos) return quarantine();
                const auto object = std::string_view(json).substr(cursor, end - cursor + 1);
                const auto taskId = stringField(object, "task_id");
                const auto meetingId = stringField(object, "meeting_id");
                const auto acknowledgedAt = numberField(object, "acknowledged_at_ms");
                if (!taskId || !meetingId || !acknowledgedAt || !DesktopApiClient::accountId(*taskId) ||
                    !DesktopApiClient::accountId(*meetingId) || hasLocalPurgeAcknowledgement(*taskId)) {
                    return quarantine();
                }
                LocalPurgeAcknowledgement record;
                record.taskId = *taskId;
                record.meetingId = *meetingId;
                record.acknowledgedAtMs = *acknowledgedAt;
                purgeAcknowledgements_.push_back(std::move(record));
                cursor = end + 1;
            }
        }
        while (cursor < json.size() && std::isspace(static_cast<unsigned char>(json[cursor]))) ++cursor;
        if (cursor + 1 != json.size() || json[cursor] != '}') return quarantine();
    }
    // A previous process has no live upload worker. Recover only after the
    // entire ledger is valid, preserving owner, identity and server ranges.
    bool recovered = false;
    for (auto& item : items_) {
        if (item.status != UploadQueueStatus::uploading) continue;
        item.status = UploadQueueStatus::retry;
        item.safeReason = "upload_interrupted";
        stamp(item);
        recovered = true;
    }
    if (legacy) {
        // Rewriting a readable version-2 ledger upgrades it and gives every row
        // the stamp it never had.
        for (auto& item : items_) {
            if (item.updatedAtMs == 0) stamp(item);
        }
        return persist();
    }
    return !recovered || persist();
}

bool DesktopUploadQueueService::enqueue(UploadCustodyItem item) {
    if (quarantined_ || !validIdentity(item.localRecordingId) || !validIdentity(item.directoryId) || !validIdentity(item.sessionId) ||
        item.packageDirectory.empty() || !AtomicFileStore::isWithinRoot(custodyRoot_, item.packageDirectory) ||
        find(item.localRecordingId) != nullptr) return false;
    if ((!item.ownerUserId.empty() || !item.ownerWorkspaceId.empty()) &&
        (!DesktopApiClient::accountId(item.ownerUserId) || !DesktopApiClient::accountId(item.ownerWorkspaceId))) return false;
    stamp(item);
    items_.push_back(std::move(item));
    return persist();
}

bool DesktopUploadQueueService::reconcile(const UploadServerTruth& truth) {
    auto* item = find(truth.localRecordingId);
    if (item == nullptr) return false;
    item->acceptedBytes = truth.acceptedBytes;
    // Adopt the server meeting id once, and only if the server sent a usable
    // one: the ledger field has to stay safe to serialize.
    if (item->meetingId.empty() && !truth.meetingId.empty() && validIdentity(truth.meetingId))
        item->meetingId = truth.meetingId;
    // The server's own fingerprint is adopted as it arrives: it describes what
    // the server holds now, and a stale copy would make the ledger claim a
    // revision or a session the server has already replaced. Every value is
    // checked before it is written, so a malformed answer cannot reach the file.
    const auto adopt = [](std::string& field, const std::string& value, bool (*valid)(std::string_view)) {
        if (!value.empty() && valid(value)) field = value;
    };
    adopt(item->mediaRevisionId, truth.mediaRevisionId, validIdentity);
    adopt(item->uploadSessionId, truth.uploadSessionId, validIdentity);
    adopt(item->serverStatus, truth.serverStatus, validSafeReason);
    adopt(item->processingStatus, truth.processingStatus, validSafeReason);
    adopt(item->mediaRevisionStatus, truth.mediaRevisionStatus, validSafeReason);
    if (truth.finalized) item->status = UploadQueueStatus::uploaded;
    else if (truth.uploadSessionExists) item->status = UploadQueueStatus::uploading;
    stamp(*item);
    return persist();
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
    if (quarantined_ || !item ||
        (item->status != UploadQueueStatus::pending && item->status != UploadQueueStatus::retry &&
         item->status != UploadQueueStatus::needsAuth && item->status != UploadQueueStatus::blocked) ||
        !DesktopApiClient::accountId(item->ownerUserId) || !DesktopApiClient::accountId(item->ownerWorkspaceId)) return false;
    const auto previous = *item;
    item->status = UploadQueueStatus::retry;
    item->attempts = 0;
    item->safeReason = "manual_retry";
    stamp(*item);
    if (persist()) return true;
    *item = previous;
    return false;
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
    bool changed = false;
    for (auto& item : items_) {
        if (item.status != UploadQueueStatus::needsAuth) continue;
        item.status = UploadQueueStatus::retry;
        item.safeReason = "auth_recovered";
        stamp(item);
        changed = true;
    }
    return !changed || persist();
}

bool DesktopUploadQueueService::markQuarantined(std::string_view id, std::string reason) {
    auto* item = find(id); if (!item || reason.empty() || !validSafeReason(reason)) return false;
    item->status = UploadQueueStatus::quarantined; item->safeReason = std::move(reason);
    stamp(*item);
    return persist();
}

bool DesktopUploadQueueService::markBlocked(std::string_view id, std::string reason) {
    auto* item = find(id); if (!item || reason.empty() || !validSafeReason(reason)) return false;
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
    // success + ledger failure this row stays quarantined, never uploadable.
    item->status = UploadQueueStatus::quarantined;
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
    if (quarantined_ || !DesktopApiClient::accountId(owner.userId) ||
        !DesktopApiClient::accountId(owner.workspaceId) || !validServerOrigin(serverOrigin)) return false;
    if (target == DeletionTarget::ownOrigin ? !validIdentity(targetId)
                                            : !DesktopApiClient::accountId(targetId)) return false;
    const auto derived = DesktopApiClient::deletionOperationId(DeletionScope{owner.userId, owner.workspaceId},
                                                              target, targetId);
    if (!isDeletionOperationId(derived)) return false;
    for (const auto& existing : deletionOperations_) {
        if (existing.operationId != derived) continue;
        if (existing.actorUserId != owner.userId || existing.workspaceId != owner.workspaceId ||
            existing.target != target || existing.targetId != targetId ||
            existing.serverOrigin != serverOrigin) {
            // The same name for a different request. Nothing is stored, because
            // storing it would either hide the earlier request or send this one
            // under a name the server has already seen.
            return false;
        }
        // Asking again for the same deletion is the same operation: the cabinet
        // is told the request is saved, and no second request is created.
        operationId = existing.operationId;
        return true;
    }
    DeletionOperationRecord record;
    record.operationId = derived;
    record.target = target;
    record.targetId = std::string(targetId);
    record.actorUserId = owner.userId;
    record.workspaceId = owner.workspaceId;
    record.serverOrigin = std::string(serverOrigin);
    record.requestedAtMs = nowMs();
    record.updatedAtMs = record.requestedAtMs;
    deletionOperations_.push_back(record);
    if (!persist()) {
        deletionOperations_.pop_back();
        return false;
    }
    operationId = derived;
    return true;
}

bool DesktopUploadQueueService::markDeletionPhase(std::string_view operationId, DeletionOperationPhase phase,
                                                 std::string_view safeReason) {
    if (quarantined_ || !validSafeReason(safeReason)) return false;
    auto* record = findOperation(operationId);
    if (record == nullptr) return false;
    // Acceptance is not a phase a caller may simply declare: it exists only
    // together with the receipt that named this target.
    if (phase == DeletionOperationPhase::accepted) return false;
    const auto now = nowMs();
    if (now < record->updatedAtMs) return false;
    if (record->phase == DeletionOperationPhase::verified) return false;
    // Deletion is monotonic: once the server accepted it, only the proof that the
    // local copies are gone may follow. A late failure is not a reason to start
    // showing a recording the server has already deleted.
    if (deletionPhaseIsAccepted(record->phase) && phase != DeletionOperationPhase::verified) return false;
    if (phase == DeletionOperationPhase::verified && record->phase != DeletionOperationPhase::accepted) return false;
    const auto previous = *record;
    record->phase = phase;
    record->updatedAtMs = now;
    record->safeReason = std::string(safeReason);
    if (phase == DeletionOperationPhase::sending) {
        record->nextAttemptAtMs = 0;
        if (record->attemptCount < std::numeric_limits<std::uint32_t>::max()) ++record->attemptCount;
    } else if (phase == DeletionOperationPhase::resolving) {
        const auto attempts = record->attemptCount == 0 ? std::size_t{0} : record->attemptCount - 1;
        record->nextAttemptAtMs =
            now + kDeletionRetryDelayMs[std::min(attempts, kDeletionRetryDelayMs.size() - 1)];
    } else {
        record->nextAttemptAtMs = 0;
    }
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
    // The receipt has to name this exact target. An answer about another
    // recording must never confirm this one, and the two receipt shapes are not
    // interchangeable.
    if (record->target == DeletionTarget::ownOrigin) {
        // A local copy is confirmed by a cancellation of that copy, or by a
        // meeting deletion that names it: the server may have resolved the copy to
        // a meeting and deleted the meeting everywhere. macOS accepts the same two
        // answers (`RecordingDeletionReceipt.matches`).
        if (receipt.receiptType != "origin_cancellation" && receipt.receiptType != "meeting_deletion") return false;
        if (receipt.localRecordingId != record->targetId) return false;
        if (receipt.receiptType == "meeting_deletion" && receipt.meetingId.empty()) return false;
    } else if (record->target == DeletionTarget::meeting) {
        if (receipt.receiptType != "meeting_deletion" || receipt.meetingId != record->targetId) return false;
    } else {
        return false;
    }
    if (record->phase == DeletionOperationPhase::verified) return true;
    if (!record->receiptRequestId.empty() && record->receiptRequestId != receipt.requestId) {
        // Two different answers for one request: keeping either would make the
        // stored state depend on which one arrived last.
        return false;
    }
    const auto now = nowMs();
    if (now < record->updatedAtMs) return false;
    const auto previous = *record;
    record->phase = DeletionOperationPhase::accepted;
    record->receiptRequestId = receipt.requestId;
    record->updatedAtMs = now;
    record->nextAttemptAtMs = 0;
    record->safeReason.clear();
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
    return !item.meetingId.empty() || item.attempts > 0 || item.status == UploadQueueStatus::uploaded;
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
    // A ledger this app could not read is not evidence about any local copy, so
    // nothing is removed and nothing is acknowledged.
    if (quarantined_) return completion;
    // A task this device already carried out is answered from the record: the rows
    // it named are gone, and looking for them again would turn a proven deletion
    // into "unverified" the second time the server asked.
    if (hasLocalPurgeAcknowledgement(task.taskId)) {
        completion.verification = LocalPurgeVerification::deleted;
        completion.reasonCode = std::string(localPurgeReasonCode(completion.verification));
        return completion;
    }
    const auto candidates = localPurgeCandidates(task);
    // Only the buffers task is about the local copies themselves. A task this
    // client cannot carry out is answered honestly, without touching a file: a
    // claim of deletion it did not verify would be exactly the false proof this
    // port removed once already.
    if (task.taskType == "purge_local_buffers" && !candidates.empty()) {
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
                return (record.target == DeletionTarget::meeting && record.targetId == item.meetingId) ||
                    (record.target == DeletionTarget::ownOrigin && record.targetId == item.directoryId);
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
    DeletionPlan plan;
    // The account has to be an account: a request stored for an unknown owner
    // could never be completed, and completing it under a guessed name would
    // delete something else. The origin is validated with the request itself.
    if (quarantined_ || !DesktopApiClient::accountId(owner.userId) ||
        !DesktopApiClient::accountId(owner.workspaceId)) {
        return plan;
    }

    // Resolve the whole selection before storing anything. macOS saves the batch
    // in one step; resolving first keeps a refusal from leaving half a selection
    // durable, and a request the user did not confirm is never stored.
    std::vector<std::pair<DeletionTarget, std::string>> resolved;
    for (const auto& request : targets) {
        if (request.target == DeletionTarget::meeting) {
            if (DesktopApiClient::accountId(request.targetId)) {
                resolved.emplace_back(request.target, request.targetId);
            }
            continue;
        }
        const auto row = std::find_if(items_.begin(), items_.end(), [&request](const auto& item) {
            return item.directoryId == request.targetId;
        });
        // A local copy this queue does not know is not a local copy this app may
        // delete: the page cannot name a directory into existence.
        if (row == items_.end()) continue;
        // A copy the server has never been told about needs no request. The caller
        // removes it and says what happened.
        if (!hasServerIdentity(*row)) {
            plan.localOnly.push_back(row->localRecordingId);
            continue;
        }
        // A copy that is being uploaded right now cannot be asked to disappear.
        if (row->status == UploadQueueStatus::uploading) continue;
        // Prefer the same target as the server row when its identity is known, the
        // way macOS does: deleting the recording the server owns is what the user
        // asked for, and it is the same request the other platform would send.
        if (!row->meetingId.empty()) resolved.emplace_back(DeletionTarget::meeting, row->meetingId);
        else resolved.emplace_back(DeletionTarget::ownOrigin, row->directoryId);
    }

    // One selection may name the same recording twice — a local row and the
    // meeting it belongs to. It is one deletion, and it is requested once.
    for (const auto& [target, targetId] : resolved) {
        std::string operationId;
        if (!requestDeletion(target, targetId, owner, serverOrigin, operationId)) continue;
        if (std::find(plan.operationIds.begin(), plan.operationIds.end(), operationId) !=
            plan.operationIds.end()) continue;
        plan.operationIds.push_back(operationId);
        DeletionRequestPlan entry;
        entry.operationId = operationId;
        entry.target = target;
        entry.targetId = targetId;
        // The two shapes are not interchangeable, and the server refuses a body
        // that carries a field its request does not have.
        entry.path = target == DeletionTarget::meeting ? DesktopApiClient::meetingDeletionPath(targetId)
                                                       : DesktopApiClient::ownOriginDeletionPath(targetId);
        entry.body = target == DeletionTarget::meeting ? DesktopApiClient::meetingDeletionBody()
                                                       : DesktopApiClient::originCancellationBody(operationId);
        plan.requests.push_back(std::move(entry));
    }
    plan.saved = !plan.operationIds.empty() || !plan.localOnly.empty();

    // A request that already has an answer, or that is waiting for its next
    // attempt, is not sent again. It is still counted in the outcome.
    const auto now = nowMs();
    plan.requests.erase(std::remove_if(plan.requests.begin(), plan.requests.end(), [&](const auto& entry) {
        const auto* stored = findDeletionOperation(entry.operationId);
        if (stored == nullptr) return true;
        if (stored->serverOrigin != serverOrigin) return true;
        if (deletionPhaseIsAccepted(stored->phase) ||
            stored->phase == DeletionOperationPhase::rejected) return true;
        return stored->nextAttemptAtMs > now;
    }), plan.requests.end());
    return plan;
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
    // Count the attempt now that it has happened. `sending` is the transition that
    // counts it, and the final phase is recorded immediately after, so the ledger
    // never lingers in a state that describes a flight nobody is watching.
    if (!markDeletionPhase(request.operationId, DeletionOperationPhase::sending, "attempt")) return false;
    if (wire.accepted()) {
        const auto receipt = DesktopApiClient::decodeDeletionReceipt(wire.body);
        if (receipt != std::nullopt && acceptDeletion(request.operationId, *receipt)) {
            // The server may have created the meeting for this local copy while
            // deleting it. The row learns that identity instead of asking the
            // server for it again.
            if (request.target == DeletionTarget::ownOrigin && !receipt->meetingId.empty()) {
                for (auto& item : items_) {
                    if (item.directoryId != request.targetId || item.meetingId == receipt->meetingId) continue;
                    item.meetingId = receipt->meetingId;
                    stamp(item);
                }
                (void)persist();
            }
            return true;
        }
        // An answer that cannot be read is not evidence that the recording is gone:
        // the request waits and is asked again.
        return markDeletionPhase(request.operationId, DeletionOperationPhase::resolving, "unreadable_receipt");
    }
    // A request that was never sent, or that waited for the gate, says nothing
    // about the target. It is left for the next pass rather than recorded as an
    // answer.
    if (!wire.waitReason.empty()) {
        return markDeletionPhase(request.operationId, DeletionOperationPhase::resolving, wire.waitReason);
    }
    // The server refused this target, and only this target. macOS reads the same
    // answer the same way: a 403 with that reason is final, everything else is a
    // wait.
    if (wire.status == 403 && wire.body.find("deletion_forbidden") != std::string::npos) {
        return markDeletionPhase(request.operationId, DeletionOperationPhase::rejected, "deletion_forbidden");
    }
    std::string_view waitReason = "connection";
    if (wire.status == 401) waitReason = "authentication";
    else if (wire.status == 404 || wire.status == 426) waitReason = "server_update";
    else if (wire.status == 429) waitReason = "rate_limit";
    const auto recorded = markDeletionPhase(request.operationId, DeletionOperationPhase::resolving, waitReason);
    if (wire.retryAfterSeconds != 0) {
        // The wait the server asked for is kept, not the client's own schedule.
        const auto delay = std::min<std::uint64_t>(
            static_cast<std::uint64_t>(wire.retryAfterSeconds) * 1000, 24ULL * 60 * 60 * 1000);
        (void)markDeletionAttempt(request.operationId, nowMs() + delay);
    }
    return recorded;
}

std::string DesktopUploadQueueService::deletionGateReason(const DeletionWireResult& context,
                                                          const DesktopAccountIdentity& owner) {
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
    const auto declared = DesktopApiClient::decodeNotificationContext(context.body);
    if (!declared || declared->protocolVersion != 1) return "server_update";
    if (declared->userId != owner.userId || declared->workspaceId != owner.workspaceId) return "scope_changed";
    return {};
}

bool DesktopUploadQueueService::deletionFailureIsShared(const DeletionWireResult& wire) noexcept {
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

bool DesktopUploadQueueService::localDeletionPending(const UploadCustodyItem& item) noexcept {
    // The mark is written before the Recycle Bin operation and removed together
    // with the row, so a row still carrying it is a deletion that did not finish.
    return item.safeReason == "local_delete_pending";
}

std::vector<std::string> DesktopUploadQueueService::pendingLocalDeletionIds() const {
    std::vector<std::string> ids;
    if (quarantined_) return ids;
    for (const auto& item : items_) {
        if (localDeletionPending(item)) ids.push_back(item.localRecordingId);
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
    if (AtomicFileStore::writeWithinRoot(custodyRoot_, ledgerPath_,
            serialize(items_, deletionOperations_, purgeAcknowledgements_, updatedAtMs_),
            4 * 1024 * 1024).ok()) return true;
    quarantined_ = true;
    return false;
}

std::string DesktopUploadQueueService::serialize(const std::vector<UploadCustodyItem>& items,
                                                 const std::vector<DeletionOperationRecord>& operations,
                                                 const std::vector<LocalPurgeAcknowledgement>& purgeAcknowledgements,
                                                 std::uint64_t updatedAtMs) {
    std::string json = std::string("{\"schema_version\":\"") + std::string(kQueueSchemaVersion) + "\",\"items\":[";
    for (std::size_t index = 0; index < items.size(); ++index) {
        if (index != 0) json += ',';
        json += "{\"local_recording_id\":\"" + jsonEscape(items[index].localRecordingId) +
            "\",\"directory_id\":\"" + jsonEscape(items[index].directoryId) +
            "\",\"session_id\":\"" + jsonEscape(items[index].sessionId) +
            "\",\"package_directory\":\"" + jsonEscape(items[index].packageDirectory.string()) +
            "\",\"status\":" + std::to_string(static_cast<int>(items[index].status)) +
            ",\"accepted_bytes\":[" + std::to_string(items[index].acceptedBytes[0]) + "," +
            std::to_string(items[index].acceptedBytes[1]) + "," + std::to_string(items[index].acceptedBytes[2]) +
            "],\"attempts\":" + std::to_string(items[index].attempts) +
            ",\"safe_reason\":\"" + jsonEscape(items[index].safeReason) +
            "\",\"owner_user_id\":\"" + jsonEscape(items[index].ownerUserId) +
            "\",\"owner_workspace_id\":\"" + jsonEscape(items[index].ownerWorkspaceId) +
            "\",\"meeting_id\":\"" + jsonEscape(items[index].meetingId) +
            "\",\"media_revision_id\":\"" + jsonEscape(items[index].mediaRevisionId) +
            "\",\"upload_session_id\":\"" + jsonEscape(items[index].uploadSessionId) +
            "\",\"server_status\":\"" + jsonEscape(items[index].serverStatus) +
            "\",\"processing_status\":\"" + jsonEscape(items[index].processingStatus) +
            "\",\"media_revision_status\":\"" + jsonEscape(items[index].mediaRevisionStatus) +
            "\",\"updated_at_ms\":" + std::to_string(items[index].updatedAtMs) + "}";
    }
    json += "],\"updated_at_ms\":" + std::to_string(updatedAtMs) + ",\"deletion_operations\":[";
    for (std::size_t index = 0; index < operations.size(); ++index) {
        if (index != 0) json += ',';
        json += "{\"operation_id\":\"" + jsonEscape(operations[index].operationId) +
            "\",\"target\":\"" + deletionTargetName(operations[index].target) +
            "\",\"target_id\":\"" + jsonEscape(operations[index].targetId) +
            "\",\"actor_user_id\":\"" + jsonEscape(operations[index].actorUserId) +
            "\",\"workspace_id\":\"" + jsonEscape(operations[index].workspaceId) +
            "\",\"server_origin\":\"" + jsonEscape(operations[index].serverOrigin) +
            "\",\"phase\":" + std::to_string(static_cast<int>(operations[index].phase)) +
            ",\"requested_at_ms\":" + std::to_string(operations[index].requestedAtMs) +
            ",\"updated_at_ms\":" + std::to_string(operations[index].updatedAtMs) +
            ",\"attempts\":" + std::to_string(operations[index].attemptCount) +
            ",\"next_attempt_at_ms\":" + std::to_string(operations[index].nextAttemptAtMs) +
            ",\"receipt_request_id\":\"" + jsonEscape(operations[index].receiptRequestId) +
            "\",\"safe_reason\":\"" + jsonEscape(operations[index].safeReason) + "\"}";
    }
    json += "],\"purge_acknowledgements\":[";
    for (std::size_t index = 0; index < purgeAcknowledgements.size(); ++index) {
        if (index != 0) json += ',';
        json += "{\"task_id\":\"" + jsonEscape(purgeAcknowledgements[index].taskId) +
            "\",\"meeting_id\":\"" + jsonEscape(purgeAcknowledgements[index].meetingId) +
            "\",\"acknowledged_at_ms\":" + std::to_string(purgeAcknowledgements[index].acknowledgedAtMs) + "}";
    }
    return json + "]}";
}

bool deletionPhaseIsAccepted(DeletionOperationPhase phase) noexcept {
    return phase == DeletionOperationPhase::accepted || phase == DeletionOperationPhase::verified;
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

} // namespace graf::windows
