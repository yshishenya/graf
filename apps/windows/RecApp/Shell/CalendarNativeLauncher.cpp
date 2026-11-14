#include "CalendarNativeLauncher.h"
#include "CalendarMeetingOpener.h"
#ifdef _WIN32
#pragma comment(lib, "windowsapp.lib")
#endif

namespace graf::windows {
bool CalendarNativeLauncher::busy() const noexcept {
#ifdef _WIN32
    return nativeCalling_ || query_ || launch_;
#else
    return nativeCalling_;
#endif
}
CalendarLauncherStart CalendarNativeLauncher::query(std::string_view https, const Current& current) noexcept {
    return start(https, true, CalendarLauncherMode::native, current);
}
CalendarLauncherStart CalendarNativeLauncher::launch(std::string_view https, CalendarLauncherMode mode, const Current& current) noexcept {
    return start(https, false, mode, current);
}
CalendarLauncherStart CalendarNativeLauncher::start(std::string_view https, bool query, CalendarLauncherMode mode, const Current& current) noexcept {
    if (busy()) return CalendarLauncherStart::busy;
    nativeCalling_ = true;
    struct Guard { bool& flag; ~Guard() { flag = false; } } guard{nativeCalling_};
    discard_ = false;
#ifdef _WIN32
    using namespace winrt::Windows::Foundation;
    using namespace winrt::Windows::System;
    bool dispatched = false;
    try {
        const auto target = mode == CalendarLauncherMode::browser
            ? CalendarMeetingOpener::validatedHTTPS(https) : CalendarMeetingOpener::nativeTarget(https);
        if (!target || !current) return CalendarLauncherStart::rejected;
        const Uri uri(winrt::to_hstring(*target));
        LauncherOptions options;
        options.IgnoreAppUriHandlers(mode == CalendarLauncherMode::browser);
        // URI/options construction and current may dispatch messages. The guard
        // precedes all of them; reentrant cancel must prevent a new OS call.
        if (discard_ || !current() || discard_) return CalendarLauncherStart::rejected;
        dispatched = true;
        if (query) query_ = Launcher::QueryUriSupportAsync(uri, LaunchQuerySupportType::Uri);
        else launch_ = Launcher::LaunchUriAsync(uri, options);
        // Keep any obtained handle even if the dispatch reentrantly cancelled.
        return query_ || launch_ ? CalendarLauncherStart::started : CalendarLauncherStart::startFailed;
    } catch (...) {
        // No owned handle: dispatch scope ended, not proof of no OS side effect.
        return dispatched ? CalendarLauncherStart::startFailed : CalendarLauncherStart::rejected;
    }
#else
    (void)https; (void)query; (void)mode; (void)current;
    return CalendarLauncherStart::rejected;
#endif
}
CalendarLauncherPoll CalendarNativeLauncher::poll() noexcept {
    if (nativeCalling_) return {CalendarLauncherPollState::pending};
    if (!busy()) return {};
    nativeCalling_ = true;
    struct Guard { bool& flag; ~Guard() { flag = false; } } guard{nativeCalling_};
#ifdef _WIN32
    using namespace winrt::Windows::Foundation;
    using namespace winrt::Windows::System;
    bool resultReady = false;
    try {
        const auto status = query_ ? query_.Status() : launch_.Status();
        if (status == AsyncStatus::Started) return {CalendarLauncherPollState::pending};
        if (status != AsyncStatus::Completed && status != AsyncStatus::Error) {
            discard_ = true; return {CalendarLauncherPollState::indeterminate};
        }
        resultReady = status == AsyncStatus::Completed;
    } catch (...) {
        discard_ = true; return {CalendarLauncherPollState::indeterminate};
    }
    auto outcome = CalendarLauncherOutcome::failed;
    try {
        if (resultReady && query_) {
            switch (query_.GetResults()) {
            case LaunchQuerySupportStatus::Available: outcome = CalendarLauncherOutcome::available; break;
            case LaunchQuerySupportStatus::AppNotInstalled: outcome = CalendarLauncherOutcome::appNotInstalled; break;
            case LaunchQuerySupportStatus::AppUnavailable: outcome = CalendarLauncherOutcome::appUnavailable; break;
            case LaunchQuerySupportStatus::NotSupported: outcome = CalendarLauncherOutcome::notSupported; break;
            case LaunchQuerySupportStatus::Unknown: outcome = CalendarLauncherOutcome::unknown; break;
            default: outcome = CalendarLauncherOutcome::unknown; break;
            }
        } else if (resultReady && launch_.GetResults()) outcome = CalendarLauncherOutcome::launched;
    } catch (...) { /* Known natural terminal, but result failed. */ }
    query_ = nullptr; launch_ = nullptr;
    return {CalendarLauncherPollState::completed, discard_ ? CalendarLauncherOutcome::cancelled : outcome};
#else
    return {};
#endif
}
}
