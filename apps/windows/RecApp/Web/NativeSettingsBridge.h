#pragma once

#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace graf::windows::NativeSettingsBridge {

// The cabinet's settings pages talk to the app the way macOS lets them talk to it:
//
//   window.webkit.messageHandlers.<handler>.postMessage({version, nonce, action, ...})
//
// is answered with `{version: 1, ...}`, and the page refuses any other answer
// (`cabinet.js`, `nativeSettingsQueue`). macOS implements that protocol natively;
// Windows reaches the same protocol through the desktop bridge, so the shim, the
// request vocabulary and the reply shape live here and the pages stay unchanged.

// The automatic-recording page: the app stores these rules, so the page reads and
// writes them through here.
inline constexpr std::string_view kRecordingSettingsHandler = "grafRecordingSettings";
// The notification page. Windows has no local meeting reminders, so this page is
// answered with that truth and stays read-only rather than offering controls whose
// promises nothing would keep.
inline constexpr std::string_view kNotificationSettingsHandler = "grafNotificationSettings";

// The actions the page sends. `read` is what it sends first and after every save;
// `set` and `setAll` are its two ways of saving an edit.
enum class Action { read, set, setAll };
[[nodiscard]] std::optional<Action> actionFromToken(std::string_view token) noexcept;
[[nodiscard]] std::string_view actionToken(Action action) noexcept;

// The rule vocabulary belongs to the page and to the stored preference alike:
// the page refuses anything outside these three words, and the app persists
// exactly these three.
[[nodiscard]] bool isRule(std::string_view token) noexcept;

struct Target {
    // Stable shared-catalog product ID. The page treats it as opaque and uses it
    // as the key of an edit, so it must be stable across restarts.
    std::string id;
    // What the page prints next to the control.
    std::string name;
    // One of the three rules above.
    std::string rule;
};

// The reply the page validates before it shows or saves anything. A reply that is
// missing a target, misnames a field or carries an unknown rule is discarded by
// the page, so the shape has exactly one definition.
[[nodiscard]] std::string settingsReply(const std::vector<Target>& targets);

// A refusal is answered, never dropped. The page waits fifteen seconds for a
// reply and then says that settings could not be loaded; answering with the reason
// is what lets it say something true instead.
[[nodiscard]] std::string failureReply(std::string_view message);

// The reply the notification page validates. It is a statement, not a preference
// surface: the page disables its controls when `canEdit` is false, and the reason
// is printed where the page shows the permission state.
[[nodiscard]] std::string notificationSettingsReply(std::string_view permission);

// The paths whose documents may use the bridge, with no query and no fragment, the
// same routes macOS bridges.
[[nodiscard]] bool isRecordingSettingsRoute(std::string_view url) noexcept;
[[nodiscard]] bool isNotificationSettingsRoute(std::string_view url) noexcept;
// True for either settings page the bridge serves.
[[nodiscard]] bool isSettingsRoute(std::string_view url) noexcept;

// Installed with the document, and only when the app can answer it: a page that
// asks and never hears back would wait fifteen seconds and then report a failure
// the app caused.
[[nodiscard]] std::string_view documentScript() noexcept;

} // namespace graf::windows::NativeSettingsBridge
