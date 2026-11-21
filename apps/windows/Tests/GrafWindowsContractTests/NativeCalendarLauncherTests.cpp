#include <windows.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.System.h>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <functional>

namespace {
using namespace winrt::Windows::Foundation;
using namespace winrt::Windows::System;
template<class T> struct ManualOperation : winrt::implements<ManualOperation<T>, IAsyncOperation<T>, IAsyncInfo> {
    AsyncStatus status = AsyncStatus::Started;
    T answer{};
    bool statusFault = false, resultFault = false;
    unsigned cancels = 0, closes = 0, reads = 0;
    std::function<void()> onStatus, onResults;
    AsyncOperationCompletedHandler<T> handler{nullptr};
    std::uint32_t Id() { return 1; }
    AsyncStatus Status() { if (onStatus) onStatus(); if (statusFault) throw winrt::hresult_error(E_FAIL); return status; }
    winrt::hresult ErrorCode() { return status == AsyncStatus::Error ? E_FAIL : S_OK; }
    void Cancel() { ++cancels; status = AsyncStatus::Canceled; }
    void Close() { ++closes; }
    void Completed(AsyncOperationCompletedHandler<T> const& value) { handler = value; }
    AsyncOperationCompletedHandler<T> Completed() { return handler; }
    T GetResults() {
        ++reads; if (onResults) onResults();
        if (resultFault || status == AsyncStatus::Error) throw winrt::hresult_error(E_FAIL);
        return answer;
    }
};
winrt::com_ptr<ManualOperation<LaunchQuerySupportStatus>> query;
winrt::com_ptr<ManualOperation<bool>> launch;
unsigned queries = 0, launches = 0;
bool startFault = false, nullStart = false, ignoreHandlers = false;
std::wstring capturedURI;
std::function<void()> onDispatch;
void reset() {
    query = winrt::make_self<ManualOperation<LaunchQuerySupportStatus>>();
    launch = winrt::make_self<ManualOperation<bool>>();
    queries = launches = 0; startFault = nullStart = ignoreHandlers = false;
    capturedURI.clear(); onDispatch = {};
}
}
namespace winrt::Windows::System {
struct TestLauncher {
    static Foundation::IAsyncOperation<LaunchQuerySupportStatus> QueryUriSupportAsync(
        Foundation::Uri const& uri, LaunchQuerySupportType type) {
        ++queries; assert(type == LaunchQuerySupportType::Uri); capturedURI = uri.AbsoluteUri();
        if (onDispatch) onDispatch();
        if (startFault) throw winrt::hresult_error(E_FAIL);
        return nullStart ? nullptr : query.as<Foundation::IAsyncOperation<LaunchQuerySupportStatus>>();
    }
    static Foundation::IAsyncOperation<bool> LaunchUriAsync(Foundation::Uri const& uri, LauncherOptions const& options) {
        ++launches; capturedURI = uri.AbsoluteUri(); ignoreHandlers = options.IgnoreAppUriHandlers();
        if (onDispatch) onDispatch();
        if (startFault) throw winrt::hresult_error(E_FAIL);
        return nullStart ? nullptr : launch.as<Foundation::IAsyncOperation<bool>>();
    }
};
}
// Same production code, actual SDK interfaces, only TU-local OS statics replaced.
// Rename the class to avoid duplicate linkage with the normal object library.
#define Launcher TestLauncher
#define CalendarNativeLauncher FixtureCalendarNativeLauncher
#include "../../RecApp/Shell/CalendarNativeLauncher.cpp"
#undef CalendarNativeLauncher
#undef Launcher

