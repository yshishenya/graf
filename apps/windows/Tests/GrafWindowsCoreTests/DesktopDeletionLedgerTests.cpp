// The ledger of deletion requests: what makes "запрос сохранён" true, and what
// keeps a recording from reappearing after the server has already deleted it.
//
// macOS stores the same state under `deletionOperations`
// (apps/macos/Shared/Sources/Models/RecordingDeletionLifecycle.swift). The cases
// below are the ones that decide whether the cabinet is told the truth: an
// operation exists exactly once per target and account, acceptance requires the
// receipt that named this target, and deletion never goes backwards.

#include "../../RecApp/Upload/DesktopUploadQueueService.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <cstdint>
#include <functional>
#include <vector>

namespace {

using namespace graf::windows;

constexpr std::string_view kActor = "11111111-1111-4111-8111-111111111111";
constexpr std::string_view kWorkspace = "22222222-2222-4222-8222-222222222222";
constexpr std::string_view kOtherActor = "55555555-5555-4555-8555-555555555555";
constexpr std::string_view kMeeting = "33333333-3333-4333-8333-333333333333";
constexpr std::string_view kRequest = "44444444-4444-4444-8444-444444444444";
constexpr std::string_view kOrigin = "https://graf.example.test";

const DesktopAccountIdentity kOwner{std::string(kActor), std::string(kWorkspace)};

std::uint64_t nowMs = 1'700'000'000'000;

std::filesystem::path freshRoot(std::string_view name) {
    const auto root = std::filesystem::temp_directory_path() / ("graf-deletion-ledger-" + std::string(name));
    std::error_code error;
    std::filesystem::remove_all(root, error);
    std::filesystem::create_directories(root, error);
    return root;
}

DeletionReceipt originReceipt(std::string recordingId) {
    DeletionReceipt receipt;
    receipt.receiptType = "origin_cancellation";
    receipt.requestId = std::string(kRequest);
    receipt.localRecordingId = std::move(recordingId);
    receipt.phase = "accepted";
    return receipt;
}

DeletionReceipt meetingReceipt(std::string meetingId) {
    DeletionReceipt receipt;
    receipt.receiptType = "meeting_deletion";
    receipt.requestId = std::string(kRequest);
    receipt.meetingId = std::move(meetingId);
    receipt.phase = "accepted";
    return receipt;
}

DesktopUploadQueueService makeQueue(const std::filesystem::path& root, std::string_view name) {
    DesktopUploadQueueService queue(root / (std::string(name) + ".json"), root);
    queue.setClock([] { return nowMs; });
    assert(queue.load());
    return queue;
}

// A ledger written by hand has to escape the separators in a Windows path, or it
// is not JSON and the loader is right to quarantine it.
std::string jsonPath(const std::filesystem::path& path) {
    std::string result;
    for (const char c : path.string()) {
        if (c == '\\' || c == '"') result += '\\';
        result += c;
    }
    return result;
}

void testRequestIsDurable() {
    const auto root = freshRoot("durable");
    {
        auto queue = makeQueue(root, "queue");
        std::string operationId;
        assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-one", kOwner, kOrigin, operationId));
        assert(!operationId.empty());
        const auto* stored = queue.findDeletionOperation(operationId);
        assert(stored != nullptr && stored->phase == DeletionOperationPhase::queued);
        assert(stored->requestedAtMs == nowMs && stored->updatedAtMs == nowMs);
        assert(stored->attemptCount == 0 && stored->nextAttemptAtMs == 0);
        assert(stored->receiptRequestId.empty() && stored->safeReason.empty());
        assert(stored->serverOrigin == kOrigin);
        // Asking again is the same request, not a second one.
        std::string again;
        nowMs += 1000;
        assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-one", kOwner, kOrigin, again));
        assert(again == operationId);
        assert(queue.deletionOperations().size() == 1);
        // A refusal stores nothing.
        std::string refused;
        assert(!queue.requestDeletion(DeletionTarget::meeting, "not-a-uuid", kOwner, kOrigin, refused));
        assert(refused.empty() && queue.deletionOperations().size() == 1);
        assert(!queue.requestDeletion(DeletionTarget::ownOrigin, "directory-two", kOwner, "http://graf.example.test",
                                      refused));
        assert(queue.deletionOperations().size() == 1);
    }
    // A restart must find the request. A server-only deletion has no local
    // package to remember it by.
    DesktopUploadQueueService reopened(root / "queue.json", root);
    assert(reopened.load());
    const auto operations = reopened.currentDeletionOperations(kOwner);
    assert(operations.size() == 1);
    assert(operations[0].target == DeletionTarget::ownOrigin && operations[0].targetId == "directory-one");
    assert(operations[0].phase == DeletionOperationPhase::queued);
    assert(operations[0].requestedAtMs == nowMs - 1000);
}

void testScopeIsolation() {
    const auto root = freshRoot("scope");
    auto queue = makeQueue(root, "queue");
    std::string first, second;
    assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-one", kOwner, kOrigin, first));
    // The same recording requested by another account is another request: the id
    // names the request, and the request belongs to the account that asked.
    const DesktopAccountIdentity other{std::string(kOtherActor), std::string(kWorkspace)};
    assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-one", other, kOrigin, second));
    assert(!second.empty() && second != first);
    assert(queue.deletionOperations().size() == 2);
    assert(queue.currentDeletionOperations(kOwner).size() == 1);
    assert(queue.currentDeletionOperations(other).size() == 1);
    assert(queue.currentDeletionOperations({}).empty());
    assert(queue.currentDeletionOperations({std::string(kActor), "not-a-uuid"}).empty());
    // The request for one account can never be confirmed through the identity of
    // the other: acceptance is looked up by operation, not by target.
    assert(queue.acceptDeletion(second, originReceipt("directory-one")));
    const auto* untouched = queue.findDeletionOperation(first);
    assert(untouched != nullptr && untouched->phase == DeletionOperationPhase::queued);
}

void testPhaseTransitions() {
    const auto root = freshRoot("phases");
    auto queue = makeQueue(root, "queue");
    std::string operationId;
    assert(queue.requestDeletion(DeletionTarget::meeting, kMeeting, kOwner, kOrigin, operationId));
    const auto requestedAt = nowMs;

    // A phase may not be declared without the receipt that proves it.
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::accepted, ""));
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::verified, ""));
    assert(!queue.markDeletionPhase("not-an-operation", DeletionOperationPhase::sending, ""));
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, "Not A Reason"));

    nowMs = requestedAt + 1000;
    assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, ""));
    assert(queue.findDeletionOperation(operationId)->attemptCount == 1);
    // A wait is a delay, never a give-up, and it grows with the attempts.
    nowMs += 1000;
    assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::resolving, "connection"));
    assert(queue.findDeletionOperation(operationId)->nextAttemptAtMs == nowMs + 5000);
    nowMs += 5000;
    assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, ""));
    nowMs += 1000;
    assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::resolving, "rate_limit"));
    assert(queue.findDeletionOperation(operationId)->nextAttemptAtMs == nowMs + 15000);
    nowMs += 15000;
    assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::rejected, "not_owner"));
    assert(queue.findDeletionOperation(operationId)->nextAttemptAtMs == 0);
    // A refused request is not a deleted recording, and nothing stops the user
    // from asking again.
    assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, ""));

    nowMs += 1000;
    const auto acceptedAt = nowMs;
    assert(queue.acceptDeletion(operationId, meetingReceipt(std::string(kMeeting))));
    const auto* accepted = queue.findDeletionOperation(operationId);
    assert(accepted->phase == DeletionOperationPhase::accepted);
    assert(accepted->receiptRequestId == kRequest && accepted->safeReason.empty());
    assert(accepted->updatedAtMs == acceptedAt);
    // The same receipt again is not an error and changes nothing.
    assert(queue.acceptDeletion(operationId, meetingReceipt(std::string(kMeeting))));
    assert(queue.findDeletionOperation(operationId)->updatedAtMs == acceptedAt);
    // Acceptance is monotonic: a late failure cannot start showing a recording
    // the server has already deleted.
    nowMs += 1000;
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, ""));
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::rejected, "late_failure"));
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::queued, ""));
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::resolving, "connection"));
    assert(queue.findDeletionOperation(operationId)->phase == DeletionOperationPhase::accepted);
    // Only the proof that the local copies are gone may follow.
    assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::verified, "local_artifacts_deleted"));
    nowMs += 1000;
    const auto* verified = queue.findDeletionOperation(operationId);
    assert(verified->phase == DeletionOperationPhase::verified);
    // Verified is terminal.
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, ""));
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::rejected, "late_failure"));
    assert(queue.findDeletionOperation(operationId)->phase == DeletionOperationPhase::verified);
    assert(deletionPhaseIsAccepted(DeletionOperationPhase::accepted));
    assert(deletionPhaseIsAccepted(DeletionOperationPhase::verified));
    assert(!deletionPhaseIsAccepted(DeletionOperationPhase::rejected));
    assert(!deletionPhaseIsAccepted(DeletionOperationPhase::queued));
}

