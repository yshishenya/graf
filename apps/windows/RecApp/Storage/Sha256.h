#pragma once

#include <filesystem>
#include <iosfwd>
#include <string>
#include <string_view>

namespace graf::windows {

// Provider-independent in-memory identity digest; rejects unsupported input lengths.
[[nodiscard]] std::string sha256(std::string_view bytes);
// Hash from the current cursor through EOF; empty result means a read/hash failure.
[[nodiscard]] std::string sha256Stream(std::istream& input);
[[nodiscard]] std::string sha256File(const std::filesystem::path& path);

} // namespace graf::windows
