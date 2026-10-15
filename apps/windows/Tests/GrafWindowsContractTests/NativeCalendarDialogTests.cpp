// Real WinUI ContentDialog + unchanged production owner, synthetic data only.
// This is NOT AppMain integration, auth, network, launch, capture or installed proof.
#include "../../RecApp/Shell/CalendarJoinOperation.h"
#include <windows.h>
#undef GetClassName
#undef GetCurrentTime
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.UI.Xaml.Interop.h>
#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Xaml.Markup.h>
#include <winrt/Microsoft.UI.Xaml.XamlTypeInfo.h>
#include <winrt/Microsoft.UI.Xaml.Media.h>
#include <winrt/Microsoft.UI.Xaml.Automation.Peers.h>
#include <winrt/Microsoft.UI.Xaml.Automation.Provider.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <chrono>
#include <cstdio>
#include <future>
#include <memory>
#include <optional>
#include <thread>

namespace {
using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;
using namespace Microsoft::UI::Xaml::Automation::Peers;
using namespace graf::windows;
using Clock = CalendarJoinOperation::Clock;
constexpr auto eventId = "11111111-1111-4111-8111-111111111111";
constexpr auto requestId = "22222222-2222-4222-8222-222222222222";
constexpr auto nextRequestId = "33333333-3333-4333-8333-333333333333";
int resultCode = 2;

Button findButton(DependencyObject const& object, hstring const& text) {
    if (auto button = object.try_as<Button>(); button && button.Content() && unbox_value<hstring>(button.Content()) == text)
        return button;
    for (int i = 0; i < Media::VisualTreeHelper::GetChildrenCount(object); ++i)
        if (auto found = findButton(Media::VisualTreeHelper::GetChild(object, i), text)) return found;
    return nullptr;
}

class NativeDialogTests : public ApplicationT<NativeDialogTests, Markup::IXamlMetadataProvider> {
public:
    Markup::IXamlType GetXamlType(Windows::UI::Xaml::Interop::TypeName const& type) { return metadata_.GetXamlType(type); }
    Markup::IXamlType GetXamlType(hstring const& name) { return metadata_.GetXamlType(name); }
    com_array<Markup::XmlnsDefinition> GetXmlnsDefinitions() { return metadata_.GetXmlnsDefinitions(); }
    void OnLaunched(LaunchActivatedEventArgs const&) {
        Resources().MergedDictionaries().Append(XamlControlsResources());
        window_ = Window(); window_.Title(L"GRAF synthetic calendar dialog test");
        root_ = Grid(); window_.Content(root_);
        timer_ = Microsoft::UI::Dispatching::DispatcherQueue::GetForCurrentThread().CreateTimer();
        timer_.IsRepeating(true);
        timer_.Interval(std::chrono::milliseconds(20));
        timer_.Tick([this](auto const&, auto const&) {
            try { tick(); }
            catch (...) { std::puts("native dialog test failed: SDK exception"); std::fflush(stdout); ExitProcess(2); }
        });
        root_.Loaded([this](auto const&, auto const&) { if (!owner_) { beginCase(); timer_.Start(); } });
        window_.Activate();
    }
private:
    // 0 Primary; 1 Close; 2 cancel+Hide; 3 stale before Primary;
    // 4 stale after Primary while closing; 5 closing exceeds click+15s.
    void beginCase() {
        startedAt_ = Clock::now();
        context_ = {"https://synthetic.invalid", "synthetic-owner", "synthetic-workspace", "synthetic-only", 1,
            CalendarJoinSource::nativeAction, 1, requestId, startedAt_ + std::chrono::seconds(45)};
        owner_ = std::make_unique<CalendarJoinOperation>();
        const auto resolver = owner_->begin(eventId, requestId, context_, startedAt_, true);
        assert(resolver); resolver_ = *resolver;
        releaseWorker_ = CreateEventW(nullptr, TRUE, FALSE, nullptr); assert(releaseWorker_);
        std::promise<bool> promise; workerResult_ = promise.get_future();
        // Future-ready is deliberately NOT thread exit. The caller observes the
        // native handle before reaping the ticket, exactly as required by AppMain.
        worker_ = std::thread([promise = std::move(promise), event = releaseWorker_]() mutable {
            promise.set_value(false);
            assert(WaitForSingleObject(event, 5000) == WAIT_OBJECT_0);
        });
        workerReady_ = opened_ = acted_ = hidden_ = stale_ = released_ = false;
        primaryEvents_ = confirmations_ = closedEvents_ = closingObservations_ = 0;
        clickedAt_.reset();
    }
    void showDialog() {
        assert(!worker_.joinable() && owner_->busy() && workerReady_ && root_.XamlRoot());
        assert(owner_->retryCurrent(resolver_.operationId, context_, Clock::now()));
        const auto ticket = owner_->retryDialog(resolver_.operationId, context_, Clock::now());
        assert(ticket); ticket_ = *ticket;
        assert(ticket_.cancellation != resolver_.cancellation && resolver_.cancellation->load());
        dialog_ = ContentDialog(); dialog_.XamlRoot(root_.XamlRoot()); dialog_.RequestedTheme(ElementTheme::Light);
        // Same current failure presentation as AppMain. Copying it does not
        // execute AppMain's private offer/poll/current code or authorize a URL.
        dialog_.Title(box_value(L"Не удалось открыть встречу"));
        dialog_.Content(box_value(L"Проверьте подключение и повторите попытку. Если событие изменилось, обновите календарь."));
        dialog_.PrimaryButtonText(L"Повторить подключение"); dialog_.CloseButtonText(L"Отмена");
        dialog_.DefaultButton(ContentDialogButton::Close);
        dialog_.Opened([this](auto const&, auto const&) { opened_ = true; });
        dialog_.PrimaryButtonClick([this](auto const&, auto const&) {
            ++primaryEvents_;
            if (clickedAt_ || hidden_ || stale_) return;
            const auto click = Clock::now();
            if (owner_->confirmRetry(ticket_, context_, click)) { clickedAt_ = click; ++confirmations_; }
        });
        dialog_.Closing([this](auto const&, ContentDialogClosingEventArgs const& args) {
            assert(!deferral_);
            deferral_ = args.GetDeferral(); closingAt_ = Clock::now();
        });
        dialog_.Closed([this](auto const&, auto const&) { ++closedEvents_; });
        operation_ = dialog_.ShowAsync(); assert(operation_ && owner_->busy());
    }
    void revoke() {
        stale_ = true;
        auto changed = context_; ++changed.authGeneration;
        assert(!owner_->retryCurrent(ticket_.operationId, changed, Clock::now()));
        assert(owner_->busy() && ticket_.cancellation->load());
    }
    void invoke(hstring const& text) {
        const auto button = findButton(dialog_, text); assert(button && button.IsEnabled());
        const auto provider = ButtonAutomationPeer(button).GetPattern(PatternInterface::Invoke)
            .as<Microsoft::UI::Xaml::Automation::Provider::IInvokeProvider>();
        assert(provider); provider.Invoke(); // Real SDK button, not our click callback.
    }
    void tick() {
        assert(Clock::now() - startedAt_ < std::chrono::seconds(25)); // Watchdog is failure, never drain.
        assert(owner_ && owner_->busy());
        if (worker_.joinable()) {
            if (!workerReady_) {
                if (workerResult_.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return;
                assert(WaitForSingleObject(worker_.native_handle(), 0) == WAIT_TIMEOUT && !operation_);
                assert(owner_->finish(resolver_.operationId, CalendarJoinState::failed,
                    CalendarJoinReason::dependencyUnavailable, context_, Clock::now()));
                assert(!owner_->retryDialog(resolver_.operationId, context_, Clock::now()));
                assert(owner_->busy()); workerReady_ = true;
                assert(SetEvent(releaseWorker_)); return;
            }
            const auto status = WaitForSingleObject(worker_.native_handle(), 0);
            assert(status == WAIT_TIMEOUT || status == WAIT_OBJECT_0);
            if (status == WAIT_TIMEOUT) return;
            worker_.join(); assert(!workerResult_.get());
            assert(CloseHandle(releaseWorker_)); releaseWorker_ = nullptr;
            assert(!owner_->complete(resolver_, context_, Clock::now()) && owner_->busy());
            showDialog(); return;
        }
        const auto status = operation_.Status();
        if (status == Windows::Foundation::AsyncStatus::Started) {
            assert(owner_->busy() && !owner_->retry(ticket_.operationId, nextRequestId, context_, Clock::now()));
            if (opened_ && !acted_) {
                acted_ = true;
                if (case_ == 2) { owner_->cancel(ticket_.operationId); hidden_ = true; dialog_.Hide(); }
                else {
                    if (case_ == 3) revoke();
                    invoke(case_ == 1 ? L"Отмена" : L"Повторить подключение");
                }
            }
            if (deferral_ && !released_) {
                ++closingObservations_;
                if (case_ == 4 && !stale_) { assert(clickedAt_ && confirmations_ == 1); revoke(); }
                const auto delay = case_ == 5 ? std::chrono::milliseconds(16000) : std::chrono::milliseconds(200);
                if (Clock::now() - closingAt_ >= delay) {
                    assert(owner_->busy()); deferral_.Complete(); deferral_ = nullptr; released_ = true;
                }
            }
            return;
        }
        assert(status == Windows::Foundation::AsyncStatus::Completed); // Unknown/Error do not pass.
        assert(opened_ && acted_ && released_ && closingObservations_ && closedEvents_ == 1);
        const auto answer = operation_.GetResults();
        assert(answer == (case_ == 1 || case_ == 2 ? ContentDialogResult::None : ContentDialogResult::Primary));
        assert(primaryEvents_ == (case_ == 1 || case_ == 2 ? 0U : 1U));
        assert(confirmations_ == (case_ == 0 || case_ == 4 || case_ == 5 ? 1U : 0U));
        operation_ = nullptr; dialog_ = nullptr;
        assert(!owner_->complete(ticket_, context_, Clock::now())); // Failed attempt stays failed.
        unsigned newTickets = 0;
        if (answer == ContentDialogResult::Primary && clickedAt_ && !hidden_ && !stale_) {
            const auto next = owner_->retry(ticket_.operationId, nextRequestId, context_, Clock::now());
            if (case_ == 0) {
                assert(next && owner_->busy() && next->operationId != ticket_.operationId && next->workId != ticket_.workId);
                assert(owner_->requestId() == nextRequestId && owner_->eventId() == eventId);
                assert(next->deadline == *clickedAt_ + std::chrono::seconds(15));
                assert(owner_->current(next->operationId, context_, Clock::now())); // Same source/expiry.
                assert(!owner_->complete(ticket_, context_, Clock::now()) && owner_->busy());
                // No resolver dispatch/HTTP in this fixture. Rejected dispatch
                // drains this new ticket only; no fresh target or launch claim.
                owner_->cancel(next->operationId);
                assert(owner_->busy() && !owner_->complete(*next, context_, Clock::now()));
                newTickets = 1;
            } else assert(case_ == 5 && !next); // Actual closing delay consumed click+15s.
        }
        owner_->cancel(ticket_.operationId);
        assert(!owner_->busy());
        std::printf("native dialog case=%u opened=1 worker_ready_not_exit=1 closed=1 closing_observed=1 primary=%u confirmed=%u new_tickets=%u\n",
            case_, primaryEvents_, confirmations_, newTickets); std::fflush(stdout);
        if (++case_ == 6) {
            timer_.Stop(); resultCode = 73;
            std::puts("NativeCalendarDialogTests PASS: 6/6 synthetic SDK cases; NOT AppMain/installed proof");
            std::fflush(stdout); window_.Close(); Exit();
        } else beginCase();
    }
    XamlTypeInfo::XamlControlsXamlMetaDataProvider metadata_;
    Window window_{nullptr}; Grid root_{nullptr};
    Microsoft::UI::Dispatching::DispatcherQueueTimer timer_{nullptr};
    std::unique_ptr<CalendarJoinOperation> owner_;
    CalendarJoinContext context_; CalendarJoinWork resolver_, ticket_;
    std::thread worker_; std::future<bool> workerResult_; HANDLE releaseWorker_ = nullptr;
    ContentDialog dialog_{nullptr}; ContentDialogClosingDeferral deferral_{nullptr};
    Windows::Foundation::IAsyncOperation<ContentDialogResult> operation_{nullptr};
    Clock::time_point startedAt_{}, closingAt_{}; std::optional<Clock::time_point> clickedAt_;
    unsigned case_ = 0, primaryEvents_ = 0, confirmations_ = 0, closedEvents_ = 0, closingObservations_ = 0;
    bool workerReady_ = false, opened_ = false, acted_ = false, hidden_ = false, stale_ = false, released_ = false;
};
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    try {
        init_apartment(apartment_type::single_threaded);
        Application::Start([](auto&&) { make<NativeDialogTests>(); });
        return resultCode;
    } catch (...) { std::puts("NativeCalendarDialogTests setup failed"); std::fflush(stdout); return 2; }
}
