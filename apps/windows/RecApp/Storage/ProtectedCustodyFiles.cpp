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
    for (const auto& part : path.relative_path()) {
        const auto& name = part.native();
        if (name.empty() || name == L"." || name == L".." || name.back() == L'.' || name.back() == L' ') return false;
    }
    const auto drive = path.root_path().wstring();
    DWORD flags = 0;
    return GetDriveTypeW(drive.c_str()) == DRIVE_FIXED
        && GetVolumeInformationW(drive.c_str(), nullptr, 0, nullptr, nullptr, &flags, nullptr, 0)
        && (flags & FILE_PERSISTENT_ACLS) != 0;
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
    return L"block." + std::to_wstring(position) + L"." + std::to_wstring(version);
}
std::wstring indexName(std::uint32_t slot) { return L"index." + std::to_wstring(slot); }
using RenameFile = NTSTATUS (NTAPI*)(HANDLE, PIO_STATUS_BLOCK, PVOID, ULONG, FILE_INFORMATION_CLASS);
// Documented FileRenameInformation=10; the user-mode SDK's partial enum omits it.
constexpr auto nativeRenameInformation = static_cast<FILE_INFORMATION_CLASS>(10);
// Native rename record, used only as an API argument, never as persisted bytes.
struct RenameInfo { BOOLEAN replace; HANDLE root; ULONG nameBytes; WCHAR name[1]; };
#endif
}

