#pragma once

#include "../Contracts/WindowsDesktopContracts.h"
#include "DesktopLocalPurgeService.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <functional>
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

struct DesktopAccountIdentity {
    std::string userId;
    std::string workspaceId;
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
    std::string ownerUserId = {};
    std::string ownerWorkspaceId = {};
};

struct UploadServerTruth {
    std::string localRecordingId;
    bool meetingExists = false;
    bool uploadSessionExists = false;
    std::array<std::uint64_t, 3> acceptedBytes{};
    bool finalized = false;
};

enum class LocalCopyRemovalResult {
    removed,
    confirmationRequired,
    unknownRecording,
    unsafePath,
    recycleFailed,
    ledgerFailure,
};

class DesktopUploadQueueService final {
public:
    explicit DesktopUploadQueueService(
        std::filesystem::path ledgerPath,
        std::filesystem::path custodyRoot = {});

    [[nodiscard]] bool load();
    [[nodiscard]] bool enqueue(UploadCustodyItem item);
    [[nodiscard]] bool reconcile(const UploadServerTruth& truth);
    [[nodiscard]] bool markRetry(std::string_view localRecordingId, std::string reason);
    // UI owner only, with no upload in flight and after current-account checks.
    // Explicit retry rearms only this owned row; accepted bytes/identity stay put.
    [[nodiscard]] bool requestRetry(std::string_view localRecordingId);
    [[nodiscard]] bool markNeedsAuth(std::string_view localRecordingId, std::string reason = "auth_required");
    // UI thread, only after explicit native confirmation against the current
    // account generation. A known owner can never be reassigned, even to itself.
    [[nodiscard]] bool assignOwner(std::string_view localRecordingId, const DesktopAccountIdentity& identity);
    [[nodiscard]] bool requeueNeedsAuth();
    [[nodiscard]] bool markQuarantined(std::string_view localRecordingId, std::string reason);
    [[nodiscard]] bool markUploaded(std::string_view localRecordingId);
    // UI thread, after scheduler cancellation/drain (busy == false) and native
    // confirmation. The callback must recycle, not permanently delete; it must
    // not mutate this queue. No server operation or purge ACK is performed.
    [[nodiscard]] LocalCopyRemovalResult removeLocalCopy(
        std::string_view localRecordingId, LocalPurgeProof proof,
        const std::function<bool(const std::filesystem::path&)>& recycle);
    [[nodiscard]] std::optional<UploadCustodyItem> nextPending() const;
    [[nodiscard]] std::vector<UploadCustodyItem> pendingItems(std::size_t limit) const;
    [[nodiscard]] const std::vector<UploadCustodyItem>& items() const noexcept { return items_; }
    [[nodiscard]] bool quarantined() const noexcept { return quarantined_; }
    [[nodiscard]] const std::filesystem::path& ledgerPath() const noexcept { return ledgerPath_; }

private:
    [[nodiscard]] bool persist();
    [[nodiscard]] static std::string serialize(const std::vector<UploadCustodyItem>& items);
    [[nodiscard]] static bool validIdentity(std::string_view value) noexcept;
    [[nodiscard]] static bool validSafeReason(std::string_view value) noexcept;
    [[nodiscard]] UploadCustodyItem* find(std::string_view localRecordingId) noexcept;

    std::filesystem::path ledgerPath_;
    std::filesystem::path custodyRoot_;
    std::vector<UploadCustodyItem> items_;
    bool quarantined_ = false;
};

} // namespace graf::windows