void testTimeNeverGoesBackwards() {
    const auto root = freshRoot("clock");
    auto queue = makeQueue(root, "queue");
    std::string operationId;
    assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-one", kOwner, kOrigin, operationId));
    const auto requestedAt = nowMs;
    nowMs = requestedAt - 1;
    assert(!queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, ""));
    assert(!queue.acceptDeletion(operationId, originReceipt("directory-one")));
    assert(queue.findDeletionOperation(operationId)->phase == DeletionOperationPhase::queued);
    // A clock that cannot answer does not change the ledger either.
    queue.setClock([]() -> std::uint64_t { throw std::runtime_error("no clock"); });
    assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, ""));
    assert(queue.findDeletionOperation(operationId)->updatedAtMs >= requestedAt);
}

void testReceiptsMustMatch() {
    const auto root = freshRoot("receipts");
    auto queue = makeQueue(root, "queue");
    std::string local, meeting;
    assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-one", kOwner, kOrigin, local));
    assert(queue.requestDeletion(DeletionTarget::meeting, kMeeting, kOwner, kOrigin, meeting));
    // The receipt has to name this target, and the two shapes are not
    // interchangeable.
    assert(!queue.acceptDeletion(local, originReceipt("directory-two")));
    assert(!queue.acceptDeletion(local, meetingReceipt(std::string(kMeeting))));
    assert(!queue.acceptDeletion(meeting, meetingReceipt("66666666-6666-4666-8666-666666666666")));
    assert(!queue.acceptDeletion(meeting, originReceipt("directory-one")));
    auto unknownShape = originReceipt("directory-one");
    unknownShape.receiptType = "something_else";
    assert(!queue.acceptDeletion(local, unknownShape));
    auto unconfirmed = originReceipt("directory-one");
    unconfirmed.phase = "pending";
    assert(!queue.acceptDeletion(local, unconfirmed));
    auto noRequest = originReceipt("directory-one");
    noRequest.requestId.clear();
    assert(!queue.acceptDeletion(local, noRequest));
    assert(queue.findDeletionOperation(local)->phase == DeletionOperationPhase::queued);
    // An answer that contradicts the stored one is refused instead of silently
    // replacing it.
    assert(queue.acceptDeletion(local, originReceipt("directory-one")));
    auto otherRequest = originReceipt("directory-one");
    otherRequest.requestId = "77777777-7777-4777-8777-777777777777";
    assert(!queue.acceptDeletion(local, otherRequest));
    assert(queue.findDeletionOperation(local)->receiptRequestId == kRequest);
}

