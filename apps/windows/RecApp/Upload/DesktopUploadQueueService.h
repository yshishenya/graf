#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <array>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <vector>

namespace graf::windows {

enum class UploadQueueStatus {
    pending,
    uploading,
    needsAuth,
    retry,
    uploaded,
    quarantined,
};

struct UploadCustodyItem {
    std::string localRecordingId;
    std::string directoryId;
    std::string sessionId;
    std::filesystem::path packageDirectory;
    UploadQueueStatus status = UploadQueueStatus::pending;
    std::array<std::uint64_t, 3> acceptedBytes{};
    std::uint32_t attempts = 0;
    std::string safeReason;
};

struct UploadServerTruth {
    std::string localRecordingId;
    bool meetingExists = false;
    bool uploadSessionExists = false;
    std::array<std::uint64_t, 3> acceptedBytes{};
    bool finalized = false;
};

class DesktopUploadQueueService final {
public:
    explicit DesktopUploadQueueService(std::filesystem::path ledgerPath);

    [[nodiscard]] bool load();
    [[nodiscard]] bool enqueue(UploadCustodyItem item);
    [[nodiscard]] bool reconcile(const UploadServerTruth& truth);
    [[nodiscard]] bool markRetry(std::string_view localRecordingId, std::string reason);
    [[nodiscard]] bool markNeedsAuth(std::string_view localRecordingId);
    [[nodiscard]] bool markUploaded(std::string_view localRecordingId);
    [[nodiscard]] std::optional<UploadCustodyItem> nextPending() const;
    [[nodiscard]] const std::vector<UploadCustodyItem>& items() const noexcept { return items_; }
    [[nodiscard]] bool quarantined() const noexcept { return quarantined_; }

private:
    [[nodiscard]] bool persist() const;
    [[nodiscard]] static std::string serialize(const std::vector<UploadCustodyItem>& items);
    [[nodiscard]] static bool validIdentity(std::string_view value) noexcept;
    [[nodiscard]] UploadCustodyItem* find(std::string_view localRecordingId) noexcept;

    std::filesystem::path ledgerPath_;
    std::vector<UploadCustodyItem> items_;
    bool quarantined_ = false;
};

} // namespace graf::windows
