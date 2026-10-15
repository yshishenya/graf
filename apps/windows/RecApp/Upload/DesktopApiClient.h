#pragma once

#include "../Contracts/WindowsDesktopContracts.h"
#include "../Storage/ProtectedCustodyCodec.h"

#include <array>
#include <atomic>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace graf::windows {

template<class String> struct BasicCreateMeetingRequest {
    String localRecordingId;
    String localMediaRevisionId;
    String sourceKind;
    String mediaScribeSourceMode;
    std::uint32_t durationSeconds = 0;
    // Built from the local wall clock at the start of the recording, the same
    // way the macOS client builds its generic title. Without it the server can
    // only show an unnamed meeting placed at the moment of upload.
    String title;
    String titleSource;
    // "YYYY-MM-DDTHH:MM:SSZ", the same wire form the macOS client sends with its
    // ISO-8601 date strategy. Empty means the package carried no usable bounds.
    String startedAtIso;
    String endedAtIso;
    int displayTimezoneOffsetMinutes = 0;
    [[nodiscard]] bool hasTimeline() const noexcept {
        return !startedAtIso.empty() && !endedAtIso.empty();
    }
};
using CreateMeetingRequest = BasicCreateMeetingRequest<std::string>;

template<class String> struct BasicUploadSessionRequest {
    std::array<std::string_view, 3> expectedTracks = kV5WireRoles;
    std::array<std::uint64_t, 3> expectedTrackSizes{};
    String manifestSha256;
};
using UploadSessionRequest = BasicUploadSessionRequest<std::string>;

// Server-declared support for deleting a recording. Nothing may be mutated
// before this is read: an older server ignores the expected-account headers, and
// a receipt that fails to decode would arrive after the change was made. The
// same gate macOS applies with `recording_deletion_protocol_version == 1`.
template<class String> struct BasicNotificationContext {
    String userId;
    String workspaceId;
    int protocolVersion = 0;
};
using NotificationContext = BasicNotificationContext<std::string>;

// Safe ephemeral calendar projection for the card and native menu, never diagnostics.
struct CalendarReminderEvent {
    std::string eventId;
    double startsAt = 0;
    double endsAt = 0;
    bool canSurface = false;
    bool titleAvailable = false;
    std::string title;
    bool meetingLinkPresent = false;
    std::string meetingUrl;
    bool allDay = false;
};

struct CalendarReminderSnapshot {
    std::string userId;
    std::string workspaceId;
    std::vector<CalendarReminderEvent> events;
    bool showUpcomingTime = true;
    bool showUpcomingTitle = true;
};

// Untrusted resolver data. URL policy/current-owner checks must still precede
// any OS handoff; providerFamily never selects the application to open.
struct CalendarJoinTarget {
    std::string eventId;
    std::string providerFamily;
    std::string httpsUrl;
};

// Data only: source/route/nonce/current-owner authority belongs to the host.
struct CalendarJoinIntent {
    std::string eventId;
    std::string requestId;
};

// Ephemeral presentation data from the cabinet, not account/route authority.
// The host must separately validate the current document and native account.
struct UserTimeMetadata {
    std::string userId;
    std::string workspaceId;
    std::string sessionId;
    std::string timeZone;
    std::string documentUrl;
};

template<class String> struct BasicDesktopHttpConfig;
using DesktopHttpConfig = BasicDesktopHttpConfig<std::string>;
struct CalendarReminderResponse {
    std::uint32_t status = 0;
    std::optional<CalendarReminderSnapshot> snapshot;
    std::optional<std::int64_t> authExpiresAt = std::nullopt;
    // Call only after validating the preceding context's owner/workspace.
    void inheritAuthExpiry(std::optional<std::int64_t> contextExpiry);
    [[nodiscard]] std::optional<std::int64_t> renewedSessionExpiry(std::int64_t now) const;
};

