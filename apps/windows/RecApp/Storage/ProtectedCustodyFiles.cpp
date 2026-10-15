#include "ProtectedCustodyFiles.h"
#include "ProtectedPackedCustodyOwner.h"
#include "ProtectedCustodyPrimitives.h"
#include "../Upload/DesktopUploadQueueService.h"
#include <algorithm>
#include <limits>
#include <new>
#include <cstring>
#include <utility>
#include <mutex>
#ifdef _WIN32
#include <windows.h>
#include <aclapi.h>
#include <sddl.h>
#include <bcrypt.h>
#include <winternl.h>
#endif

namespace graf::windows {
namespace {
template<class T> CustodyFileResult<T> failure(CustodyFileError error, std::uint32_t native = 0) {
    return {std::nullopt, error, native};
}
template<class T> CustodyFileResult<T> success(T value) { return {std::move(value), CustodyFileError::none, 0}; }
#ifdef _WIN32
struct Handle {
    HANDLE value = INVALID_HANDLE_VALUE;
    Handle() = default;
    explicit Handle(HANDLE h) : value(h) {}
    Handle(Handle&& other) noexcept : value(std::exchange(other.value, INVALID_HANDLE_VALUE)) {}
    Handle& operator=(Handle&& other) noexcept {
        if (this != &other) { close(); value = std::exchange(other.value, INVALID_HANDLE_VALUE); }
        return *this;
    }
    Handle(const Handle&) = delete;
    ~Handle() { close(); }
    void close() { if (valid()) CloseHandle(std::exchange(value, INVALID_HANDLE_VALUE)); }
    bool valid() const { return value != INVALID_HANDLE_VALUE && value != nullptr; }
};
struct LocalMemory {
    void* value = nullptr;
    ~LocalMemory() { if (value) LocalFree(value); }
};
struct WipePlain {
    CustodyBytes& bytes;
    ~WipePlain() { if (!bytes.empty()) SecureZeroMemory(bytes.data(), bytes.size()); }
};
bool localPath(const std::filesystem::path& path) {
    const auto& text = path.native();
    if (text.size() < 4 || text.size() > 30000 || text[1] != L':' || text[2] != L'\\'
        || !((text[0] >= L'A' && text[0] <= L'Z') || (text[0] >= L'a' && text[0] <= L'z'))
        || text.find(L'\0') != std::wstring::npos || text.find(L'/') != std::wstring::npos
        || text.find(L':', 2) != std::wstring::npos || text.back() == L'\\') return false;
    for (std::size_t start = 3; start < text.size();) {
        auto end = text.find(L'\\', start);
        if (end == std::wstring::npos) end = text.size();
        const std::wstring_view name(text.data() + start, end - start);
        if (!name.empty() && (name == L"." || name == L".." || name.back() == L'.' || name.back() == L' ')) return false;
        start = end + 1;
    }
    const wchar_t drive[]{text[0], L':', L'\\', L'\0'};
    DWORD flags = 0;
    return GetDriveTypeW(drive) == DRIVE_FIXED
        && GetVolumeInformationW(drive, nullptr, 0, nullptr, nullptr, &flags, nullptr, 0)
        && (flags & FILE_PERSISTENT_ACLS) != 0;
}
// API spelling only, after fixed-drive/normalized-path admission. Keep stored
// paths and handle identity checks unchanged; never accept a caller namespace.
CustodyWideString win32Path(const std::filesystem::path& path) {
    CustodyWideString result(L"\\\\?\\");
    result.append(path.native().data(), path.native().size());
    return result;
}
const wchar_t* roleName(CustodyRole role) {
    switch (role) {
    case CustodyRole::canonical: return L"canonical";
    case CustodyRole::media: return L"media";
    case CustodyRole::playback: return L"playback";
    case CustodyRole::manifest: return L"manifest";
    case CustodyRole::recovery: return L"recovery";
    case CustodyRole::queue: return L"queue";
    case CustodyRole::packageState: return L"package-state";
    case CustodyRole::bootstrap: return L"bootstrap";
    case CustodyRole::migrationIntent: return L"migration-intent";
    }
    return nullptr;
}
std::wstring blockName(std::uint64_t position, std::uint64_t version) {
    std::wstring name(L"block.");
    name += std::to_wstring(position);
    name += L".";
    name += std::to_wstring(version);
    return std::wstring(name);
}
std::wstring indexName(std::uint32_t slot) {
    std::wstring name(L"index.");
    name += std::to_wstring(slot);
    return std::wstring(name);
}
using RenameFile = NTSTATUS (NTAPI*)(HANDLE, PIO_STATUS_BLOCK, PVOID, ULONG, FILE_INFORMATION_CLASS);
// Documented FileRenameInformation=10; the user-mode SDK's partial enum omits it.
constexpr auto nativeRenameInformation = static_cast<FILE_INFORMATION_CLASS>(10);
// Native rename record, used only as an API argument, never as persisted bytes.
struct RenameInfo { BOOLEAN replace; HANDLE root; ULONG nameBytes; WCHAR name[1]; };
#endif
}

struct ProtectedCustodyFiles::State {
    CustodyContext context{};
    bool writable = false;
    bool failed = false;
    bool storeBirth = false;
    std::shared_ptr<const ProtectedCustodyFiles> rootLease;
    std::shared_ptr<const std::atomic<bool>> cancellation;
    mutable std::mutex writeGroup;
    mutable std::atomic<unsigned> pressurePercent{0};
#ifdef _WIN32
    std::filesystem::path directory;
    std::vector<std::uint8_t> tokenUser;
    LocalMemory descriptor;
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, FALSE};
    struct Directory {
        std::filesystem::path path; bool privateDirectory; Handle handle;
        Directory() = default;
        Directory(const std::filesystem::path& p, bool privateDir, Handle&& h)
            : path(p), privateDirectory(privateDir), handle(std::move(h)) {}
        Directory(Directory&& other)
            : Directory(other.path, other.privateDirectory, std::move(other.handle)) {}
    };
    std::vector<Directory> directories;
    std::filesystem::path trustedRoot;
    Handle storeId;
    Handle objectId;

    explicit State(const std::filesystem::path& root)
        : directory(root), tokenUser(std::size_t{0}), directories(std::size_t{0}), trustedRoot(root) {}

    const State& storeState() const noexcept { return rootLease ? rootLease->state_->storeState() : *this; }

