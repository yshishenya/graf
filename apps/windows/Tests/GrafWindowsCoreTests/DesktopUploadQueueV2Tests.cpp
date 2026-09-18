#include "../../RecApp/Upload/DesktopUploadQueueService.h"
#include "../../RecApp/Storage/AtomicFileStore.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>

namespace {
void testOwners(const std::filesystem::path& root) {
    using namespace graf::windows;
    const DesktopAccountIdentity owner{
        "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"};
    const auto path = root / "owner-queue.json";
    DesktopUploadQueueService queue(path, root);
    assert(queue.load());
    assert(queue.enqueue({"legacy", "directory", "session", root / "recording", UploadQueueStatus::pending, {}, 0, ""}));
    const auto read = [&] {
        std::ifstream file(path, std::ios::binary);
        return std::string(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
    };
    auto legacy = read();
    const std::string emptyOwners = R"(,"owner_user_id":"","owner_workspace_id":"")";
    const auto at = legacy.find(emptyOwners);
    assert(at != std::string::npos);
    legacy.erase(at, emptyOwners.size());
    assert(AtomicFileStore::writeWithinRoot(root, path, legacy).ok());
    assert(queue.load());
    assert(queue.items()[0].ownerUserId.empty() && queue.items()[0].ownerWorkspaceId.empty());
    assert(!queue.assignOwner("absent", owner));
    assert(!queue.assignOwner("legacy", {}));
    assert(!queue.assignOwner("legacy", {owner.userId, "invalid"}));
    assert(queue.markNeedsAuth("legacy", "local_owner_unclaimed"));
    assert(queue.assignOwner("legacy", owner));
    assert(queue.items()[0].status == UploadQueueStatus::pending);
    assert(queue.load());
    assert(queue.items()[0].ownerUserId == owner.userId && queue.items()[0].ownerWorkspaceId == owner.workspaceId);
    assert(!queue.assignOwner("legacy", owner));
    assert(!queue.assignOwner("legacy", {owner.workspaceId, owner.userId}));
    assert(queue.markNeedsAuth("legacy", "account_mismatch"));
    assert(queue.requeueNeedsAuth());
    assert(queue.items()[0].ownerUserId == owner.userId);
    assert(queue.load() && queue.items()[0].ownerWorkspaceId == owner.workspaceId);
    assert(!queue.enqueue({"partial", "directory", "session", root / "recording", UploadQueueStatus::pending,
                           {}, 0, "", owner.userId, ""}));
    assert(queue.enqueue({"new", "directory", "session", root / "recording", UploadQueueStatus::pending,
                          {}, 0, "", owner.userId, owner.workspaceId}));
    assert(queue.load() && queue.items()[1].ownerUserId == owner.userId);

    // A malformed/partial/duplicate field is not a legacy row and cannot be claimed.
    for (const auto& suffix : {
        "\"owner_user_id\":\"" + owner.userId + "\"",
        "\"owner_user_id\":null,\"owner_workspace_id\":\"" + owner.workspaceId + "\"",
        "\"owner_user_id\":\"\",\"owner_workspace_id\":\"" + owner.workspaceId + "\"",
        "\"owner_user_id\":\"bad\",\"owner_workspace_id\":\"" + owner.workspaceId + "\"",
        "\"owner_user_id\":\"" + owner.userId + "\",\"owner_user_id\":\"\",\"owner_workspace_id\":\"\"",
        std::string(R"("owner_user_\u0069d":"","owner_workspace_id":"")")}) {
        auto malformed = legacy;
        malformed.insert(malformed.size() - 3, "," + suffix);
        assert(AtomicFileStore::writeWithinRoot(root, path, malformed).ok());
        DesktopUploadQueueService invalid(path, root);
        assert(!invalid.load() && invalid.quarantined());
        assert(!invalid.assignOwner("legacy", owner));
        assert(!invalid.load() && invalid.quarantined()); // Missing ledger + quarantine is not a fresh queue.
        assert(std::filesystem::remove(path.string() + ".quarantine"));
    }

    assert(AtomicFileStore::writeWithinRoot(root, path, legacy).ok());
    DesktopUploadQueueService failing(path, root);
    assert(failing.load());
    std::filesystem::rename(path, root / "owner-backup.json");
    std::filesystem::create_directory(path); // deterministic atomic replacement failure
    assert(!failing.assignOwner("legacy", owner));
    assert(failing.quarantined() && failing.pendingItems(32).empty());
    assert(failing.items()[0].ownerUserId.empty() && failing.items()[0].ownerWorkspaceId.empty());
    assert(!failing.assignOwner("legacy", owner));
    DesktopUploadQueueService saved(root / "owner-backup.json", root);
    assert(saved.load() && saved.items()[0].ownerUserId.empty());
}

void testRetryGuards(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root);
    const auto path = root / "queue.json";
    DesktopUploadQueueService queue(path, root);
    assert(queue.load());
    const DesktopAccountIdentity owner{
        "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"};
    for (const auto status : {UploadQueueStatus::uploaded, UploadQueueStatus::quarantined,
                              UploadQueueStatus::uploading, UploadQueueStatus::needsAuth}) {
        const auto id = "recording-" + std::to_string(static_cast<int>(status));
        assert(queue.enqueue({id, id, id, root / id, status, {11, 22, 33}, 8, "original",
            owner.userId, owner.workspaceId}));
        if (status != UploadQueueStatus::needsAuth) assert(!queue.requestRetry(id));
        else {
            assert(queue.requestRetry(id));
            assert(queue.items().back().attempts == 0 && queue.items().back().status == UploadQueueStatus::retry);
            assert((queue.items().back().acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}));
            assert(queue.items().back().ownerUserId == owner.userId && queue.items().back().ownerWorkspaceId == owner.workspaceId);
        }
    }
    assert(queue.enqueue({"unclaimed", "directory", "session", root / "unclaimed", UploadQueueStatus::pending, {}, 0, ""}));
    assert(!queue.requestRetry("unclaimed") && !queue.requestRetry("unknown"));
    assert(queue.items().back().ownerUserId.empty());
    assert(queue.enqueue({"overflow", "directory", "session", root / "overflow", UploadQueueStatus::retry,
        {}, std::numeric_limits<std::uint32_t>::max(), "transport_unavailable", owner.userId, owner.workspaceId}));
    assert(queue.markRetry("overflow", "retry_budget_exhausted"));
    assert(queue.items().back().attempts == std::numeric_limits<std::uint32_t>::max());
    assert(queue.enqueue({"failed-write", "directory", "session", root / "failed-write",
        UploadQueueStatus::needsAuth, {11, 22, 33}, 8, "auth_required", owner.userId, owner.workspaceId}));
    std::filesystem::rename(path, root / "backup.json");
    std::filesystem::create_directory(path);
    assert(!queue.requestRetry("failed-write") && queue.quarantined());
    assert(queue.pendingItems(32).empty());
    assert(queue.items().back().status == UploadQueueStatus::needsAuth && queue.items().back().attempts == 8);
    assert(queue.items().back().safeReason == "auth_required");
}

