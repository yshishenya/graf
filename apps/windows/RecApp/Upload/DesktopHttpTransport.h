#pragma once

#include "DesktopApiClient.h"
#include "DesktopUploadQueueService.h"

#include <cstddef>
#include <atomic>
#include <cstdint>
#include <functional>
#include <optional>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

namespace graf::windows {

enum class DesktopTransportStatus {
    uploaded,
    authRequired,
    retryableFailure,
    serverRejected,
    invalidPackage,
    unsupportedPlatform,
};

struct DesktopTransportResult {
    DesktopTransportStatus status = DesktopTransportStatus::retryableFailure;
    std::optional<UploadServerTruth> serverTruth;
    std::string safeReason = {};
    // Server-owned retry classification from the custody projection. Empty means
    // the server expressed no opinion, and the ordinary retry path applies.
    std::string retryClass = {};
    // Server-requested pause, in seconds, from a Retry-After header on a 429.
    // Zero means the server asked for nothing and the ordinary schedule applies.
    // A pause is not a failed attempt: the server is asking the client to wait,
    // not reporting that the work cannot be done.
    std::uint32_t retryAfterSeconds = 0;
    // Server-owned session deadline, in seconds since the epoch, from
    // `X-GRAF-Auth-Expires-At` on an answered authenticated request. The server
    // renewed its session while answering, and the cabinet's own cookie has to
    // learn that deadline or the cabinet signs out while the app's calls still
    // work. Empty means the server named no deadline.
    std::optional<std::int64_t> authExpiresAt;
};

struct DesktopRemoteUploadState {
    std::string meetingId;
    std::string sessionId;
    std::string sessionStatus;
    UploadServerTruth truth;
    bool blockedByConflict = false;
    bool needsNewUploadSession = false;
    // custody.retry_class, normalized. The server decides whether another
    // automatic attempt can succeed; retrying against its own classification
    // only burns the budget and hides the real reason from the owner.
    std::string retryClass;
};

struct DesktopHttpConfig {
    std::string baseOrigin = "https://rec.2brain.pro";
    std::string workspaceId;
    std::string deviceId;
    std::string clientVersion = "windows-feature-200";
    std::size_t partSizeBytes = 4 * 1024 * 1024;
    // Copied on the UI thread before dispatch; never persisted. No UI callbacks.
    std::string sessionToken = {};
    // Account the shell already confirmed with GET /api/v1/auth/me for exactly
    // this session token. Present means the transport does not ask the server
    // again for every attempt; the owner check still runs against it. A token
    // change clears the snapshot before any upload can start.
    std::optional<DesktopAccountIdentity> confirmedIdentity = {};
    // Actor a scoped mutation is requested for. The server compares these two
    // headers with the confirmed session before it changes anything, so an
    // invalid scope means no request is made at all.
    std::optional<DeletionScope> scopedAccount = {};
    std::shared_ptr<const std::atomic_bool> cancellation = {};
};

// One deletion-protocol call. Kept apart from the upload result: a server that
// answered "no" is not a transport failure, and an unavailable server must not
// be read as permission to delete anything.
struct DesktopDeletionResponse {
    std::uint32_t status = 0;
    std::string body;
    bool transportFailed = false;
    std::uint32_t retryAfterSeconds = 0;
    // Server-owned session deadline from `X-GRAF-Auth-Expires-At`, when the
    // server renewed the session while answering this call.
    std::optional<std::int64_t> authExpiresAt;
    // Set only when the call was never sent: the scope or the target did not
    // describe something this client may name.
    std::string safeReason;
    [[nodiscard]] bool answered() const noexcept { return !transportFailed && status != 0; }
    [[nodiscard]] bool accepted() const noexcept { return !transportFailed && (status == 200 || status == 202); }
};

class DesktopHttpTransport final {
public:
    explicit DesktopHttpTransport(DesktopHttpConfig config = {});

