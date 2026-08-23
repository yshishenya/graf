#include "DesktopUploadQueueService.h"

#include "../Storage/AtomicFileStore.h"

#include <cctype>
#include <fstream>
#include <iterator>

namespace graf::windows {
namespace {

std::string jsonEscape(std::string_view value) {
    std::string result;
    for (const char c : value) {
        if (c == '\\' || c == '"') result += '\\';
        result += c;
    }
    return result;
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
    try { return std::stoull(std::string(object.substr(valueStart, end - valueStart))); }
    catch (...) { return std::nullopt; }
}

std::array<std::uint64_t, 3> acceptedField(std::string_view object) {
    const auto marker = std::string("\"accepted_bytes\":[");
    const auto start = object.find(marker);
    if (start == std::string_view::npos) return {};
    std::array<std::uint64_t, 3> result{};
    auto cursor = start + marker.size();
    for (auto& value : result) {
        const auto end = object.find_first_not_of("0123456789", cursor);
        try { value = std::stoull(std::string(object.substr(cursor, end - cursor))); }
        catch (...) { return {}; }
        cursor = object.find_first_of(",]", end);
        if (cursor == std::string_view::npos || object[cursor] == ']') break;
        ++cursor;
    }
    return result;
}

} // namespace

DesktopUploadQueueService::DesktopUploadQueueService(std::filesystem::path ledgerPath)
    : ledgerPath_(std::move(ledgerPath)) {}

bool DesktopUploadQueueService::load() {
    items_.clear(); quarantined_ = false;
    std::ifstream input(ledgerPath_, std::ios::binary);
    if (!input) return true;
    const std::string json((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    if (json.find(kQueueSchemaVersion) == std::string::npos || json.find("\"items\":[") == std::string::npos) {
        std::error_code error;
        std::filesystem::rename(ledgerPath_, ledgerPath_.string() + ".quarantine", error);
        quarantined_ = true;
        return false;
    }
    // The durable ledger is intentionally written by this class. Unknown/foreign item syntax is quarantined.
    std::size_t cursor = json.find("\"items\":[") + 9;
    while (cursor < json.size()) {
        const auto objectStart = json.find('{', cursor);
        if (objectStart == std::string::npos) break;
        const auto objectEnd = json.find('}', objectStart);
        if (objectEnd == std::string::npos) { quarantined_ = true; return false; }
        const auto object = std::string_view(json).substr(objectStart, objectEnd - objectStart + 1);
        const auto id = stringField(object, "local_recording_id");
        const auto directoryId = stringField(object, "directory_id");
        const auto sessionId = stringField(object, "session_id");
        const auto packageDirectory = stringField(object, "package_directory");
        const auto status = numberField(object, "status");
        const auto attempts = numberField(object, "attempts");
        const auto safeReason = stringField(object, "safe_reason");
        if (!id || !directoryId || !sessionId || !packageDirectory || !status || !attempts || !safeReason ||
            !validIdentity(*id) || !validIdentity(*directoryId) || !validIdentity(*sessionId) || *status > 5) {
            quarantined_ = true; return false;
        }
        UploadCustodyItem item;
        item.localRecordingId = *id; item.directoryId = *directoryId; item.sessionId = *sessionId;
        item.packageDirectory = *packageDirectory; item.status = static_cast<UploadQueueStatus>(*status);
        item.acceptedBytes = acceptedField(object); item.attempts = static_cast<std::uint32_t>(*attempts); item.safeReason = *safeReason;
        items_.push_back(std::move(item)); cursor = objectEnd + 1;
    }
    return true;
}

bool DesktopUploadQueueService::enqueue(UploadCustodyItem item) {
    if (!validIdentity(item.localRecordingId) || !validIdentity(item.directoryId) || !validIdentity(item.sessionId) ||
        item.packageDirectory.empty() || find(item.localRecordingId) != nullptr) return false;
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
    auto* item = find(id); if (!item) return false;
    item->status = UploadQueueStatus::retry; ++item->attempts; item->safeReason = std::move(reason); return persist();
}

bool DesktopUploadQueueService::markNeedsAuth(std::string_view id) {
    auto* item = find(id); if (!item) return false;
    item->status = UploadQueueStatus::needsAuth; item->safeReason = "auth_required"; return persist();
}

bool DesktopUploadQueueService::markUploaded(std::string_view id) {
    auto* item = find(id); if (!item) return false;
    item->status = UploadQueueStatus::uploaded; return persist();
}

std::optional<UploadCustodyItem> DesktopUploadQueueService::nextPending() const {
    for (const auto& item : items_) {
        if (item.status == UploadQueueStatus::pending || item.status == UploadQueueStatus::retry) return item;
    }
    return std::nullopt;
}

bool DesktopUploadQueueService::persist() const {
    return AtomicFileStore::write(ledgerPath_, serialize(items_), 4 * 1024 * 1024).ok();
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
            ",\"safe_reason\":\"" + jsonEscape(items[index].safeReason) + "\"}";
    }
    return json + "]}";
}

bool DesktopUploadQueueService::validIdentity(std::string_view value) noexcept {
    if (value.empty() || value.size() > 300) return false;
    for (const unsigned char c : value) if (!(std::isalnum(c) || c == '-' || c == '_')) return false;
    return true;
}

UploadCustodyItem* DesktopUploadQueueService::find(std::string_view id) noexcept {
    for (auto& item : items_) if (item.localRecordingId == id) return &item;
    return nullptr;
}

} // namespace graf::windows