void testInterruptedValidation(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root / "custody");
    const auto path = root / "custody" / "queue.json";
    DesktopUploadQueueService queue(path, path.parent_path());
    assert(queue.load());
    assert(queue.enqueue({"interrupted", "directory", "session", path.parent_path() / "package",
        UploadQueueStatus::uploading, {11, 22, 33}, 3, ""}));
    std::string original;
    {
        std::ifstream input(path, std::ios::binary);
        original.assign(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    }
    const auto malformed = original + " trailing";
    assert(AtomicFileStore::writeWithinRoot(root, path, malformed).ok());
    assert(!queue.load() && queue.quarantined() && queue.pendingItems(32).empty());
    {
        std::ifstream input(path.string() + ".quarantine", std::ios::binary);
        const std::string quarantined(std::istreambuf_iterator<char>(input), {});
        assert(quarantined == malformed); // No partial normalization before full validation.
    }
    // Valid input but recovery cannot atomically write outside the custody root.
    const auto outsideLedger = root / "outside.json";
    assert(AtomicFileStore::writeWithinRoot(root, outsideLedger, original).ok());
    DesktopUploadQueueService cannotPersist(outsideLedger, path.parent_path());
    assert(!cannotPersist.load() && cannotPersist.quarantined() && cannotPersist.pendingItems(32).empty());

    assert(AtomicFileStore::writeWithinRoot(root, path, original).ok());
    assert(queue.load() && queue.items()[0].status == UploadQueueStatus::retry);
    assert(queue.items()[0].attempts == 3 && queue.items()[0].ownerUserId.empty());
    assert((queue.items()[0].acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}));
    assert(queue.items()[0].directoryId == "directory" && queue.items()[0].sessionId == "session");
}
void testUploadProgressPercent() {
    using namespace graf::windows;
    // Прогресс собирается из двух половин: принятые сервером байты по дорожкам и
    // вес дорожек локального пакета. Неизмеримый прогресс молчит, а не показывает
    // ноль процентов.
    UploadCustodyItem item;
    item.acceptedBytes = {0, 0, 0};
    const std::array<std::uint64_t, 3> bytes{100, 300, 600};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 0);
    item.acceptedBytes = {100, 300, 600};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 100);
    item.acceptedBytes = {50, 150, 300};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 50);
    // Сервер не может принять больше, чем дорожка весит: иначе прогресс
    // перескочил бы за сто процентов.
    item.acceptedBytes = {100, 300, 900};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 100);
    // Пакет ещё не прочитан: веса дорожек нулевые, и прогресс неизвестен.
    item.acceptedBytes = {10, 10, 10};
    assert(!DesktopUploadQueueService::uploadProgressPercent(item, std::array<std::uint64_t, 3>{}).has_value());
    // Часть дорожек уже принята, часть ещё нет.
    item.acceptedBytes = {100, 0, 0};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 10);
}
} // namespace