void testLedgerRoundTripAndLegacyUpgrade() {
    const auto root = freshRoot("roundtrip");
    std::string operationId;
    {
        auto queue = makeQueue(root, "queue");
        assert(queue.enqueue({"local-one", "directory-one", "session-one", root / "recording-one",
                              UploadQueueStatus::pending, {1, 2, 3}, 0, "queued"}));
        assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-one", kOwner, kOrigin, operationId));
        nowMs += 1000;
        assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::sending, ""));
        nowMs += 1000;
        assert(queue.markDeletionPhase(operationId, DeletionOperationPhase::resolving, "connection"));
        assert(queue.markDeletionAttempt(operationId, nowMs + 60000));
    }
    DesktopUploadQueueService reopened(root / "queue.json", root);
    assert(reopened.load());
    assert(reopened.items().size() == 1 && reopened.items()[0].updatedAtMs != 0);
    const auto* restored = reopened.findDeletionOperation(operationId);
    assert(restored != nullptr);
    assert(restored->phase == DeletionOperationPhase::resolving && restored->attemptCount == 1);
    assert(restored->nextAttemptAtMs == nowMs + 60000 && restored->safeReason == "connection");
    // The document stamp is written with the file and survives the restart.
    std::ifstream file(root / "queue.json", std::ios::binary);
    const std::string text((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    assert(text.find("desktop-upload-queue.v3") != std::string::npos);
    assert(text.find("\"deletion_operations\":[") != std::string::npos);
    assert(text.find("\"updated_at_ms\"") != std::string::npos);

    // A version-2 ledger is still readable and is upgraded on the next write: a
    // pending upload exists only on this computer, so refusing it would lose it.
    const auto legacyRoot = freshRoot("legacy");
    const auto legacyPath = legacyRoot / "queue.json";
    {
        std::ofstream out(legacyPath, std::ios::binary);
        out << "{\"schema_version\":\"desktop-upload-queue.v2\",\"items\":[{\"local_recording_id\":\"legacy\","
               "\"directory_id\":\"directory\",\"session_id\":\"session\",\"package_directory\":\""
            << jsonPath(legacyRoot / "recording")
            << "\",\"status\":0,\"accepted_bytes\":[0,0,0],\"attempts\":0,\"safe_reason\":\"\","
               "\"owner_user_id\":\"\",\"owner_workspace_id\":\"\",\"meeting_id\":\"\"}]}";
    }
    DesktopUploadQueueService upgraded(legacyPath, legacyRoot);
    upgraded.setClock([] { return nowMs; });
    assert(upgraded.load());
    assert(upgraded.items().size() == 1 && upgraded.items()[0].localRecordingId == "legacy");
    assert(upgraded.deletionOperations().empty());
    assert(upgraded.items()[0].updatedAtMs == nowMs);
    std::ifstream rewritten(legacyPath, std::ios::binary);
    const std::string rewrittenText((std::istreambuf_iterator<char>(rewritten)), std::istreambuf_iterator<char>());
    assert(rewrittenText.find("desktop-upload-queue.v3") != std::string::npos);

    // An accepted operation without the receipt that proved it is not believed:
    // a hand-edited ledger cannot turn a rejection into a deletion.
    const auto forgedRoot = freshRoot("forged");
    const auto forgedPath = forgedRoot / "queue.json";
    {
        std::ofstream out(forgedPath, std::ios::binary);
        out << "{\"schema_version\":\"desktop-upload-queue.v3\",\"items\":[],\"updated_at_ms\":1,"
               "\"deletion_operations\":[{\"operation_id\":\""
            << operationId
            << "\",\"target\":\"meeting\",\"target_id\":\"" << kMeeting << "\",\"actor_user_id\":\"" << kActor
            << "\",\"workspace_id\":\"" << kWorkspace << "\",\"server_origin\":\"" << kOrigin
            << "\",\"phase\":3,\"requested_at_ms\":1,\"updated_at_ms\":1,\"attempts\":0,"
               "\"next_attempt_at_ms\":0,\"receipt_request_id\":\"\",\"safe_reason\":\"\"}]}";
    }
    DesktopUploadQueueService forged(forgedPath, forgedRoot);
    assert(!forged.load());
    assert(forged.quarantined());
    assert(std::filesystem::exists(forgedPath.string() + ".quarantine"));
}

void testServerOriginValidation() {
    const auto root = freshRoot("origin");
    auto queue = makeQueue(root, "queue");
    std::string operationId;
    assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-one", kOwner, "https://graf.example.test",
                                 operationId));
    // A server on this computer may answer over plain HTTP, where nothing leaves
    // the machine. Anywhere else the session would travel in the clear.
    assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-two", kOwner, "http://127.0.0.1:8080",
                                 operationId));
    assert(queue.requestDeletion(DeletionTarget::ownOrigin, "directory-three", kOwner, "http://localhost",
                                 operationId));
    for (const auto origin : {std::string(""), std::string("graf.example.test"), std::string("ftp://graf.example.test"),
                              std::string("http://graf.example.test"), std::string("https://graf.example.test/path"),
                              std::string("https://user@graf.example.test"), std::string("https://graf.example.test?a=1"),
                              std::string("https://graf.example.test#fragment")}) {
        assert(!queue.requestDeletion(DeletionTarget::ownOrigin, "directory-four", kOwner, origin, operationId));
        assert(operationId.empty());
    }
    assert(queue.deletionOperations().size() == 3);
}

void testItemTimestampsAdvance() {
    const auto root = freshRoot("stamps");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue({"local-one", "directory-one", "session-one", root / "recording-one",
                          UploadQueueStatus::pending, {0, 0, 0}, 0, "queued"}));
    assert(queue.items()[0].updatedAtMs == nowMs);
    nowMs += 1000;
    assert(queue.markRetry("local-one", "server_unavailable"));
    assert(queue.items()[0].updatedAtMs == nowMs);
    // A stamp is only written where something changed: reading the row twice must
    // not move it.
    assert(queue.items()[0].attempts == 1);
    nowMs += 1000;
    assert(queue.markUploaded("local-one"));
    assert(queue.items()[0].updatedAtMs == nowMs);
    assert(queue.load() && queue.items()[0].updatedAtMs == nowMs);
}

// A selection the cabinet confirmed. What the app does with it is the difference
// between a request that is merely sent and a deletion the user can rely on.
UploadCustodyItem item(const std::filesystem::path& custodyRoot, std::string recordingId,
                       std::string directoryId, std::string meetingId, UploadQueueStatus status,
                       std::uint32_t attempts) {
    UploadCustodyItem value;
    value.localRecordingId = std::move(recordingId);
    value.directoryId = std::move(directoryId);
    value.sessionId = "session-key";
    // The queue only accepts a package inside its own custody root, exactly as the
    // app's own enqueue path does.
    value.packageDirectory = custodyRoot / value.localRecordingId;
    value.status = status;
    value.attempts = attempts;
    value.meetingId = std::move(meetingId);
    return value;
}

