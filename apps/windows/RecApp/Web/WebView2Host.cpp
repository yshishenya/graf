#include "WebView2Host.h"

#include "../Contracts/WindowsDesktopContracts.h"

#ifdef _WIN32
#include <winrt/Windows.Data.Json.h>
#include <shellapi.h>
#include <windows.h>

#include <iterator>
#include <cmath>
#include <optional>
#endif

namespace graf::windows {

#ifdef _WIN32
namespace {

constexpr double kJsonSafeIntegerMax = 9'007'199'254'740'991.0;
constexpr double kJsonVersionMax = 4'294'967'295.0;

bool isJsonUnsignedInteger(double value, double maximum) noexcept {
    return std::isfinite(value) && value >= 0.0 && value <= maximum &&
        value <= kJsonSafeIntegerMax && std::floor(value) == value;
}

std::string newNonce() {
    GUID guid{};
    if (FAILED(CoCreateGuid(&guid))) return {};
    wchar_t value[40]{};
    if (StringFromGUID2(guid, value, static_cast<int>(std::size(value))) == 0) return {};
    return winrt::to_string(winrt::hstring(value));
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
        envelope.protocol = winrt::to_string(object.GetNamedString(L"protocol"));
        envelope.version = static_cast<std::uint32_t>(version);
        envelope.messageId = static_cast<std::uint64_t>(messageId);
        envelope.nonce = winrt::to_string(object.GetNamedString(L"nonce"));
        envelope.origin = std::move(origin);
        const auto direction = winrt::to_string(object.GetNamedString(L"direction"));
        if (direction == "native_to_web") envelope.direction = BridgeDirection::nativeToWeb;
        else if (direction == "web_to_native") envelope.direction = BridgeDirection::webToNative;
        else return std::nullopt;
        envelope.command = winrt::to_string(object.GetNamedString(L"command"));
        envelope.payloadJson = object.GetNamedValue(L"payload").Stringify();
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

} // namespace
#endif

WebView2Host::WebView2Host(WebViewRoutePolicy policy)
    : policy_(std::move(policy)), bridge_(policy_.trustedOrigin()) {}

void WebView2Host::setRuntimeState(WebRuntimeState state) noexcept {
    runtimeState_ = state;
    if (state != WebRuntimeState::ready) bridge_.invalidate();
    if (runtimeHandler_) runtimeHandler_(state);
}

void WebView2Host::close() noexcept { setRuntimeState(WebRuntimeState::closed); }

RouteEvaluation WebView2Host::navigate(std::string url) {
    const auto evaluation = policy_.evaluate(url);
    if (runtimeState_ == WebRuntimeState::ready && evaluation.decision == RouteDecision::allow) {
        currentUrl_ = std::move(url);
    }
    if (navigationHandler_) navigationHandler_(evaluation);
    return evaluation;
}

void WebView2Host::reload() {
    if (!currentUrl_.empty()) (void)navigate(currentUrl_);
}

#ifdef _WIN32
void WebView2Host::attach(Microsoft::UI::Xaml::Controls::WebView2 control) {
    control.NavigationStarting([this](auto const&, auto const& args) {
        const auto url = winrt::to_string(args.Uri());
        const auto evaluation = policy_.evaluate(url);
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
    });
    control.CoreWebView2Initialized([this](auto const& sender, auto const&) {
        auto core = sender.CoreWebView2();
        if (!core) {
            setRuntimeState(WebRuntimeState::unavailable);
            return;
        }
        core.Settings().AreHostObjectsAllowed(false);
        core.Settings().IsStatusBarEnabled(false);
        core.Settings().AreDefaultScriptDialogsEnabled(false);
        core.WebMessageReceived([this](auto const&, auto const& args) {
            const auto rawJson = winrt::to_string(args.WebMessageAsJson());
            if (rawJson.size() > kBridgeMaxSerializedBytes) return;
            const auto message = parseEnvelope(rawJson, originFromUrl(winrt::to_string(args.Source())));
            if (message && bridge_.validate(*message) == BridgeValidationError::none && webMessageHandler_) {
                webMessageHandler_(*message);
            }
        });
        core.NavigationCompleted([this, core](auto const&, auto const& args) {
            if (!args.IsSuccess()) {
                setRuntimeState(WebRuntimeState::unavailable);
                return;
            }
            const auto nonce = newNonce();
            if (nonce.empty()) {
                setRuntimeState(WebRuntimeState::unavailable);
                return;
            }
            bridge_.rotateNonce(nonce);
            setRuntimeState(WebRuntimeState::ready);
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
        });
        setRuntimeState(WebRuntimeState::initializing);
        const auto initial = policy_.trustedOrigin() + "/desktop/meetings";
        core.Navigate(winrt::to_hstring(initial));
    });
    control.EnsureCoreWebView2Async();
}
#endif

} // namespace graf::windows
