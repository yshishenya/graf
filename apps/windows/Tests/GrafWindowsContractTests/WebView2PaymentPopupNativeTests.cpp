// Native-only T102 fixture. Built separately with the real WebView2Host.cpp;
// never linked into the application. No capture or real GRAF profile/session.
#include "../../RecApp/Web/WebView2Host.h"
#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <windows.h>
#include <appmodel.h>
#include <cstdio>
#include <sstream>

namespace graf::windows {
struct WebView2PaymentPopupNativeFixture {
    static inline unsigned eventsObserved = 0;
    static inline unsigned subframesDenied = 0;
    static inline bool checkpointReached = false;
    static inline ULONGLONG attemptTime = 0;
    static inline unsigned sourceKind = 0, sourceFrame = 0, coreFrame = 0;
    static inline unsigned childNavigationStarts = 0, childContentLoads = 0;
    static inline unsigned allowedFrameStarts = 0, deniedFrameStarts = 0;
    static inline unsigned connectionAborts = 0;
    static bool paymentEnded(WebView2Host const& host) { return !host.paymentPopup_ && !host.payment_.started(); }
    static WebViewBridgeEnvelope oldBridgeMessage(WebView2Host const& host, std::uint64_t id) {
        return {"graf.desktop.bridge", 1, id, "synthetic-initial-nonce", host.policy_.trustedOrigin(),
            BridgeDirection::webToNative, "app_appearance", "{}", 0};
    }
    static bool primeBridge(WebView2Host& host) {
        host.bridge_.rotateNonce("synthetic-initial-nonce");
        return host.bridge_.validate(oldBridgeMessage(host, 1)) == BridgeValidationError::none;
    }
    static bool oldBridgeRevoked(WebView2Host& host) {
        return host.bridge_.validate(oldBridgeMessage(host, 2)) == BridgeValidationError::staleNonce;
    }
    static void report(WebView2Host const& host) {
        std::printf("popup=%d handed_off=%d active_frame=%u\n", int(bool(host.paymentPopup_)),
            int(host.paymentPopup_ && host.paymentPopup_->handedOff), host.paymentPopup_ ? host.paymentPopup_->activeFrameId : 0);
    }
    static void wire(WebView2Host& host, winrt::Microsoft::UI::Xaml::Controls::WebView2 control,
        bool failAfterAssignment, bool failFirstNavigation) {
        host.alive_ = std::make_shared<std::atomic_bool>(true);
        const auto alive = host.alive_;
        const auto core = control.CoreWebView2();
        std::printf("environment_getter_identity_stable=%d\n", int(core.Environment() == core.Environment()));
        host.nativeNavigate_ = [core](std::string_view url) { core.Navigate(winrt::to_hstring(url)); };
        host.popupHandoffCheckpoint_ = [failAfterAssignment, failFirstNavigation](bool completed, auto const& target) {
            std::printf("target_frame phase=%s id=%u\n", completed ? "after-complete" : "after-new-window", target.FrameId());
            if (completed) return;
            target.NavigationStarting([failFirstNavigation](auto const& sender, auto const& event) {
                ++childNavigationStarts;
                if (failFirstNavigation) event.Cancel(true); // Real failed navigation, without ContentLoading.
                std::printf("target_frame phase=navigation-starting id=%u nav=%llu cancelled=%d\n", sender.FrameId(),
                    static_cast<unsigned long long>(event.NavigationId()), int(event.Cancel()));
            });
            target.ContentLoading([](auto const& sender, auto const&) {
                ++childContentLoads;
                std::printf("target_frame phase=content-loading id=%u\n", sender.FrameId());
            });
            target.NavigationCompleted([](auto const&, auto const& event) {
                if (!event.IsSuccess() && event.WebErrorStatus() ==
                    winrt::Microsoft::Web::WebView2::Core::CoreWebView2WebErrorStatus::ConnectionAborted) ++connectionAborts;
                std::printf("target_navigation completed nav=%llu success=%d web_error=%d\n",
                    static_cast<unsigned long long>(event.NavigationId()), int(event.IsSuccess()), int(event.WebErrorStatus()));
            });
            target.FrameNavigationStarting([](auto const&, auto const& event) {
                if (event.Cancel()) ++deniedFrameStarts;
                else ++allowedFrameStarts;
                std::printf("target_frame phase=subframe-starting cancelled=%d\n", int(event.Cancel()));
            });
            checkpointReached = true;
            attemptTime = GetTickCount64();
            if (failAfterAssignment) throw winrt::hresult_error(E_ABORT);
        };
        core.NewWindowRequested([&host, alive, control](auto const&, auto const& args) {
            args.Handled(true);
            if (!alive->load()) return;
            ++eventsObserved;
            attemptTime = GetTickCount64();
            sourceKind = unsigned(args.OriginalSourceFrameInfo().FrameKind());
            sourceFrame = args.OriginalSourceFrameInfo().FrameId();
            coreFrame = control.CoreWebView2().FrameId();
            const bool subframe = args.OriginalSourceFrameInfo().FrameKind() ==
                winrt::Microsoft::Web::WebView2::Core::CoreWebView2FrameKind::Iframe;
            host.openPaymentPopup(control, args);
            if (subframe && !host.paymentPopup_) ++subframesDenied;
        });
    }
};
}

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;
using namespace Microsoft::Web::WebView2::Core;
using namespace graf::windows;

