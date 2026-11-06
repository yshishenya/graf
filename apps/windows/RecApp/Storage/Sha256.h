#pragma once

#include <filesystem>
#include <array>
#include <cstdint>
#include <iosfwd>
#include <string>
#include <string_view>
#ifdef _WIN32
#include "ProtectedCustodyFiles.h"
#include <atomic>
#include <objidl.h>
#endif

namespace graf::windows {

// Provider-independent in-memory identity digest; rejects unsupported input lengths.
[[nodiscard]] std::string sha256(std::string_view bytes);
[[nodiscard]] std::array<std::uint8_t, 32> sha256Digest(std::string_view bytes);
// Hash from the current cursor through EOF; empty result means a read/hash failure.
[[nodiscard]] std::string sha256Stream(std::istream& input);
[[nodiscard]] std::string sha256File(const std::filesystem::path& path);
#ifdef _WIN32
// Worker-only whole logical stream, initially at zero; exact length plus EOF.
// Owns stream/cancel/bounded wiped buffer through native completion. No effects.
[[nodiscard]] CustodyFileResult<std::array<std::uint8_t, 32>> sha256ProtectedStream(
    IStream*, std::uint64_t expectedLength, std::shared_ptr<const std::atomic<bool>> cancellation);
#endif

} // namespace graf::windows