using namespace graf::windows;
using Native = FixtureCalendarNativeLauncher;
const char* zoom = "https://zoom.us/j/123456789?pwd=synthetic";
const auto current = [] { return true; };
void preDispatch() {
    reset(); Native adapter;
    assert(adapter.poll().state == CalendarLauncherPollState::idle);
    assert(adapter.query(zoom, {}) == CalendarLauncherStart::rejected);
    assert(adapter.query(zoom, [] { return false; }) == CalendarLauncherStart::rejected);
    assert(adapter.query(zoom, []() -> bool { throw winrt::hresult_error(E_FAIL); }) == CalendarLauncherStart::rejected);
    assert(adapter.query("https://example.org/meeting", current) == CalendarLauncherStart::rejected);
    assert(adapter.launch("file:///bad", CalendarLauncherMode::browser, current) == CalendarLauncherStart::rejected);
    assert(!adapter.busy() && !queries && !launches);
    assert(adapter.query(zoom, [&] {
        assert(adapter.busy()); assert(adapter.query(zoom, current) == CalendarLauncherStart::busy);
        assert(adapter.poll().state == CalendarLauncherPollState::pending);
        adapter.cancel(); return true;
    }) == CalendarLauncherStart::rejected);
    assert(!adapter.busy() && !queries);
}
void queryStatuses() {
    for (auto status : {LaunchQuerySupportStatus::Available, LaunchQuerySupportStatus::AppNotInstalled,
            LaunchQuerySupportStatus::AppUnavailable, LaunchQuerySupportStatus::NotSupported, LaunchQuerySupportStatus::Unknown}) {
        reset(); Native adapter;
        assert(adapter.query(zoom, current) == CalendarLauncherStart::started);
        assert(capturedURI.rfind(L"zoommtg://zoom.us/join", 0) == 0 && !launches);
        assert(adapter.query(zoom, current) == CalendarLauncherStart::busy);
        assert(adapter.poll().state == CalendarLauncherPollState::pending && adapter.busy());
        query->answer = status; query->status = AsyncStatus::Completed;
        const auto answer = adapter.poll();
        const CalendarLauncherOutcome expected[] = {CalendarLauncherOutcome::available, CalendarLauncherOutcome::appNotInstalled,
            CalendarLauncherOutcome::appUnavailable, CalendarLauncherOutcome::notSupported, CalendarLauncherOutcome::unknown};
        assert(answer.state == CalendarLauncherPollState::completed && answer.outcome == expected[static_cast<int>(status)]);
        assert(!adapter.busy() && !launches && query->reads == 1 && !query->cancels && !query->closes);
    }
}
void cancelAndFaults() {
    for (bool queryMode : {true, false}) for (int fault = 0; fault < 4; ++fault) {
        reset(); Native adapter;
        const auto start = queryMode ? adapter.query(zoom, current) : adapter.launch(zoom, CalendarLauncherMode::native, current);
        assert(start == CalendarLauncherStart::started);
        const auto setStatus = [&](AsyncStatus status) { query->status = status; launch->status = status; };
        if (fault == 0) {
            adapter.cancel(); assert(adapter.busy());
            assert(adapter.poll().state == CalendarLauncherPollState::pending);
        } else {
            if (fault == 1) setStatus(AsyncStatus::Canceled);
            if (fault == 2) query->statusFault = launch->statusFault = true;
            if (fault == 3) setStatus(static_cast<AsyncStatus>(99));
            assert(adapter.poll().state == CalendarLauncherPollState::indeterminate && adapter.busy());
            assert(adapter.query(zoom, current) == CalendarLauncherStart::busy);
            query->statusFault = launch->statusFault = false;
        }
        setStatus(AsyncStatus::Completed); query->answer = LaunchQuerySupportStatus::Available; launch->answer = true;
        assert(adapter.poll().outcome == CalendarLauncherOutcome::cancelled && !adapter.busy());
        assert(!query->cancels && !query->closes && !launch->cancels && !launch->closes);
    }
    for (bool queryMode : {true, false}) for (bool statusError : {true, false}) {
        reset(); Native adapter;
        assert((queryMode ? adapter.query(zoom, current) : adapter.launch(zoom, CalendarLauncherMode::native, current)) == CalendarLauncherStart::started);
        query->status = launch->status = statusError ? AsyncStatus::Error : AsyncStatus::Completed;
        query->resultFault = launch->resultFault = !statusError;
        const auto answer = adapter.poll();
        assert(answer.state == CalendarLauncherPollState::completed && answer.outcome == CalendarLauncherOutcome::failed && !adapter.busy());
    }
}
void dispatchAndPollReentry() {
    for (bool queryMode : {true, false}) {
        reset(); Native adapter;
        const auto reenter = [&] {
            assert(adapter.busy() && adapter.query(zoom, current) == CalendarLauncherStart::busy);
            assert(adapter.poll().state == CalendarLauncherPollState::pending); adapter.cancel();
        };
        onDispatch = reenter;
        assert((queryMode ? adapter.query(zoom, current) : adapter.launch(zoom, CalendarLauncherMode::native, current)) == CalendarLauncherStart::started);
        assert(adapter.busy()); onDispatch = {};
        assert(adapter.poll().state == CalendarLauncherPollState::pending);
        query->status = launch->status = AsyncStatus::Completed; query->answer = LaunchQuerySupportStatus::Available; launch->answer = true;
        query->onResults = launch->onResults = reenter;
        assert(adapter.poll().outcome == CalendarLauncherOutcome::cancelled && !adapter.busy());
        assert(!query->cancels && !launch->cancels);
    }
    reset(); Native adapter;
    assert(adapter.query(zoom, current) == CalendarLauncherStart::started);
    query->onStatus = [&] { assert(adapter.poll().state == CalendarLauncherPollState::pending); adapter.cancel(); };
    assert(adapter.poll().state == CalendarLauncherPollState::pending && adapter.busy());
    query->onStatus = {}; query->status = AsyncStatus::Completed;
    assert(adapter.poll().outcome == CalendarLauncherOutcome::cancelled && !adapter.busy());
}
void launchAndStartFailures() {
    for (bool queryMode : {true, false}) for (bool throws : {true, false}) {
        reset(); Native adapter; startFault = throws; nullStart = !throws;
        assert((queryMode ? adapter.query(zoom, current) : adapter.launch(zoom, CalendarLauncherMode::browser, current)) == CalendarLauncherStart::startFailed);
        assert(!adapter.busy() && adapter.poll().state == CalendarLauncherPollState::idle);
        assert(queries + launches == 1); // No automatic second launch/fallback.
    }
    for (auto mode : {CalendarLauncherMode::browser, CalendarLauncherMode::native}) for (bool success : {true, false}) {
        reset(); Native adapter;
        assert(adapter.launch(zoom, mode, current) == CalendarLauncherStart::started);
        assert(ignoreHandlers == (mode == CalendarLauncherMode::browser));
        assert(capturedURI.rfind(mode == CalendarLauncherMode::browser ? L"https://" : L"zoommtg://", 0) == 0);
        assert(adapter.poll().state == CalendarLauncherPollState::pending && adapter.busy());
        launch->status = AsyncStatus::Completed; launch->answer = success;
        const auto answer = adapter.poll();
        assert(answer.state == CalendarLauncherPollState::completed && answer.outcome ==
            (success ? CalendarLauncherOutcome::launched : CalendarLauncherOutcome::failed) && !adapter.busy());
        assert(!queries && launches == 1 && !launch->cancels && !launch->closes);
    }
}
int main() {
    winrt::init_apartment(winrt::apartment_type::single_threaded);
    preDispatch(); queryStatuses(); cancelAndFaults(); dispatchAndPollReentry(); launchAndStartFailures();
    std::puts("NativeCalendarLauncherTests passed; fake statics, actual WinRT interfaces; no real launch");
}
