#pragma once

#ifdef _WIN32
#include <windows.h>
#include <winternl.h>
#include <sddl.h>
#include <aclapi.h>

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <string_view>
#include <utility>
#include <vector>

namespace graf::windows::local_file_detail {

struct File {
    HANDLE value = INVALID_HANDLE_VALUE;
    explicit File(HANDLE handle = INVALID_HANDLE_VALUE) : value(handle) {}
    File(File&& other) noexcept : value(std::exchange(other.value, INVALID_HANDLE_VALUE)) {}
    File(const File&) = delete;
    File& operator=(File&& other) noexcept {
        if (this != &other) {
            reset();
            value = std::exchange(other.value, INVALID_HANDLE_VALUE);
        }
        return *this;
    }
    ~File() { reset(); }
    explicit operator bool() const { return value != INVALID_HANDLE_VALUE && value != nullptr; }
    void reset() { if (*this) CloseHandle(std::exchange(value, INVALID_HANDLE_VALUE)); }
};

struct LocalMemory {
    void* value = nullptr;
    ~LocalMemory() { if (value) LocalFree(value); }
};

struct PrivateSecurity {
    LocalMemory descriptor;
    bool initialize(bool directory = false, bool userOwner = false) {
        HANDLE raw = nullptr;
        if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &raw)) return false;
        const File token(raw);
        DWORD size = 0;
        GetTokenInformation(token.value, TokenUser, nullptr, 0, &size);
        if (size == 0 || size > 65536) return false;
        std::vector<std::uint8_t> user(size);
        if (!GetTokenInformation(token.value, TokenUser, user.data(), size, &size)) return false;
        LPWSTR sid = nullptr;
        if (!ConvertSidToStringSidW(reinterpret_cast<const TOKEN_USER*>(user.data())->User.Sid, &sid)) return false;
        const LocalMemory sidMemory{sid};
        auto sddl = userOwner ? std::wstring(L"O:") + sid : std::wstring{};
        sddl += std::wstring(directory ? L"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;" : L"D:P(A;;FA;;;SY)(A;;FA;;;") +
            sid + L")";
        return ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(), SDDL_REVISION_1,
            &descriptor.value, nullptr) != FALSE;
    }
};

inline bool equalName(std::wstring_view a, std::wstring_view b) noexcept {
    return CompareStringOrdinal(a.data(), static_cast<int>(a.size()),
        b.data(), static_cast<int>(b.size()), TRUE) == CSTR_EQUAL;
}

template<typename Function>
Function nativeFunction(const char* name) {
    const auto address = GetProcAddress(GetModuleHandleW(L"ntdll.dll"), name);
    Function result = nullptr;
    static_assert(sizeof(result) == sizeof(address));
    std::memcpy(&result, &address, sizeof(result));
    return result;
}

using CreateFileRelative = NTSTATUS (NTAPI*)(PHANDLE, ACCESS_MASK, POBJECT_ATTRIBUTES, PIO_STATUS_BLOCK,
    PLARGE_INTEGER, ULONG, ULONG, ULONG, ULONG, PVOID, ULONG);

constexpr auto nameCollision = static_cast<NTSTATUS>(0xC0000035L);

inline File openRelative(HANDLE parent, std::wstring_view name, ACCESS_MASK access, ULONG share,
    ULONG disposition, ULONG type, void* security = nullptr, NTSTATUS* failure = nullptr) {
    static const auto create = nativeFunction<CreateFileRelative>("NtCreateFile");
    if (failure) *failure = static_cast<NTSTATUS>(0xC000000DL);
    if (!create || !parent || parent == INVALID_HANDLE_VALUE || name.empty() ||
        name.size() > 255 || name == L"." || name == L".." ||
        name.find_first_of(L"\\/:") != name.npos || name.find(wchar_t{}) != name.npos) return File{};
    const auto length = static_cast<USHORT>(name.size() * sizeof(wchar_t));
    UNICODE_STRING text{length, length, const_cast<PWSTR>(name.data())};
    OBJECT_ATTRIBUTES object{};
    InitializeObjectAttributes(&object, &text, OBJ_CASE_INSENSITIVE, parent, security);
    IO_STATUS_BLOCK io{};
    HANDLE result = nullptr;
    const auto status = create(&result, access | SYNCHRONIZE, &object, &io, nullptr, FILE_ATTRIBUTE_NORMAL,
        share, disposition, type | FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT, nullptr, 0);
    if (failure) *failure = status;
    if (status != 0) return File{};
    return File(result);
}

