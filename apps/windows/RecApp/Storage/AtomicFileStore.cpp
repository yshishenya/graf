#include "AtomicFileStore.h"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

#ifdef _WIN32
#include <aclapi.h>
#include <windows.h>
#endif

namespace graf::windows {
namespace {

std::filesystem::path temporaryPath(const std::filesystem::path& target) {
    static std::atomic_uint64_t counter{0};
    const auto ticks = std::chrono::steady_clock::now().time_since_epoch().count();
    std::filesystem::path temporary = target;
    temporary += ".tmp-" + std::to_string(ticks) + "-" + std::to_string(counter.fetch_add(1));
    return temporary;
}

bool replaceAtomically(const std::filesystem::path& temporary, const std::filesystem::path& target) {
#ifdef _WIN32
    return MoveFileExW(
        temporary.c_str(),
        target.c_str(),
        MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
    return std::rename(temporary.c_str(), target.c_str()) == 0;
#endif
}

bool applyUserOnlyAcl(const std::filesystem::path& path) {
#ifndef _WIN32
    (void)path;
    return true;
#else
    HANDLE token = nullptr;
    if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &token)) return false;
    DWORD size = 0;
    GetTokenInformation(token, TokenUser, nullptr, 0, &size);
    if (size == 0) {
        CloseHandle(token);
        return false;
    }
    std::vector<std::byte> buffer(size);
    const bool read = GetTokenInformation(token, TokenUser, buffer.data(), size, &size) != 0;
    CloseHandle(token);
    if (!read) return false;

    auto* user = reinterpret_cast<const TOKEN_USER*>(buffer.data());
    EXPLICIT_ACCESSW access{};
    access.grfAccessPermissions = GENERIC_ALL;
    access.grfAccessMode = SET_ACCESS;
    access.grfInheritance = SUB_CONTAINERS_AND_OBJECTS_INHERIT;
    access.Trustee.TrusteeForm = TRUSTEE_IS_SID;
    access.Trustee.TrusteeType = TRUSTEE_IS_USER;
    access.Trustee.ptstrName = reinterpret_cast<LPWSTR>(user->User.Sid);

    PACL acl = nullptr;
    if (SetEntriesInAclW(1, &access, nullptr, &acl) != ERROR_SUCCESS) return false;
    const auto result = SetNamedSecurityInfoW(
        const_cast<LPWSTR>(path.c_str()), SE_FILE_OBJECT,
        DACL_SECURITY_INFORMATION | PROTECTED_DACL_SECURITY_INFORMATION,
        nullptr, nullptr, acl, nullptr);
    LocalFree(acl);
    return result == ERROR_SUCCESS;
#endif
}

AtomicFileResult writeUnchecked(
    const std::filesystem::path& target,
    std::string_view bytes,
    std::size_t maximumBytes) {
    if (target.empty() || target.filename().empty()) {
        return {AtomicFileError::invalidPath};
    }
    if (bytes.size() > maximumBytes) {
        return {AtomicFileError::tooLarge};
    }

    std::error_code error;
    if (!target.parent_path().empty()) {
        std::filesystem::create_directories(target.parent_path(), error);
        if (error) {
            return {AtomicFileError::openFailed};
        }
    }

    const auto temporary = temporaryPath(target);
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        if (!output.is_open()) {
            return {AtomicFileError::openFailed};
        }
        output.write(bytes.data(), static_cast<std::streamsize>(bytes.size()));
        output.flush();
        if (!output.good()) {
            output.close();
            std::filesystem::remove(temporary, error);
            return {AtomicFileError::writeFailed};
        }
    }

    if (!applyUserOnlyAcl(temporary)) {
        std::filesystem::remove(temporary, error);
        return {AtomicFileError::permissionFailed};
    }
    if (!replaceAtomically(temporary, target)) {
        std::filesystem::remove(temporary, error);
        return {AtomicFileError::replaceFailed};
    }
    if (!applyUserOnlyAcl(target)) return {AtomicFileError::permissionFailed};
    return {};
}

} // namespace

bool AtomicFileStore::isWithinRoot(
    const std::filesystem::path& root,
    const std::filesystem::path& target) noexcept {
    if (root.empty() || target.empty()) return false;
    std::error_code error;
    const auto canonicalRoot = std::filesystem::weakly_canonical(root, error);
    if (error) return false;
    error.clear();
    const auto canonicalTarget = std::filesystem::weakly_canonical(target, error);
    if (error || canonicalTarget == canonicalRoot) return false;
    const auto relative = std::filesystem::relative(canonicalTarget, canonicalRoot, error);
    if (error || relative.empty() || relative == ".") return false;
    auto it = relative.begin();
    return it == relative.end() || *it != "..";
}

AtomicFileResult AtomicFileStore::write(
    const std::filesystem::path& target,
    std::string_view bytes,
    std::size_t maximumBytes) {
    return writeUnchecked(target, bytes, maximumBytes);
}

AtomicFileResult AtomicFileStore::writeWithinRoot(
    const std::filesystem::path& root,
    const std::filesystem::path& target,
    std::string_view bytes,
    std::size_t maximumBytes) {
    if (!isWithinRoot(root, target)) return {AtomicFileError::invalidPath};
    return writeUnchecked(target, bytes, maximumBytes);
}

} // namespace graf::windows
