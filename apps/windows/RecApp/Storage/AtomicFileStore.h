#pragma once

#include <cstddef>
#include <filesystem>
#include <string_view>

namespace graf::windows {

enum class AtomicFileError {
    none,
    invalidPath,
    tooLarge,
    openFailed,
    writeFailed,
    replaceFailed,
};

struct AtomicFileResult {
    AtomicFileError error = AtomicFileError::none;

    [[nodiscard]] bool ok() const noexcept { return error == AtomicFileError::none; }
};

class AtomicFileStore final {
public:
    [[nodiscard]] static AtomicFileResult write(
        const std::filesystem::path& target,
        std::string_view bytes,
        std::size_t maximumBytes = 8 * 1024 * 1024);
};

} // namespace graf::windows
