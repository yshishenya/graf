#include "DesktopUploadQueueService.h"

#include "../Storage/AtomicFileStore.h"

#include <cctype>
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
    std::ifstream input(ledgerPath_, std::ios::binary);
    if (!input) return true;
    const std::string json((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
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
        items_.push_back(std::move(item)); cursor = end + 1;
    }
    while (cursor < json.size() && std::isspace(static_cast<unsigned char>(json[cursor]))) ++cursor;
    if (cursor + 1 == json.size() && json[cursor] == '}') return true;
    return quarantine();
}

bool DesktopUploadQueueService::enqueue(UploadCustodyItem item) {
    if (!validIdentity(item.localRecordingId) || !validIdentity(item.directoryId) || !validIdentity(item.sessionId) ||
        item.packageDirectory.empty() || !AtomicFileStore::isWithinRoot(custodyRoot_, item.packageDirectory) ||
        find(item.localRecordingId) != nullptr) return false;
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

bool DesktopUploadQueueService::markNeedsAuth(std::string_view id) {
    auto* item = find(id); if (!item) return false;
    item->status = UploadQueueStatus::needsAuth; item->safeReason = "auth_required"; return persist();
}

bool DesktopUploadQueueService::markQuarantined(std::string_view id, std::string reason) {
    auto* item = find(id); if (!item || reason.empty() || !validSafeReason(reason)) return false;
    item->status = UploadQueueStatus::quarantined; item->safeReason = std::move(reason); return persist();
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
    return AtomicFileStore::writeWithinRoot(custodyRoot_, ledgerPath_, serialize(items_), 4 * 1024 * 1024).ok();
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
