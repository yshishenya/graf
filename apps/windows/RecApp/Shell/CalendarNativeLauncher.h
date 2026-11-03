#pragma once
#include <functional>
#include <string_view>
#ifdef _WIN32
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.System.h>
#endif

namespace graf::windows {
enum class CalendarLauncherStart { started, busy, rejected, startFailed };
enum class CalendarLauncherMode { native, browser };
enum class CalendarLauncherPollState { idle, pending, completed, indeterminate };
enum class CalendarLauncherOutcome { available, appNotInstalled, appUnavailable, notSupported, unknown,
    launched, failed, cancelled };
struct CalendarLauncherPoll {
    CalendarLauncherPollState state = CalendarLauncherPollState::idle;
    CalendarLauncherOutcome outcome = CalendarLauncherOutcome::failed;
};

// UI-thread-owned SDK child only. No auth, dialog, resolver or Record authority.
// Owner retains this instance/ticket until proven completion; destruction isn't
// completion or a promise that an already dispatched OS action was revoked.
class CalendarNativeLauncher final {
public:
    using Current = std::function<bool()>;
    CalendarNativeLauncher() = default;
    CalendarNativeLauncher(const CalendarNativeLauncher&) = delete;
    CalendarNativeLauncher& operator=(const CalendarNativeLauncher&) = delete;
    [[nodiscard]] CalendarLauncherStart query(std::string_view validatedHTTPS, const Current&) noexcept;
    [[nodiscard]] CalendarLauncherStart launch(std::string_view validatedHTTPS, CalendarLauncherMode, const Current&) noexcept;
    [[nodiscard]] CalendarLauncherPoll poll() noexcept;
    [[nodiscard]] bool busy() const noexcept;
    // Discard applicability only. RemoteAsync Cancel/Close isn't actual drain.
    void cancel() noexcept { discard_ = true; }
private:
    [[nodiscard]] CalendarLauncherStart start(std::string_view, bool query, CalendarLauncherMode, const Current&) noexcept;
    bool nativeCalling_ = false, discard_ = false;
#ifdef _WIN32
    winrt::Windows::Foundation::IAsyncOperation<winrt::Windows::System::LaunchQuerySupportStatus> query_{nullptr};
    winrt::Windows::Foundation::IAsyncOperation<bool> launch_{nullptr};
#endif
};
}
