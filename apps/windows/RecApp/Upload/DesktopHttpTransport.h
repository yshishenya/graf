#pragma once

#include "DesktopApiClient.h"
#include "DesktopUploadQueueService.h"
#include "../Storage/ProtectedCustodyCodec.h"
#ifdef _WIN32
#include "../Recording/LocalRecordingPackage.h"
#endif

#include <cstddef>
#include <atomic>
#include <chrono>
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

template<class String> struct BasicDesktopTransportResult {
    using StringType = String;
    DesktopTransportStatus status = DesktopTransportStatus::retryableFailure;
    std::optional<BasicUploadServerTruth<String>> serverTruth;
    String safeReason = {};
    // Server-owned retry classification from custody or an allowlisted HTTP 400
    // source rejection. Empty keeps the ordinary retry path.
    String retryClass = {};
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
    std::optional<std::int64_t> authExpiresAt = std::nullopt;
};
using DesktopTransportResult = BasicDesktopTransportResult<std::string>;
using ProtectedDesktopTransportResult = BasicDesktopTransportResult<CustodyString>;

template<class String> struct BasicDesktopRemoteUploadState {
    String meetingId;
    String sessionId;
    String sessionStatus;
    BasicUploadServerTruth<String> truth;
    bool blockedByConflict = false;
    bool needsNewUploadSession = false;
    // custody.retry_class, normalized. The server decides whether another
    // automatic attempt can succeed; retrying against its own classification
    // only burns the budget and hides the real reason from the owner.
    String retryClass;
};
using DesktopRemoteUploadState = BasicDesktopRemoteUploadState<std::string>;

template<class String> struct BasicDesktopHttpConfig {
    String baseOrigin = "https://rec.2brain.pro";
    String workspaceId;
    String deviceId;
    String clientVersion = "windows-feature-200";
    std::size_t partSizeBytes = 4 * 1024 * 1024;
    // Copied on the UI thread before dispatch; never persisted. No UI callbacks.
    String sessionToken = {};
    // Account the shell already confirmed with GET /api/v1/auth/me for exactly
    // this session token. Present means the transport does not ask the server
    // again for every attempt; the owner check still runs against it. A token
    // change clears the snapshot before any upload can start.
    std::optional<BasicDesktopAccountIdentity<String>> confirmedIdentity = {};
    // Actor a scoped mutation is requested for. The server compares these two
    // headers with the confirmed session before it changes anything, so an
    // invalid scope means no request is made at all.
    std::optional<BasicDeletionScope<String>> scopedAccount = {};
    std::shared_ptr<const std::atomic_bool> cancellation = {};
};
using ProtectedDesktopHttpConfig = BasicDesktopHttpConfig<CustodyString>;

// One deletion-protocol call. Kept apart from the upload result: a server that
// answered "no" is not a transport failure, and an unavailable server must not
// be read as permission to delete anything.
template<class String> struct BasicDesktopDeletionResponse {
    std::uint32_t status = 0;
    String body;
    bool transportFailed = false;
    std::uint32_t retryAfterSeconds = 0;
    // Server-owned session deadline from `X-GRAF-Auth-Expires-At`, when the
    // server renewed the session while answering this call.
    std::optional<std::int64_t> authExpiresAt;
    // Set only when the call was never sent: the scope or the target did not
    // describe something this client may name.
    String safeReason;
    [[nodiscard]] bool answered() const noexcept { return safeReason.empty() && !transportFailed && status != 0; }
    [[nodiscard]] bool accepted() const noexcept { return answered() && (status == 200 || status == 202); }
};
using DesktopDeletionResponse = BasicDesktopDeletionResponse<std::string>;
using ProtectedDeletionResponse = BasicDesktopDeletionResponse<CustodyString>;

enum class CalendarJoinResolutionState {
    resolved, authRequired, eventUnavailable, dependencyUnavailable, invalidTarget, cancelled,
};

// Data, not permission to launch. The consumer must still check current context
// and URL policy; neither this result nor 401 changes auth/UI state here.
struct CalendarJoinResolution {
    CalendarJoinResolutionState state = CalendarJoinResolutionState::dependencyUnavailable;
    std::optional<CalendarJoinTarget> target = {};
    std::optional<std::int64_t> authExpiresAt = {};
};

class DesktopHttpTransport final {
public:
    explicit DesktopHttpTransport(DesktopHttpConfig config = {});

