#include "NativeSettingsBridge.h"

namespace graf::windows::NativeSettingsBridge {
namespace {

// JSON string escaping for the reply. Only the characters JSON itself gives a
// meaning to are rewritten; UTF-8 is left as it is, so a target name in Russian
// reaches the page as the same text the page shows.
std::string escape(std::string_view value) {
    std::string result;
    result.reserve(value.size() + 8);
    for (const char character : value) {
        switch (character) {
        case '"': result += "\\\""; break;
        case '\\': result += "\\\\"; break;
        case '\n': result += "\\n"; break;
        case '\r': result += "\\r"; break;
        case '\t': result += "\\t"; break;
        default:
            if (static_cast<unsigned char>(character) < 0x20) {
                constexpr char digits[] = "0123456789abcdef";
                result += "\\u00";
                result += digits[(static_cast<unsigned char>(character) >> 4) & 0x0F];
                result += digits[static_cast<unsigned char>(character) & 0x0F];
            } else {
                result += character;
            }
        }
    }
    return result;
}

std::string quoted(std::string_view value) {
    std::string result = "\"";
    result += escape(value);
    result += "\"";
    return result;
}

} // namespace

std::optional<Action> actionFromToken(std::string_view token) noexcept {
    if (token == "read") return Action::read;
    if (token == "set") return Action::set;
    if (token == "setAll") return Action::setAll;
    return std::nullopt;
}

std::string_view actionToken(Action action) noexcept {
    switch (action) {
    case Action::read: return "read";
    case Action::set: return "set";
    case Action::setAll: return "setAll";
    }
    return "read";
}

bool isRule(std::string_view token) noexcept {
    return token == "always" || token == "ask" || token == "never";
}

namespace {

// The path of an address, and only if the address carries neither a query nor a
// fragment: those are not the documents the pages are bridged for.
std::optional<std::string_view> plainPath(std::string_view url) noexcept {
    const auto schemeEnd = url.find("://");
    if (schemeEnd == std::string_view::npos) return std::nullopt;
    const auto pathStart = url.find('/', schemeEnd + 3);
    if (pathStart == std::string_view::npos) return std::nullopt;
    const auto remainder = url.substr(pathStart);
    if (remainder.find('?') != std::string_view::npos) return std::nullopt;
    if (remainder.find('#') != std::string_view::npos) return std::nullopt;
    return remainder;
}

} // namespace

bool isRecordingSettingsRoute(std::string_view url) noexcept {
    const auto path = plainPath(url);
    return path && *path == "/desktop/settings/recording";
}

bool isNotificationSettingsRoute(std::string_view url) noexcept {
    const auto path = plainPath(url);
    return path && *path == "/desktop/settings/notifications";
}

bool isSettingsRoute(std::string_view url) noexcept {
    return isRecordingSettingsRoute(url) || isNotificationSettingsRoute(url);
}

std::string settingsReply(const std::vector<Target>& targets) {
    std::string result = "{\"version\":1,\"targets\":[";
    bool first = true;
    for (const auto& target : targets) {
        // A target that would not survive the page's validation is left out
        // rather than sent: the page discards the whole reply over one bad row,
        // and then the page would show nothing at all.
        if (target.id.empty() || !isRule(target.rule)) continue;
        if (!first) result += ",";
        first = false;
        result += "{\"id\":";
        result += quoted(target.id);
        result += ",\"name\":";
        result += quoted(target.name.empty() ? target.id : target.name);
        result += ",\"rule\":";
        result += quoted(target.rule);
        result += "}";
    }
    result += "]}";
    return result;
}

std::string notificationSettingsReply(std::string_view permission) {
    // Every false here is a fact about this platform, not a placeholder: Windows
    // keeps recording feedback inside the app and has no local meeting reminders,
    // so there is nothing to switch on, nothing to test and no system permission
    // to ask for. `canEdit` false is what makes the page show that instead of
    // controls that would save into nowhere.
    std::string result = "{\"version\":1,\"preferences\":{\"reminders\":false,\"showTitles\":false,\"sound\":false,\"offsetMinutes\":0},";
    result += "\"canEdit\":false,\"canRequestPermission\":false,\"permission\":";
    result += quoted(permission.empty() ? "Windows: напоминания о встречах в приложении не поддерживаются." : permission);
    result += "}";
    return result;
}

std::string failureReply(std::string_view message) {
    std::string result = "{\"version\":1,\"error\":";
    result += quoted(message.empty() ? "Не удалось выполнить действие." : message);
    result += "}";
    return result;
}

std::string_view documentScript() noexcept {
    return R"JS(
(() => {
  if (window.__grafNativeSettingsInstalled) return;
  window.__grafNativeSettingsInstalled = true;
  const pending = new Map();
  let nextRequestId = 1;
  // The reply arrives as a window message; the promise the page awaits is
  // resolved here, because the page expects a promise from postMessage.
  window.addEventListener('graf:native-settings-reply', (event) => {
    const detail = event.detail;
    if (!detail || typeof detail.requestId !== 'number') return;
    const entry = pending.get(detail.requestId);
    if (!entry) return;
    pending.delete(detail.requestId);
    if (detail.payload) entry.resolve(detail.payload);
    else entry.reject(new Error('unavailable'));
  });
  const handler = (name) => ({
    postMessage: (request) => new Promise((resolve, reject) => {
      const requestId = nextRequestId++;
      pending.set(requestId, {resolve, reject});
      window.dispatchEvent(new CustomEvent('graf:native-settings', {
        detail: {handler: name, requestId, request}
      }));
    })
  });
  window.webkit = window.webkit || {};
  window.webkit.messageHandlers = window.webkit.messageHandlers || {};
  // Only the handlers this app can answer are installed.
  window.webkit.messageHandlers.grafRecordingSettings = handler('grafRecordingSettings');
  window.webkit.messageHandlers.grafNotificationSettings = handler('grafNotificationSettings');
})();
)JS";
}

} // namespace graf::windows::NativeSettingsBridge
