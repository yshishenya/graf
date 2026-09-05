#include "WebView2Host.h"

#include "../Contracts/WindowsDesktopContracts.h"

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
#include <winrt/Windows.Data.Json.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Microsoft.Web.WebView2.Core.h>
#include <windows.h>
#include <combaseapi.h>
#include <commdlg.h>
#include <knownfolders.h>
#include <shlobj.h>
#include <shellapi.h>

#include <filesystem>
#include <iterator>
#include <cmath>
#include <optional>
#endif

namespace graf::windows {

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
namespace {

constexpr double kJsonSafeIntegerMax = 9'007'199'254'740'991.0;
constexpr double kJsonVersionMax = 4'294'967'295.0;

std::string utf8(winrt::hstring const& value) {
    return winrt::to_string(std::wstring_view(value));
}

bool isJsonUnsignedInteger(double value, double maximum) noexcept {
    return std::isfinite(value) && value >= 0.0 && value <= maximum &&
        value <= kJsonSafeIntegerMax && std::floor(value) == value;
}

std::string newNonce() {
    GUID guid{};
    if (FAILED(CoCreateGuid(&guid))) return {};
    wchar_t value[40]{};
    if (StringFromGUID2(guid, value, static_cast<int>(std::size(value))) == 0) return {};
    return utf8(winrt::hstring(value));
}

std::filesystem::path webViewUserDataFolder() {
    PWSTR raw = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DEFAULT, nullptr, &raw)) || raw == nullptr) {
        return {};
    }
    std::filesystem::path result(raw);
    CoTaskMemFree(raw);
    result /= "GRAF";
    result /= "WebView2";
    std::error_code error;
    std::filesystem::create_directories(result, error);
    return error ? std::filesystem::path{} : result;
}

std::wstring suggestedFileName(winrt::Microsoft::Web::WebView2::Core::CoreWebView2DownloadStartingEventArgs const& args) {
    const auto suggested = args.ResultFilePath();
    if (!suggested.empty()) {
        const auto name = std::filesystem::path(std::wstring(suggested.c_str())).filename().wstring();
        if (!name.empty()) return name;
    }
    return L"graf-export";
}

std::optional<std::wstring> chooseDownloadPath(
    winrt::Microsoft::Web::WebView2::Core::CoreWebView2DownloadStartingEventArgs const& args) {
    auto fileName = suggestedFileName(args);
    wchar_t buffer[MAX_PATH]{};
    wcsncpy_s(buffer, fileName.c_str(), _TRUNCATE);
    OPENFILENAMEW dialog{};
    dialog.lStructSize = sizeof(dialog);
    dialog.lpstrFile = buffer;
    dialog.nMaxFile = static_cast<DWORD>(std::size(buffer));
    dialog.lpstrFilter = L"GRAF files\0*.*\0All files\0*.*\0";
    dialog.nFilterIndex = 1;
    dialog.Flags = OFN_PATHMUSTEXIST | OFN_OVERWRITEPROMPT;
    return GetSaveFileNameW(&dialog) ? std::optional<std::wstring>(buffer) : std::nullopt;
}

std::optional<WebViewBridgeEnvelope> parseEnvelope(std::string_view json, std::string origin) {
    try {
        const auto object = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(json));
        const auto version = object.GetNamedNumber(L"version");
        const auto messageId = object.GetNamedNumber(L"message_id");
        const auto sentAt = object.GetNamedNumber(L"sent_at_monotonic_ms");
        if (!isJsonUnsignedInteger(version, kJsonVersionMax) ||
            !isJsonUnsignedInteger(messageId, kJsonSafeIntegerMax) ||
            !isJsonUnsignedInteger(sentAt, kJsonSafeIntegerMax)) {
            return std::nullopt;
        }
        WebViewBridgeEnvelope envelope;
        envelope.protocol = utf8(object.GetNamedString(L"protocol"));
        envelope.version = static_cast<std::uint32_t>(version);
        envelope.messageId = static_cast<std::uint64_t>(messageId);
        envelope.nonce = utf8(object.GetNamedString(L"nonce"));
        envelope.origin = std::move(origin);
        const auto direction = utf8(object.GetNamedString(L"direction"));
        if (direction == "native_to_web") envelope.direction = BridgeDirection::nativeToWeb;
        else if (direction == "web_to_native") envelope.direction = BridgeDirection::webToNative;
        else return std::nullopt;
        envelope.command = utf8(object.GetNamedString(L"command"));
        envelope.payloadJson = utf8(object.GetNamedValue(L"payload").Stringify());
        envelope.sentAtMonotonicMs = static_cast<std::uint64_t>(sentAt);
        return envelope;
    } catch (...) {
        return std::nullopt;
    }
}