struct ProtectedCustodyFiles::State {
    CustodyContext context;
    bool writable = false;
    bool failed = false;
#ifdef _WIN32
    std::filesystem::path directory;
    std::vector<std::uint8_t> tokenUser;
    LocalMemory descriptor;
    SECURITY_ATTRIBUTES security{sizeof(SECURITY_ATTRIBUTES), nullptr, FALSE};
    struct Directory { std::filesystem::path path; bool privateDirectory; Handle handle; };
    std::vector<Directory> directories;
    std::filesystem::path trustedRoot;
    Handle storeId;
    Handle objectId;

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
        const auto sddl = std::wstring(L"D:P(A;OICI;FA;;;") + static_cast<wchar_t*>(text.value) + L")";
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
        const auto wanted = std::wstring(L"\\\\?\\") + expected.wstring();
        return count > 0 && count < 32768 && wanted.size() <= static_cast<std::size_t>(std::numeric_limits<int>::max())
            && CompareStringOrdinal(actual, static_cast<int>(count), wanted.c_str(), static_cast<int>(wanted.size()), TRUE) == CSTR_EQUAL
            && (!privateFile || privateAcl(file));
    }
    CustodyFileResult<Handle> openFile(const std::filesystem::path& path, DWORD access, DWORD share) const {
        Handle file(CreateFileW(path.c_str(), access | READ_CONTROL, share, nullptr, OPEN_EXISTING,
            FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (!file.valid()) return failure<Handle>(CustodyFileError::ioFailed, GetLastError());
        if (!inspect(file.value, path, false, true)) return failure<Handle>(CustodyFileError::unsafeFile);
        return success(std::move(file));
    }
    CustodyFileResult<bool> lockDirectory(const std::filesystem::path& path, bool privateDirectory, bool create) {
        if (create && !CreateDirectoryW(path.c_str(), &security) && GetLastError() != ERROR_ALREADY_EXISTS)
            return failure<bool>(CustodyFileError::ioFailed, GetLastError());
        // Hold every ancestor without share-write/delete until the object closes.
        // Checking only the final path before opening leaves reparse/rename races.
        // FILE_LIST_DIRECTORY participates in sharing checks. Attribute/control
        // access alone does NOT acquire the share-write/delete exclusion.
        Handle dir(CreateFileW(path.c_str(), READ_CONTROL | FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY, FILE_SHARE_READ, nullptr,
            OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
        if (!dir.valid()) return failure<bool>(CustodyFileError::ioFailed, GetLastError());
        if (!inspect(dir.value, path, true, privateDirectory)) return failure<bool>(CustodyFileError::unsafePath);
        directories.push_back({path, privateDirectory, std::move(dir)}); return success(true);
    }
    CustodyFileResult<bool> identity(Handle& file, const std::filesystem::path& path, const CustodyId& expected, bool writer) {
        auto opened = openFile(path, GENERIC_READ | (writer ? GENERIC_WRITE : 0),
            FILE_SHARE_READ | (writer ? 0 : FILE_SHARE_WRITE));
        if (!opened.ok()) return failure<bool>(opened.error, opened.nativeError);
        LARGE_INTEGER size{}; DWORD got = 0; CustodyId actual{};
        if (!GetFileSizeEx(opened.value->value, &size) || size.QuadPart != 16
            || !ReadFile(opened.value->value, actual.data(), 16, &got, nullptr) || got != 16 || actual != expected)
            return failure<bool>(CustodyFileError::identityMismatch);
        file = std::move(*opened.value); return success(true);
    }
    CustodyFileResult<Handle> create(const std::filesystem::path& path, const std::uint8_t* bytes,
                                    std::uint32_t size, bool renameable = false) const {
        Handle file(CreateFileW(path.c_str(), GENERIC_READ | GENERIC_WRITE | READ_CONTROL | (renameable ? DELETE : 0),
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

CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> ProtectedCustodyFiles::open(
    const std::filesystem::path& root, std::string_view package, const CustodyContext& context, CustodyFileAccess access) try {
    using Result = std::unique_ptr<ProtectedCustodyFiles>;
#ifndef _WIN32
    (void)root; (void)package; (void)context; (void)access;
    return failure<Result>(CustodyFileError::unsupportedPlatform);
#else
    const bool service = context.role == CustodyRole::queue || context.role == CustodyRole::bootstrap
        || (context.role == CustodyRole::migrationIntent && package.empty());
    if (!roleName(context.role) || (service ? !package.empty() : !DesktopUploadQueueService::validIdentity(package))
        || (access != CustodyFileAccess::readExisting && access != CustodyFileAccess::writeExisting && access != CustodyFileAccess::createNew))
        return failure<Result>(CustodyFileError::invalidInput);
    if (!localPath(root)) return failure<Result>(CustodyFileError::unsafePath);
    auto state = std::make_unique<State>(); state->context = context;
    state->trustedRoot = root;
    state->writable = access != CustodyFileAccess::readExisting;
    if (!state->initializeSecurity()) return failure<Result>(CustodyFileError::ioFailed, GetLastError());
    auto path = root.root_path();
    auto locked = state->lockDirectory(path, false, false);
    if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    for (const auto& part : root.relative_path()) {
        path /= part;
        locked = state->lockDirectory(path, path == root, false);
        if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    }
    path = root / L".custody-v1";
    locked = state->lockDirectory(path, true, false);
    if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    auto identified = state->identity(state->storeId, path / L"store.id", context.storeId, false);
    if (!identified.ok()) return failure<Result>(identified.error, identified.nativeError);
    if (!service) {
        path = root / std::string(package);
        locked = state->lockDirectory(path, true, false);
        if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
        path /= L".custody-v1";
        locked = state->lockDirectory(path, true, access == CustodyFileAccess::createNew);
        if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    }
    state->directory = path / roleName(context.role);
    if (access == CustodyFileAccess::createNew && !CreateDirectoryW(state->directory.c_str(), &state->security)) {
        const auto error = GetLastError();
        return failure<Result>(error == ERROR_ALREADY_EXISTS ? CustodyFileError::conflict : CustodyFileError::ioFailed, error);
    }
    locked = state->lockDirectory(state->directory, true, false);
    if (!locked.ok()) return failure<Result>(locked.error, locked.nativeError);
    const auto idPath = state->directory / L"id.bin";
    if (access == CustodyFileAccess::createNew) {
        auto created = state->create(idPath, context.objectId.data(), 16);
        if (!created.ok()) return failure<Result>(created.error, created.nativeError);
    }
    identified = state->identity(state->objectId, idPath, context.objectId, state->writable);
    if (!identified.ok()) return failure<Result>(identified.error, identified.nativeError);
    return success(Result(new ProtectedCustodyFiles(std::move(state))));
#endif
} catch (const std::bad_alloc&) {
    return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::allocationFailed);
} catch (const std::filesystem::filesystem_error&) {
    return failure<std::unique_ptr<ProtectedCustodyFiles>>(CustodyFileError::unsafePath);
}

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
    auto result = state_->read(state_->directory / blockName(position, version), limit, exact);
    if (!result.ok()) return result;
    auto decoded = ProtectedCustodyCodec::openBlock(state_->context, position, version, payload, *result.value);
    if (!decoded.ok()) return failure<CustodyBytes>(codecFileError(decoded.error), decoded.nativeError);
    WipePlain wipe{*decoded.value}; return result;
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
    auto created = state_->create(state_->directory / blockName(position, version), envelope.data(), size);
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
    Search search{FindFirstFileW((state_->directory / (prefix + L"*")).c_str(), &data)};
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
    auto bytes = state_->read(state_->directory / indexName(slot), ProtectedCustodyCodec::indexEnvelopeLimit(state_->context.role));
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

CustodyFileResult<CustodySnapshot> ProtectedCustodyFiles::readValidatedSnapshot() try {
#ifndef _WIN32
    return failure<CustodySnapshot>(CustodyFileError::unsupportedPlatform);
#else
    if (state_->failed) return failure<CustodySnapshot>(CustodyFileError::writerFailed);
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) {
        state_->failed = true;
        return failure<CustodySnapshot>(error, native);
    };
    const bool audio = state_->context.role == CustodyRole::canonical || state_->context.role == CustodyRole::media
        || state_->context.role == CustodyRole::playback;
    const bool prefixAllowed = state_->context.role == CustodyRole::canonical || state_->context.role == CustodyRole::media;
    std::array<CustodyFileResult<CustodyIndex>, 2> candidates;
    std::array<bool, 2> missingSlot{};
    for (std::uint32_t slot = 0; slot < 2; ++slot) {
        auto cipher = state_->read(state_->directory / indexName(slot), ProtectedCustodyCodec::indexEnvelopeLimit(state_->context.role));
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
    if (both || missingSlot[other])
        return success(CustodySnapshot{std::move(*candidates[selected].value), CustodySnapshotState::verified, CustodyFileError::none, 0});
    if (!prefixAllowed) return reject(candidates[other].error, candidates[other].nativeError);
    state_->failed = true; // Retained prefix never authorizes a next generation/GC/effects.
    return success(CustodySnapshot{std::move(*candidates[selected].value), CustodySnapshotState::trustedPrefix,
        candidates[other].error, candidates[other].nativeError});
#endif
} catch (const std::bad_alloc&) {
    state_->failed = true;
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
        HANDLE search = FindFirstStreamW(name.c_str(), FindStreamInfoStandard, &data, 0);
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
        for (const auto& directory : confined.directories) {
            if (!confined.inspect(directory.handle.value, directory.path, true, directory.privateDirectory))
                return fail(CustodyFileError::unsafePath);
            if (!streams(directory.path, true)) return false;
        }
        const std::array<HANDLE, 3> handles{content.value, confined.storeId.value, confined.objectId.value};
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

ProtectedPackedCustodyOwner::Guard::Guard(std::shared_ptr<ProtectedPackedCustodyOwner> owner)
    : owner_(std::move(owner)), lock_(owner_->state_->mutex, std::defer_lock) {
    if (job_) lock_.lock(); // Admission BEFORE waiting on the physical owner.
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

CustodyFileResult<std::shared_ptr<ProtectedPackedCustodyOwner>> ProtectedPackedCustodyOwner::open(
    const std::filesystem::path& root, std::string_view package, const PackedCustodyContext& context, CustodyFileAccess access) try {
    using Owner = std::shared_ptr<ProtectedPackedCustodyOwner>;
#ifndef _WIN32
    (void)root; (void)package; (void)context; (void)access;
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
    auto opened = ProtectedCustodyFiles::open(root, package, context.object,
        access == CustodyFileAccess::createNew ? access : CustodyFileAccess::writeExisting);
    if (!opened.ok()) return failure<Owner>(opened.error, opened.nativeError);
    state->files = std::move(*opened.value);
    auto& confined = *state->files->state_;
    // Upgrade the immutable store-ID handle before any packed content effects.
    auto store = confined.openFile(root / L".custody-v1" / L"store.id", GENERIC_READ, FILE_SHARE_READ);
    if (!store.ok()) return failure<Owner>(store.error, store.nativeError);
    confined.storeId = std::move(*store.value);
    CustodyId storeBytes{}; DWORD got = 0; LARGE_INTEGER storeSize{}; OVERLAPPED storeOffset{};
    if (!GetFileSizeEx(confined.storeId.value, &storeSize) || storeSize.QuadPart != 16 ||
        !ReadFile(confined.storeId.value, storeBytes.data(), 16, &got, &storeOffset) || got != 16 || storeBytes != context.object.storeId)
        return failure<Owner>(CustodyFileError::identityMismatch);
    state->path = confined.directory / L"content.packed-v2";
    const auto reserve = access == CustodyFileAccess::createNew
        ? state->files->checkWriteReserve(ProtectedPackedCustodyFormat::appendOffset, 1)
        : success<std::uint64_t>(0);
    if (!reserve.ok()) return failure<Owner>(reserve.error, reserve.nativeError);
    state->content = Handle(CreateFileW(state->path.c_str(), GENERIC_READ | GENERIC_WRITE | READ_CONTROL, FILE_SHARE_READ,
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
    std::lock_guard<std::mutex> lock(state_->mutex);
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
    std::lock_guard<std::mutex> lock(state_->mutex);
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
    std::lock_guard<std::mutex> lock(state_->mutex);
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