std::string receiptBody(std::string type, std::string id) {
    const auto key = type == "origin_cancellation" ? "local_recording_id" : "meeting_id";
    return "{\"receipt_type\":\"" + type + "\",\"request_id\":\"" + std::string(kRequest) +
        "\",\"" + key + "\":\"" + id + "\",\"phase\":\"accepted\"}";
}

// The context the app reads before it may mutate anything, in the shape the
// server sends it.
std::string contextBody(std::string user, std::string workspace, int version) {
    return "{\"user_id\":\"" + std::move(user) + "\",\"workspace_id\":\"" + std::move(workspace) +
        "\",\"recording_deletion_protocol_version\":" + std::to_string(version) + "}";
}

// Performs one deletion pass the way the app does: store the selection on the
// owner thread, send the requests without touching the ledger, then record what
// the server answered. A shared failure ends the pass, leaving the rest durable.
DesktopUploadQueueService::DeletionPlan runDeletionPass(DesktopUploadQueueService& queue,
                             const std::vector<DesktopUploadQueueService::DeletionTargetRequest>& targets,
                             const DesktopAccountIdentity& owner,
                             const std::function<DesktopUploadQueueService::DeletionWireResult(
                                 const DesktopUploadQueueService::DeletionRequestPlan&)>& send,
                             std::size_t* calls = nullptr) {
    auto plan = queue.planDeletionSelection(targets, owner, kOrigin);
    if (plan.requests.empty()) return plan;
    for (const auto& request : plan.requests) {
        if (calls != nullptr) ++*calls;
        const auto wire = send(request);
        (void)queue.applyDeletionAnswer(request, owner, kOrigin, wire);
        if (DesktopUploadQueueService::deletionFailureIsShared(wire)) break;
    }
    return plan;
}

// A purge task the server sends after it deleted a meeting. Only the fields the
// client acts on are set.
LocalPurgeTask purgeTask(std::string meetingId, std::string type = "purge_local_buffers",
                         std::string state = "pending") {
    LocalPurgeTask task;
    task.taskId = "66666666-6666-4666-8666-666666666666";
    task.meetingId = std::move(meetingId);
    task.taskType = std::move(type);
    task.state = std::move(state);
    task.expiresAt = "2026-09-19T00:00:00Z";
    return task;
}

// The recycle callback the shell passes: it moves the package to the Windows
// Recycle Bin and reports whether the path is really gone afterwards.
std::function<bool(const std::filesystem::path&)> recycling(std::size_t* calls = nullptr) {
    return [calls](const std::filesystem::path& package) {
        if (calls != nullptr) ++*calls;
        std::error_code error;
        std::filesystem::remove_all(package, error);
        return !error;
    };
}

void testPurgeFailureIsRetriedNotFrozen() {
    const auto root = freshRoot("purge-retry");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-thirty", "directory-thirty", std::string(kMeeting),
                              UploadQueueStatus::retry, 1)));
    // A copy that has not reached the server cannot be purged, and the failure is
    // not recorded: freezing it would leave the local copy unremovable once the
    // upload did finish.
    const auto first = queue.completeLocalPurgeTask(purgeTask(std::string(kMeeting)), recycling());
    assert(first.verification == DesktopUploadQueueService::LocalPurgeVerification::failed);
    assert(queue.localPurgeAcknowledgements().empty());
    // Once the server owns the recording, the same task succeeds.
    assert(queue.markUploaded("local-thirty"));
    const auto second = queue.completeLocalPurgeTask(purgeTask(std::string(kMeeting)), recycling());
    assert(second.verification == DesktopUploadQueueService::LocalPurgeVerification::deleted);
    assert(second.removed == 1 && queue.items().empty());
    assert(queue.localPurgeAcknowledgements().size() == 1);
}

void testLocalOnlyDeletionIsPromisedOnlyWhenTheServerNeverHeardOfIt() {
    const auto root = freshRoot("local-only");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-thirty-one", "directory-thirty-one", std::string(), UploadQueueStatus::pending, 0)));
    // Nothing was ever sent, so deleting this copy is a local act. That promise is
    // the same rule the deletion planner uses, so the dialog and the executor
    // cannot disagree.
    assert(!DesktopUploadQueueService::hasServerIdentity(queue.items()[0]));
    assert(queue.planDeletionSelection({{DeletionTarget::ownOrigin, "directory-thirty-one"}}, kOwner, kOrigin).localOnly.size() == 1);
    // Once the upload finished the server owns the recording, and the copy can no
    // longer be deleted as if the server had never heard of it.
    assert(queue.markUploaded("local-thirty-one"));
    assert(DesktopUploadQueueService::hasServerIdentity(queue.items()[0]));
    assert(queue.planDeletionSelection({{DeletionTarget::ownOrigin, "directory-thirty-one"}}, kOwner, kOrigin).localOnly.empty());
    // A copy the server named in a meeting is not local-only either, even before
    // an upload attempt: the server knows it by that meeting.
    assert(queue.enqueue(item(root, "local-thirty-two", "directory-thirty-two", std::string(kMeeting),
                              UploadQueueStatus::pending, 0)));
    assert(DesktopUploadQueueService::hasServerIdentity(queue.items()[1]));
}

