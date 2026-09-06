#include "../../RecApp/Upload/DesktopLocalPurgeService.h"
#include "../../RecApp/Upload/DesktopUploadQueueService.h"
#include "../../RecApp/Upload/DesktopUploadRecoveryScheduler.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>

#ifdef _WIN32
#include <windows.h>
#include <objbase.h>
#endif

namespace {
void testNativeRecycle(const std::filesystem::path& root) {
    using namespace graf::windows;
    const auto package = root / "native-recycle-fixture";
    std::filesystem::create_directories(package);
    std::ofstream(package / "synthetic.txt") << "synthetic fixture; no recording content";
#ifdef _WIN32
    const auto initialized = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    assert(SUCCEEDED(initialized));
    DesktopUploadQueueService queue(root / "native-queue.json", root);
    assert(queue.load());
    assert(queue.enqueue({"native-fixture", "directory", "session", package, UploadQueueStatus::pending, {}, 0, ""}));
    constexpr auto proof = LocalPurgeProof::userConfirmedLocalCopy;
    const auto recycle = [](const auto& path) { return DesktopLocalPurgeService::recycle(path, 0); };

    // No-delete sharing makes the real Shell operation fail. It must not lose
    // the copy or remove the durable row, even with confirmation/error UI off.
    const auto file = package / "synthetic.txt";
    HANDLE held = CreateFileW(file.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, 0, nullptr);
    assert(held != INVALID_HANDLE_VALUE);
    assert(queue.removeLocalCopy("native-fixture", proof, recycle) == LocalCopyRemovalResult::recycleFailed);
    assert(std::filesystem::exists(file));
    assert(queue.items().size() == 1 && queue.pendingItems(32).empty());
    assert(CloseHandle(held));

    // UNC storage must be refused before any operation, even if it names the
    // same synthetic source through a local administrative share.
    const auto unc = std::filesystem::path(L"\\\\localhost\\" + package.root_name().native().substr(0, 1) + L"$") /
        package.relative_path();
    assert(!DesktopLocalPurgeService::recycle(unc, 0));
    assert(std::filesystem::exists(file));

    // This is the production IFileOperation path, not the rename mock below.
    // Success requires PostDeleteItem's non-null Recycle Bin destination.
    assert(queue.removeLocalCopy("native-fixture", proof, recycle) == LocalCopyRemovalResult::removed);
    assert(!std::filesystem::exists(package) && queue.items().empty());
    DesktopUploadQueueService reopened(root / "native-queue.json", root);
    assert(reopened.load() && reopened.items().empty());
    CoUninitialize();
    // Leave only our tiny synthetic folder recoverable in the bin. Never empty
    // or enumerate the user's bin as test cleanup.
    std::cout << "native_recycle=passed; locked_source_preserved=passed; nonlocal_refused=passed\n";
#else
    assert(!DesktopLocalPurgeService::recycle(package, 0));
    assert(std::filesystem::exists(package / "synthetic.txt"));
#endif
}

void testLocalCopyRemoval(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root / "recycle-bin");
    DesktopUploadQueueService queue(root / "queue.json", root);
    assert(queue.load());
    const auto add = [&](const std::string& id, std::filesystem::path package = {}) {
        if (package.empty()) package = root / id;
        std::filesystem::create_directories(package);
        std::ofstream(package / "synthetic.txt") << "synthetic fixture";
        assert(queue.enqueue({id, id + "-directory", id + "-session", package,
                              UploadQueueStatus::pending, {}, 0, ""}));
    };
    const auto recycle = [&](const std::filesystem::path& path) {
        // A reversible rename models the caller-owned native Recycle Bin.
        assert(path.parent_path() == root);
        DesktopUploadQueueService durable(root / "queue.json", root);
        assert(durable.load());
        for (const auto& item : durable.items()) if (item.packageDirectory == path) {
            assert(item.status == UploadQueueStatus::quarantined && item.safeReason == "local_delete_pending");
        }
        std::filesystem::rename(path, root / "recycle-bin" / path.filename());
        return true;
    };
    constexpr auto consent = LocalPurgeProof::userConfirmedLocalCopy;
    add("success");
    assert(queue.removeLocalCopy("success", LocalPurgeProof::none, recycle) == LocalCopyRemovalResult::confirmationRequired);
    assert(queue.removeLocalCopy("unknown", consent, recycle) == LocalCopyRemovalResult::unknownRecording);
    assert(queue.removeLocalCopy("success", consent, recycle) == LocalCopyRemovalResult::removed);
    assert(queue.items().empty() && !std::filesystem::exists(root / "success"));
    assert(std::filesystem::exists(root / "recycle-bin" / "success" / "synthetic.txt"));
    DesktopUploadQueueService disk(root / "queue.json", root);
    assert(disk.load() && disk.items().empty());