// The account a deletion is requested for. macOS sends this pair as
// `X-Graf-Expected-Actor`/`X-Graf-Expected-Workspace`, and the server compares it
// with the confirmed session before it changes anything.
template<class String> struct BasicDeletionScope {
    String userId;
    String workspaceId;
};
using DeletionScope = BasicDeletionScope<std::string>;

enum class DeletionTarget {
    ownOrigin,
    meeting,
};

enum class LifecycleState {
    allowed,
    deletionAccepted,
    canceledBeforeCreation,
    unavailable,
};

struct LifecycleEntry {
    DeletionTarget target = DeletionTarget::ownOrigin;
    std::string targetId;
    LifecycleState state = LifecycleState::unavailable;
    std::string meetingId;
};

// What the server accepted. `receiptType` says which shape arrived; an unknown
// shape is a failure, never a success.
template<class String> struct BasicDeletionReceipt {
    String receiptType;
    String requestId;
    String meetingId;
    String localRecordingId;
    String phase;
    [[nodiscard]] bool accepted() const noexcept { return phase == "accepted"; }
};
using DeletionReceipt = BasicDeletionReceipt<std::string>;

// A purge task the server asks this device to carry out: remove the local copies
// of a meeting it has already deleted, and answer with what could be proven.
// The task names a meeting; the queue names its rows, so the two are matched by
// the meeting identifier the server itself returned.
template<class String> struct BasicLocalPurgeTask {
    String taskId;
    String meetingId;
    // purge_local_buffers, purge_local_exports or confirm_local_expiry.
    String taskType;
    // pending, claimed, acknowledged, failed, unreachable, expired or
    // local_expiry_relied_upon.
    String state;
    String safeReason;
    // Kept exactly as the server sent it. The client does not schedule by it yet,
    // but a task without a usable instant is not a task it may act on.
    String expiresAt;
    [[nodiscard]] bool acknowledged() const noexcept { return state == "acknowledged"; }
};
using LocalPurgeTask = BasicLocalPurgeTask<std::string>;
template<class String> using BasicLocalPurgeTasks = std::conditional_t<std::is_same_v<String, std::string>,
    std::vector<BasicLocalPurgeTask<String>>, CustodyVector<BasicLocalPurgeTask<String>>>;

enum class LocalPurgeAckState {
    acknowledged,
    failed,
    localExpiryReliedUpon,
};

class DesktopApiClient final {
public:
    static constexpr std::string_view createMeetingPath = "/api/v1/meetings";
    static constexpr std::string_view createUploadSessionSuffix = "/upload-sessions";

    template<class String = std::string>
    [[nodiscard]] static std::optional<BasicCreateMeetingRequest<String>> createMeetingRequest(
        std::string_view localRecordingId,
        std::string_view localMediaRevisionId,
        std::uint32_t durationSeconds,
        std::uint64_t startedAtMs = 0,
        std::uint64_t stoppedAtMs = 0,
        int displayTimezoneOffsetMinutes = 0);

    // "YYYY-MM-DD HH:mm" in the display time zone of the recording, computed
    // from the epoch instant and the offset alone so the result cannot depend on
    // the machine locale of whoever replays it. Empty for an unusable instant.
    template<class String = std::string>
    [[nodiscard]] static String formatDisplayMinute(
        std::uint64_t epochMs,
        int displayTimezoneOffsetMinutes) noexcept(std::is_same_v<String, std::string>);

    // "YYYY-MM-DDTHH:MM:SSZ" for the same instant, always UTC.
    template<class String = std::string>
    [[nodiscard]] static String formatUtcInstant(std::uint64_t epochMs) noexcept(std::is_same_v<String, std::string>);

    // Exact request body for POST /api/v1/meetings. It lives here, next to the
    // request it serializes, so the wire contract can be asserted without a
    // network peer. Optional fields are omitted, never sent as null.
    template<class String>
    [[nodiscard]] static String createMeetingBody(const BasicCreateMeetingRequest<String>& request);

