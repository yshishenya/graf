#pragma once
#include <optional>
#include <string>
#include <string_view>

namespace graf::windows {
struct CalendarMeetingOpener {
    // Validation only: no network, launch or current-session authority.
    // Raw input <=8192 UTF-8 bytes; normalized owned result <=32768 bytes.
    // Non-Windows builds exercise ASCII policy, not native URI/IDNA parity.
    [[nodiscard]] static std::optional<std::string> validatedHTTPS(std::string_view raw) noexcept;
    // Only approved host/path/port conversions; nil also means browser-only.
    // Telemost uses the validated HTTPS association, not a made-up URI scheme.
    [[nodiscard]] static std::optional<std::string> nativeTarget(std::string_view raw) noexcept;
};
}
