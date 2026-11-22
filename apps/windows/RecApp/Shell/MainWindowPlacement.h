#pragma once

#include <cstdint>
#include <optional>
#include <string>

#ifdef _WIN32
#include <windows.h>
#include <winrt/Windows.Foundation.Collections.h>
#endif

namespace graf::windows {

struct MainWindowRect {
    std::int32_t x = 0, y = 0, width = 0, height = 0;
};

// Physical pixels, relative to MONITORINFO.rcWork; no runtime monitor handles.
struct MainWindowPlacement {
    std::wstring monitorIdentity;
    std::int32_t offsetX = 0, offsetY = 0, width = 0, height = 0, dpi = 0;
};

[[nodiscard]] bool validMainWindowPlacement(MainWindowPlacement const& value) noexcept;
[[nodiscard]] std::optional<MainWindowRect> restoreMainWindowRect(
    std::optional<MainWindowPlacement> const& saved, MainWindowRect work,
    std::int32_t dpi, bool sameMonitor) noexcept;

#ifdef _WIN32
struct MainWindowMonitor {
    HMONITOR handle = nullptr; // Ephemeral, never written to settings.
    MainWindowRect work;
    std::wstring identity;
    bool matchesSaved = false;
};
using MainWindowSettings = winrt::Windows::Foundation::Collections::IMap<
    winrt::hstring, winrt::Windows::Foundation::IInspectable>;
inline constexpr wchar_t mainWindowPlacementKey[] = L"main-window-placement.v1";

[[nodiscard]] std::optional<MainWindowMonitor> mainWindowRestoreMonitor(
    std::optional<MainWindowPlacement> const& saved) noexcept;
// Rejects hidden, minimized and maximized HWNDs. The WinUI caller additionally
// requires its own OverlappedPresenter to be Restored, outside restoration.
[[nodiscard]] std::optional<MainWindowPlacement> sampleMainWindowPlacement(HWND window) noexcept;
[[nodiscard]] std::optional<MainWindowPlacement> readMainWindowPlacement(MainWindowSettings const& settings) noexcept;
[[nodiscard]] bool writeMainWindowPlacement(MainWindowSettings const& settings, MainWindowPlacement const& value) noexcept;
[[nodiscard]] std::optional<MainWindowPlacement> readMainWindowPlacement() noexcept;
[[nodiscard]] bool writeMainWindowPlacement(MainWindowPlacement const& value) noexcept;

// UI-thread state shared by WinUI events and the native lifecycle regression.
// Deferred save/hide/quit consume accepted geometry, never a later HWND frame.
class MainWindowPlacementEvents {
public:
    void ready() noexcept { if (!stopped_) ready_ = true; }
    void stop() noexcept { ready_ = false; stopped_ = true; }
    [[nodiscard]] bool changed(HWND window, bool presenterRestored) noexcept;
    void flush() noexcept;
    void flush(MainWindowSettings const& settings) noexcept;
    [[nodiscard]] std::optional<MainWindowPlacement> const& pending() const noexcept { return pending_; }
private:
    bool ready_ = false, stopped_ = false;
    std::optional<MainWindowPlacement> pending_;
};
#endif

} // namespace graf::windows
