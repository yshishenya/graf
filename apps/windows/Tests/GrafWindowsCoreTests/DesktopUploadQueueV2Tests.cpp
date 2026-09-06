#include "../../RecApp/Upload/DesktopUploadQueueService.h"
#include "../../RecApp/Storage/AtomicFileStore.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iterator>

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
    assert(queue.reconcile({"recording", true, true, {10, 20, 30}, false}));
    assert(queue.items()[0].status == UploadQueueStatus::uploading);
    assert(queue.items()[0].acceptedBytes[1] == 20);
    DesktopUploadQueueService restarted(path, root);
    assert(restarted.load());
    assert(restarted.items().size() == 1 && restarted.items()[0].acceptedBytes[2] == 30);
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
