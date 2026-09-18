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
  // The cabinet's settings pages are one server page shared with macOS, so they
  // say «На этом Mac» and offer «Настройки macOS». On Windows that is simply not
  // true, and the button would lead to settings this page has no permission to
  // show. The shell corrects the words and hides that button instead of the
  // server growing a second copy of the page: a server change would also change
  // macOS, and the owner has not asked for that.
  const platformWords = [
    ['Правила автозаписи на Mac', 'Правила автозаписи в Windows'],
    ['В приложении на Mac', 'В приложении для Windows'],
    ['Уведомления на этом Mac', 'Уведомления на этом компьютере'],
    ['изменить уведомления Mac', 'изменить уведомления в приложении'],
    ['настройки этого Mac', 'настройки этого компьютера'],
    ['этого Mac', 'этого компьютера'],
    ['На этом Mac', 'На этом компьютере'],
    ['Настройки macOS', 'Настройки Windows'],
    ['разрешение macOS', 'разрешение Windows']
  ];
  // The words live outside the settings forms too: the page heading, the section
  // legend, the navigation card and the no-script note all name the Mac. Walking
  // the whole document catches them; the list is exact phrases, so nothing else
  // changes.
  const adaptPlatformWords = () => {
    try {
      const root = document.body;
      if (!root) return {found: 0, replaced: 0};
      root.querySelectorAll('[data-local-notification-action="openSystemSettings"]')
        .forEach((button) => { button.hidden = true; });
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      let found = 0;
      let replaced = 0;
      for (const node of nodes) {
        let text = node.nodeValue;
        for (const pair of platformWords) {
          if (text.indexOf(pair[0]) === -1) continue;
          found++;
          text = text.split(pair[0]).join(pair[1]);
        }
        if (text !== node.nodeValue) {
          node.nodeValue = text;
          replaced++;
        }
      }
      return {found: found, replaced: replaced};
    } catch (error) {
      return {found: 0, replaced: 0, error: String((error && error.message) || error)};
    }
  };
  // The host installs this script when the document is already under way, so a
  // single listener is not enough: the correction runs at once, on the document
  // event, on every swap and a few more times after that. The host logs an unknown
  // command, which is how this line is visible in bridge.log: without it there is
  // no way to tell «the correction found nothing» from «the correction never ran».
  const reportAdaptation = (stage) => {
    const result = adaptPlatformWords();
    try {
      // The host answers this page through the same custom event the page uses, and
      // it writes the command it refused into bridge.log. The counts travel in the
      // command name, so the log says whether the correction ran, how many phrases
      // it found and whether it threw.
      window.dispatchEvent(new CustomEvent('graf:native-settings', {
        detail: {
          handler: 'grafNotificationSettings',
          requestId: 900000 + result.found * 10 + result.replaced,
          request: {
            version: 1,
            action: 'diag_' + stage + '_f' + result.found + '_r' + result.replaced +
              (result.error ? '_err' : '')
          }
        }
      }));
    } catch (_) {}
  };
  const runAdaptation = () => {
    reportAdaptation('now');
    setTimeout(() => reportAdaptation('after-120ms'), 120);
    setTimeout(() => reportAdaptation('after-600ms'), 600);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', runAdaptation);
  else runAdaptation();
  document.addEventListener('htmx:afterSwap', () => reportAdaptation('swap'));
})();
)JS";
}

} // namespace graf::windows::NativeSettingsBridge