    template<class String = std::string>
    [[nodiscard]] static std::optional<BasicUploadSessionRequest<String>> uploadSessionRequest(
        const std::array<std::uint64_t, 3>& expectedTrackSizes,
        std::string_view manifestSha256);

    template<class String = std::string>
    [[nodiscard]] static String idempotencyKey(
        std::string_view scope,
        std::string_view directoryId,
        std::string_view sessionId);

    // Recording deletion, the same protocol the macOS client speaks. The exact
    // confirmation sentence is a server literal; inventing a variant would make
    // every request fail validation.
    static constexpr std::string_view deletionConfirmationBoundary =
        "Delete this meeting everywhere GRAF controls.";
    static constexpr std::string_view notificationContextPath = "/api/v1/desktop/notification-context";
    static constexpr std::string_view lifecyclePath = "/api/v1/desktop/recordings/lifecycle";
    static constexpr std::string_view ownOriginDeletionSuffix = "/deletion-requests";
    static constexpr std::string_view cabinetMeetingPrefix = "/api/v1/cabinet/meetings/";
    static constexpr std::string_view desktopMeetingPrefix = "/api/v1/desktop/meetings/";
    static constexpr std::string_view desktopRecordingPrefix = "/api/v1/desktop/recordings/";

    // Paths are built from one validated identifier each, so a value from the
    // cabinet can never add a path segment or query. Empty means the identifier
    // is not usable and no request may be made.
    template<class String = std::string> [[nodiscard]] static String ownOriginDeletionPath(std::string_view directoryId);
    template<class String = std::string> [[nodiscard]] static String meetingDeletionPath(std::string_view meetingId);

    template<class String = std::string>
    [[nodiscard]] static std::optional<BasicNotificationContext<String>> decodeNotificationContext(
        std::string_view json, const std::atomic<bool>* cancellation = nullptr);
    static constexpr std::string_view calendarUpcomingPath = "/api/v1/desktop/calendar/upcoming";
    [[nodiscard]] static std::optional<CalendarReminderSnapshot> decodeCalendarReminders(std::string_view json);
    // Exact, bounded ExecuteScript result. Named-zone support is validated by
    // the native formatter; this decoder grants no auth/Join authority.
    [[nodiscard]] static std::optional<UserTimeMetadata> decodeUserTimeMetadata(std::string_view json);
    [[nodiscard]] static std::string calendarJoinTargetPath(std::string_view eventId);
    [[nodiscard]] static std::optional<CalendarJoinTarget> decodeCalendarJoinTarget(
        std::string_view json, std::string_view expectedEventId);
    [[nodiscard]] static std::optional<CalendarJoinIntent> decodeCalendarJoinIntent(
        std::string_view payload, std::string_view command);
    // Validate original JSON before SDK Stringify can erase duplicate fields.
    // Owns the raw payload; does not validate bridge authority or dispatch work.
    [[nodiscard]] static std::optional<std::string> calendarJoinEnvelopePayload(
        std::string_view json, std::string_view command);
    // Bounded read-only request; no redirects, cookie jar, or upload effects.
    [[nodiscard]] static CalendarReminderResponse calendarReminders(const DesktopHttpConfig& config);
    [[nodiscard]] static std::optional<std::int64_t> calendarAuthExpiryFromHeader(std::string_view raw);
    // Strict: every listed entry must be a complete, known shape, or the whole
    // answer is rejected. A partial list would hide a target the user selected.
    [[nodiscard]] static std::optional<std::vector<LifecycleEntry>> decodeLifecycleEntries(std::string_view json);
    template<class String = std::string>
    [[nodiscard]] static std::optional<BasicDeletionReceipt<String>> decodeDeletionReceipt(
        std::string_view json, const std::atomic<bool>* cancellation = nullptr);
    template<class String = std::string> [[nodiscard]] static String originCancellationBody(std::string_view operationId);
    template<class String = std::string> [[nodiscard]] static String meetingDeletionBody();
    [[nodiscard]] static std::string lifecycleBody(const std::vector<std::string>& origins,
                                                  const std::vector<std::string>& meetingIds);
    // Bounded like the server's own limit, and never empty: the endpoint rejects
    // a selection outside 1..100 targets.
    [[nodiscard]] static bool validLifecycleSelection(
        const std::vector<std::string>& origins, const std::vector<std::string>& meetingIds,
        std::size_t maxEntries) noexcept;
    // Borrowed values: invalidated if scope is changed or destroyed.
    template<class String>
    [[nodiscard]] static std::optional<std::array<std::pair<std::string_view, std::string_view>, 2>> scopedAccountHeaders(
        const BasicDeletionScope<String>& scope);
    template<class String> static void scopedAccountHeaders(const BasicDeletionScope<String>&&) = delete;