namespace {
std::wstring profilePath;
std::wstring receiptPath;
std::string origin;
std::string scenario;
int fixtureExitCode = 2;

struct FixtureApp : ApplicationT<FixtureApp> {
    Window window{nullptr};
    Grid panel{nullptr};
    WebView2 opener{nullptr};
    Microsoft::UI::Dispatching::DispatcherQueueTimer timer{nullptr};
    std::unique_ptr<WebView2Host> host;
    bool launched = false;
    bool returned = false;
    unsigned ticks = 0;
    std::string receiptSnapshot;

    void finish(bool passed, const char* stage) {
        if (fixtureExitCode != 2) return;
        fixtureExitCode = passed ? 0 : 1;
        if (passed) std::printf("ACCEPTED_RECEIPT=%s\n", receiptSnapshot.c_str());
        std::printf("T102_NATIVE case=%s result=%s stage=%s\n", scenario.c_str(), passed ? "PASS" : "FAIL", stage);
        std::printf("events=%u kind=%u source_frame=%u core_frame=%u checkpoint=%d\n",
            WebView2PaymentPopupNativeFixture::eventsObserved, WebView2PaymentPopupNativeFixture::sourceKind,
            WebView2PaymentPopupNativeFixture::sourceFrame, WebView2PaymentPopupNativeFixture::coreFrame,
            int(WebView2PaymentPopupNativeFixture::checkpointReached));
        if (host) {
            std::printf("host_state=%d host_failure=%s children=%u\n", int(host->runtimeState()), host->failureDetail().c_str(), panel.Children().Size());
            WebView2PaymentPopupNativeFixture::report(*host);
        }
        std::fflush(stdout);
        if (timer) timer.Stop();
        if (host) host->close();
        if (opener) opener.Close();
        if (window) window.Close();
        Exit();
    }