void testInterruptedLocalDeletionIsCarriedOut() {
    const auto root = freshRoot("local-delete-resume");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-thirty-three", "directory-thirty-three", std::string(),
                              UploadQueueStatus::pending, 0)));
    std::error_code error;
    const auto package = root / "local-thirty-three";
    std::filesystem::create_directories(package, error);
    std::ofstream(package / "manifest.json") << "{\"schema_version\":\"5\"}";

    // The Recycle Bin operation fails, so the intent is left in the ledger with the
    // files still on disk: exactly the state a crash between the two leaves.
    const auto failed = queue.removeLocalCopy("local-thirty-three", LocalPurgeProof::userConfirmedLocalCopy,
        [](const std::filesystem::path&) { return false; });
    assert(failed == LocalCopyRemovalResult::recycleFailed);
    assert(queue.items().size() == 1);
    assert(DesktopUploadQueueService::localDeletionPending(queue.items()[0]));
    assert(std::filesystem::exists(package, error));
    const auto pending = queue.pendingLocalDeletionIds();
    assert(pending.size() == 1 && pending[0] == "local-thirty-three");

    // The recorded intent is the user's confirmation, so the next pass carries the
    // deletion out instead of leaving the mark forever — and the promise the
    // cabinet shows while it is pending then becomes true.
    assert(queue.removeLocalCopy(pending[0], LocalPurgeProof::userConfirmedLocalCopy, recycling()) ==
        LocalCopyRemovalResult::removed);
    assert(queue.items().empty());
    assert(queue.pendingLocalDeletionIds().empty());
    assert(!std::filesystem::exists(package, error));
    // A resumed deletion survives a restart of the app in between.
    auto reopened = makeQueue(root, "queue");
    assert(reopened.pendingLocalDeletionIds().empty());
}

void testPurgeTaskNamesOnlyItsMeeting() {
    const auto root = freshRoot("purge-match");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-twenty", "directory-twenty", std::string(kMeeting),
                              UploadQueueStatus::uploaded, 1)));
    assert(queue.enqueue(item(root, "local-twenty-one", "directory-twenty-one", std::string(kOtherActor),
                              UploadQueueStatus::uploaded, 1)));

    // The meeting the server itself returned is the only match. A task about
    // another meeting is not a reason to touch this device's files, and a task
    // that names no meeting matches nothing rather than everything.
    const auto mine = queue.localPurgeCandidates(purgeTask(std::string(kMeeting)));
    assert(mine.size() == 1 && mine[0].localRecordingId == "local-twenty" && mine[0].purgeable);
    assert(queue.localPurgeCandidates(purgeTask(std::string(kRequest))).empty());
    assert(queue.localPurgeCandidates(purgeTask("")).empty());
}

void testPurgeRemovesOnlyFinishedCopies() {
    const auto root = freshRoot("purge-partial");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-twenty-two", "directory-twenty-two", std::string(kMeeting),
                              UploadQueueStatus::uploaded, 1)));
    // The second copy of the same meeting has not reached the server: removing it
    // would destroy an upload that has not finished.
    assert(queue.enqueue(item(root, "local-twenty-three", "directory-twenty-three", std::string(kMeeting),
                              UploadQueueStatus::retry, 2)));

    // Both packages really exist, so the difference between them is the state of
    // the row and nothing else.
    std::error_code error;
    const auto finished = root / "local-twenty-two";
    const auto unfinished = root / "local-twenty-three";
    std::filesystem::create_directories(finished, error);
    std::filesystem::create_directories(unfinished, error);

    std::size_t calls = 0;
    const auto completion = queue.completeLocalPurgeTask(purgeTask(std::string(kMeeting)), recycling(&calls));
    // One copy was removed, the other was not, so nothing is claimed that was not
    // proven: the server is told the purge failed, not that it succeeded.
    assert(completion.verification == DesktopUploadQueueService::LocalPurgeVerification::failed);
    assert(completion.ack == LocalPurgeAckState::failed && completion.reasonCode == "local_purge_failed");
    assert(completion.removed == 1 && calls == 1);
    assert(!std::filesystem::exists(finished, error));
    assert(std::filesystem::exists(unfinished, error));
    assert(queue.items().size() == 1 && queue.items()[0].localRecordingId == "local-twenty-three");
}

void testPurgeOfEveryCopyIsAcknowledged() {
    const auto root = freshRoot("purge-all");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-twenty-four", "directory-twenty-four", std::string(kMeeting),
                              UploadQueueStatus::uploaded, 1)));
    assert(queue.enqueue(item(root, "local-twenty-five", "directory-twenty-five", std::string(kMeeting),
                              UploadQueueStatus::uploaded, 1)));
    // A package that really exists on disk, so the removal is not merely a row
    // disappearing from the ledger.
    std::error_code error;
    std::filesystem::create_directories(root / "local-twenty-four", error);
    std::ofstream(root / "local-twenty-four" / "manifest.json") << "{\"schema_version\":\"5\"}";

    const auto completion = queue.completeLocalPurgeTask(purgeTask(std::string(kMeeting)), recycling());
    assert(completion.verification == DesktopUploadQueueService::LocalPurgeVerification::deleted);
    assert(completion.ack == LocalPurgeAckState::acknowledged);
    assert(completion.reasonCode == "local_artifacts_deleted" && completion.removed == 2);
    assert(queue.items().empty());
    assert(!std::filesystem::exists(root / "local-twenty-four", error));
    // The proof is durable: a second pass over the same task answers from the
    // record instead of looking for rows that are already gone, so one lost answer
    // cannot turn a deletion this device performed into a failure.
    assert(queue.localPurgeAcknowledgements().size() == 1);
    assert(queue.hasLocalPurgeAcknowledgement("66666666-6666-4666-8666-666666666666"));
    const auto again = queue.completeLocalPurgeTask(purgeTask(std::string(kMeeting)), recycling());
    assert(again.verification == DesktopUploadQueueService::LocalPurgeVerification::deleted);
    assert(again.reasonCode == "local_artifacts_deleted" && again.removed == 0);

    // The proof survives a restart, because it is the answer the server asked for.
    auto reopened = makeQueue(root, "queue");
    assert(reopened.hasLocalPurgeAcknowledgement("66666666-6666-4666-8666-666666666666"));
    assert(reopened.localPurgeAcknowledgements()[0].meetingId == kMeeting);
}

void testPurgeOfATypeThisClientCannotVerify() {
    const auto root = freshRoot("purge-type");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-twenty-six", "directory-twenty-six", std::string(kMeeting),
                              UploadQueueStatus::uploaded, 1)));
    // Only the buffers task is about the local copies themselves. A task this
    // client cannot carry out is answered honestly and touches no file: a claimed
    // deletion that was not verified is the false proof this port removed once.
    for (const auto type : {std::string("purge_local_exports"), std::string("confirm_local_expiry")}) {
        std::size_t calls = 0;
        const auto completion = queue.completeLocalPurgeTask(purgeTask(std::string(kMeeting), type), recycling(&calls));
        assert(completion.verification == DesktopUploadQueueService::LocalPurgeVerification::unverified);
        assert(completion.ack == LocalPurgeAckState::failed && completion.reasonCode == "local_purge_unverified");
        assert(completion.removed == 0 && calls == 0);
    }
    assert(queue.items().size() == 1);
}

