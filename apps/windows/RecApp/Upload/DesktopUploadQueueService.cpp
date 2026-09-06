#include "DesktopUploadQueueService.h"
#include "DesktopApiClient.h"

#include "../Storage/AtomicFileStore.h"

#include <cctype>
#include <algorithm>
#include <fstream>
#include <iterator>
#include <limits>

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

DesktopUploadQueueService::DesktopUploadQueueService(
    std::filesystem::path ledgerPath,
    std::filesystem::path custodyRoot)
    : ledgerPath_(std::move(ledgerPath)),
      custodyRoot_(custodyRoot.empty() ? ledgerPath_.parent_path() : std::move(custodyRoot)) {}

bool DesktopUploadQueueService::load() {
    items_.clear(); quarantined_ = false;
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
        quarantined_ = true;
        return false;
    };
    const auto prefix = std::string("{\"schema_version\":\"") + std::string(kQueueSchemaVersion) + "\",\"items\":[";
    if (json.size() > 4 * 1024 * 1024 || json.rfind(prefix, 0) != 0) return quarantine();
    std::size_t cursor = prefix.size();
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
        if (!id || !directoryId || !sessionId || !packageDirectory || !status || !attempts || !safeReason || !accepted ||
            !validIdentity(*id) || !validIdentity(*directoryId) || !validIdentity(*sessionId) || *status > 5 ||
            *attempts > std::numeric_limits<std::uint32_t>::max() || !validSafeReason(*safeReason) ||
            packageDirectory->size() > 4096 || packageDirectory->find_first_of("\r\n\t") != std::string::npos ||
            !AtomicFileStore::isWithinRoot(custodyRoot_, *packageDirectory) ||
            find(*id) != nullptr) return quarantine();
        UploadCustodyItem item;
        item.localRecordingId = *id; item.directoryId = *directoryId; item.sessionId = *sessionId;
        item.packageDirectory = *packageDirectory; item.status = static_cast<UploadQueueStatus>(*status);
        item.acceptedBytes = *accepted; item.attempts = static_cast<std::uint32_t>(*attempts); item.safeReason = *safeReason;
        item.ownerUserId = std::move(ownerUser); item.ownerWorkspaceId = std::move(ownerWorkspace);
        items_.push_back(std::move(item)); cursor = end + 1;
    }
    while (cursor < json.size() && std::isspace(static_cast<unsigned char>(json[cursor]))) ++cursor;
    if (cursor + 1 == json.size() && json[cursor] == '}') return true;
    return quarantine();
}

bool DesktopUploadQueueService::enqueue(UploadCustodyItem item) {
    if (quarantined_ || !validIdentity(item.localRecordingId) || !validIdentity(item.directoryId) || !validIdentity(item.sessionId) ||
        item.packageDirectory.empty() || !AtomicFileStore::isWithinRoot(custodyRoot_, item.packageDirectory) ||
        find(item.localRecordingId) != nullptr) return false;
    if ((!item.ownerUserId.empty() || !item.ownerWorkspaceId.empty()) &&
        (!DesktopApiClient::accountId(item.ownerUserId) || !DesktopApiClient::accountId(item.ownerWorkspaceId))) return false;
    items_.push_back(std::move(item));
    return persist();
}

bool DesktopUploadQueueService::reconcile(const UploadServerTruth& truth) {
    auto* item = find(truth.localRecordingId);
    if (item == nullptr) return false;
    item->acceptedBytes = truth.acceptedBytes;
    if (truth.finalized) item->status = UploadQueueStatus::uploaded;
    else if (truth.uploadSessionExists) item->status = UploadQueueStatus::uploading;
    return persist();
}

bool DesktopUploadQueueService::markRetry(std::string_view id, std::string reason) {
    auto* item = find(id); if (!item || !validSafeReason(reason) || reason.empty()) return false;
    item->status = UploadQueueStatus::retry; ++item->attempts; item->safeReason = std::move(reason); return persist();
}

bool DesktopUploadQueueService::markNeedsAuth(std::string_view id, std::string reason) {
    auto* item = find(id); if (quarantined_ || !item || reason.empty() || !validSafeReason(reason)) return false;
    item->status = UploadQueueStatus::needsAuth; item->safeReason = std::move(reason); return persist();
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
        changed = true;
    }
    return !changed || persist();
}

bool DesktopUploadQueueService::markQuarantined(std::string_view id, std::string reason) {
    auto* item = find(id); if (!item || reason.empty() || !validSafeReason(reason)) return false;
    item->status = UploadQueueStatus::quarantined; item->safeReason = std::move(reason); return persist();
}

bool DesktopUploadQueueService::markUploaded(std::string_view id) {
    auto* item = find(id); if (!item) return false;
    item->status = UploadQueueStatus::uploaded; return persist();
}

LocalCopyRemovalResult DesktopUploadQueueService::removeLocalCopy(
    std::string_view id, LocalPurgeProof proof,
    const std::function<bool(const std::filesystem::path&)>& recycle) {
    if (proof != LocalPurgeProof::userConfirmedLocalCopy) return LocalCopyRemovalResult::confirmationRequired;
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

bool DesktopUploadQueueService::persist() {
    if (quarantined_) return false;
    if (AtomicFileStore::writeWithinRoot(custodyRoot_, ledgerPath_, serialize(items_), 4 * 1024 * 1024).ok()) return true;
    quarantined_ = true;
    return false;
}

std::string DesktopUploadQueueService::serialize(const std::vector<UploadCustodyItem>& items) {
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
            "\",\"owner_workspace_id\":\"" + jsonEscape(items[index].ownerWorkspaceId) + "\"}";
    }
    return json + "]}";
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
