#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <array>
#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace graf::windows {

struct CreateMeetingRequest {
    std::string localRecordingId;
    std::string localMediaRevisionId;
    std::string sourceKind;
    std::string mediaScribeSourceMode;
    std::uint32_t durationSeconds = 0;
    // Built from the local wall clock at the start of the recording, the same
    // way the macOS client builds its generic title. Without it the server can
    // only show an unnamed meeting placed at the moment of upload.
    std::string title;
    std::string titleSource;
    // "YYYY-MM-DDTHH:MM:SSZ", the same wire form the macOS client sends with its
    // ISO-8601 date strategy. Empty means the package carried no usable bounds.
    std::string startedAtIso;
    std::string endedAtIso;
    int displayTimezoneOffsetMinutes = 0;
    [[nodiscard]] bool hasTimeline() const noexcept {
        return !startedAtIso.empty() && !endedAtIso.empty();
    }
};

struct UploadSessionRequest {
    std::array<std::string_view, 3> expectedTracks = kV5WireRoles;
    std::array<std::uint64_t, 3> expectedTrackSizes{};
    std::string manifestSha256;
};

// Server-declared support for deleting a recording. Nothing may be mutated
// before this is read: an older server ignores the expected-account headers, and
// a receipt that fails to decode would arrive after the change was made. The
// same gate macOS applies with `recording_deletion_protocol_version == 1`.
struct NotificationContext {
    std::string userId;
    std::string workspaceId;
    int protocolVersion = 0;
};

// The account a deletion is requested for. macOS sends this pair as
// `X-Graf-Expected-Actor`/`X-Graf-Expected-Workspace`, and the server compares it
// with the confirmed session before it changes anything.
struct DeletionScope {
    std::string userId;
    std::string workspaceId;
};

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
struct DeletionReceipt {
    std::string receiptType;
    std::string requestId;
    std::string meetingId;
    std::string localRecordingId;
    std::string phase;
    [[nodiscard]] bool accepted() const noexcept { return phase == "accepted"; }
};

// A purge task the server asks this device to carry out: remove the local copies
// of a meeting it has already deleted, and answer with what could be proven.
// The task names a meeting; the queue names its rows, so the two are matched by
// the meeting identifier the server itself returned.
struct LocalPurgeTask {
    std::string taskId;
    std::string meetingId;
    // purge_local_buffers, purge_local_exports or confirm_local_expiry.
    std::string taskType;
    // pending, claimed, acknowledged, failed, unreachable, expired or
    // local_expiry_relied_upon.
    std::string state;
    std::string safeReason;
    // Kept exactly as the server sent it. The client does not schedule by it yet,
    // but a task without a usable instant is not a task it may act on.
    std::string expiresAt;
    [[nodiscard]] bool acknowledged() const noexcept { return state == "acknowledged"; }
};

enum class LocalPurgeAckState {
    acknowledged,
    failed,
    localExpiryReliedUpon,
};

class DesktopApiClient final {
public:
    static constexpr std::string_view createMeetingPath = "/api/v1/meetings";
    static constexpr std::string_view createUploadSessionSuffix = "/upload-sessions";

    [[nodiscard]] static std::optional<CreateMeetingRequest> createMeetingRequest(
        std::string_view localRecordingId,
        std::string_view localMediaRevisionId,
        std::uint32_t durationSeconds,
        std::uint64_t startedAtMs = 0,
        std::uint64_t stoppedAtMs = 0,
        int displayTimezoneOffsetMinutes = 0);

    // "YYYY-MM-DD HH:mm" in the display time zone of the recording, computed
    // from the epoch instant and the offset alone so the result cannot depend on
    // the machine locale of whoever replays it. Empty for an unusable instant.
    [[nodiscard]] static std::string formatDisplayMinute(
        std::uint64_t epochMs,
        int displayTimezoneOffsetMinutes) noexcept;

    // "YYYY-MM-DDTHH:MM:SSZ" for the same instant, always UTC.
    [[nodiscard]] static std::string formatUtcInstant(std::uint64_t epochMs) noexcept;

    // Exact request body for POST /api/v1/meetings. It lives here, next to the
    // request it serializes, so the wire contract can be asserted without a
    // network peer. Optional fields are omitted, never sent as null.
    [[nodiscard]] static std::string createMeetingBody(const CreateMeetingRequest& request);

    [[nodiscard]] static std::optional<UploadSessionRequest> uploadSessionRequest(
        const std::array<std::uint64_t, 3>& expectedTrackSizes,
        std::string_view manifestSha256);

    [[nodiscard]] static std::string idempotencyKey(
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
    [[nodiscard]] static std::string ownOriginDeletionPath(std::string_view directoryId);
    [[nodiscard]] static std::string meetingDeletionPath(std::string_view meetingId);

    [[nodiscard]] static std::optional<NotificationContext> decodeNotificationContext(std::string_view json);
    // Strict: every listed entry must be a complete, known shape, or the whole
    // answer is rejected. A partial list would hide a target the user selected.
    [[nodiscard]] static std::optional<std::vector<LifecycleEntry>> decodeLifecycleEntries(std::string_view json);
    [[nodiscard]] static std::optional<DeletionReceipt> decodeDeletionReceipt(std::string_view json);
    [[nodiscard]] static std::string originCancellationBody(std::string_view operationId);
    [[nodiscard]] static std::string meetingDeletionBody();
    [[nodiscard]] static std::string lifecycleBody(const std::vector<std::string>& origins,
                                                  const std::vector<std::string>& meetingIds);
    // Bounded like the server's own limit, and never empty: the endpoint rejects
    // a selection outside 1..100 targets.
    [[nodiscard]] static bool validLifecycleSelection(
        const std::vector<std::string>& origins, const std::vector<std::string>& meetingIds,
        std::size_t maxEntries) noexcept;
    [[nodiscard]] static std::vector<std::pair<std::string, std::string>> scopedAccountHeaders(
        const DeletionScope& scope);

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
    [[nodiscard]] static std::string localPurgeTaskPath(std::string_view meetingId);
    [[nodiscard]] static std::string localPurgeAckPath(std::string_view taskId);
    [[nodiscard]] static std::optional<LocalPurgeTask> decodeLocalPurgeTask(std::string_view json);
    [[nodiscard]] static std::optional<std::vector<LocalPurgeTask>> decodeLocalPurgeTaskList(std::string_view json);
    [[nodiscard]] static std::string_view localPurgeAckStateName(LocalPurgeAckState state) noexcept;
    [[nodiscard]] static bool validAckReasonCode(std::string_view reasonCode) noexcept;
    // Exact ack body. Optional fields are omitted, never sent as null, the same
    // way the macOS client encodes them.
    [[nodiscard]] static std::string localPurgeAckBody(LocalPurgeAckState state, std::string_view reasonCode,
                                                      std::string_view clientVersion,
                                                      std::string_view completedAtIso);

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