void testPurgeAsksForTheTaskItsDeletionProved() {
    const auto root = freshRoot("purge-ask");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-twenty-seven", "directory-twenty-seven", std::string(kMeeting),
                              UploadQueueStatus::uploaded, 1)));
    // Nothing is asked for before a deletion has been accepted: the server creates
    // the purge task only after it deleted the meeting, and a task for a recording
    // that is still there would be a request to destroy what the user kept.
    assert(queue.meetingsAwaitingLocalPurge().empty());
    // The local copy already knows its meeting, so the request names the meeting.
    const auto plan = queue.planDeletionSelection({{DeletionTarget::ownOrigin, "directory-twenty-seven"}}, kOwner,
        kOrigin);
    assert(plan.saved && plan.requests.size() == 1 && plan.requests[0].target == DeletionTarget::meeting);
    // A request is not a deletion: only a receipt that named this meeting counts.
    assert(queue.meetingsAwaitingLocalPurge().empty());
    assert(queue.applyDeletionAnswer(plan.requests[0], kOwner, kOrigin,
        {200, receiptBody("meeting_deletion", std::string(kMeeting)), false, 0, ""}));
    const auto meetings = queue.meetingsAwaitingLocalPurge();
    assert(meetings.size() == 1 && meetings[0] == kMeeting);
    // A deletion the server refused is not one this device asks to have purged.
    assert(queue.enqueue(item(root, "local-twenty-nine", "directory-twenty-nine", std::string(kRequest),
                              UploadQueueStatus::uploaded, 1)));
    const auto refused = queue.planDeletionSelection({{DeletionTarget::ownOrigin, "directory-twenty-nine"}}, kOwner,
        kOrigin);
    assert(refused.saved && refused.requests.size() == 1);
    assert(queue.applyDeletionAnswer(refused.requests[0], kOwner, kOrigin,
        {403, "{\"detail\":\"deletion_forbidden\"}", false, 0, ""}));
    assert(queue.meetingsAwaitingLocalPurge().size() == 1);
}

void testPurgeNeverRunsOnAQuarantinedLedger() {
    const auto root = freshRoot("purge-quarantine");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-twenty-eight", "directory-twenty-eight", std::string(kMeeting),
                              UploadQueueStatus::uploaded, 1)));
    std::ofstream(queue.ledgerPath(), std::ios::trunc | std::ios::binary) << "{ this is not a ledger";
    // A ledger that cannot be read is quarantined, and a quarantined queue is not
    // a queue that may delete anything.
    DesktopUploadQueueService broken(queue.ledgerPath(), root);
    assert(!broken.load() && broken.quarantined());
    std::size_t calls = 0;
    const auto completion = broken.completeLocalPurgeTask(purgeTask(std::string(kMeeting)), recycling(&calls));
    // A ledger this app could not read is not evidence about any local copy.
    assert(completion.verification == DesktopUploadQueueService::LocalPurgeVerification::unverified);
    assert(completion.removed == 0 && calls == 0);
    assert(broken.meetingsAwaitingLocalPurge().empty());
}

void testNothingIsSentBeforeTheServerDeclaresSupport() {
    // The gate is read before any mutation: an older server ignores the
    // expected-account headers, and a receipt that failed to decode would arrive
    // after the recording was gone.
    const auto open = [](std::uint32_t status, std::string body, bool failed = false) {
        DesktopUploadQueueService::DeletionWireResult context;
        context.status = status;
        context.body = std::move(body);
        context.transportFailed = failed;
        return DesktopUploadQueueService::deletionGateReason(context, kOwner);
    };
    assert(open(200, contextBody(std::string(kActor), std::string(kWorkspace), 1)).empty());
    assert(open(200, contextBody(std::string(kActor), std::string(kWorkspace), 2)) == "server_update");
    assert(open(200, contextBody(std::string(kActor), std::string(kWorkspace), 0)) == "server_update");
    // Another account's context is not this account's deletion.
    assert(open(200, contextBody(std::string(kOtherActor), std::string(kWorkspace), 1)) == "scope_changed");
    assert(open(200, contextBody(std::string(kActor), std::string(kOtherActor), 1)) == "scope_changed");
    assert(open(200, "{}") == "server_update");
    assert(open(404, "") == "server_update");
    assert(open(401, "") == "authentication");
    assert(open(429, "") == "rate_limit");
    assert(open(0, "", true) == "connection");
    // A pass that waits for the gate stores its requests and sends nothing.
    const auto root = freshRoot("apply-gate");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-thirteen", "directory-thirteen", "", UploadQueueStatus::retry, 1)));
    const auto plan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-thirteen"}}, kOwner,
        [](const DesktopUploadQueueService::DeletionRequestPlan&) {
            return DesktopUploadQueueService::DeletionWireResult{0, "", false, 0, "server_update"};
        });
    const auto outcome = queue.deletionSelectionOutcome(plan);
    assert(plan.saved && outcome.pending == 1 && outcome.rejected == 0 && outcome.accepted == 0);
    assert(queue.deletionOperations().size() == 1);
    assert(queue.deletionOperations()[0].phase == DeletionOperationPhase::resolving);
    // The wait it recorded is the gate's reason, not a rejection.
    assert(queue.deletionOperations()[0].safeReason == "server_update");
}