std::string originFromUrl(std::string_view url) {
    const auto schemeEnd = url.find("://");
    if (schemeEnd == std::string_view::npos) return {};
    const auto authorityStart = schemeEnd + 3;
    const auto authorityEnd = url.find_first_of("/?#", authorityStart);
    return std::string(url.substr(0, authorityEnd == std::string_view::npos ? url.size() : authorityEnd));
}

constexpr wchar_t kQuitBridgeScript[] = LR"JS(
(() => {
  if (window.__grafQuitBridgeInstalled) return;
  window.__grafQuitBridgeInstalled = true;
  let nonce = null;
  let nextMessageId = 1;
  const bind = () => {
    const button = document.querySelector('[data-graf-app-quit]');
    if (!button || button.disabled || button.dataset.grafQuitBridgeBound === 'true' || !nonce) return;
    button.dataset.grafQuitBridgeBound = 'true';
    button.addEventListener('click', () => {
      if (!nonce) return;
      window.chrome.webview.postMessage({
        protocol: 'graf.desktop.bridge',
        version: 1,
        direction: 'web_to_native',
        message_id: nextMessageId++,
        nonce,
        origin: window.location.origin,
        command: 'request_app_quit',
        payload: { action: 'quit' },
        sent_at_monotonic_ms: Math.floor(window.performance.now())
      });
    });
  };
  window.chrome.webview.addEventListener('message', (event) => {
    const message = event.data;
    if (!message || message.command !== 'native_ready' || typeof message.nonce !== 'string') return;
    nonce = message.nonce;
    nextMessageId = 1;
    bind();
  });
  bind();
})();
)JS";

} // namespace
#endif

WebView2Host::WebView2Host(WebViewRoutePolicy policy)
    : policy_(std::move(policy)), bridge_(policy_.trustedOrigin()) {}

WebView2Host::~WebView2Host() { close(); }

void WebView2Host::setRuntimeState(WebRuntimeState state) noexcept {
    runtimeState_ = state;
    if (state != WebRuntimeState::ready) bridge_.invalidate();
    try {
        if (runtimeHandler_) runtimeHandler_(state);
    } catch (...) {
        runtimeState_ = WebRuntimeState::unavailable;
        bridge_.invalidate();
    }
}

void WebView2Host::close() noexcept { setRuntimeState(WebRuntimeState::closed); }

RouteEvaluation WebView2Host::navigate(std::string url) {
    const auto evaluation = policy_.evaluate(url);
    if (runtimeState_ == WebRuntimeState::ready && evaluation.decision == RouteDecision::allow) {
#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
        if (nativeNavigate_) nativeNavigate_(url);
#endif
        currentUrl_ = std::move(url);
    }
    if (navigationHandler_) navigationHandler_(evaluation);
    return evaluation;
}

void WebView2Host::reload() {
#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
    if (nativeReload_ && runtimeState_ == WebRuntimeState::ready) {
        nativeReload_();
        return;
    }
#endif
    if (!currentUrl_.empty()) (void)navigate(currentUrl_);
}

bool WebView2Host::isAllowedQuitPayload(std::string_view payload) noexcept {
    return payload == R"({"action":"quit"})";
}

