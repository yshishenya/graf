#include "DesktopLocalPurgeService.h"

#include <system_error>
#include <utility>

#ifdef _WIN32
#include <windows.h>
#include <shellapi.h>
#include <shobjidl.h>
#include <wrl/client.h>
#include <wrl/implements.h>
#endif

namespace graf::windows {
namespace {
bool isLinkOrReparsePoint(const std::filesystem::path& path) {
    std::error_code error;
    const auto status = std::filesystem::symlink_status(path, error);
    if (error || std::filesystem::is_symlink(status)) return true;
#ifdef _WIN32
    const auto attributes = GetFileAttributesW(path.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES || (attributes & FILE_ATTRIBUTE_REPARSE_POINT)) return true;
#endif
    return !std::filesystem::is_regular_file(status) && !std::filesystem::is_directory(status);
}

#ifdef _WIN32
// SetOperationFlags expresses intent; each actual delete must still be a
// recycle operation. A failed PreDeleteItem cancels the pending operation.
class RecycleOnlySink final : public Microsoft::WRL::RuntimeClass<
    Microsoft::WRL::RuntimeClassFlags<Microsoft::WRL::ClassicCom>, IFileOperationProgressSink> {
public:
    bool recycled = false;
    bool failed = false;
    HRESULT STDMETHODCALLTYPE PreDeleteItem(DWORD flags, IShellItem*) override {
        if ((flags & TSF_DELETE_RECYCLE_IF_POSSIBLE) != 0) return S_OK;
        failed = true;
        return E_ABORT;
    }
    HRESULT STDMETHODCALLTYPE PostDeleteItem(DWORD, IShellItem*, HRESULT result, IShellItem* inRecycleBin) override {
        if (FAILED(result) || !inRecycleBin) { failed = true; return E_ABORT; }
        // The Shell contract supplies this item only for an actual Recycle Bin
        // destination; a permanently deleted item has no destination.
        recycled = true;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE StartOperations() override { return S_OK; }
    HRESULT STDMETHODCALLTYPE FinishOperations(HRESULT result) override {
        if (FAILED(result)) failed = true;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE PreRenameItem(DWORD, IShellItem*, LPCWSTR) override { return E_ABORT; }
    HRESULT STDMETHODCALLTYPE PostRenameItem(DWORD, IShellItem*, LPCWSTR, HRESULT, IShellItem*) override { return E_ABORT; }
    HRESULT STDMETHODCALLTYPE PreMoveItem(DWORD, IShellItem*, IShellItem*, LPCWSTR) override { return E_ABORT; }
    HRESULT STDMETHODCALLTYPE PostMoveItem(DWORD, IShellItem*, IShellItem*, LPCWSTR, HRESULT, IShellItem*) override { return E_ABORT; }
    HRESULT STDMETHODCALLTYPE PreCopyItem(DWORD, IShellItem*, IShellItem*, LPCWSTR) override { return E_ABORT; }
    HRESULT STDMETHODCALLTYPE PostCopyItem(DWORD, IShellItem*, IShellItem*, LPCWSTR, HRESULT, IShellItem*) override { return E_ABORT; }
    HRESULT STDMETHODCALLTYPE PreNewItem(DWORD, IShellItem*, LPCWSTR) override { return E_ABORT; }
    HRESULT STDMETHODCALLTYPE PostNewItem(DWORD, IShellItem*, LPCWSTR, LPCWSTR, DWORD, HRESULT, IShellItem*) override { return E_ABORT; }
    HRESULT STDMETHODCALLTYPE UpdateProgress(UINT, UINT) override { return S_OK; }
    HRESULT STDMETHODCALLTYPE ResetTimer() override { return S_OK; }
    HRESULT STDMETHODCALLTYPE PauseTimer() override { return S_OK; }
    HRESULT STDMETHODCALLTYPE ResumeTimer() override { return S_OK; }
};
#endif
} // namespace

DesktopLocalPurgeService::DesktopLocalPurgeService(std::filesystem::path custodyRoot)
    : custodyRoot_(std::move(custodyRoot)) {}

bool DesktopLocalPurgeService::isSafePackageDirectory(const std::filesystem::path& packageDirectory,
                                                     bool allowMissing) const {
    if (custodyRoot_.empty() || packageDirectory.empty()) return false;
    for (const auto& component : packageDirectory) if (component == "..") return false;
    std::error_code error;
    const auto root = std::filesystem::weakly_canonical(custodyRoot_, error);
    if (error || !std::filesystem::is_directory(root, error) || error) return false;
    error.clear();
    const auto target = std::filesystem::weakly_canonical(packageDirectory, error);
    if (error || target == root || target.parent_path() != root) return false;
    const auto parent = std::filesystem::weakly_canonical(packageDirectory.parent_path(), error);
    if (error || parent != root) return false;
    const auto status = std::filesystem::symlink_status(packageDirectory, error);
    if (status.type() == std::filesystem::file_type::not_found &&
        (!error || error == std::errc::no_such_file_or_directory)) return allowMissing;
    if (error || !std::filesystem::is_directory(status) || isLinkOrReparsePoint(packageDirectory)) return false;
    std::filesystem::recursive_directory_iterator it(packageDirectory, error), end;
    while (!error && it != end) {
        if (isLinkOrReparsePoint(it->path())) return false;
        it.increment(error);
    }
    return !error;
}

bool DesktopLocalPurgeService::recycle(const std::filesystem::path& packageDirectory, std::uintptr_t owner) {
#ifndef _WIN32
    (void)packageDirectory;
    (void)owner;
    return false;
#else
    // GRAF custody is local. Reject UNC/network/removable storage before Shell
    // execution rather than asking Windows to fall back when no bin is usable.
    if (!packageDirectory.is_absolute() || packageDirectory.root_name().native().size() != 2 ||
        !DesktopLocalPurgeService(packageDirectory.parent_path()).isSafePackageDirectory(packageDirectory)) return false;
    wchar_t volume[MAX_PATH]{};
    if (!GetVolumePathNameW(packageDirectory.c_str(), volume, MAX_PATH) || GetDriveTypeW(volume) != DRIVE_FIXED) return false;
    Microsoft::WRL::ComPtr<IFileOperation> operation;
    Microsoft::WRL::ComPtr<IShellItem> item;
    const auto sink = Microsoft::WRL::Make<RecycleOnlySink>();
    if (!sink || FAILED(CoCreateInstance(__uuidof(FileOperation), nullptr, CLSCTX_INPROC_SERVER,
            IID_PPV_ARGS(operation.GetAddressOf()))) ||
        FAILED(operation->SetOperationFlags(FOFX_RECYCLEONDELETE | FOF_ALLOWUNDO | FOF_NOCONFIRMATION |
            FOF_NOERRORUI | FOF_SILENT | FOFX_EARLYFAILURE)) ||
        FAILED(operation->SetOwnerWindow(reinterpret_cast<HWND>(owner))) ||
        FAILED(SHCreateItemFromParsingName(packageDirectory.c_str(), nullptr, IID_PPV_ARGS(item.GetAddressOf()))) ||
        FAILED(operation->DeleteItem(item.Get(), sink.Get())) || FAILED(operation->PerformOperations())) return false;
    BOOL aborted = TRUE;
    if (FAILED(operation->GetAnyOperationsAborted(&aborted)) || aborted || sink->failed || !sink->recycled) return false;
    std::error_code error;
    const auto status = std::filesystem::symlink_status(packageDirectory, error);
    return status.type() == std::filesystem::file_type::not_found &&
        (!error || error == std::errc::no_such_file_or_directory);
#endif
}

} // namespace graf::windows