void testSelectionIsStoredAndSent() {
    const auto root = freshRoot("apply-meeting");
    auto queue = makeQueue(root, "queue");
    // The local copy already knows its meeting, so the request names the meeting:
    // that is the same request macOS would send, and it is one deletion, not two.
    assert(queue.enqueue(item(root, "local-one", "directory-one", std::string(kMeeting),
                              UploadQueueStatus::uploaded, 1)));

    std::vector<std::string> paths;
    std::vector<std::string> bodies;
    const auto plan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-one"}}, kOwner,
        [&](const DesktopUploadQueueService::DeletionRequestPlan& request) {
            paths.push_back(request.path);
            bodies.push_back(request.body);
            return DesktopUploadQueueService::DeletionWireResult{
                200, receiptBody("meeting_deletion", std::string(kMeeting)), false, 0, ""};
        });
    const auto outcome = queue.deletionSelectionOutcome(plan);
    assert(plan.saved && outcome.accepted == 1 && outcome.pending == 0 && outcome.rejected == 0);
    assert(paths.size() == 1 && paths[0] == "/api/v1/cabinet/meetings/" + std::string(kMeeting) + "/deletion-requests");
    assert(bodies[0].find("Delete this meeting everywhere GRAF controls.") != std::string::npos);
    assert(queue.deletionOperations().size() == 1);
    assert(queue.deletionOperations()[0].phase == DeletionOperationPhase::accepted);

    // Asking again is the same request, not a second deletion: the accepted
    // request is not sent a second time.
    paths.clear();
    const auto againPlan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-one"}}, kOwner,
        [&](const DesktopUploadQueueService::DeletionRequestPlan& request) {
            paths.push_back(request.path);
            return DesktopUploadQueueService::DeletionWireResult{};
        });
    const auto again = queue.deletionSelectionOutcome(againPlan);
    assert(againPlan.saved && again.accepted == 1 && paths.empty());
    assert(queue.deletionOperations().size() == 1);
}

void testOwnOriginRequestNamesTheCopy() {
    const auto root = freshRoot("apply-origin");
    auto queue = makeQueue(root, "queue");
    // An upload was attempted, so the server has heard of this recording; it has
    // no meeting yet, so the request names the copy the server knows by directory.
    assert(queue.enqueue(item(root, "local-two", "directory-two", "", UploadQueueStatus::retry, 2)));

    std::string seenPath;
    std::string seenBody;
    const auto plan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-two"}}, kOwner,
        [&](const DesktopUploadQueueService::DeletionRequestPlan& request) {
            seenPath = request.path;
            seenBody = request.body;
            // The answer names the meeting the server created while deleting, so
            // the row learns it instead of asking the server again.
            return DesktopUploadQueueService::DeletionWireResult{202,
                "{\"receipt_type\":\"origin_cancellation\",\"request_id\":\"" + std::string(kRequest) +
                "\",\"local_recording_id\":\"directory-two\",\"meeting_id\":\"" + std::string(kMeeting) +
                "\",\"phase\":\"accepted\"}", false, 0, ""};
        });
    const auto outcome = queue.deletionSelectionOutcome(plan);
    assert(plan.saved && outcome.accepted == 1);
    assert(seenPath == "/api/v1/desktop/recordings/directory-two/deletion-requests");
    assert(seenBody.find("\"operation_id\"") != std::string::npos);
    assert(seenBody.find(queue.deletionOperations()[0].operationId) != std::string::npos);
    assert(queue.items()[0].meetingId == kMeeting);
}

void testServerMayResolveTheCopyToItsMeeting() {
    const auto root = freshRoot("apply-resolved");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-twelve", "directory-twelve", "", UploadQueueStatus::retry, 1)));
    // The server answers a request about a local copy with the meeting it resolved
    // that copy to. That is a confirmation of this copy, and the row learns the
    // meeting from the same answer instead of asking for it again.
    const auto plan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-twelve"}}, kOwner,
        [&](const DesktopUploadQueueService::DeletionRequestPlan&) {
            return DesktopUploadQueueService::DeletionWireResult{200,
                "{\"receipt_type\":\"meeting_deletion\",\"request_id\":\"" + std::string(kRequest) +
                "\",\"local_recording_id\":\"directory-twelve\",\"meeting_id\":\"" + std::string(kMeeting) +
                "\",\"phase\":\"accepted\"}", false, 0, ""};
        });
    const auto outcome = queue.deletionSelectionOutcome(plan);
    assert(plan.saved && outcome.accepted == 1 && outcome.pending == 0);
    assert(queue.items()[0].meetingId == kMeeting);
}

void testUnreadableAnswerIsNotAnAnswer() {
    const auto root = freshRoot("apply-unreadable");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-three", "directory-three", "", UploadQueueStatus::retry, 1)));
    const auto plan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-three"}}, kOwner,
        [](const DesktopUploadQueueService::DeletionRequestPlan&) {
            // 200 with a body that names nothing is not a confirmation.
            return DesktopUploadQueueService::DeletionWireResult{200, "{}", false, 0, ""};
        });
    const auto outcome = queue.deletionSelectionOutcome(plan);
    assert(plan.saved && outcome.accepted == 0 && outcome.pending == 1 && outcome.rejected == 0);
    assert(queue.deletionOperations()[0].phase == DeletionOperationPhase::resolving);
    // The wait is a delay, not a give-up: the request is still there to retry.
    assert(queue.deletionOperations()[0].nextAttemptAtMs > nowMs);
}

void testRefusalIsFinalAndSharedFailureIsNot() {
    const auto root = freshRoot("apply-refusal");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-four", "directory-four", "", UploadQueueStatus::retry, 1)));
    assert(queue.enqueue(item(root, "local-five", "directory-five", "", UploadQueueStatus::retry, 1)));

    // A server that refuses this target and only this target: the answer is
    // final, and the other request is still asked.
    std::size_t calls = 0;
    const auto refusedPlan = runDeletionPass(queue,
        {{DeletionTarget::ownOrigin, "directory-four"}, {DeletionTarget::ownOrigin, "directory-five"}},
        kOwner, [](const DesktopUploadQueueService::DeletionRequestPlan&) {
            return DesktopUploadQueueService::DeletionWireResult{
                403, "{\"detail\":\"deletion_forbidden\"}", false, 0, ""};
        }, &calls);
    const auto refused = queue.deletionSelectionOutcome(refusedPlan);
    assert(refusedPlan.saved && refused.rejected == 2 && calls == 2);

    // A shared failure is different: one attempt is evidence about all of them.
    const auto root2 = freshRoot("apply-shared");
    auto second = makeQueue(root2, "queue");
    assert(second.enqueue(item(root2, "local-six", "directory-six", "", UploadQueueStatus::retry, 1)));
    assert(second.enqueue(item(root2, "local-seven", "directory-seven", "", UploadQueueStatus::retry, 1)));
    calls = 0;
    const auto failedPlan = runDeletionPass(second,
        {{DeletionTarget::ownOrigin, "directory-six"}, {DeletionTarget::ownOrigin, "directory-seven"}},
        kOwner, [&](const DesktopUploadQueueService::DeletionRequestPlan&) {
            return DesktopUploadQueueService::DeletionWireResult{503, "", true, 0, ""};
        }, &calls);
    const auto failed = second.deletionSelectionOutcome(failedPlan);
    assert(failedPlan.saved && failed.pending == 2 && failed.accepted == 0 && calls == 1);
}