    // Identity of one deletion request. The server treats `operation_id` as the
    // name of the request, so it is derived from the target and the account that
    // asks for it: the same request made again after a restart keeps its name and
    // cannot delete anything twice, and a different account gets a different one.
    // The result is a version-4 shaped UUID because that is what the endpoint
    // validates; the value itself is derived, never random.
    [[nodiscard]] static std::string deletionOperationId(const DeletionScope& scope, DeletionTarget target,
                                                        std::string_view targetId);

    // Purge tasks. The server creates one when it has accepted a meeting
    // deletion, and asks this device to remove the local copies and answer with
    // what could actually be proven.
    static constexpr std::string_view purgeTasksPath = "/api/v1/desktop/local-purge-tasks";
    static constexpr std::string_view purgeTaskSuffix = "/local-purge-task";
    static constexpr std::string_view purgeAckSuffix = "/ack";
    static constexpr std::size_t purgeReasonCodeLimit = 120;
    // The server bounds its own answer; a longer list is not one this client acts on.
    static constexpr std::size_t purgeTaskListLimit = 200;

    // Only the canonical path is ever used. The server also sends `ack_url`, and
    // its path is ignored: a client that follows a server-provided address with
    // its session attached would let the answer decide where that session goes.
    template<class String = std::string> [[nodiscard]] static String localPurgeTaskPath(std::string_view meetingId);
    template<class String = std::string> [[nodiscard]] static String localPurgeAckPath(std::string_view taskId);
    template<class String = std::string> [[nodiscard]] static std::optional<BasicLocalPurgeTask<String>> decodeLocalPurgeTask(
        std::string_view json, const std::atomic<bool>* cancellation = nullptr);
    template<class String = std::string> [[nodiscard]] static std::optional<BasicLocalPurgeTasks<String>> decodeLocalPurgeTaskList(
        std::string_view json, const std::atomic<bool>* cancellation = nullptr);
    [[nodiscard]] static std::string_view localPurgeAckStateName(LocalPurgeAckState state) noexcept;
    [[nodiscard]] static bool validAckReasonCode(std::string_view reasonCode) noexcept;
    // Exact ack body. Optional fields are omitted, never sent as null, the same
    // way the macOS client encodes them.
    template<class String = std::string> [[nodiscard]] static String localPurgeAckBody(LocalPurgeAckState state,
        std::string_view reasonCode, std::string_view clientVersion, std::string_view completedAtIso);

    [[nodiscard]] static bool accountId(std::string_view value) noexcept;
    // Bounded, fully validated root object. Views borrow json; values retain
    // their JSON quotes/type. Duplicate or escaped keys fail closed at any depth.
    [[nodiscard]] static std::optional<std::map<std::string_view, std::string_view>> jsonObjectFields(
        std::string_view json);
    [[nodiscard]] static std::optional<std::vector<std::string_view>> jsonArrayValues(std::string_view json);

private:
    [[nodiscard]] static bool safeIdentity(std::string_view value) noexcept;
    [[nodiscard]] static bool sha256(std::string_view value) noexcept;
};

} // namespace graf::windows
