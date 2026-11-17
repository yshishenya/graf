#include "Shell/MainWindowPlacement.h"
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Storage.h>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

using namespace graf::windows;
using namespace winrt::Windows::Foundation;
using namespace winrt::Windows::Foundation::Collections;

namespace {
// Fail the real WinRT lookup/replacement interface without touching user data.
struct FaultSettings : winrt::implements<FaultSettings, MainWindowSettings,
    IIterable<IKeyValuePair<winrt::hstring, IInspectable>>> {
    MainWindowSettings values = winrt::single_threaded_map<winrt::hstring, IInspectable>();
    bool readFault = false, writeFault = false;
    unsigned inserts = 0;
    IInspectable Lookup(winrt::hstring const& key) {
        if (readFault) throw winrt::hresult_error(E_ACCESSDENIED);
        return values.Lookup(key);
    }
    std::uint32_t Size() { return values.Size(); }
    bool HasKey(winrt::hstring const& key) { return values.HasKey(key); }
    IMapView<winrt::hstring, IInspectable> GetView() { return values.GetView(); }
    bool Insert(winrt::hstring const& key, IInspectable const& value) {
        ++inserts;
        if (writeFault) throw winrt::hresult_error(E_ACCESSDENIED);
        return values.Insert(key, value);
    }
    void Remove(winrt::hstring const& key) { values.Remove(key); }
    void Clear() { values.Clear(); }
    IIterator<IKeyValuePair<winrt::hstring, IInspectable>> First() { return values.First(); }
};
bool equal(MainWindowPlacement const& a, MainWindowPlacement const& b) {
    return a.monitorIdentity == b.monitorIdentity && a.offsetX == b.offsetX && a.offsetY == b.offsetY &&
        a.width == b.width && a.height == b.height && a.dpi == b.dpi;
}
void storage() {
    const auto store = winrt::make_self<FaultSettings>();
    const auto settings = store.as<MainWindowSettings>();
    assert(!readMainWindowPlacement(settings));
    store->values.Insert(mainWindowPlacementKey, nullptr);
    assert(settings.Size() == 1 && settings.HasKey(mainWindowPlacementKey) && !settings.Lookup(mainWindowPlacementKey));
    assert(!readMainWindowPlacement(settings));
    assert(store->inserts == 0 && settings.Size() == 1 &&
        settings.HasKey(mainWindowPlacementKey) && !settings.Lookup(mainWindowPlacementKey));
    const MainWindowPlacement original{L"synthetic-interface", -41, 73, 903, 581, 144};
    assert(writeMainWindowPlacement(settings, original) && store->inserts == 1);
    assert(equal(*readMainWindowPlacement(settings), original));
    const auto previous = store->values.Lookup(mainWindowPlacementKey);
    store->readFault = true;
    assert(!readMainWindowPlacement(settings));
    store->readFault = false; store->writeFault = true;
    auto newer = original; newer.width = 1200;
    assert(!writeMainWindowPlacement(settings, newer));
    assert(store->values.Lookup(mainWindowPlacementKey) == previous);
    assert(equal(*readMainWindowPlacement(settings), original));
    store->writeFault = false;
    assert(!readMainWindowPlacement(MainWindowSettings{nullptr}));
    assert(!writeMainWindowPlacement(MainWindowSettings{nullptr}, original));
    auto invalid = original; invalid.dpi = 0;
    const auto inserts = store->inserts;
    assert(!writeMainWindowPlacement(settings, invalid) && store->inserts == inserts);
    store->values.Insert(mainWindowPlacementKey, winrt::box_value(L"bad"));
    assert(!readMainWindowPlacement(settings));
    for (int corruption = 0; corruption < 5; ++corruption) {
        assert(writeMainWindowPlacement(settings, original));
        auto composite = store->values.Lookup(mainWindowPlacementKey).as<winrt::Windows::Storage::ApplicationDataCompositeValue>();
        if (corruption == 0) composite.Remove(L"height");
        if (corruption == 1) composite.Insert(L"version", winrt::box_value(std::int32_t{2}));
        if (corruption == 2) composite.Insert(L"width", winrt::box_value(std::int32_t{-1}));
        if (corruption == 3) composite.Insert(L"x", winrt::box_value(L"13"));
        if (corruption == 4) composite.Insert(L"unknown", winrt::box_value(true));
        const auto corrupt = store->values.Lookup(mainWindowPlacementKey);
        assert(!readMainWindowPlacement(settings));
        assert(store->values.Lookup(mainWindowPlacementKey) == corrupt);
    }
    for (const auto field : {L"version", L"monitor", L"x", L"y", L"width", L"height", L"dpi"}) {
        assert(writeMainWindowPlacement(settings, original));
        const auto corrupt = store->values.Lookup(mainWindowPlacementKey);
        auto composite = corrupt.as<winrt::Windows::Storage::ApplicationDataCompositeValue>();
        // ApplicationDataCompositeValue removes the member when assigned nullptr.
        composite.Insert(field, nullptr);
        const auto beforeReadInserts = store->inserts;
        assert(composite.Size() == 6 && !composite.HasKey(field) && !composite.Lookup(field));
        assert(!readMainWindowPlacement(settings));
        assert(store->inserts == beforeReadInserts && settings.Size() == 1 && settings.Lookup(mainWindowPlacementKey) == corrupt);
        assert(composite.Size() == 6 && !composite.HasKey(field) && !composite.Lookup(field));
    }
}

struct WindowEvents {
    MainWindowPlacementEvents placement;
    unsigned accepted = 0;
};
LRESULT CALLBACK windowProcedure(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    if (message == WM_NCCREATE) {
        const auto create = reinterpret_cast<CREATESTRUCTW*>(lparam);
        SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(create->lpCreateParams));
    }
    if (message == WM_WINDOWPOSCHANGED) {
        const auto state = reinterpret_cast<WindowEvents*>(GetWindowLongPtrW(window, GWLP_USERDATA));
        if (state && state->placement.changed(window, true)) ++state->accepted;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}
void nativeWindowEvents() {
    const auto monitor = mainWindowRestoreMonitor(std::nullopt);
    assert(monitor && monitor->handle && !monitor->matchesSaved);
    WNDCLASSW windowClass{};
    windowClass.lpfnWndProc = windowProcedure;
    windowClass.hInstance = GetModuleHandleW(nullptr);
    windowClass.lpszClassName = L"GrafMainWindowPlacementContract";
    assert(RegisterClassW(&windowClass));
    WindowEvents events;
    const auto rect = restoreMainWindowRect(std::nullopt, monitor->work, 96, false);
    assert(rect);
    const auto window = CreateWindowExW(0, windowClass.lpszClassName, L"GRAF placement test",
        WS_OVERLAPPEDWINDOW, rect->x, rect->y, rect->width, rect->height,
        nullptr, nullptr, windowClass.hInstance, &events);
    assert(window);
    ShowWindow(window, SW_SHOWNOACTIVATE);
    assert(events.accepted == 0);
    events.placement.ready();
    assert(SetWindowPos(window, nullptr, rect->x + 7, rect->y + 9, rect->width - 20, rect->height - 20,
        SWP_NOZORDER | SWP_NOACTIVATE));
    assert(events.accepted && events.placement.pending());
    const auto normal = *events.placement.pending();
    const auto accepted = events.accepted;
    const auto selected = mainWindowRestoreMonitor(normal);
    assert(selected && selected->matchesSaved && selected->handle == monitor->handle);
    auto absent = normal; absent.monitorIdentity = L"synthetic-removed-monitor";
    const auto primary = mainWindowRestoreMonitor(absent);
    assert(primary && !primary->matchesSaved && primary->handle == monitor->handle);
    const auto store = winrt::make_self<FaultSettings>();
    const auto settings = store.as<MainWindowSettings>();
    assert(!events.placement.changed(window, false)); // WinUI presenter gate.
    store->writeFault = true;
    events.placement.flush(settings);
    assert(events.placement.pending() && !readMainWindowPlacement(settings));
    store->writeFault = false;
    for (const auto state : {SW_MAXIMIZE, SW_MINIMIZE, SW_HIDE}) {
        ShowWindow(window, state);
        assert(!sampleMainWindowPlacement(window));
        assert(events.accepted == accepted);
        // Hide/Quit write the accepted normal value, not the current frame.
        events.placement.flush(settings);
        assert(equal(*readMainWindowPlacement(settings), normal));
        assert(!events.placement.pending());
    }
    events.placement.stop();
    ShowWindow(window, SW_RESTORE);
    events.placement.ready(); // A queued startup callback cannot revive teardown.
    assert(!events.placement.changed(window, true) && events.accepted == accepted);
    assert(DestroyWindow(window));
    assert(!sampleMainWindowPlacement(window));
    const auto cold = readMainWindowPlacement(settings);
    assert(cold && equal(*cold, normal));
    const auto restored = restoreMainWindowRect(cold, monitor->work, normal.dpi, true);
    assert(restored && restored->width == normal.width && restored->height == normal.height);
    assert(UnregisterClassW(windowClass.lpszClassName, windowClass.hInstance));
}
}

int main() {
    winrt::init_apartment(winrt::apartment_type::single_threaded);
    assert(SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2) ||
        AreDpiAwarenessContextsEqual(GetThreadDpiAwarenessContext(), DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2));
    storage();
    nativeWindowEvents();
    winrt::uninit_apartment();
    return 0;
}