void testRefusedBeforeTheWireIsNoAnswer() {
    const auto root = freshRoot("apply-local-refusal");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-eight", "directory-eight", "", UploadQueueStatus::retry, 1)));
    const auto plan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-eight"}}, kOwner,
        [](const DesktopUploadQueueService::DeletionRequestPlan&) {
            // Never sent: the request was refused here. That says nothing about the
            // recording, so it is not a refusal by the server.
            return DesktopUploadQueueService::DeletionWireResult{0, "", false, 0, "invalid_target"};
        });
    const auto outcome = queue.deletionSelectionOutcome(plan);
    assert(plan.saved && outcome.pending == 1 && outcome.rejected == 0);
    assert(queue.deletionOperations()[0].phase == DeletionOperationPhase::resolving);
}

void testRateLimitIsAWaitNotARejection() {
    const auto root = freshRoot("apply-rate");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-nine", "directory-nine", "", UploadQueueStatus::retry, 1)));
    const auto plan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-nine"}}, kOwner,
        [](const DesktopUploadQueueService::DeletionRequestPlan&) {
            return DesktopUploadQueueService::DeletionWireResult{429, "", false, 30, ""};
        });
    const auto outcome = queue.deletionSelectionOutcome(plan);
    assert(plan.saved && outcome.pending == 1 && outcome.rejected == 0);
    assert(queue.deletionOperations()[0].safeReason == "rate_limit");
    // The wait the server asked for is kept, not the client's own schedule.
    assert(queue.deletionOperations()[0].nextAttemptAtMs == nowMs + 30'000);
}

void testLocalCopyTheServerNeverSaw() {
    const auto root = freshRoot("apply-local-only");
    auto queue = makeQueue(root, "queue");
    // Recorded, queued, never sent: the server has nothing to delete, so there is
    // no request to store. The caller removes the copy and reports the result.
    assert(queue.enqueue(item(root, "local-ten", "directory-ten", "", UploadQueueStatus::pending, 0)));
    std::size_t calls = 0;
    const auto plan = runDeletionPass(queue, {{DeletionTarget::ownOrigin, "directory-ten"}}, kOwner,
        [&](const DesktopUploadQueueService::DeletionRequestPlan&) {
            ++calls;
            return DesktopUploadQueueService::DeletionWireResult{};
        }, &calls);
    const auto outcome = queue.deletionSelectionOutcome(plan);
    assert(plan.saved && plan.localOnly.size() == 1 && plan.localOnly[0] == "local-ten");
    assert(outcome.accepted == 0 && outcome.pending == 0);
    assert(calls == 0 && queue.deletionOperations().empty());
}

void testRequestHasToNameARealAccountAndServer() {
    const auto root = freshRoot("apply-scope");
    auto queue = makeQueue(root, "queue");
    assert(queue.enqueue(item(root, "local-eleven", "directory-eleven", "", UploadQueueStatus::retry, 1)));
    const std::vector<DesktopUploadQueueService::DeletionTargetRequest> selection{
        {DeletionTarget::ownOrigin, "directory-eleven"}};
    // An account that is not an account, or a server this client may not talk to,
    // is not a request that may be stored: it would name something the server
    // cannot resolve, and "сохранено" would be a promise nobody keeps.
    for (const auto owner : {DesktopAccountIdentity{"", std::string(kWorkspace)},
                             DesktopAccountIdentity{std::string(kActor), ""},
                             DesktopAccountIdentity{"not-an-account", std::string(kWorkspace)}}) {
        assert(!queue.planDeletionSelection(selection, owner, kOrigin).saved);
    }
    for (const auto origin : {std::string(""), std::string("graf.example.test"),
                              std::string("http://graf.example.test")}) {
        assert(!queue.planDeletionSelection(selection, kOwner, origin).saved);
    }
    // An unknown local copy is not a deletion this queue may make either.
    assert(!queue.planDeletionSelection({{DeletionTarget::ownOrigin, "directory-missing"}}, kOwner,
        kOrigin).saved);
    assert(queue.deletionOperations().empty());
}

} // namespace

int main() {
    testRequestIsDurable();
    testLocalOnlyDeletionIsPromisedOnlyWhenTheServerNeverHeardOfIt();
    testInterruptedLocalDeletionIsCarriedOut();
    testPurgeTaskNamesOnlyItsMeeting();
    testPurgeFailureIsRetriedNotFrozen();
    testPurgeRemovesOnlyFinishedCopies();
    testPurgeOfEveryCopyIsAcknowledged();
    testPurgeOfATypeThisClientCannotVerify();
    testPurgeAsksForTheTaskItsDeletionProved();
    testPurgeNeverRunsOnAQuarantinedLedger();
    testScopeIsolation();
    testPhaseTransitions();
    testTimeNeverGoesBackwards();
    testReceiptsMustMatch();
    testLedgerRoundTripAndLegacyUpgrade();
    testServerOriginValidation();
    testNothingIsSentBeforeTheServerDeclaresSupport();
    testSelectionIsStoredAndSent();
    testOwnOriginRequestNamesTheCopy();
    testServerMayResolveTheCopyToItsMeeting();
    testUnreadableAnswerIsNotAnAnswer();
    testRefusalIsFinalAndSharedFailureIsNot();
    testRefusedBeforeTheWireIsNoAnswer();
    testRateLimitIsAWaitNotARejection();
    testLocalCopyTheServerNeverSaw();
    testRequestHasToNameARealAccountAndServer();
    testItemTimestampsAdvance();

    return 0;
}