    [[nodiscard]] DesktopTransportResult upload(const UploadCustodyItem& item) const;
    [[nodiscard]] std::optional<DesktopAccountIdentity> accountIdentity() const;
    struct IdentityResponse {
        std::uint32_t status = 0;
        std::string body;
        bool transportFailed = false;
    };
    struct IdentityResult {
        std::optional<DesktopAccountIdentity> identity;
        DesktopTransportStatus status = DesktopTransportStatus::authRequired;
    };
    // Read-only, bounded, no-redirect WinHTTP GET; retain HTTP/transport failure
    // separately so an unavailable server does not require a new login.
    using IdentityGet = std::function<IdentityResponse(const DesktopHttpConfig&, std::string_view)>;
    [[nodiscard]] IdentityResult accountIdentity(const IdentityGet& get) const;
    // The identity that authorises an upload. A snapshot the shell confirmed for
    // this exact session token is used as it is, so a flight does not repeat the
    // question the server already answered; without one the client asks the
    // server, which is what the contract requires of the first confirmation.
    [[nodiscard]] static IdentityResult resolveAccountIdentity(
        const DesktopHttpConfig& config, const IdentityGet& get);
    [[nodiscard]] static std::optional<std::string> decodeActiveWorkspace(std::string_view json);
    [[nodiscard]] static std::optional<DesktopAccountIdentity> decodeAccountIdentity(std::string_view json);
    [[nodiscard]] static std::string_view ownerBlockReason(
        const UploadCustodyItem& item, const std::optional<DesktopAccountIdentity>& identity);
    // The production sync-state decoder is portable so recovery decisions can
    // be tested without WinHTTP or a live recording/account.
    [[nodiscard]] static std::optional<DesktopRemoteUploadState> decodeSyncState(
        std::string_view json, std::string_view localRecordingId);
    // How long the server asked the client to wait, in seconds, for a response it
    // answered with 429. macOS honours the same header and falls back to 60 s, so
    // an unreadable value never turns into "retry immediately". Any other status
    // returns zero: an unavailable endpoint keeps the client's own schedule.
    [[nodiscard]] static std::uint32_t rateLimitPauseSeconds(
        std::uint32_t status, std::string_view retryAfter);
    // Seconds since the epoch from `X-GRAF-Auth-Expires-At`, or nothing when the
    // value is not exactly a run of ASCII digits. macOS applies the same rule, so
    // a decorated, negative or empty value is not a deadline on either platform.
    [[nodiscard]] static std::optional<std::int64_t> epochSecondsFromHeader(std::string_view raw);
    [[nodiscard]] static std::string replacementUploadSessionKey(
        const UploadCustodyItem& item, std::string_view expiredSessionId);

    // Recording deletion, the protocol the cabinet bridge drives. The gate comes
    // first: a client that mutates before reading it cannot tell an older server
    // that ignores the expected-account headers from one that honours them, and
    // a receipt that fails to decode would arrive after the recording was gone.
    [[nodiscard]] DesktopDeletionResponse notificationContext(const DeletionScope& scope) const;
    [[nodiscard]] DesktopDeletionResponse requestDeletion(std::string_view path, std::string body,
                                                          const DeletionScope& scope) const;
    [[nodiscard]] DesktopDeletionResponse recordingLifecycle(const std::vector<std::string>& origins,
                                                            const std::vector<std::string>& meetingIds,
                                                            const DeletionScope& scope) const;
    // Purge tasks: the server asks this device to remove the local copies of a
    // meeting it has deleted. The answer carries what could actually be proven,
    // never that a request was merely sent.
    [[nodiscard]] DesktopDeletionResponse ensureLocalPurgeTask(std::string_view meetingId,
                                                              const DeletionScope& scope) const;
    [[nodiscard]] DesktopDeletionResponse localPurgeTasks(const DeletionScope& scope) const;
    [[nodiscard]] DesktopDeletionResponse acknowledgeLocalPurgeTask(std::string_view taskId,
                                                                    LocalPurgeAckState state,
                                                                    std::string_view reasonCode,
                                                                    std::string_view completedAtIso,
                                                                    const DeletionScope& scope) const;
    // Same bound the server enforces (1..100 targets, extra fields forbidden).
    static constexpr std::size_t kLifecycleSelectionLimit = 100;

private:
    DesktopHttpConfig config_;
};

} // namespace graf::windows