    [[nodiscard]] DesktopTransportResult upload(const UploadCustodyItem& item) const;
    template<class String> struct BasicUploadRequest {
        String method;
        String path;
        String body;
        bool jsonBody = true;
        String idempotencyKey = {};
        std::optional<std::uint64_t> byteOffset = std::nullopt;
        String contentSha256 = {};
        std::shared_ptr<const CustodyBytes> protectedBody = {};
        [[nodiscard]] std::optional<std::string_view> bodyView() const noexcept {
            if (!protectedBody) return std::string_view(body);
            if (!body.empty()) return std::nullopt;
            if (protectedBody->empty()) return std::string_view{};
            return std::string_view(reinterpret_cast<const char*>(protectedBody->data()), protectedBody->size());
        }
    };
    using UploadRequest = BasicUploadRequest<std::string>;
    using ProtectedUploadRequest = BasicUploadRequest<CustodyString>;
    template<class String> struct BasicUploadResponse {
        using StringType = String;
        std::uint32_t status = 0;
        String body;
        bool transportFailed = false;
        String retryAfter = {};
        String authExpiresAt = {};
    };
    using UploadResponse = BasicUploadResponse<std::string>;
    using ProtectedUploadResponse = BasicUploadResponse<CustodyString>;
    using CalendarJoinGet = std::function<UploadResponse(const DesktopHttpConfig&,
        std::string_view, std::chrono::steady_clock::time_point)>;
    // Pass the ORIGINAL operation deadline, including time spent awaiting dispatch.
    [[nodiscard]] CalendarJoinResolution calendarJoinTarget(std::string_view eventId,
        std::chrono::steady_clock::time_point deadline) const;
    [[nodiscard]] CalendarJoinResolution calendarJoinTarget(std::string_view eventId,
        std::chrono::steady_clock::time_point deadline, const CalendarJoinGet& get) const;
    // Replace only the wire in portable tests; all upload/recovery decisions
    // still run through the production sequence. The app uses WinHTTP above.
    using UploadSend = std::function<UploadResponse(const DesktopHttpConfig&, const UploadRequest&)>;
    using ProtectedUploadSend = std::function<ProtectedUploadResponse(const ProtectedDesktopHttpConfig&, const ProtectedUploadRequest&)>;
    [[nodiscard]] DesktopTransportResult upload(const UploadCustodyItem& item, const UploadSend& send) const;
#ifdef _WIN32
    // Worker-only retained semantic proof, not queue/account authority. No
    // plaintext fallback; all wire decisions are shared with the ordinary path.
    // Allocate the result/control block and truth before any network effect;
    // return that same immutable owner, never a late value copy/move. Null means
    // preparation failed before the first request (including account lookup).
    // Config and queue snapshot are charged before background dispatch; the
    // operation retains both through completion. No ordinary copies here.
    [[nodiscard]] static std::shared_ptr<const ProtectedDesktopTransportResult> uploadProtected(
        const ProtectedDesktopHttpConfig& config, const ProtectedUploadQueueValue::Item& item,
        std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> proof,
        const ProtectedUploadSend& send = {});
#endif
    [[nodiscard]] std::optional<DesktopAccountIdentity> accountIdentity() const;
    struct IdentityResponse {
        std::uint32_t status = 0;
        std::string body;
        bool transportFailed = false;
    };
    template<class String> struct BasicIdentityResult {
        std::optional<BasicDesktopAccountIdentity<String>> identity;
        DesktopTransportStatus status = DesktopTransportStatus::authRequired;
    };
    using IdentityResult = BasicIdentityResult<std::string>;
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
    // One worker-owned selection step. Gate once per unchanged batch, exact
    // canonical target/body, preallocated charged result; no native UI owner.
    [[nodiscard]] static std::shared_ptr<const ProtectedDeletionResponse> deletionProtected(
        const ProtectedDesktopHttpConfig&, const BasicDeletionRequestPlan<CustodyString>&,
        bool readProtocolGate, const ProtectedUploadSend& send = {});
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
    // Worker-only charged variants. A batch may reuse its unchanged protocol
    // gate; the continuation still owns current epoch/adopted local proof.
    [[nodiscard]] static std::shared_ptr<const ProtectedDeletionResponse> localPurgeTasksProtected(
        const ProtectedDesktopHttpConfig&, bool readProtocolGate, const ProtectedUploadSend& send = {});
    [[nodiscard]] static std::shared_ptr<const ProtectedDeletionResponse> ensureLocalPurgeTaskProtected(
        const ProtectedDesktopHttpConfig&, std::string_view meetingId, bool readProtocolGate,
        const ProtectedUploadSend& send = {});
    [[nodiscard]] static std::shared_ptr<const ProtectedDeletionResponse> acknowledgeLocalPurgeTaskProtected(
        const ProtectedDesktopHttpConfig&, std::string_view taskId, LocalPurgeAckState,
        std::string_view reasonCode, std::string_view completedAtIso, bool readProtocolGate,
        const ProtectedUploadSend& send = {});
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