inline bool plainObject(HANDLE file, bool directory) {
    BY_HANDLE_FILE_INFORMATION info{};
    constexpr DWORD unsupported = FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_OFFLINE |
        FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS | FILE_ATTRIBUTE_RECALL_ON_OPEN;
    return GetFileType(file) == FILE_TYPE_DISK && GetFileInformationByHandle(file, &info) &&
        !(info.dwFileAttributes & unsupported) && ((info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0) == directory &&
        (directory || info.nNumberOfLinks == 1);
}

inline bool validPathComponent(std::wstring_view name) noexcept {
    if (name.empty() || name.size() > 255 || name.back() == L'.' || name.back() == L' ') return false;
    for (const auto c : name) {
        if (c < 32 || std::wstring_view(L"<>:\"/\\|?*").find(c) != std::wstring_view::npos) return false;
    }
    auto stem = name.substr(0, name.find(L'.'));
    while (!stem.empty() && stem.back() == L' ') stem.remove_suffix(1);
    for (const std::wstring_view reserved : {L"CON", L"PRN", L"AUX", L"NUL", L"CONIN$", L"CONOUT$"}) {
        if (equalName(stem, reserved)) return false;
    }
    return stem.size() != 4 || (!equalName(stem.substr(0, 3), L"COM") && !equalName(stem.substr(0, 3), L"LPT")) ||
        std::wstring_view(L"123456789\u00b9\u00b2\u00b3").find(stem.back()) == std::wstring_view::npos;
}

constexpr ACCESS_MASK directoryFlushAccess = READ_CONTROL | FILE_LIST_DIRECTORY | FILE_ADD_FILE;

inline std::vector<File> pinFixedLocalDirectory(const std::filesystem::path& path, ACCESS_MASK finalAccess = 0) {
    std::wstring_view text(path.native());
    if (text.size() < 3 || text.size() > 30000 || text[1] != L':' || text[2] != L'\\' ||
        !((text[0] >= L'A' && text[0] <= L'Z') || (text[0] >= L'a' && text[0] <= L'z'))) return {};
    const std::wstring root(text.substr(0, 3));
    if (GetDriveTypeW(root.c_str()) != DRIVE_FIXED) return {};
    const auto apiRoot = L"\\\\?\\" + root;
    constexpr auto access = FILE_TRAVERSE | FILE_READ_ATTRIBUTES;
    constexpr auto share = FILE_SHARE_READ | FILE_SHARE_WRITE;
    File rootFile(CreateFileW(apiRoot.c_str(), access | (text.size() == 3 ? finalAccess : 0), share, nullptr, OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT, nullptr));
    wchar_t actual[32]{};
    wchar_t filesystem[16]{};
    DWORD flags = 0;
    if (!rootFile || !plainObject(rootFile.value, true) ||
        GetFinalPathNameByHandleW(rootFile.value, actual, ARRAYSIZE(actual), VOLUME_NAME_DOS) != apiRoot.size() ||
        !equalName(actual, apiRoot) ||
        !GetVolumeInformationByHandleW(rootFile.value, nullptr, 0, nullptr, nullptr, &flags, filesystem, ARRAYSIZE(filesystem)) ||
        !equalName(filesystem, L"NTFS") || !(flags & FILE_PERSISTENT_ACLS) || (flags & FILE_READ_ONLY_VOLUME)) return {};
    std::vector<File> dirs;
    dirs.push_back(std::move(rootFile));
    text.remove_prefix(3);
    while (!text.empty()) {
        const auto separator = text.find(L'\\');
        const auto part = text.substr(0, separator);
        if (!validPathComponent(part)) return {};
        const auto extra = separator == text.npos ? finalAccess : 0;
        auto next = openRelative(dirs.back().value, part, access | extra, share, FILE_OPEN, FILE_DIRECTORY_FILE);
        if (!next || !plainObject(next.value, true)) return {};
        dirs.push_back(std::move(next));
        if (separator == text.npos) break;
        text.remove_prefix(separator + 1);
    }
    return dirs;
}

struct StagedFile {
    File file;
    bool published = false;
    ~StagedFile() {
        if (!file || published) return;
        FILE_DISPOSITION_INFO remove{TRUE};
        (void)SetFileInformationByHandle(file.value, FileDispositionInfo, &remove, sizeof(remove));
    }
};

inline NTSTATUS renameNoReplace(HANDLE file, std::wstring_view name) {
    using SetInfo = NTSTATUS (NTAPI*)(HANDLE, PIO_STATUS_BLOCK, PVOID, ULONG, FILE_INFORMATION_CLASS);
    static const auto set = nativeFunction<SetInfo>("NtSetInformationFile");
    if (!set || !validPathComponent(name)) return static_cast<NTSTATUS>(0xC000000DL);
    // A simple relative name and null RootDirectory rename within the same pinned directory.
    struct RenameInfo { BOOLEAN replace; HANDLE root; ULONG length; WCHAR name[256]; };
    RenameInfo info{};
    info.length = static_cast<ULONG>(name.size() * sizeof(wchar_t));
    std::copy(name.begin(), name.end(), info.name);
    IO_STATUS_BLOCK io{};
    // The user-mode SDK omits FileRenameInformation from its partial enum.
    const auto status = set(file, &io, &info, sizeof(info), static_cast<FILE_INFORMATION_CLASS>(10));
    return status == 0 ? io.Status : status;
}

inline bool privateObject(HANDLE handle, bool directory) {
    if (!plainObject(handle, directory)) return false;
    PrivateSecurity expected;
    if (!expected.initialize(directory)) return false;
    BOOL hasAcl = FALSE, defaulted = FALSE;
    PACL expectedAcl = nullptr, actual = nullptr;
    if (!GetSecurityDescriptorDacl(expected.descriptor.value, &hasAcl, &expectedAcl, &defaulted) ||
        !hasAcl || !expectedAcl || expectedAcl->AceCount != 2) return false;
    LocalMemory security;
    PSID owner = nullptr;
    if (GetSecurityInfo(handle, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION | OWNER_SECURITY_INFORMATION,
        &owner, nullptr, &actual, nullptr, &security.value) != ERROR_SUCCESS ||
        !actual || actual->AceCount != 2 || !owner) return false;
    SECURITY_DESCRIPTOR_CONTROL control{};
    DWORD revision = 0;
    if (!GetSecurityDescriptorControl(security.value, &control, &revision) || !(control & SE_DACL_PROTECTED)) return false;
    void* expectedOwnerAce = nullptr;
    if (!GetAce(expectedAcl, 1, &expectedOwnerAce) ||
        !EqualSid(owner, &static_cast<ACCESS_ALLOWED_ACE*>(expectedOwnerAce)->SidStart)) return false;
    unsigned matched = 0;
    for (DWORD i = 0; i < actual->AceCount; ++i) {
        void* raw = nullptr;
        if (!GetAce(actual, i, &raw)) return false;
        const auto* ace = static_cast<const ACCESS_ALLOWED_ACE*>(raw);
        if (ace->Header.AceType != ACCESS_ALLOWED_ACE_TYPE) return false;
        for (DWORD j = 0; j < expectedAcl->AceCount; ++j) {
            void* wanted = nullptr;
            if (!GetAce(expectedAcl, j, &wanted)) return false;
            const auto* entry = static_cast<const ACCESS_ALLOWED_ACE*>(wanted);
            if (ace->Header.AceFlags == entry->Header.AceFlags && ace->Mask == entry->Mask &&
                EqualSid(const_cast<DWORD*>(&ace->SidStart), const_cast<DWORD*>(&entry->SidStart))) matched |= 1u << j;
        }
    }
    return matched == 3;
}

} // namespace graf::windows::local_file_detail
#endif
