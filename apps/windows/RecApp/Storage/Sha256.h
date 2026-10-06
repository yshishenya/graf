#pragma once

#include <filesystem>
#include <string>
#include <string_view>

namespace graf::windows {

[[nodiscard]] std::string sha256(std::string_view bytes);
[[nodiscard]] std::string sha256File(const std::filesystem::path& path);

} // namespace graf::windows