#if defined(_WIN32) && defined(GRAF_WINDOWS_APP_SDK)
void WebView2Host::attach(winrt::Microsoft::UI::Xaml::Controls::WebView2 control) {
    control.NavigationStarting([this](auto const&, auto const& args) {
        try {
            const auto url = utf8(args.Uri());
            // The XAML control event is the main-frame navigation surface. A
            // trusted top-level handoff may open in the default browser; frame
            // navigation is handled separately below and never gets that path.
            const auto evaluation = policy_.evaluate(url, true);
            if (evaluation.decision == RouteDecision::openExternal) {
                args.Cancel(true);
                (void)::ShellExecuteW(nullptr, L"open", args.Uri().c_str(), nullptr, nullptr, SW_SHOWNORMAL);
            } else if (evaluation.decision != RouteDecision::allow) {
                args.Cancel(true);
            } else {
                currentUrl_ = url;
                setRuntimeState(WebRuntimeState::initializing);
                if (navigationHandler_) navigationHandler_(evaluation);
            }
        } catch (...) {
            args.Cancel(true);
            setRuntimeState(WebRuntimeState::unavailable);
        }
    });
    control.CoreWebView2Initialized([this](auto const& sender, auto const&) {
        try {
            auto core = sender.CoreWebView2();
            if (!core) {
                setRuntimeState(WebRuntimeState::unavailable);
                return;
            }
        nativeNavigate_ = [core](std::string_view url) { core.Navigate(winrt::to_hstring(url)); };
        nativeReload_ = [core] { core.Reload(); };
        core.Settings().AreHostObjectsAllowed(false);
        core.Settings().IsStatusBarEnabled(false);
        core.Settings().AreDefaultScriptDialogsEnabled(false);
        core.FrameNavigationStarting([this](auto const&, auto const& args) {
            try {
                const auto evaluation = policy_.evaluate(utf8(args.Uri()), false);
                if (evaluation.decision != RouteDecision::allow) args.Cancel(true);
            } catch (...) {
                args.Cancel(true);
            }
        });
        core.DownloadStarting([this](auto const&, auto const& args) {
            try {
                const auto path = chooseDownloadPath(args);
                if (!path) {
                    args.Cancel(true);
                    return;
                }
                args.ResultFilePath(winrt::hstring(*path));
                args.Handled(true);
            } catch (...) {
                args.Cancel(true);
            }
        });
        core.WebMessageReceived([this](auto const&, auto const& args) {
            try {
                const auto rawJson = utf8(args.WebMessageAsJson());
                if (rawJson.size() > kBridgeMaxSerializedBytes) return;
                const auto sourceUrl = utf8(args.Source());
                const auto message = parseEnvelope(rawJson, originFromUrl(sourceUrl));
                if (!message || bridge_.validate(*message) != BridgeValidationError::none) return;
                if (message->command == "request_app_quit") {
                    if (isAllowedQuitPayload(message->payloadJson) &&
                        policy_.evaluate(sourceUrl).decision == RouteDecision::allow && quitHandler_) {
                        quitHandler_();
                    }
                    return;
                }
                if (webMessageHandler_) webMessageHandler_(*message);
            } catch (...) {
                // A malformed or failed browser callback cannot affect native capture.
            }
        });
            core.NavigationCompleted([this, core](auto const&, auto const& args) {
            try {
                if (!args.IsSuccess()) {
                    setRuntimeState(WebRuntimeState::unavailable);
                    return;
                }
                if (args.HttpStatusCode() == 401 || args.HttpStatusCode() == 403) {
                    setRuntimeState(WebRuntimeState::authRequired);
                    if (currentUrl_.find("/login") == std::string::npos) {
                        core.Navigate(winrt::to_hstring(policy_.trustedOrigin() + "/login?next=/desktop/meetings"));
                    }
                    return;
                }
                const auto nonce = newNonce();
                if (nonce.empty()) {
                    setRuntimeState(WebRuntimeState::unavailable);
                    return;
                }
                bridge_.rotateNonce(nonce);
                setRuntimeState(WebRuntimeState::ready);
                // Login may happen after the first WebView2 initialization. Read the
                // current browser-owned session on every successful document boundary
                // without persisting or exposing the cookie to the web bridge.
                core.CookieManager().GetCookiesAsync(winrt::to_hstring(policy_.trustedOrigin())).Completed(
                    [this](auto const& operation, auto const&) {
                        try {
                            if (authSessionHandler_) authSessionHandler_({});
                            const auto cookies = operation.GetResults();
                            for (const auto& cookie : cookies) {
                                const auto name = winrt::to_string(cookie.Name());
                                if (name != "__Host-twobrain_rec_owner_session" && name != "graf_dev_owner_session") continue;
                                if (authSessionHandler_) authSessionHandler_(winrt::to_string(cookie.Value()));
                                break;
                            }
                        } catch (...) {
                            // Auth remains browser-owned; a cookie read failure must not affect capture.
                        }
                    });
                const auto script = core.ExecuteScriptAsync(winrt::to_hstring(kQuitBridgeScript));
                script.Completed([this, core, nonce](auto const&, auto const&) {
                    try {
                        if (runtimeState_ != WebRuntimeState::ready) return;
                        winrt::Windows::Data::Json::JsonObject ready;
                        ready.Insert(L"protocol", winrt::Windows::Data::Json::JsonValue::CreateStringValue(
                            winrt::to_hstring(std::string(kBridgeProtocol))));
                        ready.Insert(L"version", winrt::Windows::Data::Json::JsonValue::CreateNumberValue(kBridgeProtocolVersion));
                        ready.Insert(L"message_id", winrt::Windows::Data::Json::JsonValue::CreateNumberValue(1));
                        ready.Insert(L"nonce", winrt::Windows::Data::Json::JsonValue::CreateStringValue(winrt::to_hstring(nonce)));
                        ready.Insert(L"origin", winrt::Windows::Data::Json::JsonValue::CreateStringValue(
                            winrt::to_hstring(policy_.trustedOrigin())));
                        ready.Insert(L"direction", winrt::Windows::Data::Json::JsonValue::CreateStringValue(L"native_to_web"));
                        ready.Insert(L"command", winrt::Windows::Data::Json::JsonValue::CreateStringValue(L"native_ready"));
                        winrt::Windows::Data::Json::JsonObject payload;
                        payload.Insert(L"runtime", winrt::Windows::Data::Json::JsonValue::CreateStringValue(L"webview2_evergreen"));
                        ready.Insert(L"payload", payload);
                        ready.Insert(L"sent_at_monotonic_ms", winrt::Windows::Data::Json::JsonValue::CreateNumberValue(
                            static_cast<double>(GetTickCount64())));
                        core.PostWebMessageAsJson(ready.Stringify());
                    } catch (...) {
                        setRuntimeState(WebRuntimeState::unavailable);
                    }
                });
            } catch (...) {
                setRuntimeState(WebRuntimeState::unavailable);
            }
            });
            setRuntimeState(WebRuntimeState::initializing);
            const auto initial = policy_.trustedOrigin() + "/desktop/meetings";
            core.Navigate(winrt::to_hstring(initial));
        } catch (...) {
            setRuntimeState(WebRuntimeState::unavailable);
        }
    });
    try {
        const auto userData = webViewUserDataFolder();
        if (userData.empty()) {
            setRuntimeState(WebRuntimeState::unavailable);
            return;
        }
        auto environment = winrt::Microsoft::Web::WebView2::Core::CoreWebView2Environment::CreateWithOptionsAsync(
            winrt::hstring{}, winrt::hstring(userData.wstring()),
            winrt::Microsoft::Web::WebView2::Core::CoreWebView2EnvironmentOptions{});
        environment.Completed([this, control](auto const& operation, auto const&) {
            try {
                control.EnsureCoreWebView2Async(operation.GetResults());
            } catch (...) {
                setRuntimeState(WebRuntimeState::unavailable);
            }
        });
    } catch (...) {
        setRuntimeState(WebRuntimeState::unavailable);
    }
}
#endif

} // namespace graf::windows