    void OnLaunched(LaunchActivatedEventArgs const&) {
        try {
            window = Window();
            panel = Grid();
            opener = WebView2();
            panel.Children().Append(opener);
            window.Content(panel); // Deliberately never Activate: isolated hidden test window.
            host = std::make_unique<WebView2Host>(WebViewRoutePolicy(origin));
            timer = opener.DispatcherQueue().CreateTimer();
            timer.Interval(std::chrono::milliseconds(100));
            timer.Tick([this](auto const&, auto const&) {
                ++ticks;
                // The server atomically replaces this snapshot. An ordinary CRT
                // reader denies delete sharing on Windows and can break replace().
                std::istringstream receipt;
                receiptSnapshot.clear();
                const auto receiptFile = CreateFileW(receiptPath.c_str(), GENERIC_READ,
                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr, OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL, nullptr);
                if (receiptFile != INVALID_HANDLE_VALUE) {
                    char data[256];
                    DWORD size = 0;
                    const auto read = ReadFile(receiptFile, data, sizeof(data), &size, nullptr);
                    CloseHandle(receiptFile);
                    if (read && size < sizeof(data)) {
                        receiptSnapshot.assign(data, size);
                        receipt.str(receiptSnapshot);
                    }
                }
                int posts = -1, returns = -1, bodies = -1, openerProof = -1, bankPosts = -1;
                int bankBody = -1, bankOpener = -1, returnBody = -1;
                int bankGets = -1, returnCookie = -1, providerCookie = -1;
                int paymentRequests = -1;
                int liveFrameRequests = -1, endedFrameRequests = -1;
                receipt >> posts >> returns >> bodies >> openerProof >> bankPosts >> bankBody >> bankOpener >> returnBody
                    >> bankGets >> returnCookie >> providerCookie >> paymentRequests >> liveFrameRequests >> endedFrameRequests;
                const bool receiptComplete = !receipt.fail();
                const bool beforeContentFailure = scenario == "first-navigation-failure";
                const bool abortOnly = scenario == "abort-only";
                const bool denied = scenario == "iframe" || scenario == "same-url-iframe" || scenario == "cancel-after-assignment" || beforeContentFailure || abortOnly;
                const auto attemptTime = WebView2PaymentPopupNativeFixture::attemptTime;
                if (denied && launched && attemptTime && GetTickCount64() - attemptTime >= 4000) {
                    const bool attempted = WebView2PaymentPopupNativeFixture::eventsObserved > 0 &&
                        ((scenario == "cancel-after-assignment" || beforeContentFailure || abortOnly) ? WebView2PaymentPopupNativeFixture::checkpointReached :
                            WebView2PaymentPopupNativeFixture::subframesDenied > 0);
                    const bool failureRecovered = (scenario != "cancel-after-assignment" && !beforeContentFailure && !abortOnly) ||
                        (host->runtimeState() == WebRuntimeState::unavailable && !host->failureDetail().empty() &&
                            WebView2PaymentPopupNativeFixture::oldBridgeRevoked(*host) &&
                            panel.Children().Size() == 1 && opener.Visibility() == Visibility::Visible &&
                            WebView2PaymentPopupNativeFixture::paymentEnded(*host));
                    const bool failedWithoutContent = (!beforeContentFailure && !abortOnly) ||
                        (WebView2PaymentPopupNativeFixture::childNavigationStarts > 0 &&
                            WebView2PaymentPopupNativeFixture::childContentLoads == 0 &&
                            host->failureDetail().find("payment-document") == 0);
                    // A holding GET may have reached the server before stop(). No
                    // form or replacement navigation is issued in this scenario.
                    const bool requestsCorrect = abortOnly ?
                        (paymentRequests >= 0 && paymentRequests <= 1 &&
                            WebView2PaymentPopupNativeFixture::connectionAborts == 1 &&
                            WebView2PaymentPopupNativeFixture::childNavigationStarts == 1) : paymentRequests == 0;
                    finish(attempted && failureRecovered && failedWithoutContent && receiptComplete &&
                        posts == 0 && returns == 0 && bankPosts == 0 && bankGets == 0 && requestsCorrect,
                        abortOnly ? "aborted-without-successor" : "attempted-denied-no-request");
                    return;
                }
                if (!denied && returned) {
                    const bool redirect307 = scenario == "redirect-307";
                    const bool redirect303 = scenario == "redirect-303";
                    const bool openerCorrect = (redirect307 || redirect303) ? bankOpener == 1 : openerProof == 1;
                    const bool bankCorrect = scenario == "nested" ? (bankPosts == 1 && bankBody == 1 && bankOpener == 1) :
                        redirect307 ? (bankPosts == 1 && bankBody == 1 && bankOpener == 1 && bankGets == 0) :
                        redirect303 ? (bankPosts == 0 && bankBody == 0 && bankOpener == 1 && bankGets == 1) :
                        (bankPosts == 0 && bankGets == 0);
                    const bool framesCorrect = scenario != "frame-chain" ||
                        (liveFrameRequests == 1 && endedFrameRequests == 0 &&
                            WebView2PaymentPopupNativeFixture::allowedFrameStarts == 1 &&
                            WebView2PaymentPopupNativeFixture::deniedFrameStarts == 1);
                    finish(receiptComplete && posts == 1 && returns == 1 && bodies == 1 && openerCorrect && returnBody == 1 &&
                        bankCorrect && framesCorrect && returnCookie == 1 && providerCookie == 1, "original-post-session-and-return");
                    return;
                }
                if (ticks >= 200) finish(false, "deadline");
            });
            timer.Start();
            CoreWebView2EnvironmentOptions options;
            options.AdditionalBrowserArguments(L"--host-resolver-rules=\"MAP graf.test 127.0.0.1,MAP api.yookassa.test 127.0.0.1,MAP bank.test 127.0.0.1\" --no-proxy-server --ignore-certificate-errors --disable-background-networking --disable-popup-blocking");
            const auto dispatcher = opener.DispatcherQueue();
            CoreWebView2Environment::CreateWithOptionsAsync(L"", profilePath, options).Completed(
                [this, dispatcher](auto const& operation, auto const&) {
                    dispatcher.TryEnqueue([this, operation] {
                        try {
                            const auto dispatcher = opener.DispatcherQueue();
                            opener.EnsureCoreWebView2Async(operation.GetResults()).Completed(
                                [this, dispatcher](auto const& operation, auto const&) {
                                    dispatcher.TryEnqueue([this, operation] {
                                        try {
                                            operation.GetResults();
                                            const auto core = opener.CoreWebView2();
                                            // Synthetic, HttpOnly cookie in this isolated profile only.
                                            // The server reports presence as a boolean, never cookie contents.
                                            const auto cookies = core.CookieManager();
                                            const auto cookie = cookies.CreateCookie(L"graf-native-fixture", L"synthetic-profile", L"api.yookassa.test", L"/");
                                            cookie.IsSecure(true);
                                            cookie.IsHttpOnly(true);
                                            cookie.SameSite(CoreWebView2CookieSameSiteKind::None);
                                            cookies.AddOrUpdateCookie(cookie);
                                            WebView2PaymentPopupNativeFixture::wire(*host, opener,
                                                scenario == "cancel-after-assignment", scenario == "first-navigation-failure");
                                            core.NavigationStarting([this](auto const&, auto const& args) {
                                                (void)host->beginDocumentNavigation(to_string(args.Uri()), args.NavigationId(), args.IsRedirected(), GetTickCount64());
                                            });
                                            core.NavigationCompleted([this](auto const& sender, auto const& args) {
                                                if (!args.IsSuccess()) {
                                                    std::printf("parent_error=%d\n", int(args.WebErrorStatus()));
                                                    finish(false, "parent-load"); return;
                                                }
                                                const auto url = to_string(sender.Source());
                                                const auto decision = host->completeDocumentNavigation(url, args.NavigationId(), {200}, GetTickCount64());
                                                if (decision != WebResponseDecision::cabinet) { finish(false, "parent-not-cabinet"); return; }
                                                if (launched) {
                                                    returned = url == origin + "/billing/checkout" && panel.Children().Size() == 1 &&
                                                        opener.Visibility() == Visibility::Visible &&
                                                        WebView2PaymentPopupNativeFixture::paymentEnded(*host);
                                                    if (!returned) finish(false, "unsafe-or-incomplete-return");
                                                    return;
                                                }
                                                host->setRuntimeState(WebRuntimeState::ready);
                                                if (!WebView2PaymentPopupNativeFixture::primeBridge(*host)) { finish(false, "initial-bridge"); return; }
                                                launched = true;
                                                sender.ExecuteScriptAsync(L"runFixture()");
                                            });
                                            core.Navigate(to_hstring(origin + "/billing?case=" + scenario));
                                        } catch (hresult_error const& e) { std::printf("native_code=%08X\n", unsigned(e.code().value)); finish(false, "ensure"); }
                                    });
                                });
                        } catch (hresult_error const& e) { std::printf("native_code=%08X\n", unsigned(e.code().value)); finish(false, "environment"); }
                    });
                });
        } catch (hresult_error const& e) { std::printf("native_code=%08X\n", unsigned(e.code().value)); finish(false, "initialize"); }
    }
};
}

int wmain(int argc, wchar_t** argv) {
    if (argc != 6) return 2;
    profilePath = argv[1];
    receiptPath = argv[2];
    origin = to_string(argv[3]);
    scenario = to_string(argv[4]);
    const auto bootstrap = LoadLibraryW(argv[5]);
    if (!bootstrap) return 3;
    using Initialize = HRESULT(WINAPI*)(UINT32, PCWSTR, PACKAGE_VERSION, UINT32);
    const auto initialize = reinterpret_cast<Initialize>(GetProcAddress(bootstrap, "MddBootstrapInitialize2"));
    if (!initialize) return 4;
    const auto hr = initialize(0x00020000, L"", PACKAGE_VERSION{}, 0);
    if (FAILED(hr)) { std::printf("bootstrap_code=%08X\n", unsigned(hr)); return 5; }
    try {
        init_apartment(apartment_type::single_threaded);
        Application::Start([](auto&&) { make<FixtureApp>(); });
    } catch (hresult_error const& error) {
        std::printf("fixture_code=%08X\n", unsigned(error.code().value));
    }
    return fixtureExitCode;
}
