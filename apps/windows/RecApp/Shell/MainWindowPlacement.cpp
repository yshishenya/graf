#include "MainWindowPlacement.h"

#include <algorithm>
#include <limits>

#ifdef _WIN32
#include <vector>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Storage.h>
#endif

namespace graf::windows {
namespace {
bool fitsInt32(std::int64_t value) noexcept {
    return value >= (std::numeric_limits<std::int32_t>::min)() &&
        value <= (std::numeric_limits<std::int32_t>::max)();
}
std::optional<std::int32_t> scale(std::int32_t value, std::int32_t to, std::int32_t from) noexcept {
    // Both DPI values are positive int32; product and rounded numerator fit int64.
    const auto product = static_cast<std::int64_t>(value) * to;
    const auto rounded = (product + (product < 0 ? -from / 2 : from / 2)) / from;
    if (!fitsInt32(rounded)) return std::nullopt;
    return static_cast<std::int32_t>(rounded);
}
}

bool validMainWindowPlacement(MainWindowPlacement const& value) noexcept {
    return !value.monitorIdentity.empty() && value.monitorIdentity.size() < 128 &&
        value.monitorIdentity.find(L'\0') == std::wstring::npos &&
        value.width > 0 && value.height > 0 && value.dpi > 0;
}

std::optional<MainWindowRect> restoreMainWindowRect(std::optional<MainWindowPlacement> const& saved,
    MainWindowRect work, std::int32_t dpi, bool sameMonitor) noexcept {
    if (dpi <= 0 || work.width <= 0 || work.height <= 0 ||
        !fitsInt32(static_cast<std::int64_t>(work.x) + work.width) ||
        !fitsInt32(static_cast<std::int64_t>(work.y) + work.height)) return std::nullopt;
    const auto fit = [work](std::int32_t width, std::int32_t height,
                            std::int32_t offsetX, std::int32_t offsetY, bool centered) {
        width = (std::min)(width, work.width); height = (std::min)(height, work.height);
        const auto x = centered ? (work.width - width) / 2 : std::clamp(offsetX, 0, work.width - width);
        const auto y = centered ? (work.height - height) / 2 : std::clamp(offsetY, 0, work.height - height);
        return MainWindowRect{work.x + x, work.y + y, width, height};
    };
    if (saved && validMainWindowPlacement(*saved)) {
        const auto width = scale(saved->width, dpi, saved->dpi), height = scale(saved->height, dpi, saved->dpi);
        const auto x = scale(saved->offsetX, dpi, saved->dpi), y = scale(saved->offsetY, dpi, saved->dpi);
        if (width && height && *width > 0 && *height > 0 && x && y &&
            (!sameMonitor || (fitsInt32(static_cast<std::int64_t>(work.x) + *x) &&
                             fitsInt32(static_cast<std::int64_t>(work.y) + *y))))
            return fit(*width, *height, *x, *y, !sameMonitor);
    }
    const auto width = scale(1080, dpi, 96), height = scale(620, dpi, 96);
    if (!width || !height || *width <= 0 || *height <= 0) return std::nullopt;
    return fit(*width, *height, 0, 0, true);
}

#ifdef _WIN32
namespace {
struct Monitor {
    MainWindowMonitor value;
    bool primary = false;
};
BOOL CALLBACK collectMonitor(HMONITOR handle, HDC, LPRECT, LPARAM context) noexcept {
    auto& monitors = *reinterpret_cast<std::vector<Monitor>*>(context);
    try {
        MONITORINFOEXW info{}; info.cbSize = sizeof(info);
        if (!GetMonitorInfoW(handle, &info)) return FALSE;
        const auto width = static_cast<std::int64_t>(info.rcWork.right) - info.rcWork.left;
        const auto height = static_cast<std::int64_t>(info.rcWork.bottom) - info.rcWork.top;
        if (width <= 0 || height <= 0 || !fitsInt32(width) || !fitsInt32(height)) return FALSE;
        std::wstring identity;
        unsigned identities = 0;
        for (DWORD index = 0;; ++index) {
            DISPLAY_DEVICEW device{}; device.cb = sizeof(device);
            if (!EnumDisplayDevicesW(info.szDevice, index, &device, EDD_GET_DEVICE_INTERFACE_NAME)) break;
            if (!(device.StateFlags & DISPLAY_DEVICE_ACTIVE)) continue;
            ++identities; identity = device.DeviceID;
        }
        if (identities != 1) identity.clear();
        monitors.push_back({{handle, {info.rcWork.left, info.rcWork.top,
            static_cast<std::int32_t>(width), static_cast<std::int32_t>(height)}, std::move(identity), false},
            (info.dwFlags & MONITORINFOF_PRIMARY) != 0});
        return TRUE;
    } catch (...) { return FALSE; }
}
std::vector<Monitor> monitorsNow() {
    std::vector<Monitor> monitors;
    if (!EnumDisplayMonitors(nullptr, nullptr, collectMonitor, reinterpret_cast<LPARAM>(&monitors))) return {};
    // Mirrored/ambiguous identities must not select or persist an arbitrary screen.
    for (auto& monitor : monitors) {
        if (monitor.value.identity.empty()) continue;
        unsigned count = 0;
        for (const auto& other : monitors)
            if (_wcsicmp(monitor.value.identity.c_str(), other.value.identity.c_str()) == 0) ++count;
        if (count != 1) {
            const auto duplicate = monitor.value.identity;
            for (auto& other : monitors)
                if (_wcsicmp(duplicate.c_str(), other.value.identity.c_str()) == 0) other.value.identity.clear();
        }
    }
    return monitors;
}
}

std::optional<MainWindowMonitor> mainWindowRestoreMonitor(std::optional<MainWindowPlacement> const& saved) noexcept {
    try {
        const auto monitors = monitorsNow();
        if (saved && validMainWindowPlacement(*saved)) {
            for (const auto& monitor : monitors) {
                if (!monitor.value.identity.empty() &&
                    _wcsicmp(saved->monitorIdentity.c_str(), monitor.value.identity.c_str()) == 0) {
                    auto result = monitor.value; result.matchesSaved = true; return result;
                }
            }
        }
        for (const auto& monitor : monitors) if (monitor.primary) return monitor.value;
    } catch (...) {}
    return std::nullopt;
}

std::optional<MainWindowPlacement> sampleMainWindowPlacement(HWND window) noexcept {
    try {
        if (!window || !IsWindowVisible(window) || IsIconic(window) || IsZoomed(window)) return std::nullopt;
        RECT rect{};
        if (!GetWindowRect(window, &rect)) return std::nullopt;
        const auto handle = MonitorFromWindow(window, MONITOR_DEFAULTTONULL);
        const auto dpi = GetDpiForWindow(window);
        if (!dpi || dpi > static_cast<UINT>((std::numeric_limits<std::int32_t>::max)())) return std::nullopt;
        for (const auto& monitor : monitorsNow()) {
            if (monitor.value.handle != handle) continue;
            const auto x = static_cast<std::int64_t>(rect.left) - monitor.value.work.x;
            const auto y = static_cast<std::int64_t>(rect.top) - monitor.value.work.y;
            const auto width = static_cast<std::int64_t>(rect.right) - rect.left;
            const auto height = static_cast<std::int64_t>(rect.bottom) - rect.top;
            if (!fitsInt32(x) || !fitsInt32(y) || !fitsInt32(width) || !fitsInt32(height)) return std::nullopt;
            MainWindowPlacement value{monitor.value.identity, static_cast<std::int32_t>(x), static_cast<std::int32_t>(y),
                static_cast<std::int32_t>(width), static_cast<std::int32_t>(height), static_cast<std::int32_t>(dpi)};
            if (validMainWindowPlacement(value)) return value;
        }
    } catch (...) {}
    return std::nullopt;
}

std::optional<MainWindowPlacement> readMainWindowPlacement(MainWindowSettings const& settings) noexcept {
    try {
        if (!settings) return std::nullopt;
        const auto composite = settings.Lookup(mainWindowPlacementKey).as<winrt::Windows::Storage::ApplicationDataCompositeValue>();
        if (!composite || composite.Size() != 7 || winrt::unbox_value<std::int32_t>(composite.Lookup(L"version")) != 1) return std::nullopt;
        MainWindowPlacement value{std::wstring(winrt::unbox_value<winrt::hstring>(composite.Lookup(L"monitor"))),
            winrt::unbox_value<std::int32_t>(composite.Lookup(L"x")), winrt::unbox_value<std::int32_t>(composite.Lookup(L"y")),
            winrt::unbox_value<std::int32_t>(composite.Lookup(L"width")), winrt::unbox_value<std::int32_t>(composite.Lookup(L"height")),
            winrt::unbox_value<std::int32_t>(composite.Lookup(L"dpi"))};
        if (validMainWindowPlacement(value)) return value;
    } catch (...) {}
    return std::nullopt;
}
bool writeMainWindowPlacement(MainWindowSettings const& settings, MainWindowPlacement const& value) noexcept {
    try {
        if (!settings || !validMainWindowPlacement(value)) return false;
        winrt::Windows::Storage::ApplicationDataCompositeValue composite;
        composite.Insert(L"version", winrt::box_value(std::int32_t{1}));
        composite.Insert(L"monitor", winrt::box_value(winrt::hstring(value.monitorIdentity)));
        composite.Insert(L"x", winrt::box_value(value.offsetX)); composite.Insert(L"y", winrt::box_value(value.offsetY));
        composite.Insert(L"width", winrt::box_value(value.width)); composite.Insert(L"height", winrt::box_value(value.height));
        composite.Insert(L"dpi", winrt::box_value(value.dpi));
        // A single composite replacement; never remove the previous value first.
        settings.Insert(mainWindowPlacementKey, composite);
        return true;
    } catch (...) { return false; }
}
std::optional<MainWindowPlacement> readMainWindowPlacement() noexcept {
    try { return readMainWindowPlacement(winrt::Windows::Storage::ApplicationData::Current().LocalSettings().Values()); }
    catch (...) { return std::nullopt; }
}
bool writeMainWindowPlacement(MainWindowPlacement const& value) noexcept {
    try { return writeMainWindowPlacement(winrt::Windows::Storage::ApplicationData::Current().LocalSettings().Values(), value); }
    catch (...) { return false; }
}
bool MainWindowPlacementEvents::changed(HWND window, bool presenterRestored) noexcept {
    if (!ready_ || !presenterRestored) return false;
    if (auto value = sampleMainWindowPlacement(window)) {
        pending_ = std::move(value); return true;
    }
    return false;
}
void MainWindowPlacementEvents::flush() noexcept {
    if (pending_ && writeMainWindowPlacement(*pending_)) pending_.reset();
}
void MainWindowPlacementEvents::flush(MainWindowSettings const& settings) noexcept {
    if (pending_ && writeMainWindowPlacement(settings, *pending_)) pending_.reset();
}
#endif

} // namespace graf::windows