int main() {
    using namespace graf::windows;
    const auto root = std::filesystem::temp_directory_path() / "graf-feature-200-queue-root";
    const auto path = root / "desktop-upload-queue.json";
    const auto package = root / "recording";
    const auto outside = root.parent_path() / "graf-feature-200-queue-escape";
    std::filesystem::remove_all(root);
    std::filesystem::remove_all(outside);
    std::filesystem::create_directories(package);
    testOwners(root);
    testUploadProgressPercent();
    testRetryGuards(root / "retry-guards");
    testInterruptedValidation(root / "interrupted-validation");
    assert(AtomicFileStore::isWithinRoot(root, package));
    assert(!AtomicFileStore::isWithinRoot(root, root));
    assert(!AtomicFileStore::isWithinRoot(root, outside));
    assert(AtomicFileStore::writeWithinRoot(root, outside / "escape.json", "blocked").error ==
           AtomicFileError::invalidPath);
    DesktopUploadQueueService queue(path, root);
    assert(queue.load());
    assert(queue.enqueue({"recording", "directory", "session", package, UploadQueueStatus::pending, {}, 0, ""}));
    assert(!queue.enqueue({"escape", "directory", "session-escape", outside, UploadQueueStatus::pending, {}, 0, ""}));
    assert(!queue.enqueue({"recording", "directory", "session2", package, UploadQueueStatus::pending, {}, 0, ""}));
    assert(queue.reconcile({"recording", true, true, {10, 20, 30}, false, "meeting-id"}));
    assert(queue.items()[0].status == UploadQueueStatus::uploading);
    assert(queue.items()[0].acceptedBytes[1] == 20);
    // The cabinet binds a local row to its server meeting by this id, so it has
    // to survive a restart instead of being relearned from the network.
    assert(queue.items()[0].meetingId == "meeting-id");
    // A later server response must not overwrite the binding, and an unusable
    // id must not reach the ledger.
    assert(queue.reconcile({"recording", true, true, {10, 20, 30}, false, "other-id"}));
    assert(queue.items()[0].meetingId == "meeting-id");
    assert(queue.reconcile({"recording", true, true, {10, 20, 30}, false, "not a safe id"}));
    assert(queue.items()[0].meetingId == "meeting-id");
    // The rest of the server's fingerprint is written with the row and read back
    // after a restart: which revision the server accepted, which session carries
    // it and how far the meeting and its processing have come. macOS keeps the
    // same values in its queue row.
    {
        graf::windows::UploadServerTruth truth;
        truth.localRecordingId = "recording";
        truth.meetingExists = true;
        truth.uploadSessionExists = true;
        truth.acceptedBytes = {10, 20, 30};
        truth.meetingId = "meeting-id";
        truth.mediaRevisionId = "11111111-2222-3333-4444-555555555555";
        truth.uploadSessionId = "66666666-7777-8888-9999-000000000000";
        truth.serverStatus = "ingested_pending_processing";
        truth.processingStatus = "queued";
        truth.mediaRevisionStatus = "uploaded";
        assert(queue.reconcile(truth));
    }
    // A value the ledger may not hold is refused instead of being written; the
    // values already stored stay untouched.
    {
        graf::windows::UploadServerTruth truth;
        truth.localRecordingId = "recording";
        truth.meetingExists = true;
        truth.uploadSessionExists = true;
        truth.acceptedBytes = {10, 20, 30};
        truth.meetingId = "meeting-id";
        truth.mediaRevisionId = "not a safe id";
        truth.serverStatus = "Not A Safe Status";
        assert(queue.reconcile(truth));
        assert(queue.items()[0].mediaRevisionId == "11111111-2222-3333-4444-555555555555");
        assert(queue.items()[0].serverStatus == "ingested_pending_processing");
    }
    DesktopUploadQueueService restarted(path, root);
    assert(restarted.load());
    assert(restarted.items().size() == 1 && restarted.items()[0].acceptedBytes[2] == 30);
    assert(restarted.items()[0].status == UploadQueueStatus::retry);
    assert(restarted.items()[0].meetingId == "meeting-id");
    assert(restarted.items()[0].mediaRevisionId == "11111111-2222-3333-4444-555555555555");
    assert(restarted.items()[0].uploadSessionId == "66666666-7777-8888-9999-000000000000");
    assert(restarted.items()[0].serverStatus == "ingested_pending_processing");
    assert(restarted.items()[0].processingStatus == "queued");
    assert(restarted.items()[0].mediaRevisionStatus == "uploaded");
    assert(restarted.pendingItems(32).size() == 1 && restarted.nextPending());
    assert(restarted.load() && restarted.items()[0].status == UploadQueueStatus::retry);
    assert(queue.markUploaded("recording"));
    assert(!queue.nextPending().has_value());
    std::filesystem::remove(path);
    {
        std::ofstream malformed(path, std::ios::binary);
        malformed << "{\"schema_version\":\"desktop-upload-queue.v2\",\"items\":[{\"local_recording_id\":\"broken\"";
    }
    DesktopUploadQueueService quarantined(path, root);
    assert(!quarantined.load() && quarantined.quarantined() && quarantined.items().empty());
    assert(std::filesystem::exists(path.string() + ".quarantine"));
    std::filesystem::remove(path.string() + ".quarantine");
    {
        std::ofstream malformedNumber(path, std::ios::binary);
        malformedNumber << "{\"schema_version\":\"desktop-upload-queue.v2\",\"items\":[{\"local_recording_id\":\"bad\",\"directory_id\":\"directory\",\"session_id\":\"session\",\"package_directory\":\"" << package.string() << "\",\"status\":1x,\"accepted_bytes\":[0,0,0],\"attempts\":0,\"safe_reason\":\"\"}]}";
    }
    DesktopUploadQueueService malformedNumberQueue(path, root);
    assert(!malformedNumberQueue.load() && malformedNumberQueue.quarantined());
    std::filesystem::remove_all(root);
    std::filesystem::remove_all(outside);
    return 0;
}