    add("failed");
    assert(queue.removeLocalCopy("failed", consent, [](const auto&) { return false; }) == LocalCopyRemovalResult::recycleFailed);
    assert(queue.items()[0].status == UploadQueueStatus::quarantined && queue.pendingItems(32).empty());
    assert(disk.load() && disk.pendingItems(32).empty());
    // A callback claiming success without moving the files cannot forget the row.
    assert(queue.removeLocalCopy("failed", consent, [](const auto&) { return true; }) == LocalCopyRemovalResult::recycleFailed);
    assert(queue.removeLocalCopy("failed", consent, recycle) == LocalCopyRemovalResult::removed);

    add("nested", root / "container" / "package");
    assert(queue.removeLocalCopy("nested", consent, recycle) == LocalCopyRemovalResult::unsafePath);
    add("shared-a", root / "shared");
    add("shared-b", root / "shared");
    assert(queue.removeLocalCopy("shared-a", consent, recycle) == LocalCopyRemovalResult::unsafePath);

    add("post-write-failure");
    const auto ledger = root / "queue.json";
    const auto savedLedger = root / "saved-ledger.json";
    assert(queue.removeLocalCopy("post-write-failure", consent, [&](const auto& package) {
        assert(recycle(package));
        std::filesystem::rename(ledger, savedLedger);
        std::filesystem::create_directory(ledger); // deterministically fail atomic replacement
        return true;
    }) == LocalCopyRemovalResult::ledgerFailure);
    assert(queue.quarantined() && queue.pendingItems(32).empty() && !queue.nextPending());
    DesktopUploadRecoveryScheduler scheduler(queue);
    assert(!scheduler.startAsync(RecoveryTrigger::launch, DesktopHttpConfig{}));
    assert(std::filesystem::remove(ledger));
    std::filesystem::rename(savedLedger, ledger);
    assert(disk.load());
    const auto pending = disk.pendingItems(32);
    for (const auto& item : pending) assert(item.localRecordingId != "post-write-failure");
    // Relaunch after recycle/final-ledger-write failure can finish forgetting the
    // absent copy, using the persisted intent and no new delete operation.
    assert(disk.removeLocalCopy("post-write-failure", consent, [](const auto&) {
        assert(false && "already recycled; must not invoke deletion again");
        return false;
    }) == LocalCopyRemovalResult::removed);

    DesktopUploadQueueService failing(root / "failing.json", root);
    std::filesystem::create_directories(root / "untouched");
    assert(failing.enqueue({"untouched", "directory", "session", root / "untouched",
                            UploadQueueStatus::pending, {}, 0, ""}));
    std::filesystem::rename(root / "failing.json", root / "failing-backup.json");
    std::filesystem::create_directory(root / "failing.json");
    assert(failing.removeLocalCopy("untouched", consent, [](const auto&) {
        assert(false && "ledger intent failed; must not recycle");
        return true;
    }) == LocalCopyRemovalResult::ledgerFailure);
    assert(failing.quarantined() && std::filesystem::exists(root / "untouched"));
}
} // namespace

int main() {
    using namespace graf::windows;
    const auto root = std::filesystem::temp_directory_path() /
        ("graf-feature-200-custody-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    const auto directory = root / "package";
    std::filesystem::create_directories(directory);
    const DesktopLocalPurgeService custody(root);
    assert(custody.isSafePackageDirectory(directory));
    assert(!custody.isSafePackageDirectory({}));
    assert(!DesktopLocalPurgeService({}).isSafePackageDirectory(directory));
    assert(!custody.isSafePackageDirectory(root));
    assert(!custody.isSafePackageDirectory(root, true));
    assert(!custody.isSafePackageDirectory(std::filesystem::temp_directory_path()));
    assert(!custody.isSafePackageDirectory(directory / ".." / "package"));
    std::filesystem::create_directory(directory / "nested");
    assert(!custody.isSafePackageDirectory(directory / "nested"));
    assert(!custody.isSafePackageDirectory(directory / "missing", true));
    assert(!custody.isSafePackageDirectory(root / "missing"));
    assert(custody.isSafePackageDirectory(root / "missing", true));
    assert(!custody.isSafePackageDirectory(root.parent_path() / "missing", true));
    const auto file = root / "synthetic.txt";
    std::ofstream(file) << "synthetic fixture; not a package directory";
    assert(!custody.isSafePackageDirectory(file));
    assert(std::filesystem::exists(file) && std::filesystem::exists(directory / "nested"));
    testNativeRecycle(root / "native");
    testLocalCopyRemoval(root / "local-copies");
    std::error_code linkError;
    std::filesystem::create_directory_symlink(root / "local-copies", directory / "link", linkError);
#ifndef _WIN32
    assert(!linkError); // Portable validation must actually exercise symlinks.
#endif
    if (!linkError) {
        assert(!custody.isSafePackageDirectory(directory));
        assert(std::filesystem::exists(root / "local-copies" / "untouched"));
        std::filesystem::create_directory_symlink(root / "local-copies", root / "linked-package", linkError);
        assert(!linkError);
        assert(!custody.isSafePackageDirectory(root / "linked-package"));
    }
    std::filesystem::remove_all(root);
    return 0;
}
