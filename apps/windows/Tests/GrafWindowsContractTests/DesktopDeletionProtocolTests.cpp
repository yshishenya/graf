// Recording deletion, the protocol the cabinet bridge drives. Every case here is
// taken from the server contract: the confirmation sentence is one exact literal,
// the gate response carries the protocol version, and a receipt is only a
// confirmation when its type, phase and identity all check out.

#include "../../RecApp/Upload/DesktopHttpTransport.h"
#include "../../RecApp/Web/RecordingDeletionBridge.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <string>
#include <vector>

namespace {

using namespace graf::windows;

constexpr std::string_view kActor = "11111111-1111-4111-8111-111111111111";
constexpr std::string_view kWorkspace = "22222222-2222-4222-8222-222222222222";
constexpr std::string_view kMeeting = "33333333-3333-4333-8333-333333333333";
constexpr std::string_view kRequest = "44444444-4444-4444-8444-444444444444";

const DeletionScope scope{std::string(kActor), std::string(kWorkspace)};

std::string replaceOnce(std::string text, std::string_view before, std::string_view after) {
    const auto at = text.find(before);
    assert(at != std::string::npos);
    text.replace(at, before.size(), after);
    return text;
}

void testNotificationContext() {
    // The exact answer of GET /api/v1/desktop/notification-context.
    const auto gate = std::string("{\"user_id\":\"") + std::string(kActor) + "\",\"workspace_id\":\"" +
        std::string(kWorkspace) + "\",\"recording_deletion_protocol_version\":1}";
    const auto context = DesktopApiClient::decodeNotificationContext(gate);
    assert(context && context->userId == kActor && context->workspaceId == kWorkspace);
    // Version 1 is the protocol this client speaks; anything else has to be read
    // as "update the app" instead of "retry until it works".
    assert(context->protocolVersion == 1 && context->protocolVersion != 0);
    assert(DesktopApiClient::decodeNotificationContext(" \n\t" + gate + " \r\n"));
    // Unknown root fields are other server state, not authority: they are ignored.
    assert(DesktopApiClient::decodeNotificationContext(
        replaceOnce(gate, "\"recording_deletion_protocol_version\":1",
                    "\"recording_deletion_protocol_version\":1,\"retention_days\":30,\"policy\":{\"a\":[1,2]}")));
    const auto older = DesktopApiClient::decodeNotificationContext(
        replaceOnce(gate, "\"recording_deletion_protocol_version\":1", "\"recording_deletion_protocol_version\":0"));
    assert(older && older->protocolVersion != 1);
    for (const auto& invalid : {
        std::string("{}"),
        std::string("[]"),
        gate + " trailing",
        gate.substr(0, gate.size() - 1),
        replaceOnce(gate, "\"recording_deletion_protocol_version\":1", "\"recording_deletion_protocol_version\":\"1\""),
        replaceOnce(gate, "\"recording_deletion_protocol_version\":1", "\"recording_deletion_protocol_version\":-1"),
        replaceOnce(gate, "\"recording_deletion_protocol_version\":1", "\"recording_deletion_protocol_version\":1.0"),
        replaceOnce(gate, "\"recording_deletion_protocol_version\":1", "\"recording_deletion_protocol_version\":01"),
        replaceOnce(gate, std::string(kActor), "not-a-uuid"),
        replaceOnce(gate, std::string(kWorkspace), "00000000-0000-0000-0000-000000000000"),
        replaceOnce(gate, std::string(kActor), "11111111-1111-4111-8111-11111111111A"),
        replaceOnce(gate, "\"workspace_id\"", "\"workspace\""),
    }) {
        assert(!DesktopApiClient::decodeNotificationContext(invalid));
    }
}

void testDeletionPaths() {
    // One validated identifier per path, so nothing from the cabinet can add a
    // segment or a query to the target.
    assert(DesktopApiClient::ownOriginDeletionPath("directory-1--initial") ==
           "/api/v1/desktop/recordings/directory-1--initial/deletion-requests");
    assert(DesktopApiClient::meetingDeletionPath(kMeeting) ==
           "/api/v1/cabinet/meetings/" + std::string(kMeeting) + "/deletion-requests");
    for (const auto& invalid : {std::string(""), std::string("a/b"), std::string("a?b"), std::string("a b"),
                                std::string("a#b"), std::string("../../etc")}) {
        assert(DesktopApiClient::ownOriginDeletionPath(invalid).empty());
        assert(DesktopApiClient::meetingDeletionPath(invalid).empty());
    }
    // A meeting is a UUID on the wire; anything shorter never identifies one.
    assert(DesktopApiClient::meetingDeletionPath("not-a-uuid").empty());
    assert(DesktopApiClient::meetingDeletionPath("33333333-3333-4333-8333-33333333333").empty());
    assert(DesktopApiClient::meetingDeletionPath("33333333-3333-4333-8333-3333333333333").empty());
    assert(DesktopApiClient::meetingDeletionPath("33333333-3333-4333-8333-33333333333Z").empty());
    assert(!DesktopApiClient::meetingDeletionPath("55555555-5555-4555-8555-555555555555").empty());
}

void testRequestBodies() {
    // Both bodies are server literals: extra="forbid" and a Literal confirmation
    // sentence mean a variant spelling is a refused request, not a warning.
    assert(DesktopApiClient::originCancellationBody(kRequest) ==
           "{\"operation_id\":\"" + std::string(kRequest) +
           "\",\"confirmation_boundary\":\"Delete this meeting everywhere GRAF controls.\"}");
    assert(DesktopApiClient::meetingDeletionBody() ==
           "{\"confirmation_boundary\":\"Delete this meeting everywhere GRAF controls.\"}");
    assert(DesktopApiClient::originCancellationBody("").empty());
    assert(DesktopApiClient::originCancellationBody("not-a-uuid").empty());
    assert(DesktopApiClient::lifecycleBody({"directory-1", "directory-2"}, {std::string(kMeeting)}) ==
           "{\"origins\":[\"directory-1\",\"directory-2\"],\"meeting_ids\":[\"" + std::string(kMeeting) + "\"]}");
    assert(DesktopApiClient::lifecycleBody({}, {}) == "{\"origins\":[],\"meeting_ids\":[]}");
    // The endpoint accepts between one and a hundred targets and refuses the rest.
    assert(DesktopApiClient::validLifecycleSelection({"directory-1"}, {}, 100));
    assert(DesktopApiClient::validLifecycleSelection({}, {std::string(kMeeting)}, 100));
    assert(!DesktopApiClient::validLifecycleSelection({}, {}, 100));
    assert(!DesktopApiClient::validLifecycleSelection({"a/b"}, {}, 100));
    assert(!DesktopApiClient::validLifecycleSelection({}, {"not-a-uuid"}, 100));
    assert(DesktopApiClient::validLifecycleSelection(std::vector<std::string>(100, "directory"), {}, 100));
    assert(!DesktopApiClient::validLifecycleSelection(std::vector<std::string>(101, "directory"), {}, 100));
}

void testLifecycleDecoding() {
    const auto entries = std::string("[") +
        "{\"target_type\":\"own_origin\",\"target_id\":\"directory-1\",\"state\":\"allowed\",\"meeting_id\":null,\"receipt\":null}," +
        "{\"target_type\":\"meeting\",\"target_id\":\"" + std::string(kMeeting) +
        "\",\"state\":\"deletion_accepted\",\"meeting_id\":\"" + std::string(kMeeting) +
        "\",\"receipt\":{\"receipt_type\":\"meeting_deletion\",\"phase\":\"accepted\",\"request_id\":\"" +
        std::string(kRequest) + "\",\"meeting_id\":\"" + std::string(kMeeting) +
        "\",\"deletion_epoch\":3,\"report_url\":\"/report\",\"lifecycle\":{\"state\":\"deleting\",\"label\":\"Удаление\",\"can_retry\":false,\"can_view_report\":true}}}," +
        "{\"target_type\":\"own_origin\",\"target_id\":\"directory-2\",\"state\":\"canceled_before_creation\"}," +
        "{\"target_type\":\"own_origin\",\"target_id\":\"directory-3\",\"state\":\"unavailable\"}]";
    const auto decoded = DesktopApiClient::decodeLifecycleEntries(entries);
    assert(decoded && decoded->size() == 4);
    assert((*decoded)[0].target == DeletionTarget::ownOrigin && (*decoded)[0].state == LifecycleState::allowed);
    assert((*decoded)[0].meetingId.empty());
    assert((*decoded)[1].target == DeletionTarget::meeting && (*decoded)[1].state == LifecycleState::deletionAccepted);
    assert((*decoded)[1].targetId == kMeeting && (*decoded)[1].meetingId == kMeeting);
    assert((*decoded)[2].state == LifecycleState::canceledBeforeCreation);
    assert((*decoded)[3].state == LifecycleState::unavailable);
    assert(DesktopApiClient::decodeLifecycleEntries("[]")->empty());
    // One unusable entry rejects the whole answer: a partial list would hide a
    // target the user selected and asked about.
    const auto unusable = [&](std::string_view entry) {
        assert(!DesktopApiClient::decodeLifecycleEntries("[" + std::string(entry) + "]"));
    };
    unusable("{\"target_type\":\"own_origin\",\"target_id\":\"directory-1\",\"state\":\"purged\"}");
    unusable("{\"target_type\":\"own_origin\",\"target_id\":\"directory-1\",\"state\":\"\"}");
    unusable("{\"target_type\":\"backup\",\"target_id\":\"directory-1\",\"state\":\"allowed\"}");
    unusable("{\"target_type\":\"own_origin\",\"target_id\":\"a/b\",\"state\":\"allowed\"}");
    unusable("{\"target_type\":\"meeting\",\"target_id\":\"not-a-uuid\",\"state\":\"allowed\"}");
    unusable("{\"target_type\":\"own_origin\",\"target_id\":\"\",\"state\":\"allowed\"}");
    unusable("{\"target_type\":\"own_origin\",\"state\":\"allowed\"}");
    unusable("{\"target_type\":\"own_origin\",\"target_id\":\"directory-1\"}");
    unusable("{\"target_type\":\"own_origin\",\"target_id\":\"directory-1\",\"state\":\"allowed\",\"meeting_id\":\"nope\"}");
    unusable("{\"target_type\":\"own_origin\",\"target_id\":\"directory-1\",\"state\":\"allowed\",\"meeting_id\":\"\"}");
    // A list longer than the server can return is not an answer this client acts on.
    std::string oversized = "[";
    for (int index = 0; index < 101; ++index) {
        if (index != 0) oversized += ',';
        oversized += "{\"target_type\":\"own_origin\",\"target_id\":\"directory-" + std::to_string(index) +
            "\",\"state\":\"allowed\"}";
    }
    assert(!DesktopApiClient::decodeLifecycleEntries(oversized + "]"));
    assert(!DesktopApiClient::decodeLifecycleEntries("{\"targets\":[]}"));
    assert(!DesktopApiClient::decodeLifecycleEntries(entries.substr(0, entries.size() - 1)));
}

void testDeletionReceipts() {
    const auto meeting = std::string("{\"receipt_type\":\"meeting_deletion\",\"phase\":\"accepted\",\"deletion_epoch\":0,") +
        "\"local_recording_id\":\"directory-1\",\"request_id\":\"" + std::string(kRequest) + "\",\"meeting_id\":\"" +
        std::string(kMeeting) + "\",\"report_url\":\"/api/v1/cabinet/meetings/" + std::string(kMeeting) +
        "/deletion-report\",\"lifecycle\":{\"state\":\"requested\",\"label\":\"Удаление\",\"can_retry\":false,\"can_view_report\":false}}";
    const auto receipt = DesktopApiClient::decodeDeletionReceipt(meeting);
    assert(receipt && receipt->accepted() && receipt->receiptType == "meeting_deletion");
    assert(receipt->requestId == kRequest && receipt->meetingId == kMeeting && receipt->localRecordingId == "directory-1");
    const auto unlinked = DesktopApiClient::decodeDeletionReceipt(
        replaceOnce(meeting, "\"local_recording_id\":\"directory-1\"", "\"local_recording_id\":null"));
    assert(unlinked && unlinked->localRecordingId.empty());
    const auto origin = std::string("{\"receipt_type\":\"origin_cancellation\",\"request_id\":\"") + std::string(kRequest) +
        "\",\"local_recording_id\":\"directory-1\",\"accepted_at\":\"2026-09-18T12:00:00Z\",\"phase\":\"accepted\"}";
    const auto cancellation = DesktopApiClient::decodeDeletionReceipt(origin);
    assert(cancellation && cancellation->accepted() && cancellation->receiptType == "origin_cancellation");
    assert(cancellation->localRecordingId == "directory-1" && cancellation->meetingId.empty());
    // The same receipt without the identity it cancels: no confirmation at all.
    const auto anonymousCancellation = std::string("{\"receipt_type\":\"origin_cancellation\",\"request_id\":\"") +
        std::string(kRequest) + "\",\"accepted_at\":\"2026-09-18T12:00:00Z\",\"phase\":\"accepted\"}";
    assert(!DesktopApiClient::decodeDeletionReceipt(anonymousCancellation));
    // A cancellation of a local copy may also name the meeting the server created
    // for it. That answer is what teaches the queue which meeting the recording
    // became, so it must survive decoding instead of being dropped.
    const auto linkedCancellation = replaceOnce(origin, "\"phase\":\"accepted\"",
        "\"meeting_id\":\"" + std::string(kMeeting) + "\",\"phase\":\"accepted\"");
    const auto linked = DesktopApiClient::decodeDeletionReceipt(linkedCancellation);
    assert(linked && linked->localRecordingId == "directory-1" && linked->meetingId == kMeeting);
    // A deletion epoch the server reports as negative describes no deletion, and
    // macOS refuses the same receipt.
    assert(!DesktopApiClient::decodeDeletionReceipt(
        replaceOnce(meeting, "\"deletion_epoch\":0", "\"deletion_epoch\":-1")));
    // A status the client cannot read is never a confirmation, even with a 202.
    for (const auto& invalid : {
        std::string("{}"),
        replaceOnce(meeting, "\"phase\":\"accepted\"", "\"phase\":\"pending\""),
        replaceOnce(meeting, "\"receipt_type\":\"meeting_deletion\"", "\"receipt_type\":\"purge\""),
        replaceOnce(meeting, std::string(kRequest), "not-a-uuid"),
        replaceOnce(meeting, "\"meeting_id\":\"" + std::string(kMeeting) + "\"", "\"meeting_id\":null"),
        replaceOnce(meeting, "\"local_recording_id\":\"directory-1\"", "\"local_recording_id\":\"a/b\""),
        replaceOnce(origin, std::string(kRequest), ""),
    }) {
        assert(!DesktopApiClient::decodeDeletionReceipt(invalid));
    }
}

void testPurgeTaskPaths() {
    assert(DesktopApiClient::localPurgeTaskPath(kMeeting) ==
           "/api/v1/desktop/meetings/" + std::string(kMeeting) + "/local-purge-task");
    assert(DesktopApiClient::localPurgeAckPath(kRequest) ==
           "/api/v1/desktop/local-purge-tasks/" + std::string(kRequest) + "/ack");
    for (const auto& invalid : {std::string(""), std::string("not-a-uuid"), std::string("../meetings"),
                                std::string("33333333-3333-4333-8333-33333333333Z")}) {
        assert(DesktopApiClient::localPurgeTaskPath(invalid).empty());
        assert(DesktopApiClient::localPurgeAckPath(invalid).empty());
    }
}

std::string purgeTask(std::string_view taskId, std::string_view meetingId, std::string_view type,
                      std::string_view state, std::string_view safeReason, std::string_view expiresAt) {
    return "{\"task_id\":\"" + std::string(taskId) + "\",\"meeting_id\":\"" + std::string(meetingId) +
        "\",\"task_type\":\"" + std::string(type) + "\",\"state\":\"" + std::string(state) +
        "\",\"safe_reason\":" + std::string(safeReason) + ",\"expires_at\":\"" + std::string(expiresAt) +
        "\",\"ack_url\":\"/api/v1/desktop/local-purge-tasks/" + std::string(taskId) + "/ack\"}";
}

void testPurgeTaskDecoding() {
    const auto complete = purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending",
                                    "\"local_copy_present\"", "2026-09-20T12:00:00Z");
    const auto task = DesktopApiClient::decodeLocalPurgeTask(complete);
    assert(task && task->taskId == kRequest && task->meetingId == kMeeting);
    assert(task->taskType == "purge_local_buffers" && task->state == "pending");
    assert(task->safeReason == "local_copy_present" && task->expiresAt == "2026-09-20T12:00:00Z");
    assert(!task->acknowledged());
    // Every state and type the server can produce is understood.
    for (const auto& state : {"pending", "claimed", "acknowledged", "failed", "unreachable", "expired",
                              "local_expiry_relied_upon"}) {
        const auto decoded = DesktopApiClient::decodeLocalPurgeTask(
            purgeTask(kRequest, kMeeting, "purge_local_exports", state, "null", "2026-09-20T12:00:00Z"));
        assert(decoded && decoded->state == state);
        assert(decoded->acknowledged() == (std::string_view(state) == "acknowledged"));
    }
    for (const auto& type : {"purge_local_buffers", "purge_local_exports", "confirm_local_expiry"}) {
        assert(DesktopApiClient::decodeLocalPurgeTask(
            purgeTask(kRequest, kMeeting, type, "pending", "null", "2026-09-20T12:00:00Z")));
    }
    // The instants the server can write: UTC mark, offset, and a fraction.
    assert(DesktopApiClient::decodeLocalPurgeTask(
        purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending", "null", "2026-09-20T12:00:00.123456+03:00")));
    assert(DesktopApiClient::decodeLocalPurgeTask(
        purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending", "null", "2026-09-20T12:00:00-11:30")));
    // An address from the answer never becomes the target: the ack path is built
    // from the validated task identity alone, whatever the response claims.
    const auto elsewhere = replaceOnce(complete, "/api/v1/desktop/local-purge-tasks/" + std::string(kRequest) + "/ack",
                                       "https://elsewhere.invalid/collect");
    const auto redirected = DesktopApiClient::decodeLocalPurgeTask(elsewhere);
    assert(redirected && redirected->taskId == kRequest);
    assert(DesktopApiClient::localPurgeAckPath(redirected->taskId) ==
           "/api/v1/desktop/local-purge-tasks/" + std::string(kRequest) + "/ack");
    const auto unusable = [&](std::string_view json) {
        assert(!DesktopApiClient::decodeLocalPurgeTask(json));
    };
    unusable(purgeTask(kRequest, kMeeting, "purge_everything", "pending", "null", "2026-09-20T12:00:00Z"));
    unusable(purgeTask(kRequest, kMeeting, "purge_local_buffers", "purged", "null", "2026-09-20T12:00:00Z"));
    unusable(purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending", "null", "2026-09-20 12:00:00"));
    unusable(purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending", "null", ""));
    unusable(purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending", "null", "2026-09-20T12:00:00"));
    unusable(purgeTask("not-a-uuid", kMeeting, "purge_local_buffers", "pending", "null", "2026-09-20T12:00:00Z"));
    unusable(purgeTask(kRequest, "not-a-uuid", "purge_local_buffers", "pending", "null", "2026-09-20T12:00:00Z"));
    unusable("{\"meeting_id\":\"" + std::string(kMeeting) + "\",\"task_type\":\"purge_local_buffers\",\"state\":\"pending\",\"expires_at\":\"2026-09-20T12:00:00Z\"}");
    unusable("{\"task_id\":\"" + std::string(kRequest) + "\",\"task_type\":\"purge_local_buffers\",\"state\":\"pending\",\"expires_at\":\"2026-09-20T12:00:00Z\"}");
    unusable("{\"task_id\":\"" + std::string(kRequest) + "\",\"meeting_id\":\"" + std::string(kMeeting) + "\",\"state\":\"pending\",\"expires_at\":\"2026-09-20T12:00:00Z\"}");
    unusable("{\"task_id\":\"" + std::string(kRequest) + "\",\"meeting_id\":\"" + std::string(kMeeting) + "\",\"task_type\":\"purge_local_buffers\",\"expires_at\":\"2026-09-20T12:00:00Z\"}");
    unusable("[]");
}

void testPurgeTaskListDecoding() {
    const auto list = "{\"tasks\":[" +
        purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending", "null", "2026-09-20T12:00:00Z") + "," +
        purgeTask("55555555-5555-4555-8555-555555555555", "66666666-6666-4666-8666-666666666666",
                  "confirm_local_expiry", "acknowledged", "\"expired\"", "2026-09-20T12:00:00Z") + "]}";
    const auto tasks = DesktopApiClient::decodeLocalPurgeTaskList(list);
    assert(tasks && tasks->size() == 2);
    assert((*tasks)[0].taskId == kRequest && !(*tasks)[0].acknowledged());
    assert((*tasks)[1].acknowledged() && (*tasks)[1].taskType == "confirm_local_expiry");
    assert(DesktopApiClient::decodeLocalPurgeTaskList("{\"tasks\":[]}")->empty());
    // One unusable task rejects the answer: a partial list would leave the device
    // answering for a purge it never saw.
    assert(!DesktopApiClient::decodeLocalPurgeTaskList(
        "{\"tasks\":[" + purgeTask(kRequest, kMeeting, "purge_local_buffers", "purged", "null", "2026-09-20T12:00:00Z") + "]}"));
    assert(!DesktopApiClient::decodeLocalPurgeTaskList("[" + purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending", "null", "2026-09-20T12:00:00Z") + "]"));
    assert(!DesktopApiClient::decodeLocalPurgeTaskList("{}"));
    assert(!DesktopApiClient::decodeLocalPurgeTaskList("{\"tasks\":null}"));
    std::string oversized = "{\"tasks\":[";
    const auto one = purgeTask(kRequest, kMeeting, "purge_local_buffers", "pending", "null", "2026-09-20T12:00:00Z");
    for (std::size_t index = 0; index < 201; ++index) {
        if (index != 0) oversized += ',';
        oversized += one;
    }
    assert(!DesktopApiClient::decodeLocalPurgeTaskList(oversized + "]}"));
}

void testPurgeAckBodies() {
    assert(DesktopApiClient::localPurgeAckBody(LocalPurgeAckState::acknowledged, "local_artifacts_deleted",
                                               "windows-feature-200", "2026-09-18T12:00:00Z") ==
           "{\"state\":\"acknowledged\",\"reason_code\":\"local_artifacts_deleted\","
           "\"client_version\":\"windows-feature-200\",\"completed_at\":\"2026-09-18T12:00:00Z\"}");
    // The optional fields are omitted, never sent as null.
    assert(DesktopApiClient::localPurgeAckBody(LocalPurgeAckState::failed, "local_purge_unverified", "", "") ==
           "{\"state\":\"failed\",\"reason_code\":\"local_purge_unverified\"}");
    assert(DesktopApiClient::localPurgeAckBody(LocalPurgeAckState::localExpiryReliedUpon,
                                               "local_buffer_expired", "windows-feature-200", "") ==
           "{\"state\":\"local_expiry_relied_upon\",\"reason_code\":\"local_buffer_expired\","
           "\"client_version\":\"windows-feature-200\"}");
    assert(DesktopApiClient::localPurgeAckStateName(LocalPurgeAckState::acknowledged) == "acknowledged");
    assert(DesktopApiClient::localPurgeAckStateName(LocalPurgeAckState::failed) == "failed");
    assert(DesktopApiClient::localPurgeAckStateName(LocalPurgeAckState::localExpiryReliedUpon) ==
           "local_expiry_relied_upon");
    // A proof code the client does not own is not an answer.
    for (const auto& invalid : {std::string(""), std::string("Local Deleted"), std::string("local-deleted"),
                                std::string("local.deleted"), std::string(121, 'a')}) {
        assert(!DesktopApiClient::validAckReasonCode(invalid));
        assert(DesktopApiClient::localPurgeAckBody(LocalPurgeAckState::failed, invalid, "", "").empty());
    }
    // A completion instant the server cannot read is not sent at all.
    assert(DesktopApiClient::localPurgeAckBody(LocalPurgeAckState::failed, "local_purge_failed", "",
                                               "2026-09-18 12:00:00").empty());
    assert(DesktopApiClient::localPurgeAckBody(LocalPurgeAckState::failed, "local_purge_failed", "",
                                               std::string(81, 'a')).empty());
}

void testPurgeCallsRefusedBeforeTheWire() {
    DesktopHttpConfig config;
    const DesktopHttpTransport transport(config);
    const auto badTarget = transport.ensureLocalPurgeTask("not-a-uuid", scope);
    assert(badTarget.safeReason == "invalid_target" && !badTarget.answered() && !badTarget.transportFailed);
    const auto badAckTarget = transport.acknowledgeLocalPurgeTask("", LocalPurgeAckState::acknowledged,
                                                                 "local_artifacts_deleted", "", scope);
    assert(badAckTarget.safeReason == "invalid_target" && !badAckTarget.answered());
    const auto badAckBody = transport.acknowledgeLocalPurgeTask(kRequest, LocalPurgeAckState::acknowledged,
                                                               "", "", scope);
    assert(badAckBody.safeReason == "invalid_body" && !badAckBody.answered());
    // Without a session there is nothing to purge with, and nothing is attempted.
    assert(transport.localPurgeTasks(scope).safeReason == "auth_required");
    assert(transport.ensureLocalPurgeTask(kMeeting, scope).safeReason == "auth_required");
    assert(transport.acknowledgeLocalPurgeTask(kRequest, LocalPurgeAckState::failed, "local_purge_failed", "",
                                               scope).safeReason == "auth_required");
    assert(transport.localPurgeTasks(DeletionScope{}).safeReason == "invalid_scope");
}

void testScopedHeaders() {
    const auto headers = DesktopApiClient::scopedAccountHeaders(scope);
    assert(headers.size() == 2);
    assert(headers[0].first == "X-Graf-Expected-Actor" && headers[0].second == kActor);
    assert(headers[1].first == "X-Graf-Expected-Workspace" && headers[1].second == kWorkspace);
    for (const auto& invalid : {DeletionScope{}, DeletionScope{"not-a-uuid", std::string(kWorkspace)},
                                DeletionScope{std::string(kActor), ""},
                                DeletionScope{std::string(kActor), "22222222-2222-4222-8222-22222222222A"}}) {
        assert(DesktopApiClient::scopedAccountHeaders(invalid).empty());
    }
}

void testCallsRefusedBeforeTheWire() {
    DesktopHttpConfig config;
    config.sessionToken = {};
    const DesktopHttpTransport transport(config);
    // A target this client may not name is refused locally, and the refusal is
    // distinguishable from a server that answered no.
    const auto target = transport.requestDeletion("", DesktopApiClient::meetingDeletionBody(), scope);
    assert(target.safeReason == "invalid_target" && !target.answered() && !target.transportFailed);
    // A scope that does not name a real account is never sent: without both
    // expected-account headers the server would read the request as unscoped.
    const auto unscoped = transport.requestDeletion(DesktopApiClient::meetingDeletionPath(kMeeting),
                                                    DesktopApiClient::meetingDeletionBody(), DeletionScope{});
    assert(unscoped.safeReason == "invalid_scope" && !unscoped.answered());
    const auto emptySelection = transport.recordingLifecycle({}, {}, scope);
    assert(emptySelection.safeReason == "invalid_selection" && !emptySelection.answered());
    const auto oversized = transport.recordingLifecycle(std::vector<std::string>(101, "directory"), {}, scope);
    assert(oversized.safeReason == "invalid_selection" && !oversized.answered());
    // Without a session there is nothing to delete with, and the request is not
    // attempted at all.
    const auto unauthenticated = transport.notificationContext(scope);
    assert(unauthenticated.safeReason == "auth_required" && !unauthenticated.answered());
    const auto noSession = transport.recordingLifecycle({"directory-1"}, {}, scope);
    assert(noSession.safeReason == "auth_required" && !noSession.answered());
}

} // namespace

void testDeletionWaitReasonsReachThePageInItsOwnSpelling() {
    // The cabinet prints these reasons itself (`cabinet.js:404-440`), so the
    // ledger's snake_case spellings are translated at the boundary. An unknown
    // reason is passed through: the page then prints the phase instead of a state
    // it was never told about.
    assert(pageDeletionWaitReason("rate_limit") == "rateLimit");
    assert(pageDeletionWaitReason("server_update") == "serverUpdate");
    assert(pageDeletionWaitReason("connection") == "connection");
    assert(pageDeletionWaitReason("authentication") == "authentication");
    assert(pageDeletionWaitReason("deletion_forbidden") == "deletion_forbidden");
    assert(pageDeletionWaitReason("") == "");
}

int main() {
    testDeletionWaitReasonsReachThePageInItsOwnSpelling();
    testNotificationContext();
    testDeletionPaths();
    testRequestBodies();
    testLifecycleDecoding();
    testDeletionReceipts();
    testPurgeTaskPaths();
    testPurgeTaskDecoding();
    testPurgeTaskListDecoding();
    testPurgeAckBodies();
    testPurgeCallsRefusedBeforeTheWire();
    testScopedHeaders();
    testCallsRefusedBeforeTheWire();
    return 0;
}