    CustodyFileResult<std::uint64_t> physicalBytes(const std::filesystem::path& parent,
        const std::shared_ptr<const std::atomic<bool>>& cancel, unsigned depth = 0) const {
        if (depth > 8) return failure<std::uint64_t>(CustodyFileError::unsafePath);
        std::uint64_t total = 0;
        auto checked = eachChild(parent, cancel, [&](std::wstring_view name, bool directoryEntry) {
            auto child = parent;
            child /= std::filesystem::path(name);
            std::uint64_t bytes = 0;
            if (directoryEntry) {
                const auto apiPath = win32Path(child);
                Handle handle(CreateFileW(apiPath.c_str(), READ_CONTROL | FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY,
                    FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
                if (!handle.valid()) return failure<bool>(CustodyFileError::ioFailed, GetLastError());
                if (!inspect(handle.value, child, true, true)) return failure<bool>(CustodyFileError::unsafePath);
                auto nested = physicalBytes(child, cancel, depth + 1);
                if (!nested.ok()) return failure<bool>(nested.error, nested.nativeError);
                bytes = *nested.value;
            } else {
                auto file = openFile(child, FILE_READ_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE);
                if (!file.ok()) return failure<bool>(file.error, file.nativeError);
                FILE_STANDARD_INFO info{};
                if (!GetFileInformationByHandleEx(file.value->value, FileStandardInfo, &info, sizeof(info)))
                    return failure<bool>(CustodyFileError::ioFailed, GetLastError());
                if (info.AllocationSize.QuadPart < 0) return failure<bool>(CustodyFileError::invalidContent);
                bytes = static_cast<std::uint64_t>(info.AllocationSize.QuadPart);
            }
            if (bytes > (std::numeric_limits<std::uint64_t>::max)() - total)
                return failure<bool>(CustodyFileError::invalidContent);
            total += bytes;
            return success(true);
        });
        return checked.ok() ? success(total) : failure<std::uint64_t>(checked.error, checked.nativeError);
    }

    PSID sid() const { return reinterpret_cast<const TOKEN_USER*>(tokenUser.data())->User.Sid; }
    bool initializeSecurity() {
        Handle token;
        if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token.value)) return false;
        DWORD size = 0; GetTokenInformation(token.value, TokenUser, nullptr, 0, &size);
        if (size == 0 || size > 64 * 1024) return false;
        tokenUser.resize(size);
        if (!GetTokenInformation(token.value, TokenUser, tokenUser.data(), size, &size)) return false;
        LocalMemory text;
        if (!ConvertSidToStringSidW(sid(), reinterpret_cast<LPWSTR*>(&text.value))) return false;
        std::wstring sddl(L"D:P(A;OICI;FA;;;");
        sddl += static_cast<wchar_t*>(text.value);
        sddl += L")";
        if (!ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(), SDDL_REVISION_1,
            &descriptor.value, nullptr)) return false;
        security.lpSecurityDescriptor = descriptor.value;
        return true;
    }
    bool privateAcl(HANDLE file) const {
        PACL acl = nullptr; LocalMemory sd;
        if (GetSecurityInfo(file, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION, nullptr, nullptr,
            &acl, nullptr, &sd.value) != ERROR_SUCCESS || !acl || acl->AceCount != 1) return false;
        SECURITY_DESCRIPTOR_CONTROL control{}; DWORD revision = 0;
        if (!GetSecurityDescriptorControl(sd.value, &control, &revision) || !(control & SE_DACL_PROTECTED)) return false;
        void* raw = nullptr;
        if (!GetAce(acl, 0, &raw)) return false;
        const auto* ace = static_cast<const ACCESS_ALLOWED_ACE*>(raw);
        return ace->Header.AceType == ACCESS_ALLOWED_ACE_TYPE && !(ace->Header.AceFlags & INHERIT_ONLY_ACE)
            && ace->Mask == FILE_ALL_ACCESS && EqualSid(const_cast<DWORD*>(&ace->SidStart), sid());
    }
    bool inspect(HANDLE file, const std::filesystem::path& expected, bool directoryFile, bool privateFile) const {
        BY_HANDLE_FILE_INFORMATION info{};
        if (GetFileType(file) != FILE_TYPE_DISK || !GetFileInformationByHandle(file, &info)
            || (info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)
            || ((info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0) != directoryFile
            || (!directoryFile && info.nNumberOfLinks != 1)) return false;
        wchar_t actual[32768]{};
        const auto count = GetFinalPathNameByHandleW(file, actual, 32768, FILE_NAME_NORMALIZED | VOLUME_NAME_DOS);
        std::wstring wanted(L"\\\\?\\");
        const auto expectedText = expected.wstring();
        wanted += expectedText;
        return count > 0 && count < 32768 && wanted.size() <= static_cast<std::size_t>(std::numeric_limits<int>::max())
            && CompareStringOrdinal(actual, static_cast<int>(count), wanted.c_str(), static_cast<int>(wanted.size()), TRUE) == CSTR_EQUAL
            && (!privateFile || privateAcl(file));
    }
    CustodyFileResult<Handle> openFile(const std::filesystem::path& path, DWORD access, DWORD share) const {
        const auto apiPath = win32Path(path);
        Handle file(CreateFileW(apiPath.c_str(), access | READ_CONTROL, share, nullptr, OPEN_EXISTING,
            FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (!file.valid()) return failure<Handle>(CustodyFileError::ioFailed, GetLastError());
        if (!inspect(file.value, path, false, true)) return failure<Handle>(CustodyFileError::unsafeFile);
        return success(std::move(file));
    }
    CustodyFileResult<bool> lockDirectory(const std::filesystem::path& path, bool privateDirectory, bool create) {
        const auto apiPath = win32Path(path);
        if (create && !CreateDirectoryW(apiPath.c_str(), &security) && GetLastError() != ERROR_ALREADY_EXISTS)
            return failure<bool>(CustodyFileError::ioFailed, GetLastError());
        // Hold every ancestor without share-write/delete until the object closes.
        // Checking only the final path before opening leaves reparse/rename races.
        // FILE_LIST_DIRECTORY participates in sharing checks. Attribute/control
        // access alone does NOT acquire the share-write/delete exclusion.
        Handle dir(CreateFileW(apiPath.c_str(), READ_CONTROL | FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY, FILE_SHARE_READ, nullptr,
            OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (!dir.valid()) return failure<bool>(CustodyFileError::ioFailed, GetLastError());
        if (!inspect(dir.value, path, true, privateDirectory)) return failure<bool>(CustodyFileError::unsafePath);
        directories.emplace_back(path, privateDirectory, std::move(dir)); return success(true);
    }
    CustodyFileResult<bool> identityValue(HANDLE file, const CustodyId* expected, CustodyId& observed) const {
        LARGE_INTEGER size{}; DWORD got = 0; CustodyId actual{};
        if (!GetFileSizeEx(file, &size)) return failure<bool>(CustodyFileError::ioFailed, GetLastError());
        if (size.QuadPart != 16) return failure<bool>(CustodyFileError::identityMismatch);
        LARGE_INTEGER start{};
        if (!SetFilePointerEx(file, start, nullptr, FILE_BEGIN) || !ReadFile(file, actual.data(), 16, &got, nullptr))
            return failure<bool>(CustodyFileError::ioFailed, GetLastError());
        if (got != 16 || (expected && actual != *expected))
            return failure<bool>(CustodyFileError::identityMismatch);
        observed = actual; return success(true);
    }
    CustodyFileResult<bool> identity(Handle& file, const std::filesystem::path& path,
        const CustodyId* expected, CustodyId& observed, bool writer, bool immutable = false) {
        auto opened = openFile(path, GENERIC_READ | (writer ? GENERIC_WRITE : 0),
            FILE_SHARE_READ | (writer || immutable ? 0 : FILE_SHARE_WRITE));
        if (!opened.ok()) return failure<bool>(opened.error, opened.nativeError);
        auto checked = identityValue(opened.value->value, expected, observed);
        if (!checked.ok()) return checked;
        file = std::move(*opened.value); return success(true);
    }
    CustodyFileResult<bool> lockRoot(bool createMissing) {
        auto path = trustedRoot.root_path();
        auto locked = lockDirectory(path, false, false);
        if (!locked.ok()) return locked;
        const std::wstring_view names(trustedRoot.native());
        // Empty components change spelling under ordinary Win32 normalization
        // and are invalid in the extended namespace. Reject before child IO.
        if (names.find(L"\\\\", 2) != std::wstring_view::npos)
            return failure<bool>(CustodyFileError::unsafePath);
        for (std::size_t start = 3; start < names.size();) {
            auto end = names.find(L'\\', start);
            if (end == std::wstring_view::npos) end = names.size();
            if (end != start) {
                const std::filesystem::path part(names.substr(start, end - start));
                path /= part;
                bool created = false;
                if (createMissing) {
                    const auto apiPath = win32Path(path);
                    created = CreateDirectoryW(apiPath.c_str(), &security) != FALSE;
                    if (!created && GetLastError() != ERROR_ALREADY_EXISTS)
                        return failure<bool>(CustodyFileError::ioFailed, GetLastError());
                }
                locked = lockDirectory(path, created || path == trustedRoot, false);
                if (!locked.ok()) return locked;
            }
            start = end + 1;
        }
        return success(true);
    }
    CustodyFileResult<bool> openRole(CustodyFileAccess access, bool discover) {
        directory /= roleName(context.role);
        const auto apiPath = win32Path(directory);
        if (access == CustodyFileAccess::createNew && !CreateDirectoryW(apiPath.c_str(), &security)) {
            const auto error = GetLastError();
            return failure<bool>(error == ERROR_ALREADY_EXISTS ? CustodyFileError::conflict : CustodyFileError::ioFailed, error);
        }
        auto locked = lockDirectory(directory, true, false);
        if (!locked.ok()) return locked;
        std::filesystem::path idPath(directory);
        idPath /= L"id.bin";
        if (access == CustodyFileAccess::createNew) {
            auto created = create(idPath, context.objectId.data(), 16);
            if (!created.ok()) return failure<bool>(created.error, created.nativeError);
            // Keep the original CREATE_NEW handle: no close/reopen identity gap.
            objectId = std::move(*created.value);
            return identityValue(objectId.value, &context.objectId, context.objectId);
        }
        return identity(objectId, idPath, discover ? nullptr : &context.objectId, context.objectId, writable);
    }
    template<class Visit>
    CustodyFileResult<bool> eachChild(const std::filesystem::path& parent,
        const std::shared_ptr<const std::atomic<bool>>& cancel, Visit visit) const {
        if (cancel->load()) return failure<bool>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        auto pattern = parent;
        pattern /= L"*";
        const auto apiPath = win32Path(pattern);
        WIN32_FIND_DATAW data{};
        struct Find {
            HANDLE value;
            ~Find() { if (value != INVALID_HANDLE_VALUE) FindClose(value); }
        } find{FindFirstFileExW(apiPath.c_str(), FindExInfoBasic, &data, FindExSearchNameMatch, nullptr, 0)};
        if (find.value == INVALID_HANDLE_VALUE) {
            const auto error = GetLastError();
            return error == ERROR_FILE_NOT_FOUND ? success(true) : failure<bool>(CustodyFileError::ioFailed, error);
        }
        do {
            if (cancel->load()) return failure<bool>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            const std::wstring_view name(data.cFileName);
            if (name == L"." || name == L"..") continue;
            if (data.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT) return failure<bool>(CustodyFileError::unsafePath);
            const bool isDirectory = (data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
            auto accepted = visit(name, isDirectory);
            if (!accepted.ok()) return accepted;
        } while (FindNextFileW(find.value, &data));
        const auto error = GetLastError();
        return error == ERROR_NO_MORE_FILES ? success(true) : failure<bool>(CustodyFileError::ioFailed, error);
    }
    CustodyFileResult<Handle> create(const std::filesystem::path& path, const std::uint8_t* bytes,
                                    std::uint32_t size, bool renameable = false) const {
        const auto apiPath = win32Path(path);
        Handle file(CreateFileW(apiPath.c_str(), GENERIC_READ | GENERIC_WRITE | READ_CONTROL | (renameable ? DELETE : 0),
            FILE_SHARE_READ, const_cast<SECURITY_ATTRIBUTES*>(&security), CREATE_NEW,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (!file.valid()) {
            const auto error = GetLastError();
            return failure<Handle>((error == ERROR_FILE_EXISTS || error == ERROR_ALREADY_EXISTS)
                ? CustodyFileError::conflict : CustodyFileError::ioFailed, error);
        }
        // Private ACL and actual handle/path must be proven BEFORE the first write.
        if (!inspect(file.value, path, false, true)) return failure<Handle>(CustodyFileError::unsafeFile);
        std::uint32_t offset = 0;
        while (offset < size) {
            DWORD written = 0;
            const auto chunk = std::min<std::uint32_t>(size - offset, ProtectedCustodyCodec::blockBytes);
            if (!WriteFile(file.value, bytes + offset, chunk, &written, nullptr))
                return failure<Handle>(CustodyFileError::ioFailed, GetLastError());
            if (written == 0 || written > chunk) return failure<Handle>(CustodyFileError::ioFailed, ERROR_WRITE_FAULT);
            offset += written;
        }
        if (!FlushFileBuffers(file.value)) return failure<Handle>(CustodyFileError::ioFailed, GetLastError());
        return success(std::move(file));
    }
    CustodyFileResult<CustodyBytes> read(const std::filesystem::path& path, std::size_t limit, std::uint32_t exact = 0) const {
        auto file = openFile(path, GENERIC_READ, FILE_SHARE_READ); // No concurrent mutation/delete during the read.
        if (!file.ok()) return failure<CustodyBytes>(file.error, file.nativeError);
        LARGE_INTEGER size{};
        if (!GetFileSizeEx(file.value->value, &size)) return failure<CustodyBytes>(CustodyFileError::ioFailed, GetLastError());
        if (size.QuadPart < 16 || static_cast<std::uint64_t>(size.QuadPart) > limit
            || (exact != 0 && static_cast<std::uint64_t>(size.QuadPart) != exact))
            return failure<CustodyBytes>(CustodyFileError::invalidContent);
        CustodyBytes bytes(static_cast<std::size_t>(size.QuadPart));
        std::size_t offset = 0;
        while (offset < bytes.size()) {
            DWORD got = 0;
            const auto chunk = static_cast<DWORD>(std::min<std::size_t>(bytes.size() - offset, ProtectedCustodyCodec::blockBytes));
            if (!ReadFile(file.value->value, bytes.data() + offset, chunk, &got, nullptr))
                return failure<CustodyBytes>(CustodyFileError::ioFailed, GetLastError());
            if (got == 0 || got > chunk) return failure<CustodyBytes>(CustodyFileError::invalidContent);
            offset += got;
        }
        return success(std::move(bytes));
    }
#endif
};

ProtectedCustodyFiles::ProtectedCustodyFiles(std::unique_ptr<State> state) : state_(std::move(state)) {}
ProtectedCustodyFiles::~ProtectedCustodyFiles() = default;
const CustodyContext& ProtectedCustodyFiles::context() const noexcept { return state_->context; }
#ifdef _WIN32
const std::filesystem::path& ProtectedCustodyFiles::trustedRoot() const noexcept { return state_->trustedRoot; }
std::filesystem::path ProtectedCustodyFiles::packagePath() const { return state_->directory.parent_path(); }
#endif

CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::open(
    const std::filesystem::path& root, std::string_view package, const CustodyContext& context, CustodyFileAccess access) {
    return openImpl(root, package, context, access, false);
}
CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::discover(
    const std::filesystem::path& root, CustodyRole role, std::string_view package) {
    if ((role != CustodyRole::bootstrap && role != CustodyRole::queue && role != CustodyRole::migrationIntent)
        || (role != CustodyRole::migrationIntent && !package.empty()))
        return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::invalidInput);
    CustodyContext context{}; context.role = role;
    return openImpl(root, package, context, CustodyFileAccess::writeExisting, true);
}
CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::openImpl(
    const std::filesystem::path& root, std::string_view package, const CustodyContext& context,
    CustodyFileAccess access, bool discover) try {
    using Result = std::unique_ptr<ProtectedCustodyFiles>;
#ifndef _WIN32
    (void)root; (void)package; (void)context; (void)access; (void)discover;
    return failure<Result>(CustodyFileError::unsupportedPlatform);
#else
    const bool service = context.role == CustodyRole::queue || context.role == CustodyRole::bootstrap
        || (context.role == CustodyRole::migrationIntent && package.empty());
    if (!roleName(context.role) || (service ? !package.empty() : !DesktopUploadQueueService::validIdentity(package))
        || (access != CustodyFileAccess::readExisting && access != CustodyFileAccess::writeExisting && access != CustodyFileAccess::createNew))
        return failure<Result>(CustodyFileError::invalidInput);
    if (!service && !std::all_of(package.begin(), package.end(), [](unsigned char c) {
        return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
            || (c >= '0' && c <= '9') || c == '_' || c == '-';
    })) return failure<Result>(CustodyFileError::invalidInput);
    if (!localPath(root)) return failure<Result>(CustodyFileError::unsafePath);
    auto state = std::make_unique<State>(root); state->context = context;
    state->writable = access != CustodyFileAccess::readExisting;
    if (!state->initializeSecurity()) return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    auto locked = state->lockRoot(false);
    if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    auto path = root;
    path /= L".custody-v1";
    locked = state->lockDirectory(path, true, false);
    if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    std::filesystem::path storePath(path);
    storePath /= L"store.id";
    auto identified = state->identity(state->storeId, storePath,
        discover ? nullptr : &context.storeId, state->context.storeId, false, discover);
    if (!identified.ok()) return failure<Result>(identified.error, identified.nativeError);
    if (!service) {
        path = root;
        const std::wstring packageName(package.begin(), package.end());
        path /= packageName;
        locked = state->lockDirectory(path, true, false);
        if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
        path /= L".custody-v1";
        locked = state->lockDirectory(path, true, access == CustodyFileAccess::createNew);
        if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    }
    state->directory = path;
    locked = state->openRole(access, discover);
    if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    if (discover) state->writable = false; // Keep exclusive IDs, but allow readonly validation without resetting failures.
    return success(Result(new ProtectedCustodyFiles(std::move(state))));
#endif
} catch (const std::bad_alloc&) {
    return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::allocationFailed);
} catch (const std::filesystem::filesystem_error&) {
    return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::unsafePath);
}

CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::lockStoreRoot(
    const std::filesystem::path& root, std::shared_ptr<const std::atomic<bool>> cancellation,
    bool& birth) try {
    using Result = std::unique_ptr<ProtectedCustodyFiles>;
    birth = false;
    if (!cancellation) return failure<Result>(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)root;
    return failure<Result>(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    if (!localPath(root)) return failure<Result>(CustodyFileError::unsafePath);
    auto state = std::make_unique<State>(root);
    state->cancellation = cancellation;
    if (!state->initializeSecurity()) return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    auto locked = state->lockRoot(true);
    if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    Result held(new ProtectedCustodyFiles(std::move(state)));
    auto custody = root;
    custody /= L".custody-v1";
    const auto apiCustody = win32Path(custody);
    const auto attributes = GetFileAttributesW(apiCustody.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES) {
        const auto error = GetLastError();
        if (error != ERROR_FILE_NOT_FOUND && error != ERROR_PATH_NOT_FOUND)
            return failure<Result>(CustodyFileError::ioFailed, error);
        auto empty = held->validateStoreInventory(true, cancellation);
        if (!empty.ok()) return failure<Result>(empty.error, empty.nativeError);
        if (cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        // Exclusive birth: an intervening creator/partial sentinel is a conflict.
        if (!CreateDirectoryW(apiCustody.c_str(), &held->state_->security)) {
            const auto native = GetLastError();
            return failure<Result>(native == ERROR_ALREADY_EXISTS ? CustodyFileError::conflict : CustodyFileError::ioFailed, native);
        }
        birth = held->state_->storeBirth = true;
    }
    locked = held->state_->lockDirectory(custody, true, false);
    if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    auto idPath = custody;
    idPath /= L"store.id";
    if (birth) {
        const auto status = BCryptGenRandom(nullptr, held->state_->context.storeId.data(), 16, BCRYPT_USE_SYSTEM_PREFERRED_RNG);
        if (status < 0) return failure<Result>(CustodyFileError::ioFailed, static_cast<std::uint32_t>(status));
        auto created = held->state_->create(idPath, held->state_->context.storeId.data(), 16);
        if (!created.ok()) return failure<Result>(created.error, created.nativeError);
        held->state_->storeId = std::move(*created.value);
        auto checked = held->state_->identityValue(held->state_->storeId.value,
            &held->state_->context.storeId, held->state_->context.storeId);
        if (!checked.ok()) return failure<Result>(checked.error, checked.nativeError);
    } else {
        auto id = held->state_->identity(held->state_->storeId, idPath, nullptr,
            held->state_->context.storeId, false, true);
        if (!id.ok()) return failure<Result>(id.error, id.nativeError);
        auto inventory = held->validateStoreInventory(false, cancellation);
        if (!inventory.ok()) return failure<Result>(inventory.error, inventory.nativeError);
    }
    if (cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return success(std::move(held));
#endif
} catch (const std::bad_alloc&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::allocationFailed); }
  catch (const std::filesystem::filesystem_error&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::unsafePath); }

std::unique_lock<std::mutex> ProtectedCustodyFiles::lockWriteGroup() {
#ifdef _WIN32
    return std::unique_lock<std::mutex>(state_->storeState().writeGroup);
#else
    return std::unique_lock<std::mutex>(state_->writeGroup);
#endif
}

unsigned ProtectedCustodyFiles::storagePressurePercent() const noexcept {
#ifdef _WIN32
    return state_->storeState().pressurePercent.load(std::memory_order_relaxed);
#else
    return 0;
#endif
}

CustodyFileResult<std::shared_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::createPackageRoot(
    std::shared_ptr<const ProtectedCustodyFiles> root, std::string_view name,
    std::shared_ptr<const std::atomic<bool>> cancellation, std::shared_ptr<ProtectedCustodyFiles>* retainedFailure) try {
    using Result = std::shared_ptr<ProtectedCustodyFiles>;
    if (!root || !cancellation || !retainedFailure || name.empty() || name.size() > 300 ||
        !std::all_of(name.begin(), name.end(), [](unsigned char c) {
            return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
        })) return failure<Result>(CustodyFileError::invalidInput);
#ifndef _WIN32
    return failure<Result>(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    auto state = std::make_unique<State>(root->state_->trustedRoot);
    state->rootLease = std::move(root); state->cancellation = std::move(cancellation);
    state->context.storeId = state->rootLease->state_->context.storeId;
    state->writable = true;
    if (!state->initializeSecurity()) return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    Result held(new ProtectedCustodyFiles(std::move(state)), [](ProtectedCustodyFiles* p) { delete p; },
        CustodyAllocator<ProtectedCustodyFiles>{});
    *retainedFailure = held;
    auto group = held->lockWriteGroup();
    auto reserve = held->checkWriteReserve(128 * 1024, 20); // Exclusive package/role identities and metadata birth peak.
    if (!reserve.ok()) return failure<Result>(reserve.error, reserve.nativeError);
    auto& native = *held->state_;
    const std::wstring packageName(name.begin(), name.end());
    native.directory /= packageName;
    const auto apiPackage = win32Path(native.directory);
    if (!CreateDirectoryW(apiPackage.c_str(), &native.security)) {
        const auto error = GetLastError();
        return failure<Result>(error == ERROR_ALREADY_EXISTS ? CustodyFileError::conflict : CustodyFileError::ioFailed, error);
    }
    auto checked = native.lockDirectory(native.directory, true, false);
    if (!checked.ok()) return failure<Result>(checked.error, checked.nativeError);
    native.directory /= L".custody-v1";
    const auto apiCustody = win32Path(native.directory);
    if (!CreateDirectoryW(apiCustody.c_str(), &native.security))
        return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    checked = native.lockDirectory(native.directory, true, false);
    if (!checked.ok()) return failure<Result>(checked.error, checked.nativeError);
    return success(std::move(held));
#endif
} catch (const std::bad_alloc&) { return failure<std::shared_ptr<ProtectedCustodyFiles>>(CustodyFileError::allocationFailed); }
  catch (const std::filesystem::filesystem_error&) { return failure<std::shared_ptr<ProtectedCustodyFiles>>(CustodyFileError::unsafePath); }

CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::openPackageState(
    std::shared_ptr<const ProtectedCustodyFiles> root, std::string_view name,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Result = std::unique_ptr<ProtectedCustodyFiles>;
    if (!root || !cancellation || name.empty() || name.size() > 300 ||
        !std::all_of(name.begin(), name.end(), [](unsigned char c) {
            return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_' || c == '-';
        })) return failure<Result>(CustodyFileError::invalidInput);
#ifndef _WIN32
    return failure<Result>(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    auto state = std::make_unique<State>(root->state_->trustedRoot);
    state->context = {root->state_->context.storeId, {}, CustodyRole::packageState};
    state->rootLease = std::move(root); state->cancellation = std::move(cancellation);
    if (!state->initializeSecurity()) return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    state->directory /= std::wstring(name.begin(), name.end());
    auto checked = state->lockDirectory(state->directory, true, false);
    if (!checked.ok()) return failure<Result>(checked.error, checked.nativeError);
    state->directory /= L".custody-v1";
    checked = state->lockDirectory(state->directory, true, false);
    if (!checked.ok()) return failure<Result>(checked.error, checked.nativeError);
    // Acquire the existing identity exclusively, then expose only read validation.
    // No root/store reopen and no early blockWrites(), which would poison reads.
    state->writable = true;
    checked = state->openRole(CustodyFileAccess::writeExisting, true);
    if (!checked.ok()) return failure<Result>(checked.error, checked.nativeError);
    state->writable = false;
    if (state->cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return success(Result(new ProtectedCustodyFiles(std::move(state))));
#endif
} catch (const std::bad_alloc&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::allocationFailed); }
  catch (const std::filesystem::filesystem_error&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::unsafePath); }

CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::openPackageMember(
    std::shared_ptr<const ProtectedCustodyFiles> packageState, const CustodyContext& context,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Result = std::unique_ptr<ProtectedCustodyFiles>;
    if (!packageState || !cancellation || !packageState->state_->rootLease ||
        packageState->state_->writable || packageState->state_->failed ||
        packageState->context().role != CustodyRole::packageState ||
        packageState->state_->cancellation.get() != cancellation.get() ||
        packageState->context().storeId != context.storeId ||
        context.role < CustodyRole::canonical || context.role > CustodyRole::recovery)
        return failure<Result>(CustodyFileError::identityMismatch);
#ifndef _WIN32
    return failure<Result>(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    // Handles keep identities confined, but ACLs can still change while held.
    // Recheck the genuine parents for flat members too, without path reopening.
    for (const auto* held = packageState->state_.get(); held; held = held->rootLease ? held->rootLease->state_.get() : nullptr) {
        for (const auto& directory : held->directories)
            if (!held->inspect(directory.handle.value, directory.path, true, directory.privateDirectory))
                return failure<Result>(CustodyFileError::unsafePath);
        if (held->objectId.valid() && !held->inspect(held->objectId.value, held->directory / L"id.bin", false, true))
            return failure<Result>(CustodyFileError::unsafeFile);
    }
    const auto& retained = *packageState->state_;
    if (!retained.inspect(retained.storeState().storeId.value,
        retained.trustedRoot / L".custody-v1" / L"store.id", false, true))
        return failure<Result>(CustodyFileError::unsafeFile);
    auto state = std::make_unique<State>(packageState->state_->trustedRoot);
    state->context = context;
    // The genuine package-state lease already confines these parents. Keep it,
    // including the original birth store.id handle, through last member release.
    state->directory = packageState->state_->directory.parent_path();
    state->rootLease = std::move(packageState); state->cancellation = std::move(cancellation);
    if (!state->initializeSecurity()) return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    state->writable = true; // Acquire the exact existing identity exclusively, never discover/create.
    auto checked = state->openRole(CustodyFileAccess::writeExisting, false);
    if (!checked.ok()) return failure<Result>(checked.error, checked.nativeError);
    state->writable = false;
    if (state->cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    return success(Result(new ProtectedCustodyFiles(std::move(state))));
#endif
} catch (const std::bad_alloc&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::allocationFailed); }
  catch (const std::filesystem::filesystem_error&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::unsafePath); }

CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::createPackageRole(
    std::shared_ptr<const ProtectedCustodyFiles> root, CustodyRole role,
    std::unique_ptr<ProtectedCustodyFiles>* retainedFailure) try {
    using Result = std::unique_ptr<ProtectedCustodyFiles>;
    if (!root || !retainedFailure || (role != CustodyRole::packageState && (role < CustodyRole::canonical || role > CustodyRole::recovery)))
        return failure<Result>(CustodyFileError::invalidInput);
#ifndef _WIN32
    return failure<Result>(CustodyFileError::unsupportedPlatform);
#else
    auto state = std::make_unique<State>(root->state_->trustedRoot);
    state->context.storeId = root->state_->context.storeId;
    state->context.role = role; state->writable = true;
    state->directory = root->state_->directory;
    state->cancellation = root->state_->cancellation;
    state->rootLease = std::move(root);
    if (state->cancellation->load()) return failure<Result>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    if (!state->initializeSecurity()) return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    const auto rng = BCryptGenRandom(nullptr, state->context.objectId.data(), 16, BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (rng < 0) return failure<Result>(CustodyFileError::ioFailed, static_cast<std::uint32_t>(rng));
    if (state->context.objectId == CustodyId{} || state->context.objectId == state->context.storeId)
        return failure<Result>(CustodyFileError::identityMismatch);
    *retainedFailure = Result(new ProtectedCustodyFiles(std::move(state)));
    auto opened = (*retainedFailure)->state_->openRole(CustodyFileAccess::createNew, false);
    if (!opened.ok()) return failure<Result>(opened.error, opened.nativeError);
    return success(std::move(*retainedFailure));
#endif
} catch (const std::bad_alloc&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::allocationFailed); }
  catch (const std::filesystem::filesystem_error&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::unsafePath); }

CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::openStoreObject(
    std::shared_ptr<const ProtectedCustodyFiles> root, CustodyRole role, bool birth) try {
    using Result = std::unique_ptr<ProtectedCustodyFiles>;
    if (!root || (role != CustodyRole::bootstrap && role != CustodyRole::queue)) return failure<Result>(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)root; (void)birth;
    return failure<Result>(CustodyFileError::unsupportedPlatform);
#else
    // Borrow the continuously held root/store identity; never reopen store.id.
    auto state = std::make_unique<State>(root->state_->trustedRoot);
    state->context.storeId = root->state_->context.storeId;
    state->cancellation = root->state_->cancellation;
    state->rootLease = std::move(root);
    state->context.role = role;
    state->writable = true;
    if (!state->initializeSecurity()) return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    state->directory /= L".custody-v1";
    if (birth) {
        const auto status = BCryptGenRandom(nullptr, state->context.objectId.data(), 16, BCRYPT_USE_SYSTEM_PREFERRED_RNG);
        if (status < 0) return failure<Result>(CustodyFileError::ioFailed, static_cast<std::uint32_t>(status));
        if (state->context.objectId == state->context.storeId) return failure<Result>(CustodyFileError::identityMismatch);
    }
    auto opened = state->openRole(birth ? CustodyFileAccess::createNew : CustodyFileAccess::writeExisting, !birth);
    if (!opened.ok()) return failure<Result>(opened.error, opened.nativeError);
    return success(Result(new ProtectedCustodyFiles(std::move(state))));
#endif
} catch (const std::bad_alloc&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::allocationFailed); }
  catch (const std::filesystem::filesystem_error&) { return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::unsafePath); }

CustodyFileResult<bool> ProtectedCustodyFiles::validateStoreInventory(
    bool virgin, std::shared_ptr<const std::atomic<bool>> cancellation, bool completeBirth) const try {
    if (!cancellation) return failure<bool>(CustodyFileError::invalidInput);
#ifndef _WIN32
    (void)virgin; (void)completeBirth;
    return failure<bool>(CustodyFileError::unsupportedPlatform);
#else
    const auto inspectDirectory = [&](const std::filesystem::path& path) {
        const auto apiPath = win32Path(path);
        Handle dir(CreateFileW(apiPath.c_str(), READ_CONTROL | FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY,
            FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (!dir.valid()) return failure<bool>(CustodyFileError::ioFailed, GetLastError());
        return state_->inspect(dir.value, path, true, true) ? success(true) : failure<bool>(CustodyFileError::unsafePath);
    };
    bool fixedSeen = false;
    auto scanned = state_->eachChild(state_->trustedRoot, cancellation, [&](std::wstring_view name, bool dir) {
        if (virgin || !dir) return failure<bool>(CustodyFileError::recoveryRequired);
        auto child = state_->trustedRoot;
        child /= std::filesystem::path(name);
        auto checked = inspectDirectory(child);
        if (!checked.ok()) return checked;
        if (name == L".custody-v1") {
            fixedSeen = true;
            unsigned fixed = 0;
            auto service = state_->eachChild(child, cancellation, [&](std::wstring_view entry, bool directoryEntry) {
                unsigned bit = 0;
                if (entry == L"store.id" && !directoryEntry) bit = 1;
                if (entry == L"bootstrap" && directoryEntry) bit = 2;
                if (entry == L"queue" && directoryEntry) bit = 4;
                if (!bit || (fixed & bit)) return failure<bool>(CustodyFileError::recoveryRequired);
                fixed |= bit;
                auto path = child;
                path /= std::filesystem::path(entry);
                if (directoryEntry) return inspectDirectory(path);
                // The birth handle still has write access. Sharing write here
                // permits that SAME handle, not another writer (it denies share-write).
                auto id = state_->openFile(path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE);
                if (!id.ok()) return failure<bool>(id.error, id.nativeError);
                LARGE_INTEGER size{}; DWORD got = 0; CustodyId actual{};
                if (!GetFileSizeEx(id.value->value, &size) || !ReadFile(id.value->value, actual.data(), 16, &got, nullptr))
                    return failure<bool>(CustodyFileError::ioFailed, GetLastError());
                return size.QuadPart == 16 && got == 16 && actual == state_->context.storeId
                    ? success(true) : failure<bool>(CustodyFileError::identityMismatch);
            });
            if (!service.ok()) return service;
            return fixed == 7 ? success(true) : failure<bool>(CustodyFileError::recoveryRequired);
        }
        if (state_->storeBirth || name.empty() || name.size() > 300 ||
            !std::all_of(name.begin(), name.end(), [](wchar_t c) {
                return (c >= L'a' && c <= L'z') || (c >= L'A' && c <= L'Z') ||
                    (c >= L'0' && c <= L'9') || c == L'_' || c == L'-';
            })) return failure<bool>(CustodyFileError::recoveryRequired);
        // Known protected package layout only. No legacy reader, intent/tombstone
        // recovery or package effects authority is inferred from this inventory.
        bool custodySeen = false;
        auto package = state_->eachChild(child, cancellation, [&](std::wstring_view entry, bool directoryEntry) {
            if (entry != L".custody-v1" || !directoryEntry || custodySeen) return failure<bool>(CustodyFileError::recoveryRequired);
            custodySeen = true;
            auto path = child;
            path /= L".custody-v1";
            auto privateDirectory = inspectDirectory(path);
            if (!privateDirectory.ok()) return privateDirectory;
            bool packageState = false;
            auto roles = state_->eachChild(path, cancellation, [&](std::wstring_view role, bool roleDirectory) {
                if (!roleDirectory || (role != L"package-state" && role != L"canonical" && role != L"media" &&
                    role != L"playback" && role != L"manifest" && role != L"recovery"))
                    return failure<bool>(CustodyFileError::recoveryRequired);
                packageState |= role == L"package-state";
                auto rolePath = path;
                rolePath /= std::filesystem::path(role);
                return inspectDirectory(rolePath);
            });
            if (!roles.ok()) return roles;
            return packageState ? success(true) : failure<bool>(CustodyFileError::recoveryRequired);
        });
        if (!package.ok()) return package;
        return custodySeen ? success(true) : failure<bool>(CustodyFileError::recoveryRequired);
    });
    if (!scanned.ok()) return scanned;
    if (!virgin && !fixedSeen) return failure<bool>(CustodyFileError::recoveryRequired);
    if (cancellation->load()) return failure<bool>(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    if (completeBirth) state_->storeBirth = false;
    return success(true);
#endif
} catch (const std::bad_alloc&) { return failure<bool>(CustodyFileError::allocationFailed); }
  catch (const std::filesystem::filesystem_error&) { return failure<bool>(CustodyFileError::unsafePath); }

CustodyFileResult<CustodyBytes> ProtectedCustodyFiles::readBlock(
    std::uint64_t position, std::uint64_t version, std::uint32_t payload, std::uint32_t exact) try {
#ifndef _WIN32
    (void)position; (void)version; (void)payload; (void)exact;
    return failure<CustodyBytes>(CustodyFileError::unsupportedPlatform);
#else
    const auto limit = ProtectedCustodyCodec::blockEnvelopeLimit(payload);
    const auto logical = ProtectedCustodyCodec::logicalLimit(state_->context.role);
    if (limit == 0 || exact < 16 || exact > limit || version == 0
        || position >= (logical + ProtectedCustodyCodec::blockBytes - 1) / ProtectedCustodyCodec::blockBytes
        || payload > logical - position * ProtectedCustodyCodec::blockBytes)
        return failure<CustodyBytes>(CustodyFileError::invalidInput);
    const auto name = blockName(position, version);
    std::filesystem::path path(state_->directory);
    path /= name;
    auto result = state_->read(path, limit, exact);
    if (!result.ok()) return result;
    auto decoded = ProtectedCustodyCodec::openBlock(state_->context, position, version, payload, *result.value);
    if (!decoded.ok()) return failure<CustodyBytes>(codecFileError(decoded.error), decoded.nativeError);
    WipePlain wipe{*decoded.value}; return result;
#endif
} catch (const std::bad_alloc&) {
    return failure<CustodyBytes>(CustodyFileError::allocationFailed);
}

CustodyFileResult<CustodyBytes> ProtectedCustodyFiles::readMigrationBirthEnvelope(
    std::uint64_t version, std::uint32_t exact) try {
    const auto limit = ProtectedCustodyCodec::blockEnvelopeLimit(65536);
    if (state_->context.role != CustodyRole::migrationIntent || !version || exact <= 16 || exact > limit)
        return failure<CustodyBytes>(CustodyFileError::invalidInput);
#ifndef _WIN32
    return failure<CustodyBytes>(CustodyFileError::unsupportedPlatform);
#else
    const auto name = blockName(0, version);
    std::filesystem::path path(state_->directory);
    path /= name;
    auto cipher = state_->read(path, limit, exact);
    if (!cipher.ok()) return cipher;
    auto plain = ProtectedCustodyCodec::openMigrationBirthBlock(state_->context, version, *cipher.value);
    if (!plain.ok()) return failure<CustodyBytes>(codecFileError(plain.error), plain.nativeError);
    return cipher; // Charged plaintext is wiped on release; caller verifies the direct ref.
#endif
} catch (const std::bad_alloc&) {
    return failure<CustodyBytes>(CustodyFileError::allocationFailed);
}

CustodyFileResult<std::uint32_t> ProtectedCustodyFiles::writeBlock(
    std::uint64_t position, std::uint64_t version, std::uint32_t payload, const CustodyBytes& envelope) try {
#ifndef _WIN32
    (void)position; (void)version; (void)payload; (void)envelope;
    return failure<std::uint32_t>(CustodyFileError::unsupportedPlatform);
#else
    if (!state_->writable || state_->failed) return failure<std::uint32_t>(CustodyFileError::writerFailed);
    auto decoded = ProtectedCustodyCodec::openBlock(state_->context, position, version, payload, envelope);
    if (!decoded.ok()) return failure<std::uint32_t>(codecFileError(decoded.error), decoded.nativeError);
    WipePlain wipe{*decoded.value};
    const auto size = static_cast<std::uint32_t>(envelope.size()); // Codec proved the physical bound.
    const auto name = blockName(position, version);
    std::filesystem::path path(state_->directory);
    path /= name;
    auto created = state_->create(path, envelope.data(), size);
    if (!created.ok()) { state_->failed = true; return failure<std::uint32_t>(created.error, created.nativeError); }
    created.value->close();
    auto reopened = readBlock(position, version, payload, size);
    if (!reopened.ok() || *reopened.value != envelope) {
        state_->failed = true;
        return failure<std::uint32_t>(reopened.ok() ? CustodyFileError::invalidContent : reopened.error, reopened.nativeError);
    }
    return success(size);
#endif
} catch (const std::bad_alloc&) {
    state_->failed = true;
    return failure<std::uint32_t>(CustodyFileError::allocationFailed);
}

void ProtectedCustodyFiles::blockWrites() noexcept { state_->failed = true; }

CustodyFileResult<std::uint64_t> ProtectedCustodyFiles::nextBlockVersion(std::uint64_t position) try {
#ifndef _WIN32
    (void)position; return failure<std::uint64_t>(CustodyFileError::unsupportedPlatform);
#else
    if (!state_->writable || state_->failed) return failure<std::uint64_t>(CustodyFileError::writerFailed);
    const auto limit = ProtectedCustodyCodec::logicalLimit(state_->context.role);
    if (position >= (limit + ProtectedCustodyCodec::blockBytes - 1) / ProtectedCustodyCodec::blockBytes)
        return failure<std::uint64_t>(CustodyFileError::invalidInput);
    const auto prefix = L"block." + std::to_wstring(position) + L".";
    WIN32_FIND_DATAW data{};
    struct Search { HANDLE value; ~Search() { if (value != INVALID_HANDLE_VALUE) FindClose(value); } };
    const auto apiPattern = win32Path(state_->directory / (prefix + L"*"));
    Search search{FindFirstFileW(apiPattern.c_str(), &data)};
    if (search.value == INVALID_HANDLE_VALUE) {
        const auto error = GetLastError();
        return error == ERROR_FILE_NOT_FOUND ? success(std::uint64_t{1}) : failure<std::uint64_t>(CustodyFileError::ioFailed, error);
    }
    std::uint64_t highest = 0;
    do {
        const std::wstring_view name(data.cFileName);
        if (name.substr(0, prefix.size()) != prefix) continue;
        const auto suffix = name.substr(prefix.size());
        // Non-generated names remain untouched; canonical integer names alone
        // participate. A canonical over-limit version blocks, never wraps.
        if (suffix.empty() || (suffix.size() > 1 && suffix[0] == L'0')
            || suffix.find_first_not_of(L"0123456789") != std::wstring_view::npos) continue;
        std::uint64_t version = 0;
        for (const auto digit : suffix) {
            if (version > ((std::numeric_limits<std::uint64_t>::max)() - (digit - L'0')) / 10)
                return failure<std::uint64_t>(CustodyFileError::invalidContent);
            version = version * 10 + (digit - L'0');
        }
        if (version == 0 || (data.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)))
            return failure<std::uint64_t>(CustodyFileError::unsafeFile);
        highest = std::max(highest, version);
    } while (FindNextFileW(search.value, &data));
    const auto error = GetLastError();
    if (error != ERROR_NO_MORE_FILES) return failure<std::uint64_t>(CustodyFileError::ioFailed, error);
    if (highest == (std::numeric_limits<std::uint64_t>::max)()) return failure<std::uint64_t>(CustodyFileError::invalidInput);
    return success(highest + 1);
#endif
} catch (const std::bad_alloc&) {
    return failure<std::uint64_t>(CustodyFileError::allocationFailed);
}

CustodyFileResult<std::uint64_t> ProtectedCustodyFiles::checkWriteReserve(std::uint64_t peakBytes, std::uint32_t newFiles) try {
#ifndef _WIN32
    (void)peakBytes; (void)newFiles; return failure<std::uint64_t>(CustodyFileError::unsupportedPlatform);
#else
    if (!state_->writable || state_->failed) return failure<std::uint64_t>(CustodyFileError::writerFailed);
    DISK_SPACE_INFORMATION info{};
    const auto hr = GetDiskSpaceInformationW(state_->directory.root_path().c_str(), &info);
    if (FAILED(hr)) return failure<std::uint64_t>(CustodyFileError::ioFailed, static_cast<std::uint32_t>(hr));
    const auto cluster = std::uint64_t{info.SectorsPerAllocationUnit} * info.BytesPerSector;
    const auto maximum = (std::numeric_limits<std::uint64_t>::max)();
    const auto availableUnits = std::min(info.ActualAvailableAllocationUnits, info.CallerAvailableAllocationUnits);
    const auto unavailableUnits = std::max(info.ActualPoolUnavailableAllocationUnits, info.CallerPoolUnavailableAllocationUnits);
    if (!cluster || info.ActualTotalAllocationUnits > maximum / cluster || availableUnits > maximum / cluster
        || unavailableUnits > availableUnits || newFiles > maximum / cluster || peakBytes > maximum - newFiles * (cluster - 1))
        return failure<std::uint64_t>(CustodyFileError::invalidInput);
    const auto available = (availableUnits - unavailableUnits) * cluster;
    const auto reserve = std::min(std::uint64_t{10'000'000'000}, info.ActualTotalAllocationUnits * cluster / 10);
    const auto peak = peakBytes + newFiles * (cluster - 1); // Conservative sum of per-file rounding.
    if (state_->rootLease) {
        auto used = state_->physicalBytes(state_->trustedRoot, state_->cancellation);
        if (!used.ok()) return failure<std::uint64_t>(used.error, used.nativeError);
        constexpr std::uint64_t cap = 5'000'000'000ULL;
        state_->storeState().pressurePercent.store(static_cast<unsigned>(std::min<std::uint64_t>(100,
            *used.value >= cap || peak >= cap - *used.value ? 100 : (*used.value + peak) * 100 / cap)), std::memory_order_relaxed);
        // The critical95% boundary closes admission; never truncate/GC existing bytes.
        if (*used.value > cap * 95 / 100 || peak > cap * 95 / 100 - *used.value)
            return failure<std::uint64_t>(CustodyFileError::ioFailed, ERROR_DISK_FULL);
    }
    if (available < reserve || peak > available - reserve)
        return failure<std::uint64_t>(CustodyFileError::ioFailed, ERROR_DISK_FULL);
    return success(peak);
#endif
} catch (const std::bad_alloc&) {
    return failure<std::uint64_t>(CustodyFileError::allocationFailed);
}

CustodyFileResult<CustodyBytes> ProtectedCustodyFiles::readIndex(std::uint32_t slot) try {
#ifndef _WIN32
    (void)slot; return failure<CustodyBytes>(CustodyFileError::unsupportedPlatform);
#else
    if (slot > 1) return failure<CustodyBytes>(CustodyFileError::invalidInput);
    const auto name = indexName(slot);
    std::filesystem::path path(state_->directory);
    path /= name;
    auto bytes = state_->read(path, ProtectedCustodyCodec::indexEnvelopeLimit(state_->context.role));
    if (!bytes.ok()) return bytes;
    const auto decoded = ProtectedCustodyCodec::openIndex(state_->context, slot, *bytes.value);
    if (!decoded.ok()) return failure<CustodyBytes>(codecFileError(decoded.error), decoded.nativeError);
    return bytes;
#endif
} catch (const std::bad_alloc&) {
    return failure<CustodyBytes>(CustodyFileError::allocationFailed);
}

CustodyPublishResult ProtectedCustodyFiles::publishIndex(std::uint32_t slot, const CustodyBytes& envelope) try {
#ifndef _WIN32
    (void)slot; (void)envelope;
    return {CustodyPublishState::notPublished, CustodyFileError::unsupportedPlatform, 0};
#else
    if (!state_->writable || state_->failed) return {CustodyPublishState::notPublished, CustodyFileError::writerFailed, 0};
    const auto decoded = ProtectedCustodyCodec::openIndex(state_->context, slot, envelope);
    if (!decoded.ok()) return {CustodyPublishState::notPublished, codecFileError(decoded.error), decoded.nativeError};
    const auto module = GetModuleHandleW(L"ntdll.dll"); // Already loaded system module, no DLL search/load.
    const auto procedure = module ? GetProcAddress(module, "NtSetInformationFile") : nullptr;
    if (!procedure) return {CustodyPublishState::notPublished, CustodyFileError::ioFailed, ERROR_PROC_NOT_FOUND};
    RenameFile rename = nullptr;
    static_assert(sizeof(rename) == sizeof(procedure));
    std::memcpy(&rename, &procedure, sizeof(rename));
    std::array<std::uint8_t, 16> random{};
    const auto rng = BCryptGenRandom(nullptr, random.data(), static_cast<ULONG>(random.size()), BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    if (rng < 0) return {CustodyPublishState::notPublished, CustodyFileError::ioFailed, static_cast<std::uint32_t>(rng)};
    constexpr wchar_t digits[] = L"0123456789abcdef";
    std::wstring name = L"index.tmp-";
    for (const auto b : random) { name += digits[b >> 4]; name += digits[b & 15]; }
    auto temporary = state_->create(state_->directory / name, envelope.data(), static_cast<std::uint32_t>(envelope.size()), true);
    if (!temporary.ok()) { state_->failed = true; return {CustodyPublishState::notPublished, temporary.error, temporary.nativeError}; }
    const auto target = indexName(slot);
    // Nt's documented same-directory simple-name rename preserves the held
    // namespace locks. The Win32 wrapper expands a simple name against process
    // CWD; its absolute-name form opens the parent for write and conflicts with
    // those locks. Neither release the locks nor change process CWD to publish.
    const auto targetPath = state_->directory / target;
    const auto nameBytes = target.size() * sizeof(wchar_t);
    const auto renameSize = sizeof(RenameInfo) + nameBytes;
    // uint64_t storage gives native alignment; no persisted struct bytes.
    std::vector<std::uint64_t> buffer((renameSize + 7) / 8);
    auto* info = reinterpret_cast<RenameInfo*>(buffer.data());
    info->replace = TRUE; info->root = nullptr;
    info->nameBytes = static_cast<ULONG>(nameBytes);
    std::copy(target.begin(), target.end(), info->name);
    // From the publication attempt onward, retain artifacts and prohibit further
    // writes until the logical owner reconciles both slots in a fresh instance.
    state_->failed = true;
    // These are private synchronous CreateFile handles (no FILE_FLAG_OVERLAPPED):
    // the native call returns completion, never a caller-owned overlapped request.
    IO_STATUS_BLOCK io{};
    const auto status = rename(temporary.value->value, &io, info, static_cast<ULONG>(renameSize), nativeRenameInformation);
    if (status != 0 || io.Status != 0) return {CustodyPublishState::ambiguous, CustodyFileError::ioFailed,
        static_cast<std::uint32_t>(status != 0 ? status : io.Status)};
    if (!state_->inspect(temporary.value->value, targetPath, false, true))
        return {CustodyPublishState::ambiguous, CustodyFileError::unsafeFile, 0};
    if (!FlushFileBuffers(temporary.value->value))
        return {CustodyPublishState::ambiguous, CustodyFileError::ioFailed, GetLastError()};
    temporary.value->close();
    auto reopened = readIndex(slot);
    if (!reopened.ok() || *reopened.value != envelope)
        return {CustodyPublishState::ambiguous, reopened.ok() ? CustodyFileError::invalidContent : reopened.error, reopened.nativeError};
    state_->failed = false;
    return {CustodyPublishState::published, CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) {
    const auto publication = state_->failed ? CustodyPublishState::ambiguous : CustodyPublishState::notPublished;
    state_->failed = true;
    return {publication, CustodyFileError::allocationFailed, 0};
}

CustodyFileResult<CustodySnapshot> ProtectedCustodyFiles::readValidatedSnapshot() {
    return readValidatedSnapshotImpl(nullptr, nullptr);
}
CustodyFileResult<CustodyMetadataIndices> ProtectedCustodyFiles::readValidatedMetadataPair() try {
    const auto role = static_cast<unsigned>(state_->context.role);
    if (role < static_cast<unsigned>(CustodyRole::manifest) || role > static_cast<unsigned>(CustodyRole::migrationIntent))
        return failure<CustodyMetadataIndices>(CustodyFileError::invalidInput);
    CustodyMetadataIndices pair;
    CustodyIndex peer;
    auto current = readValidatedSnapshotImpl(&peer, &pair.selectedSlot);
    if (!current.ok()) return failure<CustodyMetadataIndices>(current.error, current.nativeError);
    pair.indices[pair.selectedSlot] = std::move(current.value->index);
    pair.indices[1-pair.selectedSlot] = std::move(peer);
    return success(std::move(pair));
} catch (const std::bad_alloc&) {
    return failure<CustodyMetadataIndices>(CustodyFileError::allocationFailed);
}
CustodyFileResult<CustodySnapshot> ProtectedCustodyFiles::readValidatedSnapshotImpl(
    CustodyIndex* peer, std::uint32_t* selectedSlot) try {
#ifndef _WIN32
    (void)peer; (void)selectedSlot;
    return failure<CustodySnapshot>(CustodyFileError::unsupportedPlatform);
#else
    if (state_->failed) return failure<CustodySnapshot>(CustodyFileError::writerFailed);
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) {
        if (!peer || error != CustodyFileError::allocationFailed) state_->failed = true;
        return failure<CustodySnapshot>(error, native);
    };
    const bool audio = state_->context.role == CustodyRole::canonical || state_->context.role == CustodyRole::media
        || state_->context.role == CustodyRole::playback;
    const bool prefixAllowed = state_->context.role == CustodyRole::canonical || state_->context.role == CustodyRole::media;
    std::array<CustodyFileResult<CustodyIndex>, 2> candidates;
    std::array<bool, 2> missingSlot{};
    for (std::uint32_t slot = 0; slot < 2; ++slot) {
        const auto name = indexName(slot);
        std::filesystem::path path(state_->directory);
        path /= name;
        auto cipher = state_->read(path, ProtectedCustodyCodec::indexEnvelopeLimit(state_->context.role));
        if (!cipher.ok()) {
            missingSlot[slot] = cipher.error == CustodyFileError::ioFailed && cipher.nativeError == ERROR_FILE_NOT_FOUND;
            candidates[slot] = failure<CustodyIndex>(cipher.error, cipher.nativeError);
        } else {
            auto decoded = ProtectedCustodyCodec::openIndex(state_->context, slot, *cipher.value);
            if (!decoded.ok()) candidates[slot] = failure<CustodyIndex>(codecFileError(decoded.error), decoded.nativeError);
            else {
                candidates[slot] = success(std::move(*decoded.value));
                auto remaining = candidates[slot].value->logicalLength;
                std::uint64_t position = 0;
                for (const auto& entry : candidates[slot].value->entries) {
                    const auto payload = static_cast<std::uint32_t>(std::min(remaining, std::uint64_t{ProtectedCustodyCodec::blockBytes}));
                    if (entry.flags == 0) {
                        const auto block = readBlock(position, entry.version, payload, entry.envelopeBytes);
                        if (!block.ok()) {
                            candidates[slot].error = block.error; candidates[slot].nativeError = block.nativeError;
                            break;
                        }
                    }
                    remaining -= payload; ++position;
                }
                if (candidates[slot].error != CustodyFileError::none) candidates[slot].value.reset();
            }
        }
        const auto& candidate = candidates[slot];
        // Metadata requires BOTH slots. Preserve an observed fault even if the
        // next candidate cannot allocate; a read-only refusal alone is retryable.
        if (peer && !candidate.ok() && candidate.error != CustodyFileError::allocationFailed)
            state_->failed = true;
        // Only authenticated semantic invalidity or proven file absence permits
        // trying another candidate. Native/hash/allocation/ACL/unknown IO never does.
        if (!candidate.ok() && candidate.error != CustodyFileError::invalidContent
            && !(candidate.error == CustodyFileError::ioFailed && candidate.nativeError == ERROR_FILE_NOT_FOUND))
            return reject(candidate.error, candidate.nativeError);
    }
    if (candidates[0].ok() && candidates[1].ok()
        && candidates[0].value->generation == candidates[1].value->generation) {
        const auto& a = *candidates[0].value; const auto& b = *candidates[1].value;
        if (audio || a.generation != 1 || a.logicalLength != b.logicalLength || a.entries.size() != b.entries.size()
            || !std::equal(a.entries.begin(), a.entries.end(), b.entries.begin(), [](const auto& x, const auto& y) {
                return x.version == y.version && x.envelopeBytes == y.envelopeBytes && x.flags == y.flags;
            })) return reject(CustodyFileError::conflict);
    }
    // Codec admits g1/slot1 for metadata birth; that exception is not audio placement.
    if (audio && candidates[1].ok() && candidates[1].value->generation == 1)
        candidates[1] = failure<CustodyIndex>(CustodyFileError::invalidContent);
    const bool both = candidates[0].ok() && candidates[1].ok();
    if (!both && (!audio || (!candidates[0].ok() && !candidates[1].ok()))) {
        const auto bad = candidates[0].ok() ? 1U : 0U;
        return reject(missingSlot[bad] ? CustodyFileError::recoveryRequired : candidates[bad].error, candidates[bad].nativeError);
    }
    const auto selected = candidates[1].ok() && (!candidates[0].ok()
        || candidates[1].value->generation > candidates[0].value->generation) ? 1U : 0U;
    const auto other = 1U - selected;
    if (peer && both) { *peer = std::move(*candidates[other].value); *selectedSlot = selected; }
    if (both || missingSlot[other])
        return success(CustodySnapshot{std::move(*candidates[selected].value), CustodySnapshotState::verified, CustodyFileError::none, 0});
    if (!prefixAllowed) return reject(candidates[other].error, candidates[other].nativeError);
    state_->failed = true; // Retained prefix never authorizes a next generation/GC/effects.
    return success(CustodySnapshot{std::move(*candidates[selected].value), CustodySnapshotState::trustedPrefix,
        candidates[other].error, candidates[other].nativeError});
#endif
} catch (const std::bad_alloc&) {
    if (!peer) state_->failed = true;
    return failure<CustodySnapshot>(CustodyFileError::allocationFailed);
}

struct ProtectedPackedCustodyOwner::State {
    CustodyPin pin; // Declared first: native handles/operations close before pin release.
    std::unique_ptr<ProtectedCustodyFiles> files;
    PackedCustodyContext context;
    std::mutex mutex;
    std::uint64_t epoch = 0;
    bool writable = false;
    CustodyFileError fault = CustodyFileError::none;
    std::uint32_t nativeError = 0;
    bool headAttempted = false; // Sticky ambiguity until a NEW owner performs full reconciliation.
#ifdef _WIN32
    Handle content;
    std::filesystem::path path;
    std::array<FILE_ID_INFO, 3> identities{};
    bool fail(CustodyFileError error, std::uint32_t native = 0) noexcept {
        if (fault == CustodyFileError::none) { fault = error; nativeError = native; }
        return false;
    }
    static bool sameIdentity(const FILE_ID_INFO& a, const FILE_ID_INFO& b) noexcept {
        return a.VolumeSerialNumber == b.VolumeSerialNumber &&
            std::memcmp(a.FileId.Identifier, b.FileId.Identifier, sizeof(a.FileId.Identifier)) == 0;
    }
    bool streams(const std::filesystem::path& name, bool directory) {
        WIN32_FIND_STREAM_DATA data{};
        const auto apiPath = win32Path(name);
        HANDLE search = FindFirstStreamW(apiPath.c_str(), FindStreamInfoStandard, &data, 0);
        if (search == INVALID_HANDLE_VALUE) {
            const auto error = GetLastError();
            return directory && error == ERROR_HANDLE_EOF ? true : fail(CustodyFileError::unsafeFile, error);
        }
        const bool first = !directory && std::wcscmp(data.cStreamName, L"::$DATA") == 0;
        const bool next = FindNextStreamW(search, &data) != FALSE;
        const auto error = next ? ERROR_SUCCESS : GetLastError();
        FindClose(search);
        return first && !next && error == ERROR_HANDLE_EOF ? true : fail(CustodyFileError::unsafeFile, error);
    }
    bool check(bool acquire = false) {
        auto& confined = *files->state_;
        for (const auto* held = &confined; held; held = held->rootLease ? held->rootLease->state_.get() : nullptr) {
            for (const auto& directory : held->directories) {
                if (!held->inspect(directory.handle.value, directory.path, true, directory.privateDirectory))
                    return fail(CustodyFileError::unsafePath);
                if (!streams(directory.path, true)) return false;
            }
        }
        const std::array<HANDLE, 3> handles{content.value, confined.storeState().storeId.value, confined.objectId.value};
        const std::array<std::filesystem::path, 3> paths{
            path, confined.trustedRoot / L".custody-v1" / L"store.id", confined.directory / L"id.bin"};
        for (std::size_t i = 0; i < handles.size(); ++i) {
            FILE_ID_INFO identity{}; DWORD flags = 0;
            if (!confined.inspect(handles[i], paths[i], false, true) || !GetHandleInformation(handles[i], &flags)
                || (flags & HANDLE_FLAG_INHERIT) || !GetFileInformationByHandleEx(handles[i], FileIdInfo, &identity, sizeof(identity)))
                return fail(CustodyFileError::unsafeFile);
            if (!acquire && !sameIdentity(identity, identities[i])) return fail(CustodyFileError::identityMismatch);
            if (!streams(paths[i], false)) return false;
            FILE_ID_INFO after{};
            if (!GetFileInformationByHandleEx(handles[i], FileIdInfo, &after, sizeof(after)) || !sameIdentity(identity, after))
                return fail(CustodyFileError::identityMismatch);
            if (acquire) identities[i] = identity;
        }
        return true;
    }
    CustodyFileResult<std::uint64_t> size() {
        LARGE_INTEGER value{};
        if (!GetFileSizeEx(content.value, &value) || value.QuadPart < 0) {
            fail(CustodyFileError::ioFailed, GetLastError());
            return failure<std::uint64_t>(fault, nativeError);
        }
        return success(static_cast<std::uint64_t>(value.QuadPart));
    }
    bool transfer(bool write, std::uint64_t offset, std::uint8_t* bytes, std::size_t count) {
        if (!bytes || count == 0 || offset > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) - count)
            return fail(CustodyFileError::invalidInput);
        for (std::size_t done = 0; done < count;) {
            const auto position = offset + done;
            OVERLAPPED operation{};
            operation.Offset = static_cast<DWORD>(position);
            operation.OffsetHigh = static_cast<DWORD>(position >> 32);
            const auto chunk = static_cast<DWORD>(std::min<std::size_t>(count - done, ProtectedPackedCustodyFormat::blockBytes));
            DWORD transferred = 0;
            // Synchronous handle + explicit offsets. Never use a caller/shared cursor.
            const auto ok = write ? WriteFile(content.value, bytes + done, chunk, &transferred, &operation)
                                  : ReadFile(content.value, bytes + done, chunk, &transferred, &operation);
            if (!ok) return fail(CustodyFileError::ioFailed, GetLastError());
            if (transferred != chunk) return fail(CustodyFileError::ioFailed, write ? ERROR_WRITE_FAULT : ERROR_READ_FAULT);
            done += transferred;
        }
        return true;
    }
    CustodyFileResult<CustodyBytes> read(std::uint64_t offset, std::uint32_t count) {
        if (!count || count > ProtectedPackedCustodyFormat::blockBytes + 4096 ||
            offset > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) - count)
            return failure<CustodyBytes>(CustodyFileError::invalidInput);
        const auto length = size();
        if (!length.ok()) return failure<CustodyBytes>(fault, nativeError);
        if (offset + count > *length.value) {
            fail(CustodyFileError::invalidContent);
            return failure<CustodyBytes>(fault, nativeError);
        }
        CustodyBytes bytes(count);
        if (!transfer(false, offset, bytes.data(), count)) return failure<CustodyBytes>(fault, nativeError);
        return success(std::move(bytes));
    }
    bool flush() {
        return FlushFileBuffers(content.value) != FALSE ? true : fail(CustodyFileError::ioFailed, GetLastError());
    }
    bool birth() {
        const auto prefix = ProtectedPackedCustodyFormat::encodePrefix(context);
        CustodyBytes body(128, 0); custody_detail::WipeBytes wipe{body};
        const auto put = [&](std::size_t at, std::uint64_t value, unsigned count) {
            for (unsigned i = 0; i < count; ++i) body[at + i] = static_cast<std::uint8_t>(value >> (8 * i));
        };
        put(0, 1, 8); put(16, ProtectedPackedCustodyFormat::appendOffset, 8);
        put(24, ProtectedPackedCustodyFormat::blockBytes, 4); put(32, 64, 4); put(36, 3, 4);
        std::array<CustodyBytes, 2> heads;
        for (std::uint32_t slot = 0; slot < 2; ++slot) {
            auto sealed = ProtectedPackedCustodyCodec::seal(context,
                {PackedRecordKind::head, 128 + slot * 16384ULL, slot, 1, 128}, body);
            if (!sealed.ok()) return fail(codecFileError(sealed.error), sealed.nativeError);
            heads[slot] = std::move(*sealed.value);
        }
        CustodyBytes bytes(static_cast<std::size_t>(ProtectedPackedCustodyFormat::appendOffset), 0);
        std::copy(prefix->begin(), prefix->end(), bytes.begin());
        for (std::size_t slot = 0; slot < 2; ++slot)
            std::copy(heads[slot].begin(), heads[slot].end(), bytes.begin() + 128 + slot * 16384);
        if (!check() || !transfer(true, 0, bytes.data(), bytes.size()) || !flush()) return false;
        CustodyBytes{}.swap(bytes); // Release writer copies BEFORE independent reads.
        for (auto& head : heads) CustodyBytes{}.swap(head);
        const auto actual = read(0, 128);
        if (!actual.ok() || !ProtectedPackedCustodyFormat::prefixMatches(actual.value->data(), 128, context))
            return fail(CustodyFileError::invalidContent);
        for (std::uint32_t slot = 0; slot < 2; ++slot) {
            const auto actualHead = read(128 + slot * 16384ULL, 16384);
            if (!actualHead.ok()) return false;
            auto decoded = ProtectedPackedCustodyCodec::openHead(context, slot, *actualHead.value, 1);
            if (!decoded.ok()) return fail(codecFileError(decoded.error), decoded.nativeError);
            custody_detail::WipeBytes decodedWipe{decoded.value->body};
            if (decoded.value->body != body) return fail(CustodyFileError::invalidContent);
        }
        return check(); // Physical empty birth only, never normal package authority.
    }
#endif
};

ProtectedPackedCustodyOwner::ProtectedPackedCustodyOwner(std::shared_ptr<State> state) : state_(std::move(state)) {}
ProtectedPackedCustodyOwner::~ProtectedPackedCustodyOwner() = default;
std::uint64_t ProtectedPackedCustodyOwner::epoch() const noexcept { return state_->epoch; }

ProtectedPackedCustodyOwner::Guard::Guard(std::shared_ptr<ProtectedPackedCustodyOwner> owner, bool writing)
    : owner_(std::move(owner)), lock_(owner_->state_->mutex, std::defer_lock) {
    if (job_) {
        if (writing) groupLock_ = owner_->state_->files->lockWriteGroup();
        lock_.lock(); // Writes: admission -> root group -> physical owner; reads never block another package's growth.
    }
}
const PackedCustodyContext& ProtectedPackedCustodyOwner::Guard::context() const noexcept {
    return owner_->state_->context;
}
CustodyFileResult<bool> ProtectedPackedCustodyOwner::Guard::reject(CustodyFileError error, std::uint32_t native) noexcept {
#ifndef _WIN32
    (void)error; (void)native;
    return failure<bool>(CustodyFileError::unsupportedPlatform);
#else
    if (!job_) return failure<bool>(CustodyFileError::allocationFailed);
    auto& state = *owner_->state_;
    state.fail(error, native); // Called while lock/job/owner are STILL held.
    return failure<bool>(state.fault, state.nativeError);
#endif
}
CustodyFileResult<bool> ProtectedPackedCustodyOwner::Guard::check() {
#ifndef _WIN32
    return failure<bool>(CustodyFileError::unsupportedPlatform);
#else
    if (!job_) return failure<bool>(CustodyFileError::allocationFailed);
    auto& state = *owner_->state_;
    if (state.fault != CustodyFileError::none || !state.check()) return failure<bool>(state.fault, state.nativeError);
    return success(true);
#endif
}
CustodyFileResult<std::uint64_t> ProtectedPackedCustodyOwner::Guard::size() {
#ifndef _WIN32
    return failure<std::uint64_t>(CustodyFileError::unsupportedPlatform);
#else
    const auto checked = check();
    if (!checked.ok()) return failure<std::uint64_t>(checked.error, checked.nativeError);
    return owner_->state_->size(); // EXACT native EOF, not rounded append position.
#endif
}
CustodyFileResult<CustodyBytes> ProtectedPackedCustodyOwner::Guard::read(std::uint64_t offset, std::uint32_t count) {
#ifndef _WIN32
    (void)offset; (void)count;
    return failure<CustodyBytes>(CustodyFileError::unsupportedPlatform);
#else
    if (!count || count > ProtectedPackedCustodyFormat::blockBytes + 4096 ||
        offset > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) - count)
        return failure<CustodyBytes>(CustodyFileError::invalidInput);
    auto checked = check();
    if (!checked.ok()) return failure<CustodyBytes>(checked.error, checked.nativeError);
    auto result = owner_->state_->read(offset, count);
    if (!result.ok()) return result;
    checked = check();
    return checked.ok() ? std::move(result) : failure<CustodyBytes>(checked.error, checked.nativeError);
#endif
}

CustodyFileResult<bool> ProtectedPackedCustodyOwner::Guard::writeReady() {
    const auto checked = check();
    if (!checked.ok()) return checked;
    return groupLock_.owns_lock() && owner_->state_->writable ? success(true) : failure<bool>(CustodyFileError::writerFailed);
}
CustodyFileResult<std::uint64_t> ProtectedPackedCustodyOwner::Guard::reserve(std::uint64_t bytes) {
    const auto checked = writeReady();
    if (!checked.ok()) return failure<std::uint64_t>(checked.error, checked.nativeError);
    auto result = owner_->state_->files->checkWriteReserve(bytes, 0);
    if (!result.ok()) {
        const auto rejected = reject(result.error, result.nativeError);
        return failure<std::uint64_t>(rejected.error, rejected.nativeError);
    }
    return result;
}
CustodyFileResult<std::uint32_t> ProtectedPackedCustodyOwner::Guard::append(
    const PackedRecordAddress& address, const CustodyBytes& envelope) {
    const auto checked = writeReady();
    return checked.ok() ? owner_->appendLocked(address, envelope) :
        failure<std::uint32_t>(checked.error, checked.nativeError);
}
CustodyFileResult<bool> ProtectedPackedCustodyOwner::Guard::flush() {
    const auto checked = writeReady();
    return checked.ok() ? owner_->flushLocked() : checked;
}
CustodyPublishResult ProtectedPackedCustodyOwner::Guard::publishHead(std::uint32_t slot, const CustodyBytes& envelope) {
    const auto checked = writeReady();
    return checked.ok() ? owner_->publishHeadLocked(slot, envelope) :
        CustodyPublishResult{CustodyPublishState::notPublished, checked.error, checked.nativeError};
}

CustodyFileResult<std::shared_ptr<ProtectedPackedCustodyOwner>> ProtectedPackedCustodyOwner::open(
    const std::filesystem::path& root, std::string_view package, const PackedCustodyContext& context, CustodyFileAccess access) {
    return openImpl(root, package, context, access, nullptr);
}
CustodyFileResult<std::shared_ptr<ProtectedPackedCustodyOwner>> ProtectedPackedCustodyOwner::openImpl(
    const std::filesystem::path& root, std::string_view package, const PackedCustodyContext& context, CustodyFileAccess access,
    std::unique_ptr<ProtectedCustodyFiles>* prepared, std::shared_ptr<ProtectedPackedCustodyOwner>* retainedFailure) try {
    using Owner = std::shared_ptr<ProtectedPackedCustodyOwner>;
#ifndef _WIN32
    (void)root; (void)package; (void)context; (void)access; (void)prepared; (void)retainedFailure;
    return failure<Owner>(CustodyFileError::unsupportedPlatform);
#else
    if (!ProtectedPackedCustodyFormat::encodePrefix(context) ||
        (access != CustodyFileAccess::readExisting && access != CustodyFileAccess::writeExisting && access != CustodyFileAccess::createNew))
        return failure<Owner>(CustodyFileError::invalidInput);
    CustodyNativeJob job;
    if (!job) return failure<Owner>(CustodyFileError::allocationFailed);
    auto state = std::allocate_shared<State>(CustodyAllocator<State>{});
    if (!state->pin) return failure<Owner>(CustodyFileError::allocationFailed);
    state->context = context; state->writable = access != CustodyFileAccess::readExisting;
    static std::atomic<std::uint64_t> epochs{0};
    auto previous = epochs.load(std::memory_order_relaxed);
    do {
        if (previous == std::numeric_limits<std::uint64_t>::max()) return failure<Owner>(CustodyFileError::recoveryRequired);
    } while (!epochs.compare_exchange_weak(previous, previous + 1, std::memory_order_relaxed));
    state->epoch = previous + 1; // Consume, never recycle, before native content effects.
    Owner preparedOwner;
    if (prepared) {
        if (!*prepared || (access == CustodyFileAccess::createNew && !retainedFailure))
            return failure<Owner>(CustodyFileError::invalidInput);
        const auto& actual = (*prepared)->context();
        if ((access != CustodyFileAccess::createNew && access != CustodyFileAccess::readExisting) ||
            !(*prepared)->state_->rootLease ||
            actual.storeId != context.object.storeId || actual.objectId != context.object.objectId || actual.role != context.object.role)
            return failure<Owner>(CustodyFileError::identityMismatch);
        if (access == CustodyFileAccess::readExisting &&
            ((*prepared)->state_->writable || (*prepared)->state_->failed || (*prepared)->trustedRoot() != root ||
                (*prepared)->packagePath() != root / std::wstring(package.begin(), package.end()) / L".custody-v1"))
            return failure<Owner>(CustodyFileError::identityMismatch);
        // Allocate all ownership/control blocks before transferring any lease.
        // A partial native content birth stays held by the genuine package,
        // even though this factory returns no usable owner/proof on failure.
        if (access == CustodyFileAccess::createNew) {
            CustodyAllocator<ProtectedPackedCustodyOwner> allocator;
            auto* raw = allocator.allocate(1);
            new (raw) ProtectedPackedCustodyOwner(state);
            preparedOwner = Owner(raw, [](ProtectedPackedCustodyOwner* owner) {
                owner->~ProtectedPackedCustodyOwner(); CustodyAllocator<ProtectedPackedCustodyOwner>{}.deallocate(owner, 1);
            }, allocator);
            *retainedFailure = preparedOwner;
        }
        state->files = std::move(*prepared);
    } else {
        auto opened = ProtectedCustodyFiles::open(root, package, context.object,
            access == CustodyFileAccess::createNew ? access : CustodyFileAccess::writeExisting);
        if (!opened.ok()) return failure<Owner>(opened.error, opened.nativeError);
        state->files = std::move(*opened.value);
    }
    auto& confined = *state->files->state_;
    // A genuine prepared child borrows the continuously held immutable store
    // identity. The legacy path entry still upgrades its own original handle.
    if (!confined.rootLease) {
        auto store = confined.openFile(root / L".custody-v1" / L"store.id", GENERIC_READ, FILE_SHARE_READ);
        if (!store.ok()) return failure<Owner>(store.error, store.nativeError);
        confined.storeId = std::move(*store.value);
    }
    CustodyId storeBytes{}; DWORD got = 0; LARGE_INTEGER storeSize{}; OVERLAPPED storeOffset{};
    const auto storeHandle = confined.storeState().storeId.value;
    std::unique_lock<std::mutex> group;
    if (access != CustodyFileAccess::readExisting) group = state->files->lockWriteGroup();
    if (!GetFileSizeEx(storeHandle, &storeSize) || storeSize.QuadPart != 16 ||
        !ReadFile(storeHandle, storeBytes.data(), 16, &got, &storeOffset) || got != 16 || storeBytes != context.object.storeId)
        return failure<Owner>(CustodyFileError::identityMismatch);
    state->path = confined.directory / L"content.packed-v2";
    const auto reserve = access == CustodyFileAccess::createNew
        ? state->files->checkWriteReserve(ProtectedPackedCustodyFormat::appendOffset, 1)
        : success<std::uint64_t>(0);
    if (!reserve.ok()) return failure<Owner>(reserve.error, reserve.nativeError);
    const auto apiContent = win32Path(state->path);
    state->content = Handle(CreateFileW(apiContent.c_str(), GENERIC_READ | GENERIC_WRITE | READ_CONTROL, FILE_SHARE_READ,
        &confined.security, access == CustodyFileAccess::createNew ? CREATE_NEW : OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
    if (!state->content.valid()) return failure<Owner>(CustodyFileError::ioFailed, GetLastError());
    if (!state->check(true)) return failure<Owner>(state->fault, state->nativeError);
    if (access == CustodyFileAccess::createNew) {
        if (!state->birth()) return failure<Owner>(state->fault, state->nativeError);
    } else {
        const auto size = state->size();
        if (!size.ok()) return failure<Owner>(size.error, size.nativeError);
        if (*size.value < ProtectedPackedCustodyFormat::appendOffset) return failure<Owner>(CustodyFileError::invalidContent);
        const auto prefix = state->read(0, 128);
        if (!prefix.ok()) return failure<Owner>(prefix.error, prefix.nativeError);
        if (!ProtectedPackedCustodyFormat::prefixMatches(prefix.value->data(), 128, context))
            return failure<Owner>(CustodyFileError::identityMismatch);
        if (!state->check()) return failure<Owner>(state->fault, state->nativeError);
    }
    if (preparedOwner) return success(std::move(preparedOwner));
    CustodyAllocator<ProtectedPackedCustodyOwner> allocator;
    auto* raw = allocator.allocate(1);
    new (raw) ProtectedPackedCustodyOwner(std::move(state));
    return success(Owner(raw, [](ProtectedPackedCustodyOwner* owner) {
        owner->~ProtectedPackedCustodyOwner(); CustodyAllocator<ProtectedPackedCustodyOwner>{}.deallocate(owner, 1);
    }, CustodyAllocator<ProtectedPackedCustodyOwner>{}));
#endif
} catch (const std::bad_alloc&) {
    return failure<std::shared_ptr<ProtectedPackedCustodyOwner>>(CustodyFileError::allocationFailed);
} catch (const std::filesystem::filesystem_error&) {
    return failure<std::shared_ptr<ProtectedPackedCustodyOwner>>(CustodyFileError::unsafePath);
}

CustodyFileResult<PackedCipherRead> ProtectedPackedCustodyOwner::readCiphertext(std::uint64_t offset, std::uint32_t count) {
#ifndef _WIN32
    (void)offset;
    (void)count;
    return failure<PackedCipherRead>(CustodyFileError::unsupportedPlatform);
#else
    if (!count || count > ProtectedPackedCustodyFormat::blockBytes + 4096 ||
        offset > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) - count)
        return failure<PackedCipherRead>(CustodyFileError::invalidInput);
    auto retained = shared_from_this();
    CustodyNativeJob job;
    if (!job)
        return failure<PackedCipherRead>(CustodyFileError::allocationFailed);
    std::lock_guard<std::mutex> lock(state_->mutex);
    try {
        if (state_->fault != CustodyFileError::none)
            return failure<PackedCipherRead>(state_->fault, state_->nativeError);
        CustodyPin pin;
        if (!pin) return failure<PackedCipherRead>(CustodyFileError::allocationFailed);
        // Debug vector construction can allocate its charged iterator proxy.
        // Pin admission and the entire exception boundary precede that allocation.
        // Count construction (even zero) is potentially throwing. MSVC's
        // default vector constructor is noexcept despite its Debug proxy IO.
        PackedCipherRead result{CustodyBytes(0), std::move(pin), {}};
        if (!state_->check())
            return failure<PackedCipherRead>(state_->fault, state_->nativeError);
        auto bytes = state_->read(offset, count);
        if (!bytes.ok())
            return failure<PackedCipherRead>(bytes.error, bytes.nativeError);
        if (!state_->check())
            return failure<PackedCipherRead>(state_->fault, state_->nativeError);
        result.owner = std::move(retained);
        result.bytes = std::move(*bytes.value);
        return success(std::move(result));
    } catch (const std::bad_alloc &) {
        if (state_->fault == CustodyFileError::none)
            state_->fault = CustodyFileError::allocationFailed;
        return failure<PackedCipherRead>(state_->fault, state_->nativeError);
    }
#endif
}

CustodyFileResult<std::uint64_t> ProtectedPackedCustodyOwner::appendPosition() {
#ifndef _WIN32
    return failure<std::uint64_t>(CustodyFileError::unsupportedPlatform);
#else
    const auto retained = shared_from_this();
    CustodyNativeJob job;
    if (!job)
        return failure<std::uint64_t>(CustodyFileError::allocationFailed);
    std::lock_guard<std::mutex> lock(state_->mutex);
    try {
        if (state_->fault != CustodyFileError::none)
            return failure<std::uint64_t>(state_->fault, state_->nativeError);
        if (!state_->check())
            return failure<std::uint64_t>(state_->fault, state_->nativeError);
        const auto length = state_->size();
        if (!length.ok())
            return length;
        if (*length.value < ProtectedPackedCustodyFormat::appendOffset ||
            *length.value > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) - 15) {
            state_->fail(CustodyFileError::invalidContent);
            return failure<std::uint64_t>(state_->fault, state_->nativeError);
        }
        return success((*length.value + 15) & ~std::uint64_t{15});
    } catch (const std::bad_alloc &) {
        if (state_->fault == CustodyFileError::none)
            state_->fault = CustodyFileError::allocationFailed;
        return failure<std::uint64_t>(state_->fault, state_->nativeError);
    }
#endif
}

CustodyFileResult<std::uint32_t> ProtectedPackedCustodyOwner::append(const PackedRecordAddress &address, const CustodyBytes &envelope) {
#ifndef _WIN32
    (void)address;
    (void)envelope;
    return failure<std::uint32_t>(CustodyFileError::unsupportedPlatform);
#else
    const auto retained = shared_from_this();
    CustodyNativeJob job;
    if (!job)
        return failure<std::uint32_t>(CustodyFileError::allocationFailed);
    auto group = state_->files->lockWriteGroup();
    std::lock_guard<std::mutex> lock(state_->mutex);
    return appendLocked(address, envelope);
#endif
}

CustodyFileResult<std::uint32_t> ProtectedPackedCustodyOwner::appendLocked(
    const PackedRecordAddress& address, const CustodyBytes& envelope) {
#ifndef _WIN32
    (void)address; (void)envelope;
    return failure<std::uint32_t>(CustodyFileError::unsupportedPlatform);
#else
    try {
        if (!state_->writable || state_->fault != CustodyFileError::none)
            return failure<std::uint32_t>(state_->fault == CustodyFileError::none ? CustodyFileError::writerFailed : state_->fault,
                                          state_->nativeError);
        if (!state_->check())
            return failure<std::uint32_t>(state_->fault, state_->nativeError);
        const auto length = state_->size();
        if (!length.ok())
            return failure<std::uint32_t>(length.error, length.nativeError);
        if (*length.value < ProtectedPackedCustodyFormat::appendOffset ||
            *length.value > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) - 15 ||
            address.offset != ((*length.value + 15) & ~std::uint64_t{15}) || address.kind == PackedRecordKind::head ||
            envelope.size() > ProtectedPackedCustodyFormat::blockBytes + 4096 ||
            address.offset > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()) - envelope.size())
            return failure<std::uint32_t>(CustodyFileError::invalidInput);
        const auto digest = custody_detail::digest(envelope.data(), envelope.size());
        if (!digest) {
            state_->fail(CustodyFileError::hashFailed);
            return failure<std::uint32_t>(state_->fault);
        }
        const PackedReference ref{address.kind,
                                  static_cast<std::uint32_t>(envelope.size()),
                                  address.offset,
                                  address.version,
                                  address.kind == PackedRecordKind::data ? address.bodyBytes : 0,
                                  *digest};
        {
            auto decoded = ProtectedPackedCustodyCodec::openReferenced(state_->context, address.selector, ref, envelope);
            if (!decoded.ok()) {
                state_->fail(codecFileError(decoded.error), decoded.nativeError);
                return failure<std::uint32_t>(state_->fault, state_->nativeError);
            }
            custody_detail::WipeBytes wipe{decoded.value->body};
            if (decoded.value->body.size() != address.bodyBytes) {
                state_->fail(CustodyFileError::invalidContent);
                return failure<std::uint32_t>(state_->fault);
            }
        }
        const auto reserve = state_->files->checkWriteReserve(envelope.size() + 15, 0);
        if (!reserve.ok()) {
            state_->fail(reserve.error, reserve.nativeError);
            return failure<std::uint32_t>(state_->fault, state_->nativeError);
        }
        std::array<std::uint8_t, 15> zero{};
        const auto padding = static_cast<std::size_t>(address.offset - *length.value);
        if ((padding && !state_->transfer(true, *length.value, zero.data(), padding)) ||
            !state_->transfer(true, address.offset, const_cast<std::uint8_t *>(envelope.data()), envelope.size()) || !state_->check())
            return failure<std::uint32_t>(state_->fault, state_->nativeError);
        return success(static_cast<std::uint32_t>(envelope.size())); // Written, NOT durable logical ACK.
    } catch (const std::bad_alloc &) {
        if (state_->fault == CustodyFileError::none)
            state_->fault = CustodyFileError::allocationFailed;
        return failure<std::uint32_t>(state_->fault, state_->nativeError);
    }
#endif
}

CustodyFileResult<bool> ProtectedPackedCustodyOwner::flush() {
#ifndef _WIN32
    return failure<bool>(CustodyFileError::unsupportedPlatform);
#else
    const auto retained = shared_from_this();
    CustodyNativeJob job;
    if (!job)
        return failure<bool>(CustodyFileError::allocationFailed);
    auto group = state_->files->lockWriteGroup();
    std::lock_guard<std::mutex> lock(state_->mutex);
    return flushLocked();
#endif
}

CustodyFileResult<bool> ProtectedPackedCustodyOwner::flushLocked() {
#ifndef _WIN32
    return failure<bool>(CustodyFileError::unsupportedPlatform);
#else
    try {
        if (!state_->writable || state_->fault != CustodyFileError::none)
            return failure<bool>(state_->fault == CustodyFileError::none ? CustodyFileError::writerFailed : state_->fault,
                                 state_->nativeError);
        if (!state_->check() || !state_->flush() || !state_->check())
            return failure<bool>(state_->fault, state_->nativeError);
        return success(true);
    } catch (const std::bad_alloc &) {
        if (state_->fault == CustodyFileError::none)
            state_->fault = CustodyFileError::allocationFailed;
        return failure<bool>(state_->fault, state_->nativeError);
    }
#endif
}

CustodyPublishResult ProtectedPackedCustodyOwner::publishHead(std::uint32_t slot, const CustodyBytes &envelope) {
#ifndef _WIN32
    (void)slot;
    (void)envelope;
    return {CustodyPublishState::notPublished, CustodyFileError::unsupportedPlatform, 0};
#else
    const auto retained = shared_from_this();
    CustodyNativeJob job;
    if (!job)
        return {CustodyPublishState::notPublished, CustodyFileError::allocationFailed, 0};
    auto group = state_->files->lockWriteGroup();
    std::lock_guard<std::mutex> lock(state_->mutex);
    return publishHeadLocked(slot, envelope);
#endif
}

CustodyPublishResult ProtectedPackedCustodyOwner::publishHeadLocked(std::uint32_t slot, const CustodyBytes& envelope) {
#ifndef _WIN32
    (void)slot; (void)envelope;
    return {CustodyPublishState::notPublished, CustodyFileError::unsupportedPlatform, 0};
#else
    try {
        if (!state_->writable || state_->fault != CustodyFileError::none)
            return {state_->headAttempted ? CustodyPublishState::ambiguous : CustodyPublishState::notPublished,
                    state_->fault == CustodyFileError::none ? CustodyFileError::writerFailed : state_->fault, state_->nativeError};
        if (!state_->check())
            return {CustodyPublishState::notPublished, state_->fault, state_->nativeError};
        {
            auto decoded = ProtectedPackedCustodyCodec::openHead(state_->context, slot, envelope);
            if (!decoded.ok()) {
                state_->fail(codecFileError(decoded.error), decoded.nativeError);
                return {CustodyPublishState::notPublished, state_->fault, state_->nativeError};
            }
            custody_detail::WipeBytes wipe{decoded.value->body};
        }
        // Allocate independent readback before the ambiguous write boundary.
        CustodyBytes readback(16384);
        const auto offset = 128 + slot * 16384ULL;
        state_->headAttempted = true;
        if (!state_->transfer(true, offset, const_cast<std::uint8_t *>(envelope.data()), envelope.size()) || !state_->flush() ||
            !state_->transfer(false, offset, readback.data(), readback.size()) || !state_->check())
            return {CustodyPublishState::ambiguous, state_->fault, state_->nativeError};
        if (readback != envelope) {
            state_->fail(CustodyFileError::invalidContent);
            return {CustodyPublishState::ambiguous, state_->fault, state_->nativeError};
        }
        state_->headAttempted = false;
        return {CustodyPublishState::published, CustodyFileError::none, 0}; // Only this cell, never paired logical commit.
    } catch (const std::bad_alloc &) {
        if (state_->fault == CustodyFileError::none)
            state_->fault = CustodyFileError::allocationFailed;
        return {state_->headAttempted ? CustodyPublishState::ambiguous : CustodyPublishState::notPublished, state_->fault,
                state_->nativeError};
    }
#endif
}

void ProtectedPackedCustodyOwner::revokeWrites() noexcept {
    std::lock_guard<std::mutex> lock(state_->mutex);
    state_->writable = false;
}
void ProtectedPackedCustodyOwner::blockWrites() noexcept {
    std::lock_guard<std::mutex> lock(state_->mutex);
    if (state_->fault == CustodyFileError::none)
        state_->fault = CustodyFileError::recoveryRequired;
}

} // namespace graf::windows
