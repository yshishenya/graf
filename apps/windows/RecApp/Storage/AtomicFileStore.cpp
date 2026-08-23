#include "AtomicFileStore.h"

#include <atomic>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <string>

#ifdef _WIN32
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

} // namespace

AtomicFileResult AtomicFileStore::write(
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

    if (!replaceAtomically(temporary, target)) {
        std::filesystem::remove(temporary, error);
        return {AtomicFileError::replaceFailed};
    }
    return {};
}

} // namespace graf::windows
