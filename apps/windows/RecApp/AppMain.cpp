#ifdef _WIN32

#include <windows.h>
// Project headers can include WinUI: remove Win32 aliases before any of them.
#ifdef GetClassName
#undef GetClassName
#endif
#ifdef GetCurrentTime
#undef GetCurrentTime
#endif

#include "Audio/RecordingAudioTimeline.h"
#include "Audio/WasapiEndpointEnumerator.h"
#include "Capture/WindowsCaptureSessionController.h"
#include "Diagnostics/MetadataSafeDiagnostics.h"
#include "MeetingDetection/AutomaticRecordingPolicy.h"
#include "Permissions/WindowsReadinessGate.h"
#include "Recording/V5LocalRecordingWriter.h"
#include "Recording/NativeCapture.h"
#include "Recording/LocalRecordingPackage.h"
#include "Storage/AtomicFileStore.h"
#include "Shell/CabinetWindow.h"
#include "Shell/WindowsTray.h"
#include "Shell/WindowsAppUpdateController.h"
#include "Shell/ShellClosePolicy.h"
#include "Shell/AutomaticRecordingPrompt.h"
#include "Shell/MicrophoneConsentKey.h"
#include "Shell/RecordingNoticePresenter.h"
#include "Shell/RecordingOutcomeText.h"
#include "Shell/ShellPalette.h"
#include "Upload/DesktopUploadQueueService.h"
#include "Upload/DesktopUploadRecoveryScheduler.h"
#include "Upload/DesktopApiClient.h"
#include "Upload/DesktopHttpTransport.h"
#include "Upload/ProductAttributionHandoff.h"
#include "Shell/MeetingReminderPresenter.h"
#include "Shell/CalendarNativeLauncher.h"
#include "Shell/CalendarMeetingOpener.h"
#include "Web/NativeSettingsBridge.h"
#include "../Native/GrafAEC3/GrafAEC3WebRtcAdapter.h"

#include <knownfolders.h>
#include <combaseapi.h>
#include <shlobj.h>
#include <shellapi.h>
#include <winreg.h>

#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Xaml.Controls.Primitives.h>
#include <winrt/Microsoft.UI.Xaml.Input.h>
#include <winrt/Microsoft.UI.Xaml.Automation.h>
#include <winrt/Microsoft.UI.Xaml.Automation.Peers.h>
#include <winrt/Microsoft.UI.Xaml.Media.h>
#include <winrt/Microsoft.UI.Xaml.Markup.h>
#include <winrt/Microsoft.UI.Xaml.XamlTypeInfo.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#include <winrt/Microsoft.UI.Windowing.h>
#include <winrt/Microsoft.Windows.AppLifecycle.h>
#include <winrt/Windows.ApplicationModel.Activation.h>
#include <winrt/Windows.ApplicationModel.h>
#include <winrt/Windows.ApplicationModel.DataTransfer.h>
#include <appmodel.h>

#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Graphics.h>
#include <winrt/Windows.System.Profile.h>
#include <winrt/Windows.System.h>
#include <winrt/Windows.Storage.h>
#include <winrt/Windows.Data.Json.h>
#include <dwmapi.h>
#include <fstream>

// Заголовок окна рисует система, поэтому её же библиотека нужна для его цветов.
#pragma comment(lib, "dwmapi.lib")
#include <winrt/Windows.UI.h>
#include <winrt/Windows.UI.Text.h>
#include <winrt/Windows.UI.Xaml.Interop.h>
#include <microsoft.ui.xaml.window.h>

#include <mfapi.h>
#include <mftransform.h>

#include <chrono>
#include <filesystem>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <cwchar>
#include <iterator>
#include <limits>
#include <future>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

namespace {

using namespace winrt;
using namespace winrt::Microsoft::UI::Xaml;
using namespace winrt::Microsoft::UI::Xaml::Controls;
using namespace winrt::Microsoft::UI::Xaml::Media;
using winrt::Windows::UI::Text::FontWeight;
using winrt::Windows::UI::Text::FontWeights;
using winrt::Microsoft::UI::Dispatching::DispatcherQueueTimer;

using graf::windows::NativeCapture;
using graf::windows::AecSelection;
using graf::windows::native_capture_detail::CustodyMutationScope;
using graf::windows::native_capture_detail::newSessionId;
using graf::windows::native_capture_detail::deviceDisplayName;

std::int64_t attributionNow() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

// AppLifecycle can deliver a second launch before XAML exists or from another
// thread. Keep only the last validated handoff; the UI thread owns persistence.
struct PendingActivation {
    bool bringForward = false;
    std::optional<graf::windows::ProductAttributionHandoff> handoff;
};
std::mutex activationMutex;
PendingActivation pendingActivation;

void receiveActivation(const winrt::Microsoft::Windows::AppLifecycle::AppActivationArguments& args) noexcept {
    try {
        using winrt::Microsoft::Windows::AppLifecycle::ExtendedActivationKind;
        std::optional<graf::windows::ProductAttributionHandoff> handoff;
        if (args.Kind() == ExtendedActivationKind::Protocol) {
            const auto protocol = args.Data().try_as<winrt::Windows::ApplicationModel::Activation::IProtocolActivatedEventArgs>();
            if (!protocol) return;
            const auto uri = protocol.Uri().RawUri();
            if (uri.size() > graf::windows::ProductAttributionHandoff::maximumLinkBytes) return;
            handoff = graf::windows::ProductAttributionHandoff::parse(winrt::to_string(uri), attributionNow());
            if (!handoff) return;
        } else if (args.Kind() != ExtendedActivationKind::Launch) return;
        std::lock_guard<std::mutex> lock(activationMutex);
        pendingActivation.bringForward = true;
        if (handoff) pendingActivation.handoff = std::move(handoff);
    } catch (...) {} // Invalid/optional analytics never blocks ordinary launch.
}

void redirectActivation(const winrt::Microsoft::Windows::AppLifecycle::AppInstance& instance,
                        const winrt::Microsoft::Windows::AppLifecycle::AppActivationArguments& args) {
    struct RedirectCompletion {
        winrt::handle event{CreateEventW(nullptr, TRUE, FALSE, nullptr)};
        HRESULT result = E_FAIL;
    };
    auto completion = std::make_shared<RedirectCompletion>();
    if (!completion->event) winrt::throw_last_error();
    // Redirect asynchronously from MTA while STA pumps COM calls. Calling get()
    // on the XAML STA can deadlock activation. Shared state survives a timeout.
    std::thread([completion, target = winrt::agile_ref(instance), activation = winrt::agile_ref(args)] {
        try {
            winrt::init_apartment(winrt::apartment_type::multi_threaded);
            target.get().RedirectActivationToAsync(activation.get()).get();
            completion->result = S_OK;
        } catch (...) { completion->result = winrt::to_hresult(); }
        SetEvent(completion->event.get());
    }).detach();
    HANDLE event = completion->event.get();
    DWORD index = 0;
    winrt::check_hresult(CoWaitForMultipleHandles(COWAIT_DISPATCH_CALLS, 30000, 1, &event, &index));
    winrt::check_hresult(completion->result);
}

// Какая тема у системы. Кабинет объявляет «system», когда пользователь не выбрал
// тему в самом кабинете, и тогда оформление окна обязано совпасть с системой.
// Значок берётся из пакета: без него в заголовке и на панели задач виден
// системный значок-заглушка, и приложение выглядит чужим. Значок ставится
// каждому окну: у настроек, автозаписи и полосы записи он свой.
void applyWindowIcon(const winrt::Microsoft::UI::Xaml::Window& window) noexcept {
    try {
        const winrt::Windows::ApplicationModel::Package package =
            winrt::Windows::ApplicationModel::Package::Current();
        window.AppWindow().SetIcon(package.InstalledLocation().Path() + L"\\Assets\\Graf.ico");
    } catch (...) {
        // Незапакованный запуск: значок остаётся системным, работа важнее.
    }
}

bool systemThemeIsDark() {
    DWORD appsUseLightTheme = 1;
    DWORD size = sizeof(appsUseLightTheme);
    HKEY key = nullptr;
    if (RegOpenKeyExW(HKEY_CURRENT_USER,
                      L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                      0, KEY_QUERY_VALUE, &key) == ERROR_SUCCESS) {
        if (RegQueryValueExW(key, L"AppsUseLightTheme", nullptr, nullptr,
                            reinterpret_cast<LPBYTE>(&appsUseLightTheme), &size) != ERROR_SUCCESS) {
            appsUseLightTheme = 1;
        }
        RegCloseKey(key);
    }
    return appsUseLightTheme == 0;
}

// Высокая контрастность Windows распоряжается цветами сама.
bool shellHighContrast() {
    HIGHCONTRASTW contrast{sizeof(HIGHCONTRASTW)};
    return SystemParametersInfoW(SPI_GETHIGHCONTRAST, sizeof(contrast), &contrast, 0) &&
        (contrast.dwFlags & HCF_HIGHCONTRASTON) != 0;
}

// Кисти оболочки берутся из одного набора (`ShellPalette`), значения которого
// совпадают с палитрой кабинета и с macOS. Высокая контрастность Windows
// распоряжается цветами сама: там значения набора не применяются.
void refreshShellPalette(bool isDark) {
    const bool highContrast = shellHighContrast();
    // Кисти обновляются всегда: ранний выход по «тема не менялась» однажды
    // разошёлся с тем, что видно на экране, и окно осталось светлым при тёмной
    // теме. Пересборка двух десятков кистей дешевле такого расхождения.
    const auto contrastColor = [](std::wstring_view key) {
        // Полоса записи — состояние, а не оформление: остаётся цветом окна.
        if (key.find(L"RecordingStrip") != std::wstring_view::npos) return COLOR_WINDOW;
        // Текст обязан быть виден на окне: system colors дают его иначе невидимым.
        if (key.find(L"TextBrush") != std::wstring_view::npos) return COLOR_WINDOWTEXT;
        if (key.find(L"Stroke") != std::wstring_view::npos ||
            key.find(L"Line") != std::wstring_view::npos) {
            return COLOR_WINDOWTEXT;
        }
        if (key.find(L"Accent") != std::wstring_view::npos) return COLOR_HIGHLIGHT;
        return COLOR_WINDOW;
    };
    auto resources = Application::Current().Resources();
    for (const auto& entry : graf::windows::shellPaletteEntries()) {
        const auto palette = graf::windows::shellPaletteColor(entry, isDark);
        const auto system = GetSysColor(contrastColor(std::wstring_view(entry.key)));
        const auto red = highContrast ? GetRValue(system) : static_cast<BYTE>(palette.rgb >> 16);
        const auto green = highContrast ? GetGValue(system) : static_cast<BYTE>(palette.rgb >> 8);
        const auto blue = highContrast ? GetBValue(system) : static_cast<BYTE>(palette.rgb & 0xFF);
        const auto alpha = highContrast ? static_cast<BYTE>(255)
                                        : static_cast<BYTE>(palette.alpha * 255.0 + 0.5);
        const auto value = winrt::Windows::UI::ColorHelper::FromArgb(alpha, red, green, blue);
        const auto key = box_value(entry.key);
        if (resources.HasKey(key)) {
            if (const auto brush = resources.Lookup(key).try_as<SolidColorBrush>()) {
                brush.Color(value);
                continue;
            }
        }
        resources.Insert(key, SolidColorBrush(value));
    }
}

HWND nativeWindowHandle(Window const& window) noexcept;

// Размер окна задан в логических точках, как у macOS, а WinUI считает размер в
// физических пикселях. На экране с масштабом 200 % окно выходило вдвое меньше
// задуманного: панель управления не помещалась по ширине.
void resizeWindowLogical(Window const& window, std::int32_t logicalWidth, std::int32_t logicalHeight, bool centerOnWorkArea = false) {
    try {
        const auto handle = nativeWindowHandle(window);
        const auto dpi = handle ? static_cast<double>(GetDpiForWindow(handle)) : 96.0;
        const auto scale = dpi > 0.0 ? dpi / 96.0 : 1.0;
        auto width = static_cast<std::int32_t>(logicalWidth * scale + 0.5);
        auto height = static_cast<std::int32_t>(logicalHeight * scale + 0.5);
        // Окно не должно оказаться больше рабочей области: иначе часть
        // управления недоступна, а окно нельзя подвинуть.
        try {
            const auto area = winrt::Microsoft::UI::Windowing::DisplayArea::GetFromWindowId(
                window.AppWindow().Id(), winrt::Microsoft::UI::Windowing::DisplayAreaFallback::Primary);
            const auto work = area.WorkArea();
            if (work.Width > 0 && work.Height > 0) {
                width = std::min(width, work.Width);
                height = std::min(height, work.Height);
            }
        } catch (...) {
            // Рабочая область недоступна: размер остаётся задуманным.
        }
        window.AppWindow().Resize(winrt::Windows::Graphics::SizeInt32{width, height});
        // Главное окно и настройки становятся по центру рабочей области, как
        // окна macOS: системное размещение оставляет их в углу экрана.
        if (centerOnWorkArea) {
            try {
                const auto area = winrt::Microsoft::UI::Windowing::DisplayArea::GetFromWindowId(
                    window.AppWindow().Id(), winrt::Microsoft::UI::Windowing::DisplayAreaFallback::Primary);
                const auto work = area.WorkArea();
                if (work.Width > 0 && work.Height > 0) {
                    const auto left = work.X + (work.Width - width) / 2;
                    const auto top = work.Y + (work.Height - height) / 2;
                    window.AppWindow().Move(winrt::Windows::Graphics::PointInt32{left, top});
                }
            } catch (...) {
                // Рабочая область недоступна: окно остаётся там, где его поставила система.
            }
        }
    } catch (...) {
        // Окно остаётся системного размера: это не повод не показывать его.
    }
}

HWND nativeWindowHandle(Window const& window) noexcept {
    HWND handle = nullptr;
    try {
        auto native = window.as<::IWindowNative>();
        if (native) (void)native->get_WindowHandle(&handle);
    } catch (...) {
        handle = nullptr;
    }
    return handle;
}

// Системный заголовок окна Windows рисует сама и по системной теме: на тёмном
// приложении он остаётся светлой полосой. Цвета заголовка задаются явно, чтобы
// окна приложения выглядели одинаково в обеих темах.
void applyWindowChrome(HWND window, bool isDark) {
    if (!window) return;
    BOOL dark = isDark ? TRUE : FALSE;
    // 20 — Windows 11, 19 — сборки до неё: первый поддерживаемый и решает.
    if (FAILED(DwmSetWindowAttribute(window, 20, &dark, sizeof(dark)))) {
        DwmSetWindowAttribute(window, 19, &dark, sizeof(dark));
    }
    const auto colorOf = [isDark](std::wstring_view key, COLORREF fallback) {
        for (const auto& entry : graf::windows::shellPaletteEntries()) {
            if (entry.key != key) continue;
            const auto value = graf::windows::shellPaletteColor(entry, isDark);
            return RGB((value.rgb >> 16) & 0xFF, (value.rgb >> 8) & 0xFF, value.rgb & 0xFF);
        }
        return fallback;
    };
    // 35 — фон заголовка, 36 — его текст, 34 — рамка окна.
    const auto caption = colorOf(L"GrafPanelBrush", isDark ? RGB(29, 31, 35) : RGB(255, 255, 255));
    const auto text = colorOf(L"GrafTextBrush", isDark ? RGB(240, 241, 244) : RGB(29, 34, 43));
    const auto border = colorOf(L"GrafLineSoftBrush", isDark ? RGB(70, 74, 84) : RGB(226, 229, 235));
    DwmSetWindowAttribute(window, 35, &caption, sizeof(caption));
    DwmSetWindowAttribute(window, 36, &text, sizeof(text));
    DwmSetWindowAttribute(window, 34, &border, sizeof(border));
}

Brush themeBrush(std::wstring_view name) {
    return Application::Current().Resources().Lookup(box_value(hstring(name))).as<Brush>();
}

// Текст оболочки всегда берёт цвет из набора оформления: системный цвет текста
// совпадает с фоном окна в противоположной теме и делает надписи нечитаемыми.
void styleText(TextBlock const& text, double size = 13.0,
               FontWeight weight = FontWeights::Normal(), bool muted = false) {
    text.FontSize(size);
    text.FontWeight(weight);
    text.TextWrapping(TextWrapping::Wrap);
    text.Foreground(themeBrush(muted ? L"GrafMutedTextBrush" : L"GrafTextBrush"));
}

void setAccessible(DependencyObject const& element, std::wstring name, std::wstring help = {}) {
    element.SetValue(winrt::Microsoft::UI::Xaml::Automation::AutomationProperties::NameProperty(), box_value(name));
    if (!help.empty()) {
        element.SetValue(winrt::Microsoft::UI::Xaml::Automation::AutomationProperties::HelpTextProperty(), box_value(help));
    }
}

// Кнопки оболочки рисуются её же кистями, а не системными: иначе в светлой теме
// на тёмной панели появляются светлые кнопки с тёмными подписями. Рецепт тот же,
// что у кнопок кабинета: поверхность `surface-2`, граница `line`, текст `text`,
// наведение — `surface-3`, скругление 9.
void applyShellButtonPalette(Button const& button) {
    // В высокой контрастности кнопки остаются системными: свои кисти сделали бы
    // неактивную кнопку неотличимой от активной.
    if (shellHighContrast()) return;
    button.CornerRadius(CornerRadius{9, 9, 9, 9});
    auto resources = button.Resources();
    const std::pair<const wchar_t*, const wchar_t*> entries[] = {
        {L"ButtonBackground", L"GrafSurface2Brush"},
        {L"ButtonBackgroundPointerOver", L"GrafSurface3Brush"},
        {L"ButtonBackgroundPressed", L"GrafSurface3Brush"},
        {L"ButtonBackgroundDisabled", L"GrafPanelBrush"},
        {L"ButtonForeground", L"GrafTextBrush"},
        {L"ButtonForegroundPointerOver", L"GrafTextBrush"},
        {L"ButtonForegroundPressed", L"GrafTextBrush"},
        {L"ButtonForegroundDisabled", L"GrafMutedTextBrush"},
        {L"ButtonBorderBrush", L"GrafLineBrush"},
        {L"ButtonBorderBrushPointerOver", L"GrafAccentBrush"},
        {L"ButtonBorderBrushPressed", L"GrafAccentBrush"},
        {L"ButtonBorderBrushDisabled", L"GrafLineSoftBrush"},
    };
    for (const auto& [key, token] : entries) {
        resources.Insert(box_value(key), themeBrush(token));
    }
}

Button styledButton(std::wstring label, bool primary = false) {
    auto button = Button();
    button.Content(box_value(label));
    button.MinHeight(36);
    button.Padding(Thickness{14, 0, 14, 0});
    if (primary) {
        button.Style(Application::Current().Resources().Lookup(box_value(L"AccentButtonStyle")).as<Style>());
        button.CornerRadius(CornerRadius{9, 9, 9, 9});
        // Стиль акцентной кнопки берёт системный акцент: заливка обязана быть
        // акцентом GRAF, как у macOS, иначе кнопка выпадает из оформления окна.
        auto accent = button.Resources();
        const std::pair<const wchar_t*, const wchar_t*> accents[] = {
            {L"AccentButtonBackground", L"GrafAccentSolidBrush"},
            {L"AccentButtonBackgroundPointerOver", L"GrafAccentHoverBrush"},
            {L"AccentButtonBackgroundPressed", L"GrafAccentHoverBrush"},
            {L"AccentButtonBackgroundDisabled", L"GrafSurface3Brush"},
            {L"AccentButtonForeground", L"GrafAccentForegroundBrush"},
            {L"AccentButtonForegroundPointerOver", L"GrafAccentForegroundBrush"},
            {L"AccentButtonForegroundPressed", L"GrafAccentForegroundBrush"},
            {L"AccentButtonForegroundDisabled", L"GrafMutedTextBrush"},
            {L"AccentButtonBorderBrush", L"GrafAccentSolidBrush"},
        };
        for (const auto& [key, token] : accents) {
            accent.Insert(box_value(key), themeBrush(token));
        }
        return button;
    }
    applyShellButtonPalette(button);
    return button;
}

Button iconButton(Symbol symbol, std::wstring label) {
    auto button = styledButton(L"");
    button.Content(SymbolIcon(symbol));
    button.Width(40);
    button.Height(40);
    button.Padding(Thickness{0, 0, 0, 0});
    setAccessible(button, label);
    ToolTipService::SetToolTip(button, box_value(label));
    return button;
}

Border card(UIElement const& child, double padding = 14.0) {
    auto result = Border();
    result.Child(child);
    result.Padding(Thickness{padding, padding, padding, padding});
    result.Background(themeBrush(L"CardBackgroundFillColorDefaultBrush"));
    result.BorderBrush(themeBrush(L"CardStrokeColorDefaultBrush"));
    result.BorderThickness(Thickness{1, 1, 1, 1});
    result.CornerRadius(CornerRadius{8, 8, 8, 8});
    return result;
}

std::filesystem::path localAppData() {
    PWSTR raw = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DEFAULT, nullptr, &raw)) || raw == nullptr) {
        return {};
    }
    std::filesystem::path result(raw);
    CoTaskMemFree(raw);
    return result;
}

std::filesystem::path localCustodyRoot() {
    const auto appData = localAppData();
    if (appData.empty()) return {};
    return appData / "GRAF" / "recordings";
}


class UnavailableAec3 final : public graf::windows::IAec3Processor {
public:
    bool process(const float*, const float*, float*) noexcept override { return false; }
};


AecSelection selectAec() {
    auto native = graf::windows::GrafAEC3WebRtcAdapter::create();
    if (native != nullptr) {
        return {std::shared_ptr<graf::windows::IAec3Processor>(std::move(native)), true};
    }
    return {std::make_shared<UnavailableAec3>(), false};
}


class GrafApp : public ApplicationT<GrafApp, winrt::Microsoft::UI::Xaml::Markup::IXamlMetadataProvider> {
    struct ReminderIntent { graf::windows::ReminderActionTarget target; graf::windows::NoticeAction action; };
public:
    // This native-only app has no generated App.xaml provider. WinUI control
    // resources still need the SDK's type metadata when loading their XBF.
    winrt::Microsoft::UI::Xaml::Markup::IXamlType GetXamlType(winrt::Windows::UI::Xaml::Interop::TypeName const& type) {
        return xamlMetadata_.GetXamlType(type);
    }
    winrt::Microsoft::UI::Xaml::Markup::IXamlType GetXamlType(hstring const& name) {
        return xamlMetadata_.GetXamlType(name);
    }
    winrt::com_array<winrt::Microsoft::UI::Xaml::Markup::XmlnsDefinition> GetXmlnsDefinitions() {
        return xamlMetadata_.GetXmlnsDefinitions();
    }
    void OnLaunched(LaunchActivatedEventArgs const&) {
        try {
            const auto directory = localAppData();
            if (!directory.empty()) attribution_ = std::make_unique<graf::windows::ProductAttributionHandoffStore>(
                directory / "GRAF" / "product-attribution.v1");
        } catch (...) {} // Attribution storage must not prevent sign-in or capture.
        applyPendingActivation(false);
        Resources().MergedDictionaries().Append(XamlControlsResources());
        const bool systemIsDark = systemThemeIsDark();
        shellIsDark_ = graf::windows::resolveShellIsDark(announcedAppearance_, systemIsDark);
        refreshShellPalette(shellIsDark_);
        if (cabinet_) cabinet_->webView().setPreferredColorScheme(shellIsDark_);
        window_ = Window();
        root_ = Grid();
        root_.RequestedTheme(shellIsDark_ ? ElementTheme::Dark : ElementTheme::Light);
        root_.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
        window_.Content(root_);
        bool shellReady = false;
        try {
            buildShell();
            window_.AppWindow().Title(L"GRAF");
            applyWindowIcon(window_);
            // Размер ставится при первой активации: до неё окно ещё не привязано
            // к монитору, `GetDpiForWindow` отвечает промежуточным значением, и
            // окно получалось втрое больше задуманного. Смысл размера прежний:
            // вся нативная панель помещается на небольшом экране Windows, а
            // кабинет остаётся отзывчивым внутри оболочки.
            window_.Activated([this](auto const&, WindowActivatedEventArgs const& args) {
                if (mainWindowSized_ || args.WindowActivationState() == WindowActivationState::Deactivated) return;
                mainWindowSized_ = true;
                resizeWindowLogical(window_, 1080, 620, true);
            });
            capture_ = std::make_unique<NativeCapture>(localCustodyRoot(), selectAec());
            capture_->startStorageValidation();
            capture_->notificationCard().setDarkTheme(shellIsDark_);
            capture_->notificationCard().protectedFramesProvider = [this] { return notificationProtectedFrames(); };
            capture_->notificationCard().interactionPermitProvider = [this] { return interactionPermit(); };
            reminders_ = std::make_unique<graf::windows::MeetingReminderPresenter>(capture_->notificationCard());
            reminders_->onMeetingPresented = [this] { playOptionalNotificationSound(); };
            const auto alive = alive_;
            capture_->onShortRecordingPresented = [this, alive] {
                if (alive->load()) playOptionalNotificationSound();
            };
            reminders_->onActionRequested = [this](auto target, auto action) {
                if (action == graf::windows::NoticeAction::join || action == graf::windows::NoticeAction::joinAndRecord) {
                    beginNativeCalendarJoin({std::move(target), action}); return;
                }
                if (pendingReminderAction_ || reminderFlightAction_) return;
                pendingReminderAction_ = ReminderIntent{std::move(target), action};
                lastReminderRequest_ = 0; // a click requires a new server read
            };
            root_.KeyDown([this](auto const&, auto const& args) {
                if (args.Key() == winrt::Windows::System::VirtualKey::F6 && focusBackgroundSurface()) args.Handled(true);
            });
            capture_->setSessionExpiryHandler([this](std::int64_t seconds) {
                if (!cabinet_ || shuttingDown_) return;
                // The cookie is rewritten only while it still holds the token the
                // request used; a session that changed meanwhile is never prolonged.
                cabinet_->webView().extendAuthCookieExpiry(capture_->authSessionToken(), seconds);
            });
            (void)ensureRecordingIndicator(false);
            refreshNativeState();
            shellReady = true;
        } catch (const winrt::hresult_error& error) {
            showStartupError(error.message().c_str());
        } catch (...) {
            showStartupError(L"Не удалось инициализировать Windows shell");
        }
        window_.AppWindow().Closing([this](auto const&, auto const& args) {
            if (shuttingDown_) return;
            using namespace graf::windows;
            const auto state = capture_ ? capture_->indicator().state : SessionState::idle;
            const auto action = shellCloseAction(ShellCloseIntent::window, state,
                tray_ && tray_->available(), recordingIndicatorAvailable(), exitRequested_);
            if (action == ShellCloseAction::close) {
                beginExit();
                if (exitWorkDrained()) return;
                // Cancel is a request, not proof that Windows has stopped the
                // deployment. Keep polling before releasing the app lifetime.
            }
            args.Cancel(true);
            // Hiding must not cancel automaticPolicy_: it also owns tracking
            // and end-of-meeting Stop for the current automatic recording.
            if (action == ShellCloseAction::hide) { cancelCalendarJoin(); window_.AppWindow().Hide(); }
            else refreshTrayAvailability();
        });
        window_.Closed([this](auto const&, auto const&) {
            cancelLocalPlayback();
            cancelCalendarJoin();
            // Teardown is not drain. A resolver owns only copied config/result,
            // but its std::thread still must be reaped before member destruction.
            if (calendarResolverThread_.joinable()) calendarResolverThread_.join();
            shuttingDown_ = true;
            alive_->store(false);
            if (reminderCancellation_) reminderCancellation_->store(true);
            reminderRequestIdentity_ = {};
            if (reminders_) reminders_->invalidate();
            automaticPolicy_.cancel();
            (void)closeAutomaticPrompt(automaticPromptGeneration_);
            if (cabinet_) cabinet_->webView().close();
            if (settingsWindow_) settingsWindow_.Close();
            appUpdate_.close();
            if (updateWindow_) updateWindow_.Close();
            if (stateTimer_) stateTimer_.Stop();
            if (capture_) capture_->shutdown();
            if (indicatorWindow_) indicatorWindow_.Close();
            tray_.reset();
        });
        if (!shellReady) {
            window_.Activate();
            return;
        }
        window_.Activated([this](auto const&, auto const&) {
            if (capture_) capture_->recover(graf::windows::RecoveryTrigger::activation);
            if (!mainWindowHandle_) {
                mainWindowHandle_ = nativeWindowHandle(window_);
                if (!mainWindowHandle_) mainWindowHandle_ = FindWindowW(nullptr, L"GRAF");
            }
            window_.Content().DispatcherQueue().TryEnqueue([this] { initializeWebView(); });
        });
        stateTimer_ = window_.Content().DispatcherQueue().CreateTimer();
        stateTimer_.Interval(winrt::Windows::Foundation::TimeSpan{2500000});
        stateTimer_.Tick([this](auto const&, auto const&) {
            refreshNativeState();
        });
        stateTimer_.Start();
        window_.Activate();
        if (!mainWindowHandle_) {
            mainWindowHandle_ = nativeWindowHandle(window_);
            if (!mainWindowHandle_) mainWindowHandle_ = FindWindowW(nullptr, L"GRAF");
        }
        try {
            tray_ = std::make_unique<graf::windows::WindowsTray>(
            reinterpret_cast<std::uintptr_t>(mainWindowHandle_),
            [this] {
                // Возврат окна из значка — то, что нельзя проверить иначе, чем
                // живым щелчком: шаг записывается в журнал оформления.
                try {
                    const auto folder = winrt::Windows::Storage::ApplicationData::Current().LocalFolder().Path();
                    std::ofstream log(std::filesystem::path(folder.c_str()) / L"appearance.log", std::ios::app);
                    log << GetTickCount64() << " tray-open\n";
                } catch (...) {}
                openMainWindow();
            },
            [this] { stopCapture(); },
            [this] { requestExit(); },
            [this] { pauseResumeCapture(); },
            [this] { recordCapture(); },
            [this] { openAccountSettings(); },
            [this] {
                if (!shuttingDown_ && capture_ && capture_->notificationCard().visible())
                    capture_->notificationCard().focus();
            },
            [this] { invalidateNotificationInteraction(); });
            tray_->setTheme(shellIsDark_);
            tray_->setUpdateHandler([this] { openUpdateWindow(); });
            const auto alive = alive_;
            tray_->setCalendarHandler([this, alive](graf::windows::UpcomingMeetingRow row) {
                if (alive->load()) beginMenuCalendarJoin(std::move(row));
            });
        } catch (...) {
            trayFailureText_.Text(L"Значок GRAF недоступен. Управляйте записью в этом окне; кнопка «Остановить» остаётся доступной.");
            trayFailureText_.Visibility(Visibility::Visible);
            inspectorExpanded_ = true;
            window_.Activate();
        }
        refreshNativeState();
        // Permission recovery stays inline; open the dialog only on request.
    }

private:
    void applyPendingActivation(bool showWindow = true) {
        if (capture_ && capture_->updateAdmissionBlocked()) return;
        const CustodyMutationScope mutation(shellMutations_);
        PendingActivation activation;
        {
            std::lock_guard<std::mutex> lock(activationMutex);
            activation = std::exchange(pendingActivation, {});
        }
        if (activation.handoff) {
            attributionSignInRequested_ = true;
            if (attribution_) {
                try { (void)attribution_->save(*activation.handoff); } catch (...) {}
            }
        }
        if (attributionSignInRequested_ && cabinet_) {
            attributionSignInRequested_ = false;
            (void)cabinet_->open(cabinet_->webView().signInUrl());
        }
        if (activation.bringForward && showWindow && window_ && !shuttingDown_) {
            window_.AppWindow().Show();
            if (mainWindowHandle_) {
                ShowWindow(mainWindowHandle_, SW_RESTORE);
                SetForegroundWindow(mainWindowHandle_);
            }
            window_.Activate();
        }
    }

    void openMainWindow() {
        if (!window_ || shuttingDown_) return;
        window_.AppWindow().Show();
        if (mainWindowHandle_) {
            ShowWindow(mainWindowHandle_, SW_RESTORE);
            SetForegroundWindow(mainWindowHandle_);
        }
        window_.Activate();
    }

    void openAccountSettings() {
        if (shuttingDown_ || exitRequested_) return;
        openMainWindow();
        initializeWebView();
        if (cabinet_) {
            const auto url = cabinet_->webView().routePolicy().trustedOrigin() + "/desktop/settings/account";
            (void)cabinet_->open(url);
        }
    }

    bool focusBackgroundSurface() {
        // Explicit keyboard navigation is allowed to activate a background
        // surface; automatic detection and capture must never use this path.
        if (shuttingDown_) return false;
        if (capture_ && capture_->notificationCard().visible() &&
            capture_->notificationCard().kind() == graf::windows::NoticeKind::recordingPrompt) {
            capture_->notificationCard().focus();
            return true;
        }
        if (capture_ && capture_->indicator().visible && recordingIndicatorAvailable()) {
            indicatorWindow_.Activate();
            return indicatorStop_.Focus(FocusState::Keyboard);
        }
        if (capture_ && capture_->notificationCard().visible()) {
            capture_->notificationCard().focus();
            return true;
        }
        return false;
    }

    std::vector<graf::windows::NoticeRect> notificationProtectedFrames() const {
        std::vector<graf::windows::NoticeRect> frames;
        if (!capture_ || !capture_->indicator().visible) return frames;
        const auto protectWindow = [&frames](HWND handle) {
            RECT rect{};
            if (handle && IsWindowVisible(handle) && !IsIconic(handle) && GetWindowRect(handle, &rect))
                frames.push_back({rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top});
        };
        // Protect the complete compact indicator, which always contains Stop.
        if (indicatorWindow_) protectWindow(nativeWindowHandle(indicatorWindow_));
        if (mainWindowHandle_ && IsWindowVisible(mainWindowHandle_) && !IsIconic(mainWindowHandle_)) {
            try {
                const auto point = recordingStripStop_.TransformToVisual(root_).TransformPoint({0, 0});
                POINT client{};
                const auto scale = static_cast<double>(GetDpiForWindow(mainWindowHandle_)) / 96.0;
                if (!ClientToScreen(mainWindowHandle_, &client) || scale <= 0 ||
                    recordingStripStop_.ActualWidth() <= 0 || recordingStripStop_.ActualHeight() <= 0) {
                    protectWindow(mainWindowHandle_);
                } else frames.push_back({client.x + static_cast<int>(std::floor(point.X * scale)),
                    client.y + static_cast<int>(std::floor(point.Y * scale)),
                    static_cast<int>(std::ceil(recordingStripStop_.ActualWidth() * scale)),
                    static_cast<int>(std::ceil(recordingStripStop_.ActualHeight() * scale))});
            } catch (...) { protectWindow(mainWindowHandle_); }
        }
        return frames;
    }

    void refreshTrayAvailability() {
        if (shuttingDown_ || !window_) return;
        const bool available = tray_ && tray_->available();
        if (trayFailureText_) {
            trayFailureText_.Text(available ? L"" :
                L"Значок GRAF недоступен. Окно остаётся открытым для управления записью. Для выхода выберите «Закрыть GRAF».");
            trayFailureText_.Visibility(available ? Visibility::Collapsed : Visibility::Visible);
        }
        if (trayExitButton_) {
            trayExitButton_.Visibility(available ? Visibility::Collapsed : Visibility::Visible);
            trayExitButton_.IsEnabled(!exitRequested_);
        }
        if (!available) {
            inspectorExpanded_ = true;
            updateInspectorVisibility();
            // Explorer can disappear after the window has already been hidden.
            // Restore a reachable shell without stealing the meeting's focus.
            if (!window_.AppWindow().IsVisible()) window_.AppWindow().Show(false);
            if (mainWindowHandle_ && IsIconic(mainWindowHandle_))
                ShowWindow(mainWindowHandle_, SW_SHOWNOACTIVATE);
        }
    }

    void buildShell() {
        root_.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
        recordingStripRow_ = RowDefinition();
        recordingStripRow_.Height(GridLengthHelper::FromValueAndType(0.0, GridUnitType::Pixel));
        root_.RowDefinitions().Append(recordingStripRow_);
        auto contentRow = RowDefinition();
        contentRow.Height(GridLengthHelper::FromValueAndType(1.0, GridUnitType::Star));
        root_.RowDefinitions().Append(contentRow);
        buildRecordingStrip();
        content_ = Grid();
        auto mainColumn = ColumnDefinition();
        mainColumn.Width(GridLengthHelper::FromValueAndType(1.0, GridUnitType::Star));
        auto inspectorColumn = ColumnDefinition();
        inspectorColumn_ = inspectorColumn;
        inspectorColumn_.Width(GridLengthHelper::FromValueAndType(52.0, GridUnitType::Pixel));
        content_.ColumnDefinitions().Append(mainColumn);
        content_.ColumnDefinitions().Append(inspectorColumn_);
        buildMeetingsSurface();
        buildInspector();
        Grid::SetRow(content_, 1);
        root_.Children().Append(recordingStrip_);
        root_.Children().Append(content_);
        window_.Content(root_);
    }

    void buildRecordingStrip() {
        recordingStrip_ = Border();
        recordingStrip_.Background(themeBrush(L"GrafRecordingStripBrush"));
        recordingStrip_.Padding(Thickness{16, 6, 12, 6});
        auto row = Grid();
        auto textColumn = ColumnDefinition();
        textColumn.Width(GridLengthHelper::FromValueAndType(1.0, GridUnitType::Star));
        row.ColumnDefinitions().Append(textColumn);
        auto actionColumn = ColumnDefinition();
        actionColumn.Width(GridLengthHelper::FromValueAndType(120.0, GridUnitType::Pixel));
        row.ColumnDefinitions().Append(actionColumn);
        recordingStripText_ = TextBlock();
        styleText(recordingStripText_, 13, FontWeights::SemiBold());
        recordingStripText_.VerticalAlignment(VerticalAlignment::Center);
        setAccessible(recordingStripText_, L"Идёт запись", L"Нативный индикатор записи GRAF");
        row.Children().Append(recordingStripText_);
        recordingStripStop_ = styledButton(L"Остановить");
        recordingStripStop_.MinHeight(32);
        recordingStripStop_.Click([this](auto const&, auto const&) { stopCapture(); });
        setAccessible(recordingStripStop_, L"Остановить запись");
        Grid::SetColumn(recordingStripStop_, 1);
        row.Children().Append(recordingStripStop_);
        recordingStrip_.Child(row);
        recordingStrip_.Visibility(Visibility::Collapsed);
    }

    void buildMeetingsSurface() {
        meetingsSurface_ = Grid();
        meetingsSurface_.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
        auto navigationRow = RowDefinition();
        navigationRow.Height(GridLengthHelper::FromValueAndType(48.0, GridUnitType::Pixel));
        meetingsSurface_.RowDefinitions().Append(navigationRow);
        meetingsSurface_.RowDefinitions().Append(RowDefinition());
        auto navigation = StackPanel();
        navigation.Orientation(Orientation::Horizontal);
        navigation.Spacing(4);
        navigation.Margin(Thickness{8, 4, 8, 4});
        backButton_ = iconButton(Symbol::Back, L"Назад в кабинете");
        backButton_.Click([this](auto const&, auto const&) { if (cabinet_) cabinet_->webView().back(); });
        forwardButton_ = iconButton(Symbol::Forward, L"Вперёд в кабинете");
        forwardButton_.Click([this](auto const&, auto const&) { if (cabinet_) cabinet_->webView().forward(); });
        auto reload = iconButton(Symbol::Refresh, L"Обновить кабинет");
        reload.Click([this](auto const&, auto const&) {
            if (cabinet_) cabinet_->webView().reload();
        });
        auto meetings = styledButton(L"Встречи");
        meetings.Click([this](auto const&, auto const&) { if (cabinet_) (void)cabinet_->openCabinet(); });
        navigation.Children().Append(backButton_);
        navigation.Children().Append(forwardButton_);
        navigation.Children().Append(reload);
        navigation.Children().Append(meetings);
        meetingsSurface_.Children().Append(navigation);
        webView_ = WebView2();
        webView_.HorizontalAlignment(HorizontalAlignment::Stretch);
        webView_.VerticalAlignment(VerticalAlignment::Stretch);
        Grid::SetRow(webView_, 1);
        meetingsSurface_.Children().Append(webView_);
        localFallback_ = Border();
        localFallback_.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
        localFallback_.Padding(Thickness{24, 24, 24, 24});
        auto fallback = StackPanel();
        fallback.Spacing(18);
        auto heading = TextBlock();
        heading.Text(L"Записи");
        styleText(heading, 22, FontWeights::SemiBold());
        auto subtitle = TextBlock();
        subtitle.Text(L"Кабинет загрузится после входа. Нативная запись и локальная сохранность работают отдельно от веб-страницы.");
        styleText(subtitle, 13);
        auto statusCard = StackPanel();
        statusCard.Spacing(8);
        fallbackCabinetTitle_ = TextBlock();
        fallbackCabinetTitle_.Text(L"Кабинет недоступен");
        styleText(fallbackCabinetTitle_, 15, FontWeights::SemiBold());
        fallbackCabinetDetail_ = TextBlock();
        fallbackCabinetDetail_.Text(L"Проверьте соединение или войдите снова — локальная запись не потеряется.");
        styleText(fallbackCabinetDetail_, 13);
        statusCard.Children().Append(fallbackCabinetTitle_);
        statusCard.Children().Append(fallbackCabinetDetail_);
        fallback.Children().Append(heading);
        fallback.Children().Append(subtitle);
        fallback.Children().Append(card(statusCard));
        fallbackCabinetAction_ = styledButton(L"Повторить загрузку");
        fallbackCabinetAction_.Click([this](auto const&, auto const&) {
            if (cabinet_) {
                auto& host = cabinet_->webView();
                if (host.pendingAuthRecovery() != graf::windows::WebResponseDecision::ignore) {
                    fallbackCabinetAction_.IsEnabled(false);
                    if (host.navigate(host.recoveryUrl()).decision != graf::windows::RouteDecision::allow)
                        fallbackCabinetAction_.IsEnabled(true);
                } else host.reload();
            } else initializeWebView();
        });
        setAccessible(fallbackCabinetAction_, L"Повторить загрузку кабинета", L"Запись и локальная очередь не сбрасываются");
        fallback.Children().Append(fallbackCabinetAction_);
        localFallback_.Child(fallback);
        localFallback_.Visibility(Visibility::Visible);
        Grid::SetRow(localFallback_, 1);
        meetingsSurface_.Children().Append(localFallback_);
        Grid::SetColumn(meetingsSurface_, 0);
        content_.Children().Append(meetingsSurface_);
    }

    void initializeWebView() {
        if (webViewAttached_ || !meetingsSurface_ || !webView_) return;
        try {
            configureCabinet();
            cabinet_->attach(webView_);
            webViewAttached_ = true;
        } catch (...) {
            showCabinetFallback(L"Не удалось открыть кабинет", L"Повторите загрузку. Нативная запись остаётся доступной.");
        }
    }

    void buildInspector() {
        expandedInspector_ = Border();
        expandedInspector_.Background(themeBrush(L"LayerFillColorDefaultBrush"));
        auto scroll = ScrollViewer();
        auto body = StackPanel();
        body.Spacing(12);

        expandedInspectorToggle_ = iconButton(Symbol::Forward, L"Скрыть панель управления");
        expandedInspectorToggle_.HorizontalAlignment(HorizontalAlignment::Right);
        expandedInspectorToggle_.Click([this](auto const&, auto const&) { toggleInspector(); });
        body.Children().Append(expandedInspectorToggle_);

        auto header = Grid();
        header.ColumnDefinitions().Append(ColumnDefinition());
        auto headerActionColumn = ColumnDefinition();
        headerActionColumn.Width(GridLengthHelper::FromValueAndType(36.0, GridUnitType::Pixel));
        header.ColumnDefinitions().Append(headerActionColumn);
        auto headerText = TextBlock();
        headerText.Text(L"Запись");
        styleText(headerText, 15, FontWeights::SemiBold());
        header.Children().Append(headerText);
        auto settingsButton = iconButton(Symbol::Setting, L"Настройки");
        settingsButton.Width(36);
        settingsButton.Padding(Thickness{0, 0, 0, 0});
        settingsButton.Click([this](auto const&, auto const&) { openAccountSettings(); });
        setAccessible(settingsButton, L"Настройки");
        Grid::SetColumn(settingsButton, 1);
        header.Children().Append(settingsButton);
        body.Children().Append(header);
        auto captureCard = StackPanel();
        captureCard.Spacing(10);
        captureStatus_ = TextBlock();
        styleText(captureStatus_, 13, FontWeights::SemiBold());
        setAccessible(captureStatus_, L"Статус записи", L"Текущее состояние нативной записи GRAF");
        captureCard.Children().Append(captureStatus_);
        captureOutcomeText_ = TextBlock();
        styleText(captureOutcomeText_, 12);
        captureCard.Children().Append(captureOutcomeText_);
        recordButton_ = styledButton(L"Начать запись", true);
        setAccessible(recordButton_, L"Начать запись системного звука");
        recordButton_.Click([this](auto const&, auto const&) { recordCapture(); });
        captureCard.Children().Append(recordButton_);
        pauseButton_ = styledButton(L"Пауза");
        setAccessible(pauseButton_, L"Поставить запись на паузу");
        pauseButton_.Click([this](auto const&, auto const&) {
            pauseResumeCapture();
        });
        stopButton_ = styledButton(L"Остановить");
        setAccessible(stopButton_, L"Остановить запись");
        stopButton_.Click([this](auto const&, auto const&) { stopCapture(); });
        auto controls = StackPanel();
        controls.Orientation(Orientation::Horizontal);
        controls.Spacing(8);
        controls.Children().Append(pauseButton_);
        controls.Children().Append(stopButton_);
        captureCard.Children().Append(controls);
        readinessText_ = TextBlock();
        styleText(readinessText_, 12);
        captureCard.Children().Append(readinessText_);
        diagnosticsButton_ = styledButton(L"Скопировать безопасную сводку");
        setAccessible(diagnosticsButton_, L"Скопировать безопасную сводку последней завершённой записи",
            L"Только технические состояния и счётчики, без аудио, текста встреч, путей и токенов");
        diagnosticsButton_.Visibility(Visibility::Collapsed);
        diagnosticsButton_.Click([this](auto const&, auto const&) {
            if (!capture_ || capture_->diagnostics().empty()) return;
            try {
                winrt::Windows::ApplicationModel::DataTransfer::DataPackage package;
                package.SetText(winrt::to_hstring(capture_->diagnostics()));
                winrt::Windows::ApplicationModel::DataTransfer::Clipboard::SetContent(package);
                winrt::Windows::ApplicationModel::DataTransfer::Clipboard::Flush();
                localActionNotice_ = L"Безопасная сводка последней завершённой записи скопирована. Аудио и текст встреч в неё не входят.";
            } catch (...) { localActionNotice_ = L"Не удалось скопировать сводку. Повторите действие."; }
            refreshNativeState();
        });
        captureCard.Children().Append(diagnosticsButton_);
        microphonePicker_ = ComboBox();
        microphonePicker_.Header(box_value(L"Микрофон записи"));
        microphonePicker_.HorizontalAlignment(HorizontalAlignment::Stretch);
        setAccessible(microphonePicker_, L"Выбрать микрофон записи", L"Источник можно изменить до начала записи");
        microphonePicker_.SelectionChanged([this](auto const&, auto const&) {
            if (updatingMicrophonePicker_ || !capture_) return;
            const auto item = microphonePicker_.SelectedItem().try_as<ComboBoxItem>();
            if (!item) return;
            const auto identity = winrt::to_string(unbox_value<hstring>(item.Tag()));
            microphoneSettingError_ = capture_->selectMicrophone(identity) ? L"" : L"Не удалось сохранить выбор микрофона";
            // The state timer refreshes the picker after SelectionChanged returns.
            // Clearing its items inside this callback invalidates WinUI selection.
            microphoneChoicesKey_.clear();
        });
        captureCard.Children().Append(microphonePicker_);
        microphoneSourceText_ = TextBlock();
        styleText(microphoneSourceText_, 12);
        captureCard.Children().Append(microphoneSourceText_);
        privacyNotice_ = TextBlock();
        privacyNotice_.Text(L"GRAF не может проверить, выключен ли микрофон во встрече. Чтобы ваша речь не попала в запись, используйте «Паузу» или «Остановить» в GRAF.");
        styleText(privacyNotice_, 12);
        captureCard.Children().Append(privacyNotice_);
        auto meters = StackPanel();
        meters.Spacing(6);
        auto metersTitle = TextBlock();
        metersTitle.Text(L"Уровни звука");
        styleText(metersTitle, 12, FontWeights::SemiBold());
        meters.Children().Append(metersTitle);
        auto microphoneMeterLabel = TextBlock();
        microphoneMeterLabel.Text(L"Микрофон");
        styleText(microphoneMeterLabel, 11);
        meters.Children().Append(microphoneMeterLabel);
        microphoneMeter_ = Grid();
        microphoneMeter_.Height(6);
        microphoneMeter_.Background(themeBrush(L"ControlFillColorSecondaryBrush"));
        microphoneMeterFill_ = Border();
        microphoneMeterFill_.HorizontalAlignment(HorizontalAlignment::Left);
        microphoneMeterFill_.Height(6);
        microphoneMeterFill_.Width(0);
        microphoneMeterFill_.Background(themeBrush(L"AccentFillColorDefaultBrush"));
        microphoneMeter_.Children().Append(microphoneMeterFill_);
        setAccessible(microphoneMeter_, L"Уровень микрофона");
        meters.Children().Append(microphoneMeter_);
        auto systemMeterLabel = TextBlock();
        systemMeterLabel.Text(L"Системный звук");
        styleText(systemMeterLabel, 11);
        meters.Children().Append(systemMeterLabel);
        systemRenderMeter_ = Grid();
        systemRenderMeter_.Height(6);
        systemRenderMeter_.Background(themeBrush(L"ControlFillColorSecondaryBrush"));
        systemRenderMeterFill_ = Border();
        systemRenderMeterFill_.HorizontalAlignment(HorizontalAlignment::Left);
        systemRenderMeterFill_.Height(6);
        systemRenderMeterFill_.Width(0);
        systemRenderMeterFill_.Background(themeBrush(L"AccentFillColorDefaultBrush"));
        systemRenderMeter_.Children().Append(systemRenderMeterFill_);
        setAccessible(systemRenderMeter_, L"Уровень системного звука");
        meters.Children().Append(systemRenderMeter_);
        meters.Visibility(Visibility::Collapsed);
        meters_ = meters;
        captureCard.Children().Append(meters_);
        permissionButton_ = styledButton(L"Разрешить микрофон");
        setAccessible(permissionButton_, L"Разрешить доступ к микрофону",
                      L"Открывает настройки конфиденциальности Windows");
        permissionButton_.Click([this](auto const&, auto const&) {
            showPermissionOnboarding();
        });
        permissionButton_.Visibility(Visibility::Collapsed);
        captureCard.Children().Append(permissionButton_);
        auto autoRecord = TextBlock();
        autoRecord.Text(L"Автозапись");
        styleText(autoRecord, 12, FontWeights::SemiBold());
        autoRecord.Margin(Thickness{0, 4, 0, 0});
        captureCard.Children().Append(autoRecord);
        autoRecordDetail_ = TextBlock();
        autoRecordDetail_.Text(L"Проверка приложений недоступна");
        styleText(autoRecordDetail_, 12);
        captureCard.Children().Append(autoRecordDetail_);
        auto automaticSettings = styledButton(L"Настроить автозапись");
        automaticSettings.Click([this](auto const&, auto const&) { openNativeSettings(); });
        captureCard.Children().Append(automaticSettings);
        body.Children().Append(card(captureCard, 12));
        auto custody = StackPanel();
        custody.Spacing(6);
        auto custodyHeader = TextBlock();
        custodyHeader.Text(L"Локальная сохранность");
        styleText(custodyHeader, 13, FontWeights::SemiBold());
        custody.Children().Append(custodyHeader);
        auto custodyBody = StackPanel();
        custodyBody.Spacing(6);
        auto custodyTitle = TextBlock();
        custodyTitle.Text(L"Запись сначала сохраняется на этом компьютере");
        styleText(custodyTitle, 13, FontWeights::SemiBold());
        auto custodyDetail = TextBlock();
        custodyDetail.Text(L"После финализации отправим её автоматически. Если сеть или вход недоступны, пакет останется в очереди.");
        styleText(custodyDetail, 12);
        custodyStatus_ = TextBlock();
        custodyStatus_.Text(L"Локальная очередь загружается…");
        styleText(custodyStatus_, 12, FontWeights::SemiBold());
        custodyBody.Children().Append(custodyTitle);
        custodyBody.Children().Append(custodyDetail);
        custodyBody.Children().Append(custodyStatus_);
        selectedRecordingPanel_ = ContentControl();
        selectedRecordingPanel_.IsTabStop(true);
        selectedRecordingPanel_.HorizontalContentAlignment(HorizontalAlignment::Stretch);
        selectedRecordingPanel_.Visibility(Visibility::Collapsed);
        custodyBody.Children().Append(selectedRecordingPanel_);
        custody.Children().Append(custodyBody);
        body.Children().Append(card(custody, 12));

        runtimeText_ = TextBlock();
        runtimeText_.Text(L"WebView2: проверяем кабинет…");
        styleText(runtimeText_, 11);
        body.Children().Append(runtimeText_);
        trayFailureText_ = TextBlock();
        styleText(trayFailureText_, 12);
        trayFailureText_.Visibility(Visibility::Collapsed);
        body.Children().Append(trayFailureText_);
        trayExitButton_ = styledButton(L"Закрыть GRAF");
        trayExitButton_.Visibility(Visibility::Collapsed);
        trayExitButton_.Click([this](auto const&, auto const&) { requestExit(); });
        setAccessible(trayExitButton_, L"Закрыть GRAF после сохранения записи");
        body.Children().Append(trayExitButton_);
        scroll.Content(body);
        expandedInspector_.Child(scroll);
        Grid::SetColumn(expandedInspector_, 1);
        content_.Children().Append(expandedInspector_);

        compactInspector_ = Border();
        compactInspector_.Background(themeBrush(L"LayerFillColorDefaultBrush"));
        auto compact = StackPanel();
        compact.HorizontalAlignment(HorizontalAlignment::Center);
        compact.Spacing(8);
        inspectorToggle_ = iconButton(Symbol::Back, L"Показать панель управления");
        inspectorToggle_.Width(40);
        inspectorToggle_.Height(40);
        setAccessible(inspectorToggle_, L"Показать панель управления", L"Раскрывает правую панель GRAF");
        inspectorToggle_.Click([this](auto const&, auto const&) { toggleInspector(); });
        compact.Children().Append(inspectorToggle_);
        compactStatus_ = SymbolIcon(Symbol::Microphone);
        setAccessible(compactStatus_, L"Статус записи");
        compact.Children().Append(compactStatus_);
        compactRecordButton_ = iconButton(Symbol::Microphone, L"Начать запись");
        compactRecordButton_.Width(40);
        compactRecordButton_.Height(40);
        setAccessible(compactRecordButton_, L"Начать запись");
        compactRecordButton_.Click([this](auto const&, auto const&) { recordCapture(); });
        compact.Children().Append(compactRecordButton_);
        compactAttentionButton_ = iconButton(Symbol::Important, L"Локальная сохранность: требуется внимание");
        compactAttentionButton_.Width(40);
        compactAttentionButton_.Height(32);
        compactAttentionButton_.Padding(Thickness{0, 0, 0, 0});
        setAccessible(compactAttentionButton_, L"Локальная сохранность: требуется внимание");
        compactAttentionButton_.Click([this](auto const&, auto const&) {
            attentionExpansionDismissed_ = false;
            inspectorExpanded_ = true;
            updateInspectorVisibility();
        });
        compactAttentionButton_.Visibility(Visibility::Collapsed);
        compact.Children().Append(compactAttentionButton_);
        compactInspector_.Child(compact);
        Grid::SetColumn(compactInspector_, 1);
        content_.Children().Append(compactInspector_);
        updateInspectorVisibility();
    }

    void configureCabinet() {
        cabinet_ = std::make_unique<graf::windows::CabinetWindow>();
        auto& host = cabinet_->webView();
        host.setSignInUrlBuilder([this](std::string_view plain) {
            if (!attribution_) return std::string(plain);
            const auto now = attributionNow();
            return graf::windows::applyingSignInQueryItems(plain, attribution_->current(now).handoff, now);
        });
        // Тема уже решена до создания среды: страница обязана увидеть ту же.
        host.setPreferredColorScheme(shellIsDark_);
        host.setNavigationHandler([this](graf::windows::RouteEvaluation evaluation) {
            if (evaluation.decision == graf::windows::RouteDecision::allow &&
                evaluation.kind == graf::windows::RouteKind::nativeSettings) {
                openNativeSettings();
                return;
            }
            if (evaluation.decision == graf::windows::RouteDecision::allow && localFallback_) {
                hideCabinetFallback();
            }
        });
        host.setRuntimeHandler([this](graf::windows::WebRuntimeState state) {
            if (state == graf::windows::WebRuntimeState::unavailable) {
                const auto detail = cabinet_->webView().failureDetail();
                showCabinetFallback(L"Не удалось открыть кабинет", L"Запись доступна отдельно. Повторите загрузку. " + std::wstring(winrt::to_hstring(detail).c_str()));
                runtimeText_.Text(L"Кабинет недоступен · локальная запись сохраняется на компьютере");
            } else if (state == graf::windows::WebRuntimeState::initializing) {
                showCabinetFallback(L"Загружаем кабинет…", L"Нативные управление записью и локальная очередь работают независимо.");
                fallbackCabinetAction_.IsEnabled(false);
                runtimeText_.Text(L"Загружаем кабинет…");
            } else if (state == graf::windows::WebRuntimeState::authRequired) {
                const auto recovery = cabinet_->webView().pendingAuthRecovery();
                if (recovery != graf::windows::WebResponseDecision::ignore) {
                    const bool reselect = recovery == graf::windows::WebResponseDecision::workspaceReselection;
                    const auto title = reselect ? L"Нужно выбрать пространство" : L"Нужно войти";
                    const auto action = reselect ? L"Войти и выбрать пространство" : L"Войти в кабинет";
                    showCabinetFallback(title, reselect
                        ? L"Доступ к выбранному пространству больше не подтвержден. Войдите снова и выберите доступное пространство. Запись на этом компьютере остается доступна."
                        : L"Войдите снова, чтобы видеть встречи. Запись на этом компьютере остается доступна.");
                    fallbackCabinetAction_.Content(winrt::box_value(action));
                    // The covered document must not retain keyboard focus/input.
                    webView_.Visibility(Visibility::Collapsed);
                    setAccessible(fallbackCabinetAction_, action, L"Открыть вход и сохранить место возврата. Локальные записи не удаляются.");
                    runtimeText_.Text(title);
                } else {
                    hideCabinetFallback();
                    runtimeText_.Text(L"Вход в кабинет");
                }
            } else if (state == graf::windows::WebRuntimeState::unprivileged) {
                hideCabinetFallback();
                runtimeText_.Text(L"Открыта веб-страница · локальная запись работает отдельно");
            } else if (state == graf::windows::WebRuntimeState::ready) {
                if (capture_) (void)capture_->recover(graf::windows::RecoveryTrigger::authRecovered);
                hideCabinetFallback();
                runtimeText_.Text(L"Кабинет GRAF открыт");
            }
        });
        host.setQuitHandler([this]() { requestExit(); });
        host.setUpdateHandler([this] { openUpdateWindow(); });
        host.setAppUpdateAvailable(appUpdate_.available());
        host.setAuthSessionHandler([this](std::string token) {
            if (capture_ && token != capture_->authSessionToken()) {
                cancelLocalPlayback();
                if (cabinet_) cabinet_->webView().bindUserTimeAccount({}, {}, {}, {}, 0);
                cancelCalendarJoin();
                if (reminderCancellation_) reminderCancellation_->store(true);
                reminderRequestIdentity_ = {};
                if (reminders_) reminders_->invalidate();
                pendingReminderAction_.reset(); reminderFlightAction_.reset(); lastReminderRequest_ = 0;
            }
            if (capture_) capture_->setAuthSessionToken(std::move(token));
        });
        host.setCalendarJoinHandlers(
            [this](auto request) { beginDocumentCalendarJoin(std::move(request)); },
            [this](auto request) {
                if (calendarFlight_ && calendarFlight_->document &&
                    calendarFlight_->document->documentGeneration == request.documentGeneration &&
                    calendarFlight_->document->nonce == request.nonce &&
                    calendarFlight_->document->intent.requestId == request.intent.requestId &&
                    calendarFlight_->document->intent.eventId == request.intent.eventId) cancelCalendarJoin();
            });
        host.setLocalRecordingHandler([this](auto request) {
            handleLocalRecording(request);
        });
        host.setDeletionSelectionHandler([this](graf::windows::WebView2Host::DeletionRequest request) {
            handleDeletionSelection(std::move(request));
        });
        host.setAppearanceHandler([this](std::string theme) { applyCabinetAppearance(theme); });
        host.setNativeSettingsHandler([this](graf::windows::WebView2Host::NativeSettingsRequest request) {
            return answerNativeSettings(request);
        });
        host.setRecreateHandler([this] {
            if (shuttingDown_) return;
            std::uint32_t index = 0;
            if (!meetingsSurface_.Children().IndexOf(webView_, index)) return;
            meetingsSurface_.Children().RemoveAt(index);
            webView_ = WebView2();
            Grid::SetRow(webView_, 1);
            meetingsSurface_.Children().InsertAt(index, webView_);
            cabinet_->attach(webView_);
        });
        // A cold protocol launch must choose login before the first WebView
        // navigation; a server 303 from meetings would otherwise omit handoff.
        if (attributionSignInRequested_) {
            attributionSignInRequested_ = false;
            (void)cabinet_->open(host.signInUrl());
        }
    }

    void updateLocalRecordings() {
        if (!cabinet_ || !capture_) return;
        bindNotificationContext();
        const auto observation = capture_->localObservation();
        const auto context = capture_->localProblemContext();
        cabinet_->webView().setProtectedLocalRecordings(observation.value, observation.complete,
            context.origin, context.owner, context.workspace, capture_->authGeneration(), observation.timings);
    }

    // The cabinet's theme setting decides the appearance of the native surfaces.
    // What follows the page is what the system draws — menus, dialogs, scrollbars,
    // control chrome — because the shell's own colours are the shipped dark design
    // tokens on both platforms. `system` is the default the app starts with, so a
    // page that has not chosen one changes nothing.
    void applyCabinetAppearance(const std::string& theme) {
        // Объявление кабинета решает всё, кроме «system»: там решает система.
        // Кисти оболочки пересобираются вместе с темой, иначе окно остаётся
        // тёмным на светлой странице или наоборот.
        // Оформление окна — то, что человек видит, поэтому решение записывается
        // в журнал: без него расхождение окна и страницы неотличимо от ошибки.
        const auto note = [&](const char* step, bool dark) {
            try {
                const auto folder = winrt::Windows::Storage::ApplicationData::Current().LocalFolder().Path();
                std::ofstream log(std::filesystem::path(folder.c_str()) / L"appearance.log", std::ios::app);
                log << GetTickCount64() << ' ' << step << " announced=" << theme
                    << " dark=" << (dark ? 1 : 0) << '\n';
            } catch (...) {}
        };
        // Что получилось на самом деле: цвет фона окна после применения набора.
        const auto applied = [this] {
            try {
                const auto brush = Application::Current().Resources()
                    .Lookup(box_value(L"GrafBackgroundBrush")).as<SolidColorBrush>();
                const auto value = brush.Color();
                char text[16]{};
                std::snprintf(text, sizeof(text), "#%02X%02X%02X", value.R, value.G, value.B);
                return std::string(text);
            } catch (...) { return std::string("unknown"); }
        };
        note(("received " + applied()).c_str(), shellIsDark_);
        // "system" can resolve differently even when the stored choice has not
        // changed. Compare the resolved palette, not just the preference token.
        announcedAppearance_ = theme;
        const bool isDark = graf::windows::resolveShellIsDark(theme, systemThemeIsDark());
        if (isDark == shellIsDark_ && root_) { note(("same-theme " + applied()).c_str(), isDark); return; }
        note(("resolved " + applied()).c_str(), isDark);
        shellIsDark_ = isDark;
        refreshShellPalette(isDark);
        if (capture_) capture_->notificationCard().setDarkTheme(isDark);
        // Страница узнаёт системную тему из `prefers-color-scheme`: без этого
        // кабинет с оформлением «системная» рисуется тёмным на светлом окне.
        if (cabinet_) cabinet_->webView().setPreferredColorScheme(isDark);
        const auto requested = isDark ? ElementTheme::Dark : ElementTheme::Light;
        // Заголовки окон рисует система: без явных цветов они остаются светлыми.
        applyWindowChrome(mainWindowHandle_, isDark);
        if (settingsWindow_) applyWindowChrome(nativeWindowHandle(settingsWindow_), isDark);
        if (playbackWindow_) {
            playbackPanel_.RequestedTheme(requested);
            applyWindowChrome(nativeWindowHandle(playbackWindow_), isDark);
        }
        if (indicatorWindow_) applyWindowChrome(nativeWindowHandle(indicatorWindow_), isDark);
        if (root_) root_.RequestedTheme(requested);
        // Собственные окна приложения следуют той же теме, что и главное.
        if (settingsContent_) settingsContent_.RequestedTheme(requested);
        if (indicatorPanel_) indicatorPanel_.RequestedTheme(requested);
    }

    bool playbackDocumentCurrent(const graf::windows::WebView2Host::LocalRecordingRequest& request,
                                 std::uint64_t epoch) const {
        return capture_ && cabinet_ && !shuttingDown_ && !exitRequested_ && !capture_->updateAdmissionBlocked() &&
            capture_->authGeneration() == epoch &&
            cabinet_->webView().localPlaybackDocumentCurrent(request.documentGeneration, request.nonce);
    }

    void dismissPlaybackWindow() {
        auto closing = playbackWindow_; playbackWindow_ = nullptr;
        ++playbackWindowGeneration_; // Invalidate callbacks BEFORE Close can reenter the UI owner.
        playbackPanel_ = nullptr; playbackStatus_ = nullptr; playbackButton_ = nullptr;
        playbackTime_ = nullptr; playbackSeek_ = nullptr;
        if (closing) closing.Close();
    }

    void cancelLocalPlayback() {
        pendingPlayback_.reset(); playbackRequest_.reset(); playbackAuthorized_ = false;
        if (capture_) capture_->closeLocalPlayback(); // Cancellation never proves worker/native drain.
        dismissPlaybackWindow();
    }

    void showLocalPlayback() {
        if (playbackWindow_) { playbackWindow_.Activate(); return; }
        playbackWindow_ = Window();
        playbackWindow_.Title(L"Локальная запись");
        const auto generation = ++playbackWindowGeneration_;
        playbackPanel_ = StackPanel();
        playbackPanel_.Padding(Thickness{16, 8, 16, 8}); playbackPanel_.Spacing(4);
        playbackPanel_.Background(themeBrush(L"GrafBackgroundBrush"));
        playbackPanel_.RequestedTheme(shellIsDark_ ? ElementTheme::Dark : ElementTheme::Light);
        playbackStatus_ = TextBlock(); styleText(playbackStatus_, 12);
        playbackStatus_.TextWrapping(TextWrapping::Wrap);
        winrt::Microsoft::UI::Xaml::Automation::AutomationProperties::SetLiveSetting(playbackStatus_,
            winrt::Microsoft::UI::Xaml::Automation::Peers::AutomationLiveSetting::Polite);
        playbackStatus_.Text(L"Проверяем локальную запись…");
        playbackPanel_.Children().Append(playbackStatus_);
        auto transport = StackPanel(); transport.Orientation(Orientation::Horizontal); transport.Spacing(12);
        playbackButton_ = styledButton(L"Воспроизвести"); playbackButton_.IsEnabled(false);
        setAccessible(playbackButton_, L"Воспроизвести локальную запись");
        playbackButton_.Click([this, generation](auto const&, auto const&) {
            if (generation != playbackWindowGeneration_ || !playbackRequest_ || pendingPlayback_) return;
            if (!playbackDocumentCurrent(playbackRequest_->request, playbackRequest_->epoch)) { cancelLocalPlayback(); return; }
            const auto state = capture_->localPlaybackObservation();
            if (!state.present || state.documentGeneration != playbackRequest_->request.documentGeneration) return;
            if (state.terminal && FAILED(state.media.error)) {
                pendingPlayback_ = *playbackRequest_;
                pollLocalPlayback();
                return;
            }
            if (state.terminal || !state.media.ready || FAILED(state.media.error)) return;
            if (state.media.ended) (void)capture_->seekLocalPlayback(0);
            (void)capture_->pauseLocalPlayback(state.media.ended ? false : !state.media.paused);
        });
        transport.Children().Append(playbackButton_);
        playbackTime_ = TextBlock(); styleText(playbackTime_, 12);
        playbackTime_.VerticalAlignment(VerticalAlignment::Center);
        transport.Children().Append(playbackTime_); playbackPanel_.Children().Append(transport);
        playbackSeek_ = Slider(); playbackSeek_.Minimum(0); playbackSeek_.Maximum(1); playbackSeek_.IsEnabled(false);
        setAccessible(playbackSeek_, L"Позиция воспроизведения", L"Используйте клавиши со стрелками для перемотки.");
        playbackSeek_.ValueChanged([this, generation](auto const&, auto const& args) {
            if (generation != playbackWindowGeneration_ || updatingPlaybackSeek_ || !playbackRequest_ || pendingPlayback_) return;
            if (!playbackDocumentCurrent(playbackRequest_->request, playbackRequest_->epoch)) { cancelLocalPlayback(); return; }
            (void)capture_->seekLocalPlayback(args.NewValue());
        });
        playbackPanel_.Children().Append(playbackSeek_);
        playbackPanel_.KeyDown([this, generation](auto const&, auto const& args) {
            if (generation != playbackWindowGeneration_ || args.Key() != winrt::Windows::System::VirtualKey::Escape) return;
            args.Handled(true);
            cancelLocalPlayback();
        });
        auto scroll = ScrollViewer();
        scroll.VerticalScrollBarVisibility(ScrollBarVisibility::Auto);
        scroll.HorizontalScrollBarVisibility(ScrollBarVisibility::Disabled);
        scroll.BringIntoViewOnFocusChange(true);
        scroll.Content(playbackPanel_);
        playbackWindow_.Content(scroll);
        auto presenter = playbackWindow_.AppWindow().Presenter().try_as<winrt::Microsoft::UI::Windowing::OverlappedPresenter>();
        if (presenter) { presenter.IsResizable(false); presenter.IsMaximizable(false); presenter.IsMinimizable(false); }
        playbackWindow_.Closed([this, generation](auto const&, auto const&) {
            if (generation != playbackWindowGeneration_) return;
            playbackWindow_ = nullptr; // Already closed; do not call Close again from its own callback.
            cancelLocalPlayback(); // Native work stays owned until its actual terminal observation.
        });
        playbackWindow_.Activate();
        applyWindowChrome(nativeWindowHandle(playbackWindow_), shellIsDark_);
        // Mac's 540x120 is CONTENT, not outer chrome. Account for Windows' DPI-scaled frame.
        const auto handle = nativeWindowHandle(playbackWindow_);
        const auto dpi = GetDpiForWindow(handle);
        if (!handle || !dpi) throw winrt::hresult_error(E_FAIL);
        RECT frame{0, 0, MulDiv(540, static_cast<int>(dpi), 96), MulDiv(120, static_cast<int>(dpi), 96)};
        if (!AdjustWindowRectExForDpi(&frame, static_cast<DWORD>(GetWindowLongPtrW(handle, GWL_STYLE)), FALSE,
            static_cast<DWORD>(GetWindowLongPtrW(handle, GWL_EXSTYLE)), dpi)) throw winrt::hresult_error(HRESULT_FROM_WIN32(GetLastError()));
        resizeWindowLogical(playbackWindow_, MulDiv(frame.right - frame.left, 96, static_cast<int>(dpi)),
            MulDiv(frame.bottom - frame.top, 96, static_cast<int>(dpi)), true);
    }

    void pollLocalPlayback() {
        if (!capture_) return;
        if (pendingPlayback_ && !playbackDocumentCurrent(pendingPlayback_->request, pendingPlayback_->epoch)) {
            cancelLocalPlayback(); return;
        }
        if (!pendingPlayback_ && playbackRequest_ && !playbackDocumentCurrent(playbackRequest_->request, playbackRequest_->epoch)) {
            cancelLocalPlayback(); return;
        }
        auto state = capture_->localPlaybackObservation();
        if (pendingPlayback_ && (!state.present || state.terminal)) {
            dismissPlaybackWindow(); // Each new operation gets a fresh native-window callback generation.
            auto next = std::move(*pendingPlayback_); pendingPlayback_.reset();
            playbackRequest_.reset(); playbackAuthorized_ = false;
            if (!capture_->openLocalPlayback(next.request.id, next.request.documentGeneration)) {
                localActionNotice_ = L"Запись сейчас недоступна или занята отправкой. Повторите открытие позже.";
                cancelLocalPlayback(); return; // No endless retry of a rejected request.
            }
            playbackRequest_ = std::move(next);
            try { showLocalPlayback(); } catch (...) { cancelLocalPlayback(); return; }
            state = capture_->localPlaybackObservation();
        }
        if (!playbackRequest_) return;
        if (!state.present || state.documentGeneration != playbackRequest_->request.documentGeneration) {
            cancelLocalPlayback(); return;
        }
        if (!pendingPlayback_ && !state.terminal && SUCCEEDED(state.media.error) && state.media.ready && !playbackAuthorized_) {
            playbackAuthorized_ = capture_->authorizeLocalPlayback(state.documentGeneration);
            if (!playbackAuthorized_) { cancelLocalPlayback(); return; }
        }
        if (!playbackWindow_) return;
        const bool usable = !pendingPlayback_ && !state.preparing && !state.terminal && SUCCEEDED(state.media.error) && state.media.ready;
        const bool retry = !pendingPlayback_ && state.terminal && FAILED(state.media.error);
        playbackStatus_.Text(pendingPlayback_ ? L"Закрываем предыдущую запись…" : FAILED(state.media.error) ?
            (retry ? L"Запись недоступна или занята. Нажмите «Повторить», чтобы попробовать снова." :
                L"Запись недоступна или занята. Завершаем воспроизведение…") : state.terminal ?
            L"Воспроизведение завершено." : state.preparing || !state.media.ready ? L"Проверяем локальную запись…" :
            state.media.ended ? L"Запись закончилась" : state.media.paused ? L"Пауза" : L"Воспроизведение");
        setAccessible(playbackStatus_, std::wstring(playbackStatus_.Text().c_str()));
        playbackButton_.IsEnabled(usable || retry);
        const bool play = state.media.paused || state.media.ended;
        playbackButton_.Content(box_value(retry ? L"Повторить" : play ? L"Воспроизвести" : L"Пауза"));
        setAccessible(playbackButton_, retry ? L"Повторить открытие локальной записи" :
            play ? L"Воспроизвести локальную запись" : L"Приостановить воспроизведение");
        playbackSeek_.IsEnabled(usable);
        const auto time = [](double seconds) {
            const auto whole = static_cast<std::uint64_t>(std::max(0.0, seconds));
            const auto minutes = whole / 60, remainder = whole % 60;
            return std::to_wstring(minutes) + L":" + (remainder < 10 ? L"0" : L"") + std::to_wstring(remainder);
        };
        playbackTime_.Text(time(state.media.positionSeconds) + L" / " + time(state.media.durationSeconds));
        updatingPlaybackSeek_ = true;
        playbackSeek_.Maximum(std::max(1.0, state.media.durationSeconds));
        playbackSeek_.Value(state.media.positionSeconds);
        updatingPlaybackSeek_ = false;
    }

    void handleLocalRecording(const graf::windows::WebView2Host::LocalRecordingRequest& request) {
        const auto& action = request.action;
        const auto& id = request.id;
        if (!capture_ || shuttingDown_ || exitRequested_) return;
        if (action == "open") {
            const auto epoch = capture_->authGeneration();
            if (!playbackDocumentCurrent(request, epoch) || !cabinet_->webView().localRecordingActionAllowed(action, id)) return;
            pendingPlayback_ = PlaybackRequest{request, epoch}; // One bounded latest replacement, no native references.
            capture_->closeLocalPlayback();
            pollLocalPlayback();
            return;
        }
        if (action == "send") {
            const auto epoch = capture_->authGeneration();
            if (!playbackDocumentCurrent(request, epoch) || pendingManualSend_ ||
                !cabinet_->webView().localRecordingActionAllowed(action, id)) return;
            if (capture_->authSessionToken().empty()) {
                (void)cabinet_->open(cabinet_->webView().signInUrl());
                localActionNotice_ = L"Войдите в GRAF — запись остаётся на этом компьютере.";
            } else if (!capture_->currentAccount()) {
                localActionNotice_ = L"Сервер пока не подтвердил текущий аккаунт. Отправка приостановлена, запись сохранена локально.";
            } else {
                const auto observation = capture_->localObservation();
                if (!observation.complete || !observation.value) {
                    localActionNotice_ = capture_->custodySummary(); return;
                }
                PendingLocalAction pending{request, epoch, 0}; // Allocate reply address before native admission.
                const auto ticket = capture_->requestProtectedManualSend(observation.value, id, epoch, false);
                if (ticket) {
                    pending.ticket = ticket->id;
                    pendingManualSend_ = std::move(pending);
                    localActionNotice_ = L"Сохраняем запрос отправки… Запись остаётся на этом компьютере.";
                } else localActionNotice_ = L"Аккаунт или состояние записи изменились либо отправка приостановлена. Дождитесь завершения текущего действия и повторите отправку.";
            }
            return;
        }
        if (action == "delete") {
            const auto epoch = capture_->authGeneration();
            if (!playbackDocumentCurrent(request, epoch) || pendingLocalRemoval_ ||
                !cabinet_->webView().localRecordingActionAllowed(action, id)) return;
            const auto observation = capture_->localObservation();
            if (!observation.complete || !observation.value) { localActionNotice_ = capture_->custodySummary(); return; }
            if (capture_->uploadsBusy() || capture_->indicator().visible) {
                localActionNotice_ = L"Дождитесь завершения записи или отправки, затем удалите локальную копию.";
                return;
            }
            confirmLocalAction(L"Удалить локальную копию?",
                L"Локальная копия выбранной записи будет перемещена в Корзину Windows. Уже отправленная запись на сервере не изменится.",
                L"Переместить в Корзину", [this, request, epoch, snapshot = observation.value] {
                    if (!playbackDocumentCurrent(request, epoch) || pendingLocalRemoval_ ||
                        !cabinet_->webView().localRecordingActionAllowed("delete", request.id)) return;
                    PendingLocalAction pending{request, epoch, 0}; // No owning copy after accepted intent.
                    const auto ticket = capture_->requestProtectedLocalRemoval(snapshot, request.id, epoch);
                    if (ticket) {
                        pending.ticket = ticket->id;
                        pendingLocalRemoval_ = std::move(pending);
                        localActionNotice_ = L"Удаляем локальную копию… Запись на сервере не изменяется.";
                    } else localActionNotice_ = L"Состояние записи изменилось. Обновите список и подтвердите удаление ещё раз.";
                });
        }
    }

    void pollLocalRecordingSend() {
        if (!pendingManualSend_) return;
        const auto request = std::get_if<graf::windows::WebView2Host::LocalRecordingRequest>(&pendingManualSend_->source);
        if (!request || !playbackDocumentCurrent(*request, pendingManualSend_->epoch)) {
            if (localActionNotice_ == L"Сохраняем запрос отправки… Запись остаётся на этом компьютере.")
                localActionNotice_.clear(); // Preserve a newer notice from another action; storage truth is still pending.
            pendingManualSend_.reset(); return; // Storage still adopts truth; stale UI has no capability.
        }
        const auto ticket = capture_->protectedManualSendTicket(pendingManualSend_->ticket);
        if (!ticket || ticket->state == NativeCapture::QueueTicketState::pending) return;
        localActionNotice_ = ticket->state == NativeCapture::QueueTicketState::committed && ticket->error == graf::windows::CustodyFileError::none
            ? L"Запрос отправки сохранён. GRAF отправит запись с учётом ответа сервера."
            : L"Не удалось подтвердить сохранение запроса отправки. Запись остаётся на компьютере; проверьте состояние хранилища.";
        pendingManualSend_.reset();
    }

    void pollLocalRecordingRemoval() {
        if (!capture_ || !pendingLocalRemoval_) return;
        const auto web = std::get_if<graf::windows::WebView2Host::LocalRecordingRequest>(&pendingLocalRemoval_->source);
        const auto native = std::get_if<ProblemTarget>(&pendingLocalRemoval_->source);
        const bool current = web ? playbackDocumentCurrent(*web, pendingLocalRemoval_->epoch)
            : native && native->authGeneration == pendingLocalRemoval_->epoch &&
                nativeLocalRemovalContextCurrent(*native, pendingLocalRemoval_->selectionRevision);
        if (!current && localActionNotice_ == L"Удаляем локальную копию… Запись на сервере не изменяется.")
            localActionNotice_.clear();
        // Always consume the native completion, even for a stale document. The
        // adopted intent belongs to the native owner, not the page's lifetime.
        const auto result = capture_->takeProtectedDeletionCompletion(pendingLocalRemoval_->ticket);
        if (!result) return;
        pendingLocalRemoval_.reset(); // Consumed scalar result cannot be polled again if notice allocation fails.
        if (current) localActionNotice_ = result->unknown
            ? L"Результат удаления пока неизвестен. Проверьте состояние хранилища после перезапуска GRAF."
            : !result->saved
            ? L"Не удалось сохранить запрос удаления. Локальная копия не удалена. Обновите список и подтвердите удаление ещё раз."
            : result->accepted == 1 && result->pending == 0
            ? L"Локальная копия больше не хранится в GRAF. Если файл был на диске, он перемещён в Корзину Windows. Запись на сервере не изменена."
            : L"Удаление локальной копии ещё не завершено. Намерение сохранено; GRAF повторит удаление после восстановления доступа. Проверьте очередь и Корзину.";
    }

    // The shell retains only the charged reply address. NativeCapture owns the
    // intent -> HTTP -> answer -> storage ACK chain, independently of this page.
    void handleDeletionSelection(graf::windows::WebView2Host::DeletionRequest request) {
        if (!cabinet_ || !capture_ || shuttingDown_) return;
        if (exitRequested_ || deletionSelectionsInFlight_ || capture_->updateAdmissionBlocked()) {
            cabinet_->webView().completeDeletionSelection(request, {});
            return;
        }
        try {
            graf::windows::CustodyString requestId{std::string_view(request.selection.requestId)};
            graf::windows::ProtectedDeletionTargets targets;
            targets.reserve(request.targets.size());
            for (const auto& target : request.targets) targets.push_back({target.target,
                graf::windows::CustodyString(std::string_view(target.targetId))});
            const auto ticket = capture_->beginProtectedDeletionSelection(std::move(targets));
            if (ticket) {
                deletionRequestId_ = std::move(requestId);
                deletionDocumentGeneration_ = request.documentGeneration;
                deletionJobId_ = ticket->id;
                ++deletionSelectionsInFlight_;
                return;
            }
        } catch (...) {
            // Pre-admission allocation refusal is not a saved deletion.
        }
        cabinet_->webView().completeDeletionSelection(request, {});
    }

    // Network, durable intent, native purge and ACK share the owned continuation.
    void startLocalPurgePass() {
        if (capture_ && !shuttingDown_ && !exitRequested_) (void)capture_->beginProtectedLocalPurgePass();
    }
    void pollDeletionSelection() {
        if (!capture_ || !deletionJobId_ || deletionReplyCalling_) return;
        if (!deletionReply_) deletionReply_ = capture_->takeProtectedDeletionCompletion(deletionJobId_);
        if (!deletionReply_) return;
        const CustodyMutationScope calling(deletionReplyCalling_);
        const auto& result = *deletionReply_;
        const bool deliver = cabinet_ && !shuttingDown_ && !exitRequested_ && !capture_->updateAdmissionBlocked() &&
            result.epoch == capture_->authGeneration() && capture_->currentAccount();
        if (deliver) try {
            graf::windows::CabinetDeletionOutcome reply;
            reply.saved = result.saved; reply.unknown = result.unknown;
            reply.accepted = result.accepted; reply.pending = result.pending; reply.rejected = result.rejected;
            if (!cabinet_->webView().completeDeletionSelection(deletionDocumentGeneration_, deletionRequestId_, reply)) return;
        } catch (...) { return; } // Retry only delivery, never HTTP/storage; retain address and result.
        deletionJobId_ = deletionDocumentGeneration_ = 0;
        deletionRequestId_.clear(); deletionReply_.reset();
        deletionSelectionsInFlight_ = 0;
    }

    void confirmLocalAction(hstring title, hstring body, hstring button, std::function<void()> confirmed) {
        if (exitRequested_ || !capture_ || localActionDialogOpen_) return;
        ContentDialog dialog;
        dialog.XamlRoot(root_.XamlRoot());
        dialog.Title(box_value(title));
        dialog.Content(box_value(body));
        dialog.PrimaryButtonText(button);
        dialog.CloseButtonText(L"Отмена");
        dialog.DefaultButton(ContentDialogButton::Close);
        const auto dispatcher = root_.DispatcherQueue();
        const auto alive = alive_;
        localActionDialogOpen_ = true;
        try {
            dialog.ShowAsync().Completed([this, alive, dispatcher, confirmed = std::move(confirmed)](auto const& operation, auto const&) {
                dispatcher.TryEnqueue([this, alive, operation, confirmed] {
                    if (!alive->load()) return;
                    localActionDialogOpen_ = false;
                    try {
                        if (operation.GetResults() == ContentDialogResult::Primary) {
                            if (exitRequested_ || !capture_)
                                localActionNotice_ = L"Действие не выполнено: GRAF закрывается.";
                            else if (capture_->updateAdmissionBlocked())
                                localActionNotice_ = L"Действие не выполнено: готовится обновление GRAF. Повторите после завершения или отмены обновления.";
                            else confirmed();
                        }
                        updateLocalRecordings();
                    } catch (...) { localActionNotice_ = L"Не удалось завершить действие с локальной записью."; }
                });
            });
        } catch (...) { localActionDialogOpen_ = false; localActionNotice_ = L"Закройте другое диалоговое окно и повторите действие."; }
    }

    void showCabinetFallback(std::wstring title, std::wstring detail) {
        fallbackCabinetTitle_.Text(std::move(title));
        fallbackCabinetDetail_.Text(std::move(detail));
        fallbackCabinetAction_.Content(winrt::box_value(L"Повторить загрузку"));
        fallbackCabinetAction_.IsEnabled(true);
        setAccessible(fallbackCabinetAction_, L"Повторить загрузку кабинета", L"Запись и локальная очередь не сбрасываются");
        localFallback_.Visibility(Visibility::Visible);
    }

    void hideCabinetFallback() {
        webView_.Visibility(Visibility::Visible);
        localFallback_.Visibility(Visibility::Collapsed);
    }

    void openNativeSettings() {
        if (settingsWindow_) {
            settingsWindow_.Activate();
            return;
        }
        settingsWindow_ = Window();
        settingsWindow_.AppWindow().Title(L"Настройки GRAF");
            applyWindowIcon(settingsWindow_);
        // Размер ставится после активации: тогда масштаб окна уже известен.

        auto settingsLayout = Grid();
        settingsContent_ = settingsLayout;
        settingsLayout.RequestedTheme(shellIsDark_ ? ElementTheme::Dark : ElementTheme::Light);
        settingsLayout.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
        auto sidebarColumn = ColumnDefinition();
        sidebarColumn.Width(GridLengthHelper::FromValueAndType(176.0, GridUnitType::Pixel));
        settingsLayout.ColumnDefinitions().Append(sidebarColumn);
        settingsLayout.ColumnDefinitions().Append(ColumnDefinition());
        auto sidebar = Border();
        sidebar.Background(themeBrush(L"LayerFillColorDefaultBrush"));
        auto sidebarBody = StackPanel();
        sidebarBody.Spacing(18);
        auto back = iconButton(Symbol::Back, L"Назад");
        back.HorizontalAlignment(HorizontalAlignment::Left);
        back.Click([this](auto const&, auto const&) { if (settingsWindow_) settingsWindow_.Close(); });
        setAccessible(back, L"Назад");
        sidebarBody.Children().Append(back);
        auto sidebarTitle = TextBlock();
        sidebarTitle.Text(L"Встречи");
        styleText(sidebarTitle, 12, FontWeights::SemiBold());
        sidebarBody.Children().Append(sidebarTitle);
        auto sidebarPage = TextBlock();
        sidebarPage.Text(L"Автозапись");
        styleText(sidebarPage, 13, FontWeights::SemiBold());
        auto sidebarPageSurface = Border();
        sidebarPageSurface.Padding(Thickness{10, 8, 10, 8});
        sidebarPageSurface.Background(themeBrush(L"CardBackgroundFillColorDefaultBrush"));
        sidebarPageSurface.Child(sidebarPage);
        setAccessible(sidebarPageSurface, L"Автозапись");
        sidebarBody.Children().Append(sidebarPageSurface);
        sidebar.Child(sidebarBody);
        settingsLayout.Children().Append(sidebar);
        auto scroll = ScrollViewer();
        auto body = StackPanel();
        body.Margin(Thickness{28, 24, 28, 24});
        body.Spacing(16);
        auto title = TextBlock();
        title.Text(L"Автозапись");
        styleText(title, 26, FontWeights::SemiBold());
        body.Children().Append(title);
        auto applications = TextBlock();
        applications.Text(L"Приложения");
        styleText(applications, 16, FontWeights::SemiBold());
        body.Children().Append(applications);
        automaticPreferencePickers_.clear();
        bulkAutomaticPreference_ = automaticPreferencePicker(L"Для всех приложений", std::nullopt);
        body.Children().Append(bulkAutomaticPreference_);
        const auto settings = automaticPolicy_.settings();
        for (const auto& application : settings.applications) {
            auto picker = automaticPreferencePicker(deviceDisplayName(application.target.displayName), application.target);
            automaticPreferencePickers_.emplace_back(application.target, picker);
            body.Children().Append(picker);
        }
        if (settings.applications.empty()) {
            auto empty = TextBlock();
            empty.Text(L"Список появится после загрузки проверенного реестра приложений. Сейчас автозапись недоступна; ручная запись остаётся доступной.");
            styleText(empty, 13);
            body.Children().Append(empty);
        }
        auto rules = TextBlock();
        rules.Text(L"«Спрашивать»: запись начнётся через 8 секунд. «Записать сейчас» и «Не записывать» действуют на текущую встречу. «Запомнить выбор» сохраняет «Всегда» или «Никогда» только после нажатия.");
        styleText(rules, 12);
        body.Children().Append(rules);
        automaticSettingsError_ = TextBlock();
        styleText(automaticSettingsError_, 12);
        body.Children().Append(automaticSettingsError_);
        refreshAutomaticSettings();
        auto notificationTitle = TextBlock();
        notificationTitle.Text(L"Уведомления на этом компьютере");
        styleText(notificationTitle, 16, FontWeights::SemiBold());
        body.Children().Append(notificationTitle);
        auto notificationDetail = TextBlock();
        notificationDetail.Text(L"GRAF показывает карточки, пока приложение запущено. Тихий режим скрывает необязательные уведомления, но не предложение автозаписи и не управление записью.");
        styleText(notificationDetail, 13);
        body.Children().Append(notificationDetail);
        localNotificationToggles_.clear();
        for (const auto& [field, label] : std::vector<std::pair<std::string, std::wstring>>{
                 {"reminders", L"Напоминать о встречах"}, {"showTitles", L"Показывать названия встреч"},
                 {"sound", L"Звук уведомлений"}, {"quiet", L"Тихий режим"}}) {
            CheckBox toggle;
            toggle.Content(box_value(label));
            setAccessible(toggle, label);
            const auto changed = [this, field](auto const& sender, auto const&) {
                if (updatingLocalNotifications_) return;
                const auto value = sender.template as<CheckBox>().IsChecked();
                graf::windows::NativeSettingsBridge::NotificationRequest request;
                request.action = graf::windows::NativeSettingsBridge::NotificationAction::set;
                request.field = field;
                request.booleanValue = value && value.Value();
                applyLocalNotificationSetting(request);
            };
            toggle.Checked(changed);
            toggle.Unchecked(changed);
            localNotificationToggles_.emplace_back(field, toggle);
            body.Children().Append(toggle);
        }
        localNotificationOffset_ = ComboBox();
        localNotificationOffset_.Header(box_value(L"Напомнить до начала встречи"));
        localNotificationOffset_.HorizontalAlignment(HorizontalAlignment::Stretch);
        setAccessible(localNotificationOffset_, L"Напомнить до начала встречи");
        for (const auto label : {L"В момент начала", L"За 1 минуту", L"За 5 минут"})
            localNotificationOffset_.Items().Append(box_value(label));
        localNotificationOffset_.SelectionChanged([this](auto const&, auto const&) {
            if (updatingLocalNotifications_) return;
            const auto index = localNotificationOffset_.SelectedIndex();
            if (index < 0 || index > 2) return;
            graf::windows::NativeSettingsBridge::NotificationRequest request;
            request.action = graf::windows::NativeSettingsBridge::NotificationAction::set;
            request.field = "offsetMinutes";
            request.offsetMinutes = index == 0 ? 0 : index == 1 ? 1 : 5;
            applyLocalNotificationSetting(request);
        });
        body.Children().Append(localNotificationOffset_);
        localNotificationTest_ = styledButton(L"Проверить уведомление");
        setAccessible(localNotificationTest_, L"Проверить уведомление");
        localNotificationTest_.Click([this](auto const&, auto const&) {
            graf::windows::NativeSettingsBridge::NotificationRequest request;
            request.action = graf::windows::NativeSettingsBridge::NotificationAction::test;
            applyLocalNotificationSetting(request);
        });
        body.Children().Append(localNotificationTest_);
        localNotificationStatus_ = TextBlock();
        styleText(localNotificationStatus_, 13);
        winrt::Microsoft::UI::Xaml::Automation::AutomationProperties::SetLiveSetting(localNotificationStatus_,
            winrt::Microsoft::UI::Xaml::Automation::Peers::AutomationLiveSetting::Polite);
        body.Children().Append(localNotificationStatus_);
        refreshLocalNotificationSettings();
        auto captureTitle = TextBlock();
        captureTitle.Text(L"Запись и разрешения");
        styleText(captureTitle, 16, FontWeights::SemiBold());
        body.Children().Append(captureTitle);
        auto permissionTitle = TextBlock();
        permissionTitle.Text(L"Разрешения Windows");
        styleText(permissionTitle, 16, FontWeights::SemiBold());
        body.Children().Append(permissionTitle);
        auto microphone = styledButton(L"Открыть настройки микрофона");
        microphone.Click([](auto const&, auto const&) {
            ShellExecuteW(nullptr, L"open", L"ms-settings:privacy-microphone", nullptr, nullptr, SW_SHOWNORMAL);
        });
        setAccessible(microphone, L"Открыть настройки микрофона");
        body.Children().Append(microphone);
        auto sound = styledButton(L"Открыть настройки звука");
        sound.Click([](auto const&, auto const&) {
            ShellExecuteW(nullptr, L"open", L"ms-settings:sound", nullptr, nullptr, SW_SHOWNORMAL);
        });
        setAccessible(sound, L"Открыть настройки звука");
        body.Children().Append(sound);
        auto account = styledButton(L"Настройки аккаунта в кабинете");
        account.Click([this](auto const&, auto const&) {
            if (cabinet_) (void)cabinet_->open("https://rec.2brain.pro/desktop/account/profile");
            if (settingsWindow_) settingsWindow_.Close();
            window_.Activate();
        });
        setAccessible(account, L"Открыть настройки аккаунта");
        body.Children().Append(account);
        auto note = TextBlock();
        note.Text(L"GRAF записывает общий микс выбранного устройства вывода и отдельный физический микрофон. Запись сначала сохраняется локально и отправляется после входа.");
        styleText(note, 12);
        body.Children().Append(card(note, 12));
        scroll.Content(body);
        Grid::SetColumn(scroll, 1);
        settingsLayout.Children().Append(scroll);
        settingsWindow_.Content(settingsLayout);
        // Окно открывается заново каждый раз: тему и заголовок берём из текущего
        // оформления, а не из того, что было при первом запуске.
        settingsLayout.RequestedTheme(shellIsDark_ ? ElementTheme::Dark : ElementTheme::Light);
        applyWindowChrome(nativeWindowHandle(settingsWindow_), shellIsDark_);
        settingsWindow_.Closed([this](auto const&, auto const&) {
            settingsWindow_ = nullptr;
            bulkAutomaticPreference_ = nullptr;
            automaticPreferencePickers_.clear();
            automaticSettingsError_ = nullptr;
            localNotificationToggles_.clear();
            localNotificationOffset_ = nullptr;
            localNotificationTest_ = nullptr;
            localNotificationStatus_ = nullptr;
        });
        settingsWindow_.Activate();
        resizeWindowLogical(settingsWindow_, 760, 500, true);
    }

    void bindNotificationContext() {
        if (!reminders_ || !capture_) return;
        const auto account = capture_->currentAccount();
        if (cabinet_) {
            auto& host = cabinet_->webView();
            if (account && !shuttingDown_ && !exitRequested_) host.bindUserTimeAccount(
                graf::windows::DesktopHttpConfig{}.baseOrigin, account->userId, account->workspaceId,
                capture_->authSessionToken(), capture_->authGeneration());
            else host.bindUserTimeAccount({}, {}, {}, {}, capture_->authGeneration());
        }
        if (account) reminders_->bind(account->userId, account->workspaceId,
            graf::windows::DesktopHttpConfig{}.baseOrigin);
        else if (!reminders_->owner().empty()) reminders_->invalidate();
        if (problemContextEpoch_ != reminders_->epoch() || problemAuthGeneration_ != capture_->authGeneration()) {
            pendingProblems_.clear();
            presentedProblem_.reset();
            selectedRecording_.reset();
            problemContextEpoch_ = reminders_->epoch();
            problemAuthGeneration_ = capture_->authGeneration();
            refreshSelectedRecording();
        }
    }

    void setLocalNotificationStatus(winrt::hstring const& text) {
        if (!localNotificationStatus_ || localNotificationStatus_.Text() == text) return;
        localNotificationStatus_.Text(text);
        try {
            using namespace winrt::Microsoft::UI::Xaml::Automation::Peers;
            if (const auto peer = FrameworkElementAutomationPeer::FromElement(localNotificationStatus_))
                peer.RaiseAutomationEvent(AutomationEvents::LiveRegionChanged);
        } catch (...) {} // Assistive client failure never alters the saved preference.
    }

    void refreshLocalNotificationSettings() {
        if (!localNotificationOffset_) return;
        bindNotificationContext();
        const bool editable = reminders_ && !reminders_->owner().empty();
        const auto preferences = reminders_ ? reminders_->preferences() : graf::windows::NotificationPreferences{};
        updatingLocalNotifications_ = true;
        for (const auto& [field, toggle] : localNotificationToggles_) {
            const auto value = field == "reminders" ? preferences.reminders : field == "showTitles" ? preferences.showTitles :
                field == "sound" ? preferences.sound : preferences.quiet;
            toggle.IsChecked(value);
            toggle.IsEnabled(editable);
        }
        localNotificationOffset_.SelectedIndex(preferences.offsetMinutes == 0 ? 0 : preferences.offsetMinutes == 1 ? 1 : 2);
        localNotificationOffset_.IsEnabled(editable && preferences.reminders);
        localNotificationTest_.IsEnabled(editable);
        updatingLocalNotifications_ = false;
        if (!editable) setLocalNotificationStatus(L"Войдите в GRAF, чтобы изменить настройки уведомлений.");
        else if (localNotificationEpoch_ != reminders_->epoch()) setLocalNotificationStatus(L"");
        localNotificationEpoch_ = reminders_ ? reminders_->epoch() : 0;
    }

    void applyLocalNotificationSetting(const graf::windows::NativeSettingsBridge::NotificationRequest& request) {
        if (capture_ && capture_->updateAdmissionBlocked()) {
            refreshLocalNotificationSettings();
            setLocalNotificationStatus(L"Настройка не изменена: готовится обновление GRAF.");
            return;
        }
        const CustodyMutationScope mutation(shellMutations_);
        const auto displayedEpoch = localNotificationEpoch_;
        bindNotificationContext(); // never write using the previous account's context
        if (!reminders_ || !capture_ || !localNotificationStatus_) return;
        if (displayedEpoch != reminders_->epoch()) {
            refreshLocalNotificationSettings();
            setLocalNotificationStatus(L"Аккаунт изменился. Проверьте настройки и повторите действие.");
            return;
        }
        try {
            const auto reply = reminders_->settings(request, reminderWallTime(), std::chrono::steady_clock::now(),
                capture_->indicator().visible);
            const auto result = winrt::Windows::Data::Json::JsonObject::Parse(winrt::to_hstring(reply));
            refreshLocalNotificationSettings(); // failed save restores the persisted values
            setLocalNotificationStatus(result.HasKey(L"error") ? result.GetNamedString(L"error") : result.GetNamedString(L"message"));
        } catch (...) {
            refreshLocalNotificationSettings();
            setLocalNotificationStatus(L"Не удалось подтвердить настройку. Проверьте выбранные значения и повторите.");
        }
        if (cabinet_) cabinet_->webView().refreshNativeSettings();
    }

    ComboBox automaticPreferencePicker(std::wstring title,
        std::optional<graf::windows::VerifiedTargetIdentity> target) {
        ComboBox picker;
        picker.Header(box_value(title));
        picker.PlaceholderText(L"Разные настройки");
        picker.HorizontalAlignment(HorizontalAlignment::Stretch);
        setAccessible(picker, L"Автозапись: " + title);
        for (auto preference : {graf::windows::AutomaticRecordingPreference::always,
                                graf::windows::AutomaticRecordingPreference::ask,
                                graf::windows::AutomaticRecordingPreference::never}) {
            picker.Items().Append(box_value(winrt::to_hstring(graf::windows::automaticRecordingPreferenceLabel(preference))));
        }
        picker.SelectionChanged([this, target](auto const& sender, auto const&) {
            if (updatingAutomaticPreferences_) return;
            if (capture_ && capture_->updateAdmissionBlocked()) {
                automaticPreferenceError_ = true;
                refreshAutomaticSettings();
                return;
            }
            const CustodyMutationScope mutation(shellMutations_);
            const auto selected = sender.template as<ComboBox>().SelectedIndex();
            if (selected < 0 || selected > 2) return;
            const auto preference = selected == 0 ? graf::windows::AutomaticRecordingPreference::always :
                selected == 1 ? graf::windows::AutomaticRecordingPreference::ask : graf::windows::AutomaticRecordingPreference::never;
            const auto saved = target ? automaticPolicy_.setPreference(*target, preference) :
                automaticPolicy_.setAllPreferences(preference);
            automaticPreferenceError_ = !saved;
            refreshAutomaticSettings();
        });
        return picker;
    }

    // The cabinet's automatic-recording page asks this app what it stores, and
    // saves through it. One store, two surfaces: the native page and the cabinet
    // page cannot disagree about what an application's rule is.
    std::string recordingSettingsAnswer() const {
        const auto settings = automaticPolicy_.settings();
        std::vector<graf::windows::NativeSettingsBridge::Target> targets;
        targets.reserve(settings.applications.size());
        for (const auto& application : settings.applications) {
            targets.push_back({
                application.target.targetKey,
                application.target.displayName,
                std::string(graf::windows::automaticRecordingPreferenceToken(application.preference))});
        }
        return graf::windows::NativeSettingsBridge::settingsReply(targets);
    }

    std::string answerNativeSettings(const graf::windows::WebView2Host::NativeSettingsRequest& request) {
        using graf::windows::NativeSettingsBridge::Action;
        if (capture_ && capture_->updateAdmissionBlocked()) {
            if (request.handler == graf::windows::NativeSettingsBridge::kNotificationSettingsHandler)
                return graf::windows::NativeSettingsBridge::notificationSettingsReply({}, false, {},
                    "Настройки недоступны во время обновления GRAF. Повторите после завершения или отмены обновления.");
            return graf::windows::NativeSettingsBridge::failureReply(
                "Настройки недоступны во время обновления GRAF. Повторите после завершения или отмены обновления.");
        }
        const CustodyMutationScope mutation(shellMutations_);
        if (request.handler == graf::windows::NativeSettingsBridge::kNotificationSettingsHandler) {
            if (!reminders_ || !request.notification)
                return graf::windows::NativeSettingsBridge::notificationSettingsReply({}, false, {}, "Обновите окно настроек. Запрос уведомлений не поддерживается.");
            bindNotificationContext();
            const auto reply = reminders_->settings(*request.notification, reminderWallTime(), std::chrono::steady_clock::now(),
                capture_->indicator().visible);
            refreshLocalNotificationSettings();
            return reply;
        }
        if (request.handler != graf::windows::NativeSettingsBridge::kRecordingSettingsHandler) {
            return graf::windows::NativeSettingsBridge::failureReply("Неизвестная страница настроек.");
        }
        const auto action = graf::windows::NativeSettingsBridge::actionFromToken(request.action);
        if (!action) return graf::windows::NativeSettingsBridge::failureReply("Неизвестное действие.");
        if (*action == Action::read) return recordingSettingsAnswer();
        const auto preference = graf::windows::automaticRecordingPreferenceFromToken(request.rule);
        if (!preference) {
            return graf::windows::NativeSettingsBridge::failureReply("Неизвестное значение автозаписи.");
        }
        bool saved = false;
        if (*action == Action::setAll) {
            saved = automaticPolicy_.setAllPreferences(*preference);
        } else {
            const auto* target = verifiedTarget(request.targetId);
            if (!target) return graf::windows::NativeSettingsBridge::failureReply("Приложение не найдено в списке.");
            saved = automaticPolicy_.setPreference(*target, *preference);
        }
        if (!saved) {
            return graf::windows::NativeSettingsBridge::failureReply(
                "Настройки не сохранены. Предыдущий выбор продолжает действовать.");
        }
        automaticPreferenceError_ = false;
        // The native page shows the same store, so it is brought to the state that
        // was just saved; the cabinet page is answered with that same state.
        refreshAutomaticSettings();
        return recordingSettingsAnswer();
    }

    const graf::windows::VerifiedTargetIdentity* verifiedTarget(std::string_view targetKey) const {
        if (targetKey.empty()) return nullptr;
        for (const auto& target : verifiedTargets_.targets()) {
            if (target.targetKey == targetKey) return &target;
        }
        return nullptr;
    }

    void refreshAutomaticSettings() {
        if (!bulkAutomaticPreference_) return;
        const auto settings = automaticPolicy_.settings();
        updatingAutomaticPreferences_ = true;
        const auto index = [](graf::windows::AutomaticRecordingPreference value) {
            return value == graf::windows::AutomaticRecordingPreference::always ? 0 :
                value == graf::windows::AutomaticRecordingPreference::ask ? 1 : 2;
        };
        bulkAutomaticPreference_.IsEnabled(!settings.applications.empty());
        bulkAutomaticPreference_.SelectedIndex(settings.bulkPreference ? index(*settings.bulkPreference) : -1);
        for (const auto& [target, picker] : automaticPreferencePickers_)
            picker.SelectedIndex(index(automaticPolicy_.preference(target)));
        updatingAutomaticPreferences_ = false;
        if (cabinet_) cabinet_->webView().refreshNativeSettings();
        const auto failed = automaticPreferenceError_ || settings.preferenceWriteFailed;
        automaticSettingsError_.Text(failed ? L"Настройки не сохранены. Предыдущий выбор продолжает действовать." : L"");
        automaticSettingsError_.Visibility(failed ? Visibility::Visible : Visibility::Collapsed);
    }

    [[nodiscard]] graf::windows::InteractionPermit interactionPermit() const noexcept {
        return !shuttingDown_ && tray_ ? tray_->interactionPermit() : graf::windows::InteractionPermit{};
    }

    void invalidateNotificationInteraction() {
        if (shuttingDown_ || !capture_) return;
        cancelCalendarJoin();
        pendingProblems_.clear();
        presentedProblem_.reset();
        // Revoke proposals and pending starts, but keep tracking an accepted
        // automatic recording. Its indicator and Stop are independent surfaces.
        if (!capture_->indicator().visible || capture_->indicator().state == graf::windows::SessionState::starting)
            automaticPolicy_.cancel();
        capture_->notificationCard().invalidatePresentation();
        (void)closeAutomaticPrompt(automaticPromptGeneration_);
        detectionSnapshot_ = {};
        detectionNotBefore_ = graf::windows::DetectionClock::now();
        if (reminderCancellation_) reminderCancellation_->store(true);
        reminderRequestIdentity_ = {};
        pendingReminderAction_.reset();
        reminderFlightAction_.reset();
        if (reminders_) reminders_->calendarFailed(); // not an account/history reset
        lastReminderRequest_ = 0;
    }

    void refreshNotificationInteraction() {
        const auto permit = interactionPermit();
        if (permit.epoch != notificationInteractionEpoch_ || (!permit.allowed && notificationInteractionAllowed_))
            invalidateNotificationInteraction();
        notificationInteractionEpoch_ = permit.epoch;
        notificationInteractionAllowed_ = permit.allowed;
    }

    graf::windows::AutomaticRecordingPrerequisites automaticPrerequisites() const {
        graf::windows::AutomaticRecordingPrerequisites result;
        result.capture = capture_->readiness();
        result.recordingAlreadyActive = capture_->indicator().visible;
        // Only this decision's own starting lease is exempt. A manual start or
        // a different session remains an active-recording blocker.
        if (capture_->indicator().state == graf::windows::SessionState::starting &&
            automaticPolicy_.hasPendingStart(capture_->sessionId())) result.recordingAlreadyActive = false;
        result.visibleIndicatorAvailable = indicatorWindow_ && indicatorText_;
        result.oneActionStopAvailable = result.visibleIndicatorAvailable && indicatorStop_ && indicatorStop_.IsEnabled();
        result.suppressed = shuttingDown_ || exitRequested_ || capture_->updateAdmissionBlocked() || permissionDialogOpen_ || localActionDialogOpen_ ||
            !interactionPermit().allowed;
        return result;
    }

    void consumeDetectionSnapshot() {
        if (detectionFuture_.valid() && detectionFuture_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto snapshot = detectionFuture_.get();
                detectionSnapshot_ = snapshot.observedAt >= detectionNotBefore_ ? std::move(snapshot) :
                    graf::windows::TargetDetectionSnapshot{};
            }
            catch (...) { detectionSnapshot_ = {}; }
        }
    }

    void refreshAutomaticRecording() {
        consumeDetectionSnapshot();
        const auto now = graf::windows::DetectionClock::now();
        if (automaticPolicy_.shouldStopCapture(detectionSnapshot_, capture_->indicator().visible, now))
            (void)capture_->stop();
        if (!detectionFuture_.valid() && now - lastDetectionRequest_ >= std::chrono::seconds(1)) {
            lastDetectionRequest_ = now;
            // The worker owns an immutable registry copy; no UI/queue reference
            // survives shutdown, and signature verification never blocks Stop.
            std::packaged_task<graf::windows::TargetDetectionSnapshot()> task([registry = verifiedTargets_] {
                return graf::windows::WindowsTargetDetector::snapshot(registry);
            });
            try {
                auto future = task.get_future();
                std::thread(std::move(task)).detach();
                detectionFuture_ = std::move(future);
            } catch (...) { detectionSnapshot_ = {}; }
        }
        const auto decision = automaticPolicy_.update(detectionSnapshot_, automaticPrerequisites(), now);
        if (decision.shouldStart) startAutomaticRecording(decision);
        switch (detectionSnapshot_.status) {
        case graf::windows::TargetDetectionStatus::noVerifiedTargets:
            autoRecordDetail_.Text(L"Нет проверенного реестра приложений. Ручная запись доступна.");
            break;
        case graf::windows::TargetDetectionStatus::ready:
            autoRecordDetail_.Text(automaticPolicy_.state() == graf::windows::AutomaticPromptState::countdown
                ? L"Обнаружена встреча — ожидаем ваш выбор"
                : capture_->indicator().visible ? L"Идёт запись. Остановить её можно в панели записи."
                : automaticPrerequisites().allowsStart() ? L"Ожидаем встречу. Действует выбранный режим автозаписи."
                : L"Автозапись приостановлена. Проверьте готовность записи в панели управления.");
            break;
        default:
            autoRecordDetail_.Text(L"Не удалось проверить приложения. Автозапись приостановлена.");
            break;
        }
        if (automaticPreferenceError_) autoRecordDetail_.Text(
            std::wstring(autoRecordDetail_.Text().c_str()) + L" Выбор не сохранён. Предыдущая настройка продолжает действовать.");
        updateAutomaticPrompt();
    }

    void startAutomaticRecording(const graf::windows::AutomaticRecordingDecision& decision) {
        if (!decision.shouldStart || !automaticPolicy_.canBindStart(decision.generation)) return;
        const auto permit = interactionPermit();
        if (!permit.allowed || !automaticPrerequisites().allowsStart() || !ensureRecordingIndicator()) {
            automaticPolicy_.cancel();
            return;
        }
        const auto result = capture_->record([this, generation = decision.generation, interactionEpoch = permit.epoch](const std::string& sessionId) {
            const bool bound = automaticPolicy_.bindStart(generation, sessionId);
            return [this, generation, bound, interactionEpoch](std::string_view currentSession) {
                if (!bound) return false;
                // pollHealth also runs from pause/resume and before the ordinary
                // detection tick. Consume any completed observation here, without
                // waiting, pumping UI events or reentering capture polling.
                consumeDetectionSnapshot();
                capture_->refreshPermission();
                auto prerequisites = automaticPrerequisites();
                prerequisites.visibleIndicatorAvailable = recordingIndicatorAvailable();
                prerequisites.oneActionStopAvailable = prerequisites.visibleIndicatorAvailable;
                // Prerequisite queries can outlive the interaction epoch. This
                // final fresh permit must be the last query before acceptance.
                const auto permit = interactionPermit();
                if (!permit.allowed || permit.epoch != interactionEpoch) return false;
                return automaticPolicy_.acceptStart(generation, currentSession, detectionSnapshot_, prerequisites);
            };
        });
        if (result.accepted() && (result.state == graf::windows::SessionState::starting ||
                                  result.state == graf::windows::SessionState::recording)) {
            recordingStartedAt_ = 0;
        } else {
            automaticPolicy_.cancel();
        }
    }

    bool closeAutomaticPrompt(std::uint64_t generation) noexcept {
        if (generation != automaticPromptGeneration_) return true;
        const auto id = std::exchange(automaticPromptId_, std::string{});
        automaticPromptTargetKey_.clear();
        rememberAutomaticChoice_ = false;
        if (capture_ && capture_->notificationCard().visible() &&
            capture_->notificationCard().kind() == graf::windows::NoticeKind::recordingPrompt &&
            capture_->notificationCard().id() == id) capture_->notificationCard().dismiss();
        return true;
    }

    void updateAutomaticPrompt() {
        using namespace graf::windows;
        const auto view = AutomaticRecordingPrompt::view(automaticPolicy_);
        const auto key = VerifiedTargetRegistry::identityKey(automaticPolicy_.target());
        if (!automaticPromptId_.empty() && automaticPromptTargetKey_ != key)
            (void)closeAutomaticPrompt(automaticPromptGeneration_);
        if (!view.visible) { (void)closeAutomaticPrompt(automaticPromptGeneration_); return; }
        if (automaticPromptId_.empty()) {
            ++automaticPromptGeneration_;
            automaticPromptId_ = "prompt:" + std::to_string(automaticPromptGeneration_);
            automaticPromptTargetKey_ = key;
            rememberAutomaticChoice_ = false;
        }
        const auto generation = automaticPromptGeneration_;
        const auto current = [this, generation, key] {
            return !shuttingDown_ && capture_ && !capture_->updateAdmissionBlocked() &&
                !automaticPromptId_.empty() && generation == automaticPromptGeneration_ &&
                automaticPolicy_.state() == AutomaticPromptState::countdown &&
                VerifiedTargetRegistry::identityKey(automaticPolicy_.target()) == key;
        };
        NoticeContent content{NoticeKind::recordingPrompt, automaticPromptId_,
            std::wstring(winrt::to_hstring(view.title).c_str()),
            deviceDisplayName(view.applicationName) + L". " +
                std::wstring(winrt::to_hstring(view.accessibleDescription).c_str()),
            {{std::wstring(winrt::to_hstring(view.secondaryAction).c_str()), NoticeAction::skip},
             {std::wstring(winrt::to_hstring(view.primaryAction).c_str()), NoticeAction::record}}};
        content.checkboxTitle = std::wstring(winrt::to_hstring(view.rememberChoiceLabel).c_str());
        content.rememberChoice = rememberAutomaticChoice_;
        NoticePresentationHooks hooks;
        hooks.beforeFirstShow = [this, current] {
            capture_->refreshPermission();
            return current() && automaticPrerequisites().allowsStart();
        };
        hooks.onPresented = [this, current] {
            if (current() && !automaticPolicy_.confirmPromptPresented(
                capture_->notificationCard().deadline() - std::chrono::seconds(8))) automaticPolicy_.cancel();
        };
        hooks.onRememberChanged = [this, current](bool value) { if (current()) rememberAutomaticChoice_ = value; };
        hooks.onInvalidated = [this, generation, current] {
            if (current()) automaticPolicy_.cancel();
            (void)closeAutomaticPrompt(generation);
        };
        hooks.onExpired = [this, generation, current] {
            if (current()) {
                consumeDetectionSnapshot();
                const auto decision = automaticPolicy_.update(detectionSnapshot_, automaticPrerequisites());
                if (decision.shouldStart) startAutomaticRecording(decision);
                else automaticPolicy_.cancel();
            }
            (void)closeAutomaticPrompt(generation);
        };
        const auto now = std::chrono::steady_clock::now();
        const bool shown = capture_->notificationCard().present(std::move(content), now, now + std::chrono::seconds(8),
            [this, generation, current](NoticeAction action) {
                if (!current()) return;
                const CustodyMutationScope mutation(shellMutations_);
                consumeDetectionSnapshot();
                AutomaticRecordingDecision decision;
                if (action == NoticeAction::record)
                    decision = automaticPolicy_.recordNow(rememberAutomaticChoice_, detectionSnapshot_, automaticPrerequisites());
                else if (action == NoticeAction::skip) decision = automaticPolicy_.refuse(rememberAutomaticChoice_);
                else return;
                automaticPreferenceError_ = automaticPolicy_.settings().preferenceWriteFailed;
                (void)closeAutomaticPrompt(generation);
                startAutomaticRecording(decision);
                refreshAutomaticSettings();
                refreshNativeState();
            },
            [this, generation, current] {
                if (current()) automaticPolicy_.cancel();
                (void)closeAutomaticPrompt(generation);
            }, std::move(hooks));
        if (!shown) {
            if (current()) {
                automaticPolicy_.cancel();
                localActionNotice_ = L"Не удалось показать предложение автозаписи. Начните запись вручную.";
            }
            (void)closeAutomaticPrompt(generation);
        }
    }

    void syncUpdateAdmission() noexcept {
        if (capture_) capture_->setUpdateAdmissionBlocked(appUpdate_.blocksNewWork());
        if (appUpdate_.blocksNewWork()) { try { cancelLocalPlayback(); } catch (...) {} }
    }

    [[nodiscard]] bool readyForUpdate() const noexcept {
        return capture_ && !shuttingDown_ && !exitRequested_ && capture_->localQueueComplete() &&
            capture_->updateWorkDrained() && deletionSelectionsInFlight_ == 0 &&
            shellMutations_ == 0 && !calendarJoin_.busy() && !calendarCalling_;
    }

    void refreshUpdateWindow() {
        appUpdate_.tick(graf::windows::WindowsAppUpdateController::Clock::now(), readyForUpdate(),
            [this] { return readyForUpdate(); });
        syncUpdateAdmission();
        const bool available = appUpdate_.available();
        if (available != updateBadgeVisible_) {
            updateBadgeVisible_ = available;
            if (cabinet_) cabinet_->webView().setAppUpdateAvailable(available);
        }
        if (!updateWindow_) return;
        updateContent_.RequestedTheme(shellIsDark_ ? ElementTheme::Dark : ElementTheme::Light);
        const auto detail = graf::windows::appUpdateDetail(appUpdate_.result(), appUpdate_.busy());
        if (updateDetail_.Text() != detail) {
            updateDetail_.Text(detail);
            setAccessible(updateDetail_, detail);
            try {
                using namespace winrt::Microsoft::UI::Xaml::Automation::Peers;
                if (const auto peer = FrameworkElementAutomationPeer::FromElement(updateDetail_))
                    peer.RaiseAutomationEvent(AutomationEvents::LiveRegionChanged);
            } catch (...) {}
        }
        updateCheckButton_.IsEnabled(!appUpdate_.busy() && !exitRequested_);
        updateInstallButton_.IsEnabled(appUpdate_.canInstall() && capture_ &&
            !graf::windows::isCaptureState(capture_->indicator().state) &&
            capture_->localQueueComplete() && !exitRequested_);
        updateInstallButton_.Visibility(appUpdate_.canInstall() ? Visibility::Visible : Visibility::Collapsed);
        updateCancelButton_.Visibility(appUpdate_.blocksNewWork() ? Visibility::Visible : Visibility::Collapsed);
    }

    void openUpdateWindow() {
        if (shuttingDown_ || exitRequested_) return;
        if (updateWindow_) { updateWindow_.Activate(); return; }
        updateWindow_ = Window();
        updateWindow_.Title(L"Обновления GRAF");
        updateContent_ = StackPanel();
        updateContent_.Spacing(18);
        updateContent_.Padding(Thickness{24, 24, 24, 24});
        updateContent_.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
        auto title = TextBlock();
        title.Text(L"Обновления GRAF");
        styleText(title, 24, FontWeights::SemiBold());
        updateContent_.Children().Append(title);
        updateDetail_ = TextBlock();
        styleText(updateDetail_, 14);
        winrt::Microsoft::UI::Xaml::Automation::AutomationProperties::SetLiveSetting(updateDetail_,
            winrt::Microsoft::UI::Xaml::Automation::Peers::AutomationLiveSetting::Polite);
        updateContent_.Children().Append(updateDetail_);
        updateCheckButton_ = styledButton(L"Проверить снова", true);
        setAccessible(updateCheckButton_, L"Проверить обновления GRAF", L"Проверка не прерывает запись и не устанавливает обновление");
        updateCheckButton_.Click([this](auto const&, auto const&) {
            if (shuttingDown_ || exitRequested_) return;
            (void)appUpdate_.check(graf::windows::WindowsAppUpdateController::Clock::now());
            refreshUpdateWindow();
        });
        updateContent_.Children().Append(updateCheckButton_);
        updateInstallButton_ = styledButton(L"Установить обновление", true);
        setAccessible(updateInstallButton_, L"Установить обновление GRAF",
            L"Дождаться завершения фоновых операций и передать установку Windows. Во время записи установка недоступна");
        updateInstallButton_.Click([this](auto const&, auto const&) {
            if (shuttingDown_ || exitRequested_ || !capture_ || !appUpdate_.canInstall()) return;
            // Close admission before native source checks can enter COM and
            // dispatch a queued Record/delete action on this STA.
            capture_->setUpdateAdmissionBlocked(true);
            const bool preparing = appUpdate_.beginInstall(graf::windows::WindowsAppUpdateController::Clock::now(),
                graf::windows::isCaptureState(capture_->indicator().state), capture_->localQueueComplete());
            syncUpdateAdmission();
            if (preparing) {
                automaticPolicy_.cancel();
                (void)closeAutomaticPrompt(automaticPromptGeneration_);
            }
            refreshUpdateWindow();
        });
        updateContent_.Children().Append(updateInstallButton_);
        updateCancelButton_ = styledButton(L"Отменить обновление");
        setAccessible(updateCancelButton_, L"Отменить обновление GRAF",
            L"После начала установки нужно дождаться подтверждения отмены от Windows");
        updateCancelButton_.Click([this](auto const&, auto const&) {
            appUpdate_.close();
            syncUpdateAdmission();
            refreshUpdateWindow();
        });
        updateContent_.Children().Append(updateCancelButton_);
        auto close = styledButton(L"Закрыть");
        close.Click([this](auto const&, auto const&) { if (updateWindow_) updateWindow_.Close(); });
        updateContent_.Children().Append(close);
        auto scroll = ScrollViewer();
        scroll.Content(updateContent_);
        updateWindow_.Content(scroll);
        updateWindow_.Closed([this](auto const&, auto const&) {
            appUpdate_.close();
            syncUpdateAdmission();
            updateWindow_ = nullptr;
            updateContent_ = nullptr;
            updateDetail_ = nullptr;
            updateCheckButton_ = nullptr;
            updateInstallButton_ = nullptr;
            updateCancelButton_ = nullptr;
        });
        (void)appUpdate_.check(graf::windows::WindowsAppUpdateController::Clock::now());
        refreshUpdateWindow();
        updateWindow_.Activate();
        resizeWindowLogical(updateWindow_, 500, 360, true);
    }

    void showPermissionOnboarding() {
        if (permissionDialogOpen_ || !root_.XamlRoot()) return;
        permissionDialogOpen_ = true;
        ContentDialog dialog;
        dialog.XamlRoot(root_.XamlRoot());
        dialog.Title(box_value(L"Разрешите запись звука"));
        dialog.Content(box_value(L"Для записи встречи GRAF нужен доступ к микрофону. Системный звук захватывается через общий микс Windows без виртуального драйвера."));
        dialog.PrimaryButtonText(L"Открыть настройки");
        dialog.SecondaryButtonText(L"Повторить проверку");
        dialog.CloseButtonText(L"Позже");
        const auto dispatcher = root_.DispatcherQueue();
        const auto alive = alive_;
        try {
            dialog.ShowAsync().Completed([this, alive, dispatcher](auto const& operation, auto const&) {
                dispatcher.TryEnqueue([this, alive, operation] {
                    if (!alive->load()) return;
                    permissionDialogOpen_ = false;
                    try {
                        const auto result = operation.GetResults();
                        if (result == ContentDialogResult::Primary) {
                            ShellExecuteW(nullptr, L"open", L"ms-settings:privacy-microphone", nullptr, nullptr, SW_SHOWNORMAL);
                        } else if (result == ContentDialogResult::Secondary) refreshNativeState();
                    } catch (...) {}
                });
            });
        } catch (...) {
            permissionDialogOpen_ = false;
        }
    }

    bool canStartRecording() const {
        return !shuttingDown_ && !exitRequested_ && capture_ &&
            !capture_->updateAdmissionBlocked() &&
            !graf::windows::isCaptureState(capture_->indicator().state) && capture_->recordingReady();
    }

    void recordCapture(const std::function<bool()>& current = {}) {
        if (shuttingDown_ || exitRequested_ || !capture_ || capture_->updateAdmissionBlocked() ||
            graf::windows::isCaptureState(capture_->indicator().state) || (current && !current())) return;
        if (!capture_->localQueueComplete()) {
            localActionNotice_ = capture_->custodySummary();
            return;
        }
        // A tray command can outlive its menu snapshot. Use the same fresh
        // permission/device/storage gate as the shell, not the painted flags.
        capture_->refreshReadiness();
        if ((current && !current()) || !canStartRecording() || !ensureRecordingIndicator()) { refreshNativeState(); return; }
        if (!canStartRecording() || (current && !current())) return;
        localActionNotice_.clear();
        automaticPolicy_.cancel();
        recordingStartedAt_ = 0;
        (void)capture_->record();
        refreshNativeState();
    }

    void stopCapture() {
        if (!capture_) return;
        automaticPolicy_.cancel();
        (void)capture_->stop();
        refreshNativeState();
    }

    [[nodiscard]] bool shellExitJobsDrained() const noexcept {
        return deletionSelectionsInFlight_ == 0 && shellMutations_ == 0 &&
            !calendarResolverThread_.joinable() && !calendarCalling_ && !calendarJoin_.busy();
    }
    [[nodiscard]] bool exitWorkDrained() const noexcept {
        return exitRequested_ && shellExitJobsDrained() && !appUpdate_.blocksNewWork() &&
            (!capture_ || capture_->shutdownWorkDrained());
    }
    void beginExit() {
        exitRequested_ = true;
        cancelLocalPlayback();
        cancelCalendarJoin();
        automaticPolicy_.cancel();
        (void)closeAutomaticPrompt(automaticPromptGeneration_);
        appUpdate_.close();
        syncUpdateAdmission();
        if (capture_) {
            capture_->requestShutdown(); // Stop/cancel now; already accepted deletion replies still drain.
            if (shellExitJobsDrained()) capture_->shutdown();
        }
    }
    void requestExit() {
        if (!window_ || shuttingDown_) return;
        beginExit();
        if (exitWorkDrained()) window_.Close();
    }

    bool recordingIndicatorAvailable() const {
        if (!indicatorWindow_ || !indicatorStop_ || !indicatorWindow_.AppWindow().IsVisible()) return false;
        const auto handle = nativeWindowHandle(indicatorWindow_);
        return handle && IsWindowVisible(handle) && !IsIconic(handle) &&
            indicatorStop_.IsEnabled() && indicatorStop_.Visibility() == Visibility::Visible;
    }

    bool ensureRecordingIndicator(bool show = true) {
        try {
            if (!indicatorWindow_) {
                indicatorWindow_ = Window();
                indicatorWindow_.AppWindow().Title(L"Запись — GRAF");
            applyWindowIcon(indicatorWindow_);
            applyWindowChrome(nativeWindowHandle(indicatorWindow_), shellIsDark_);
                indicatorWindow_.AppWindow().SetPresenter(winrt::Microsoft::UI::Windowing::AppWindowPresenterKind::CompactOverlay);
                resizeWindowLogical(indicatorWindow_, 360, 150);
                auto panel = StackPanel();
                indicatorPanel_ = panel;
                panel.RequestedTheme(shellIsDark_ ? ElementTheme::Dark : ElementTheme::Light);
                panel.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
                panel.Padding(Thickness{12, 8, 12, 8});
                panel.Spacing(8);
                indicatorText_ = TextBlock();
                indicatorText_.Text(L"Запуск записи…");
                styleText(indicatorText_, 13, FontWeights::SemiBold());
                panel.Children().Append(indicatorText_);
                indicatorStop_ = styledButton(L"Остановить запись", true);
                setAccessible(indicatorStop_, L"Остановить запись GRAF");
                indicatorStop_.Click([this](auto const&, auto const&) { stopCapture(); });
                panel.Children().Append(indicatorStop_);
                indicatorWindow_.Content(panel);
                indicatorWindow_.AppWindow().Closing([this](auto const&, auto const& args) {
                    if (!shuttingDown_ && capture_ && capture_->indicator().visible) {
                        args.Cancel(true);
                        window_.Activate();
                    }
                });
                indicatorWindow_.Closed([this](auto const&, auto const&) {
                    indicatorWindow_ = nullptr;
                    indicatorText_ = nullptr;
                    indicatorStop_ = nullptr;
                });
            }
            // Prepared once, without displaying a false recording indicator.
            if (!show) return indicatorText_ && indicatorStop_ && indicatorStop_.IsEnabled();
            indicatorText_.Text(L"Запуск записи…");
            indicatorWindow_.AppWindow().Show(false);
            if (!recordingIndicatorAvailable()) throw winrt::hresult_error(E_FAIL);
            return true;
        } catch (...) {
            try { if (indicatorWindow_) indicatorWindow_.Close(); } catch (...) {}
            indicatorWindow_ = nullptr;
            indicatorText_ = nullptr;
            indicatorStop_ = nullptr;
            localActionNotice_ = L"Не удалось открыть индикатор записи. Перезапустите GRAF перед записью.";
            return false;
        }
    }

    void pauseResumeCapture() {
        if (!capture_) return;
        if (capture_->indicator().state == graf::windows::SessionState::paused) (void)capture_->resume();
        else (void)capture_->pause();
        refreshNativeState();
    }

    void toggleInspector() {
        if (shouldShowExpandedInspector()) {
            inspectorExpanded_ = false;
            attentionExpansionDismissed_ = hasInspectorAttention();
        } else {
            inspectorExpanded_ = true;
            attentionExpansionDismissed_ = false;
        }
        updateInspectorVisibility();
    }

    bool hasInspectorAttention() const {
        if (!capture_) return false;
        const auto state = capture_->indicator().state;
        return state == graf::windows::SessionState::failed ||
            state == graf::windows::SessionState::degraded ||
            (state == graf::windows::SessionState::stopping &&
             capture_->indicator().reason == graf::windows::ReasonCode::finalizationFailed) ||
            capture_->custodyAttentionCount() != 0 || !localActionNotice_.empty();
    }

    bool shouldShowExpandedInspector() const {
        return inspectorExpanded_ || (hasInspectorAttention() && !attentionExpansionDismissed_);
    }

    void updateInspectorVisibility() {
        if (!inspectorColumn_ || !expandedInspector_ || !compactInspector_) return;
        const auto expanded = shouldShowExpandedInspector();
        inspectorColumn_.Width(GridLengthHelper::FromValueAndType(
            expanded ? 308.0 : 52.0, GridUnitType::Pixel));
        expandedInspector_.Visibility(expanded ? Visibility::Visible : Visibility::Collapsed);
        compactInspector_.Visibility(expanded ? Visibility::Collapsed : Visibility::Visible);
        if (inspectorToggle_) {
            inspectorToggle_.Content(SymbolIcon(Symbol::Back));
            setAccessible(inspectorToggle_, expanded ? L"Скрыть панель управления" : L"Показать панель управления");
        }
    }

    void showStartupError(std::wstring_view detail) {
        root_.Children().Clear();
        auto error = StackPanel();
        error.Spacing(10);
        error.Margin(Thickness{32, 32, 32, 32});
        auto title = TextBlock();
        title.Text(L"GRAF не удалось запустить");
        styleText(title, 22, FontWeights::SemiBold());
        auto message = TextBlock();
        message.Text(detail);
        styleText(message, 13);
        error.Children().Append(title);
        error.Children().Append(message);
        auto quit = styledButton(L"Закрыть GRAF");
        quit.Click([this](auto const&, auto const&) { requestExit(); });
        error.Children().Append(quit);
        root_.Children().Append(error);
    }

    static double reminderWallTime() {
        return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
    }

    void playOptionalNotificationSound() {
        if (!shuttingDown_ && !exitRequested_ && capture_ && reminders_ &&
            !capture_->indicator().visible && reminders_->preferences().sound &&
            !reminders_->preferences().quiet && interactionPermit().allowed) MessageBeep(MB_OK);
    }

    struct ProblemTarget {
        graf::windows::LocalProblemContext context;
        std::string sessionId, incidentId;
        std::uint64_t authGeneration = 0, contextEpoch = 0, interactionEpoch = 0, occurredAtMs = 0;
        graf::windows::RecordingNoticePresenter::Clock::time_point expires;
    };

    [[nodiscard]] bool problemContextCurrent(const ProblemTarget& target) const {
        return !shuttingDown_ && !exitRequested_ && capture_ && reminders_ &&
            target.authGeneration == capture_->authGeneration() && target.contextEpoch == reminders_->epoch() &&
            target.context.origin == reminders_->origin() && target.context.owner == reminders_->owner() &&
            target.context.workspace == reminders_->workspace() &&
            capture_->ownsRecordingSession(target.context, target.sessionId);
    }

    [[nodiscard]] bool problemActionCurrent(const ProblemTarget& target) const try {
        if (!problemContextCurrent(target)) return false;
        const auto permit = interactionPermit();
        if (!permit.allowed || permit.epoch == 0 || permit.epoch != target.interactionEpoch) return false;
        const auto problems = capture_->recordingProblems(static_cast<std::uint64_t>(reminderWallTime() * 1000));
        return std::any_of(problems.begin(), problems.end(), [&](const auto& problem) {
            return std::string_view(problem.sessionId) == target.sessionId && std::string_view(problem.incidentId) == target.incidentId &&
                problem.state == graf::windows::LocalProblemState::problem;
        });
    } catch (const std::bad_alloc&) {
        return false;
    }

    void openProblemRecording(const ProblemTarget& target) {
        if (!problemActionCurrent(target)) return;
        if (selectedRecordingRevision_ == std::numeric_limits<std::uint64_t>::max()) return;
        ++selectedRecordingRevision_; // Every explicit choice, including the same recording, revokes older UI results.
        selectedRecording_ = target;
        selectedRecordingDisplayKey_.clear();
        inspectorExpanded_ = true;
        attentionExpansionDismissed_ = false;
        refreshSelectedRecording();
        updateInspectorVisibility();
        openMainWindow();
        const auto alive = alive_;
        // Layout follows expansion; the queued focus must still name the same
        // account/session, not whichever recording became current meanwhile.
        (void)root_.DispatcherQueue().TryEnqueue([this, alive, target] {
            if (!alive->load() || !selectedRecording_ || selectedRecording_->sessionId != target.sessionId ||
                !problemActionCurrent(target) || !selectedRecordingPanel_) return;
            selectedRecordingPanel_.StartBringIntoView();
            (void)selectedRecordingPanel_.Focus(FocusState::Programmatic);
        });
    }

    void reconcileRecordingProblems() try {
        if (!capture_ || !reminders_ || shuttingDown_ || exitRequested_ || capture_->updateAdmissionBlocked()) return;
        using State = graf::windows::LocalProblemState;
        using Clock = graf::windows::RecordingNoticePresenter::Clock;
        const auto now = Clock::now();
        const auto permit = interactionPermit();
        const auto problems = capture_->recordingProblems(static_cast<std::uint64_t>(reminderWallTime() * 1000));
        auto& card = capture_->notificationCard();
        const auto lookup = [&](const ProblemTarget& target) {
            return std::find_if(problems.begin(), problems.end(), [&](const auto& problem) {
                return std::string_view(problem.sessionId) == target.sessionId && std::string_view(problem.incidentId) == target.incidentId;
            });
        };
        const auto actionCurrent = [&](const ProblemTarget& target) {
            const auto problem = lookup(target);
            return permit.allowed && permit.epoch != 0 && permit.epoch == target.interactionEpoch &&
                problemContextCurrent(target) && problem != problems.end() && problem->state == State::problem;
        };
        // Unknown/absent observations revoke UI actions, but never erase the
        // durable incident. Only complete, owned, all-uploaded truth resolves it.
        for (const auto& problem : problems) {
            if (problem.state == graf::windows::LocalProblemState::positivelyResolved &&
                problemStore_.resolveProblem(reminders_->origin(), reminders_->owner(), reminders_->workspace(), problem.incidentId))
                card.resolveProblem(std::string(problem.incidentId.data(), problem.incidentId.size()));
        }
        pendingProblems_.erase(std::remove_if(pendingProblems_.begin(), pendingProblems_.end(), [&](const auto& target) {
            const auto problem = lookup(target);
            return now >= target.expires || !problemContextCurrent(target) || !permit.allowed ||
                permit.epoch != target.interactionEpoch || problem == problems.end() || problem->state != State::problem;
        }), pendingProblems_.end());
        if (presentedProblem_) {
            const bool visible = card.visible() && card.kind() == graf::windows::NoticeKind::problem && card.id() == presentedProblem_->incidentId;
            if (!visible || !actionCurrent(*presentedProblem_)) {
                presentedProblem_.reset();
                if (visible) card.invalidate();
            }
        }
        for (const auto& problem : problems) {
            if (problem.state != State::problem || !problem.fresh || problem.incidentId.size() > 1024) continue;
            if (!problemStore_.claimProblem(reminders_->origin(), reminders_->owner(), reminders_->workspace(), problem.incidentId)) continue;
            const auto expires = now + std::chrono::seconds(300);
            card.recordProblemHistory(std::string(problem.incidentId.data(), problem.incidentId.size()), expires);
            if (reminders_->preferences().quiet) continue;
            if (!permit.allowed || permit.epoch == 0 || pendingProblems_.size() >= 256) continue;
            pendingProblems_.push_back({{reminders_->origin(), reminders_->owner(), reminders_->workspace()},
                std::string(problem.sessionId.data(), problem.sessionId.size()),
                std::string(problem.incidentId.data(), problem.incidentId.size()), capture_->authGeneration(), reminders_->epoch(),
                permit.epoch, problem.occurredAtMs, expires});
        }
        if (reminders_->preferences().quiet) { pendingProblems_.clear(); return; }
        if (!permit.allowed || card.automaticPromptActive() ||
            (card.visible() && static_cast<int>(card.kind()) >= static_cast<int>(graf::windows::NoticeKind::problem))) return;
        if (pendingProblems_.empty()) return;
        const auto next = std::min_element(pendingProblems_.begin(), pendingProblems_.end(), [](const auto& a, const auto& b) {
            return a.occurredAtMs == b.occurredAtMs ? a.incidentId < b.incidentId : a.occurredAtMs < b.occurredAtMs;
        });
        const auto target = *next;
        pendingProblems_.erase(next); // a failed/invalidated show is not replayed
        if (!actionCurrent(target)) return;
        const auto alive = alive_;
        graf::windows::NoticePresentationHooks hooks;
        hooks.beforeFirstShow = [this, alive, target] {
            return alive->load() && Clock::now() < target.expires && problemActionCurrent(target) && !reminders_->preferences().quiet;
        };
        hooks.onPresented = [this, alive, target] {
            if (alive->load() && problemActionCurrent(target)) playOptionalNotificationSound();
        };
        presentedProblem_ = target;
        if (!card.present({graf::windows::NoticeKind::problem, target.incidentId, L"Запись требует вашего внимания",
                L"Откройте запись в GRAF, чтобы проверить её сохранность и отправку.",
                {{L"Открыть запись", graf::windows::NoticeAction::openRecording}}}, now, now + std::chrono::seconds(20),
            [this, alive, target](graf::windows::NoticeAction action) {
                if (alive->load() && action == graf::windows::NoticeAction::openRecording && problemActionCurrent(target))
                    openProblemRecording(target);
            }, {}, std::move(hooks))) presentedProblem_.reset();
    } catch (const std::bad_alloc&) {
        // A failed observation revokes only problem actions. It is not proof
        // of resolution and must not erase incidents or cancel other prompts.
        pendingProblems_.clear();
        presentedProblem_.reset();
        selectedRecording_.reset();
        selectedRecordingDisplayKey_.clear();
        if (capture_) {
            auto& card = capture_->notificationCard();
            if (card.visible() && card.kind() == graf::windows::NoticeKind::problem) card.invalidate();
        }
        refreshSelectedRecording();
    }

    [[nodiscard]] bool nativeLocalRemovalContextCurrent(const ProblemTarget& target, std::uint64_t revision) const {
        if (shuttingDown_ || exitRequested_ || !capture_ || !reminders_ || capture_->updateAdmissionBlocked() ||
            !revision || revision != selectedRecordingRevision_ || target.authGeneration != capture_->authGeneration() ||
            capture_->authSessionToken().empty() || !capture_->currentAccount()) return false;
        const auto& account = *capture_->currentAccount();
        const auto permit = interactionPermit();
        // Completion currency deliberately does not require the removed row or its problem to remain present.
        return permit.allowed && permit.epoch != 0 && permit.epoch == target.interactionEpoch &&
            target.contextEpoch == reminders_->epoch() && target.context.origin == reminders_->origin() &&
            target.context.owner == reminders_->owner() && target.context.workspace == reminders_->workspace() &&
            target.context.owner == account.userId && target.context.workspace == account.workspaceId;
    }

    [[nodiscard]] bool selectedLocalRemovalAllowed(const ProblemTarget& target, std::uint64_t revision,
        std::string_view localId, const std::shared_ptr<const graf::windows::ProtectedUploadQueueValue>& snapshot) const {
        if (!nativeLocalRemovalContextCurrent(target, revision) || !selectedRecording_ || pendingLocalRemoval_ ||
            selectedRecording_->sessionId != target.sessionId || selectedRecording_->incidentId != target.incidentId ||
            capture_->uploadsBusy() || capture_->indicator().visible || localId.empty() || !snapshot) return false;
        const auto observation = capture_->localObservation();
        if (!observation.complete || observation.value != snapshot) return false;
        std::size_t matches = 0;
        bool allowed = false;
        const auto& rows = snapshot->items();
        for (std::size_t index = 0; index < rows.size(); ++index) {
            const auto& row = rows[index];
            if (std::string_view(row.sessionId) != target.sessionId) continue;
            ++matches;
            if (std::string_view(row.localRecordingId) == localId &&
                std::string_view(row.ownerUserId) == target.context.owner &&
                std::string_view(row.ownerWorkspaceId) == target.context.workspace)
                allowed = snapshot->canLocalRemoval(index, target.context.owner, target.context.workspace);
        }
        return matches == 1 && allowed; // A session with multiple packages is not an unambiguous selected local copy.
    }

    void removeSelectedLocalCopy(const ProblemTarget& target, std::uint64_t revision, const std::string& localId) {
        if (!capture_) return;
        const auto observation = capture_->localObservation();
        if (!selectedLocalRemovalAllowed(target, revision, localId, observation.value)) return;
        confirmLocalAction(L"Удалить локальную копию?",
            L"Локальная копия выбранной записи будет перемещена в Корзину Windows. Уже отправленная запись на сервере не изменится.",
            L"Переместить в Корзину", [this, target, revision, localId, snapshot = observation.value] {
                if (!nativeLocalRemovalContextCurrent(target, revision)) return;
                if (!selectedLocalRemovalAllowed(target, revision, localId, snapshot)) {
                    localActionNotice_ = L"Состояние записи изменилось. Откройте запись и подтвердите удаление ещё раз.";
                    return;
                }
                PendingLocalAction pending{target, target.authGeneration, 0, revision};
                const auto ticket = capture_->requestProtectedLocalRemoval(snapshot, localId, target.authGeneration);
                if (ticket) {
                    pending.ticket = ticket->id;
                    pendingLocalRemoval_ = std::move(pending);
                    localActionNotice_ = L"Удаляем локальную копию… Запись на сервере не изменяется.";
                } else localActionNotice_ = L"Состояние записи изменилось. Откройте запись и подтвердите удаление ещё раз.";
            });
    }

    void refreshSelectedRecording() {
        if (!selectedRecordingPanel_) return;
        if (!selectedRecording_ || !nativeLocalRemovalContextCurrent(*selectedRecording_, selectedRecordingRevision_)) {
            selectedRecording_.reset();
            selectedRecordingDisplayKey_.clear();
            selectedRecordingPanel_.Content(nullptr);
            selectedRecordingStatus_ = nullptr;
            selectedLocalRemovalButton_ = nullptr;
            selectedLocalRecordingId_.clear();
            selectedRecordingPanel_.Visibility(Visibility::Collapsed);
            return;
        }
        const auto target = *selectedRecording_;
        std::wstring detail;
        if (capture_->sessionId() == target.sessionId) {
            const auto& state = capture_->indicator();
            detail = winrt::to_hstring(state.statusText).c_str();
            if (state.state == graf::windows::SessionState::failed) {
                detail += L"\n" + graf::windows::recordingFailureText(
                    graf::windows::effectiveFailureReason(state.reason, capture_->microphonePermissionGranted()),
                    capture_->finalization().trustedPrefixRetained);
            }
        }
        const auto observation = capture_->localObservation();
        const auto context = capture_->localProblemContext();
        std::string localId;
        if (observation.value && observation.complete) for (const auto& item : observation.value->items()) {
            if (std::string_view(item.sessionId) != target.sessionId || std::string_view(item.ownerUserId) != context.owner ||
                std::string_view(item.ownerWorkspaceId) != context.workspace) continue;
                if (!detail.empty()) detail += L"\n";
                detail += winrt::to_hstring(graf::windows::WebView2Host::localRecordingStatus(item)).c_str();
                localId.assign(item.localRecordingId.data(), item.localRecordingId.size());
            break;
        }
        // A busy observation is not a replacement selection. Keep the disabled
        // control's identity until a complete observation proves a different row.
        if (!observation.complete && !selectedRecordingDisplayKey_.empty()) localId = selectedLocalRecordingId_;
        if (observation.complete && localId.empty()) {
            if (!detail.empty()) detail += L"\n";
            detail += L"Локальная копия сейчас недоступна.";
        }
        if (detail.empty()) detail = L"Состояние записи уточняется. Это не подтверждение её отправки.";
        const auto revision = selectedRecordingRevision_;
        const auto key = target.sessionId + "\n" + target.incidentId + "\n" + localId + "\n" + std::to_string(revision);
        if (key != selectedRecordingDisplayKey_) {
            auto body = StackPanel(); body.Spacing(6);
            auto title = TextBlock();
            title.Text(L"Выбранная запись");
            styleText(title, 13, FontWeights::SemiBold());
            body.Children().Append(title);
            selectedRecordingStatus_ = TextBlock(); styleText(selectedRecordingStatus_, 13);
            body.Children().Append(selectedRecordingStatus_);
            selectedLocalRemovalButton_ = styledButton(L"Удалить локальную копию…");
            setAccessible(selectedLocalRemovalButton_, L"Удалить локальную копию выбранной записи. Серверная запись не изменится.");
            ToolTipService::SetToolTip(selectedLocalRemovalButton_, box_value(L"Только локальная копия. Серверная запись не изменится."));
            const auto alive = alive_;
            selectedLocalRemovalButton_.Click([this, alive, target, revision, localId](auto const&, auto const&) {
                if (!alive->load()) return;
                try { removeSelectedLocalCopy(target, revision, localId); }
                catch (...) { localActionNotice_ = L"Не удалось обновить состояние удаления. Проверьте очередь и Корзину Windows."; }
            });
            body.Children().Append(selectedLocalRemovalButton_);
            selectedRecordingPanel_.Content(body);
            selectedLocalRecordingId_ = localId;
            selectedRecordingDisplayKey_ = key;
        }
        if (selectedRecordingStatus_.Text() != detail) {
            selectedRecordingStatus_.Text(detail);
            setAccessible(selectedRecordingPanel_, L"Выбранная запись. " + detail);
        }
        const auto allowed = selectedLocalRemovalAllowed(target, revision, localId, observation.value);
        if (selectedLocalRemovalButton_.IsEnabled() != allowed) selectedLocalRemovalButton_.IsEnabled(allowed);
        selectedRecordingPanel_.Visibility(Visibility::Visible);
    }

    bool calendarAuthCurrent(const graf::windows::CalendarJoinContext& context, std::uint64_t interactionEpoch) const {
        const auto permit = interactionPermit();
        if (shuttingDown_ || exitRequested_ || !capture_ || capture_->updateAdmissionBlocked() ||
            !permit.allowed || permit.epoch != interactionEpoch || !capture_->currentAccount()) return false;
        const auto& account = *capture_->currentAccount();
        return context.origin == graf::windows::DesktopHttpConfig{}.baseOrigin &&
            context.owner == account.userId && context.workspace == account.workspaceId &&
            context.authGeneration == capture_->authGeneration() && !context.sessionToken.empty() &&
            context.sessionToken == capture_->authSessionToken();
    }

    bool calendarSourceCurrent() {
        if (!calendarFlight_) return false;
        const auto& flight = *calendarFlight_;
        const auto& context = flight.context;
        bool source = calendarAuthCurrent(context, flight.interactionEpoch);
        if (flight.document) source = source && cabinet_ && cabinet_->webView().calendarJoinCurrent(*flight.document);
        else if (flight.native) {
            const auto expiry = reminders_ && capture_ ? reminders_->pendingActionExpiry(flight.native->target,
                flight.native->action, reminderWallTime(), capture_->indicator().visible) : std::nullopt;
            source = source && expiry && *expiry == context.actionExpiresAt && reminders_->epoch() == context.sourceEpoch &&
                reminders_->owner() == context.owner && reminders_->workspace() == context.workspace && reminders_->origin() == context.origin;
        } else if (flight.menu) {
            source = source && reminders_ && reminders_->epoch() == context.sourceEpoch &&
                reminders_->owner() == context.owner && reminders_->workspace() == context.workspace &&
                reminders_->origin() == context.origin &&
                reminders_->upcomingCurrent(flight.menu->event, flight.menu->epoch, reminderWallTime()) &&
                std::chrono::steady_clock::now() < context.actionExpiresAt;
        } else source = false;
        return source;
    }

    bool calendarCurrent() {
        if (!calendarFlight_) return false;
        const auto& flight = *calendarFlight_;
        auto context = flight.context;
        const bool source = calendarSourceCurrent();
        if (!source) context = {}; // Revocation, not a replacement native snapshot.
        return calendarJoin_.current(flight.id, context, std::chrono::steady_clock::now());
    }

    bool calendarRetryCurrent() {
        if (!calendarFlight_ || !calendarFlight_->menu) return false;
        if (!calendarSourceCurrent()) { calendarJoin_.cancel(calendarFlight_->id); return false; }
        return calendarJoin_.retryCurrent(calendarFlight_->id, calendarFlight_->context, std::chrono::steady_clock::now());
    }

    void cancelCalendarJoin() {
        if (!calendarFlight_) return;
        calendarJoin_.cancel(calendarFlight_->id);
        calendarLauncher_.cancel(); // Discard only, never SDK Cancel/Close.
        if (calendarDialog_ && !calendarFlight_->hideRequested) {
            calendarFlight_->hideRequested = true;
            try { calendarDialog_.Hide(); } catch (...) {} // Handle/ticket remain owned.
        }
    }

    void publishCalendarResult() {
        if (!calendarFlight_) return;
        const auto result = calendarJoin_.result();
        if (result.state == calendarFlight_->reported.state && result.reason == calendarFlight_->reported.reason) return;
        calendarFlight_->reported = result; // Before a script/dialog/card can reenter.
        if (result.state == graf::windows::CalendarJoinState::failed || result.state == graf::windows::CalendarJoinState::cancelled)
            calendarFlight_->https.clear();
        if (calendarFlight_->document && cabinet_) {
            try { cabinet_->webView().replyCalendarJoin(*calendarFlight_->document, result); }
            catch (...) { cancelCalendarJoin(); }
        } else if (calendarFlight_->native && reminders_ && capture_ &&
            (result.state == graf::windows::CalendarJoinState::failed || result.state == graf::windows::CalendarJoinState::cancelled)) {
            reminders_->failAction(calendarFlight_->native->target, calendarFlight_->native->action,
                result.reason, reminderWallTime(), capture_->indicator().visible);
        }
    }

    void failCalendarJoin(graf::windows::CalendarJoinReason reason) {
        if (!calendarFlight_) return;
        if (calendarFlight_->retryDialog) cancelCalendarJoin(); // Unknown dialog exit retains ticket, revokes Primary.
        if (calendarCurrent())
            (void)calendarJoin_.finish(calendarFlight_->id, graf::windows::CalendarJoinState::failed, reason,
                calendarFlight_->context, std::chrono::steady_clock::now());
        if (calendarDialog_ && !calendarFlight_->hideRequested) {
            calendarFlight_->hideRequested = true;
            try { calendarDialog_.Hide(); } catch (...) {} // Failed old dialog still needs actual drain.
        }
        publishCalendarResult();
    }

    void beginDocumentCalendarJoin(graf::windows::WebView2Host::CalendarJoinRequest request) {
        beginCalendarJoin(std::move(request), std::nullopt);
    }
    void beginNativeCalendarJoin(ReminderIntent intent) {
        beginCalendarJoin(std::nullopt, std::move(intent));
    }
    void beginMenuCalendarJoin(graf::windows::UpcomingMeetingRow row) {
        beginCalendarJoin(std::nullopt, std::nullopt, std::move(row));
    }
    void beginCalendarJoin(std::optional<graf::windows::WebView2Host::CalendarJoinRequest> document,
        std::optional<ReminderIntent> native, std::optional<graf::windows::UpcomingMeetingRow> menu = std::nullopt) {
        using namespace graf::windows;
        const auto deny = [&](CalendarJoinReason reason) {
            if (document && cabinet_) cabinet_->webView().replyCalendarJoin(*document, {CalendarJoinState::cancelled, reason});
            else if (native && reminders_ && capture_) reminders_->failAction(native->target, native->action, reason,
                reminderWallTime(), capture_->indicator().visible);
        };
        if (calendarCalling_ || calendarJoin_.busy() || calendarFlight_ || calendarResolverThread_.joinable()) {
            deny(CalendarJoinReason::busy); return;
        }
        const CustodyMutationScope call(calendarCalling_);
        if (!capture_ || !capture_->currentAccount()) { deny(CalendarJoinReason::notReady); return; }
        CalendarJoinContext context;
        context.origin = DesktopHttpConfig{}.baseOrigin;
        context.owner = capture_->currentAccount()->userId; context.workspace = capture_->currentAccount()->workspaceId;
        context.authGeneration = capture_->authGeneration(); context.sessionToken = capture_->authSessionToken();
        const auto permit = interactionPermit();
        std::string event, request;
        if (document && cabinet_ && cabinet_->webView().calendarJoinCurrent(*document)) {
            context.source = CalendarJoinSource::document; context.sourceEpoch = document->documentGeneration;
            context.sourceIdentity = document->nonce; event = document->intent.eventId; request = document->intent.requestId;
        } else if (native && reminders_) {
            const auto expiry = reminders_->pendingActionExpiry(native->target, native->action, reminderWallTime(), capture_->indicator().visible);
            if (!expiry) { deny(CalendarJoinReason::stale); return; }
            context.source = CalendarJoinSource::nativeAction; context.sourceEpoch = native->target.epoch;
            context.actionExpiresAt = *expiry; request = newSessionId(); context.sourceIdentity = request;
            event = native->target.eventId;
        } else if (menu && reminders_) {
            const auto wallNow = reminderWallTime();
            const auto expiry = MeetingReminderPresenter::upcomingExpiry(menu->event.endsAt, wallNow, std::chrono::steady_clock::now());
            if (!menu->enabled || !expiry || !reminders_->upcomingCurrent(menu->event, menu->epoch, wallNow) ||
                reminders_->epoch() != menu->epoch || reminders_->owner() != context.owner ||
                reminders_->workspace() != context.workspace || reminders_->origin() != context.origin) {
                deny(CalendarJoinReason::stale); return;
            }
            context.source = CalendarJoinSource::nativeAction; context.sourceEpoch = menu->epoch;
            context.actionExpiresAt = *expiry; request = newSessionId(); context.sourceIdentity = request;
            event = menu->event.eventId;
        } else { deny(CalendarJoinReason::notReady); return; }
        if (!calendarAuthCurrent(context, permit.epoch)) { deny(CalendarJoinReason::notReady); return; }
        // All allocating source/context copies precede admission. Moving the
        // prepared flight after begin cannot leave a busy owner without it.
        CalendarFlight flight;
        flight.context = context; flight.interactionEpoch = permit.epoch;
        flight.document = document; flight.native = native; flight.menu = menu;
        const auto ticket = calendarJoin_.begin(event, request, std::move(context), std::chrono::steady_clock::now(), menu.has_value());
        if (!ticket) { deny(CalendarJoinReason::notReady); return; }
        flight.id = ticket->operationId;
        calendarFlight_.emplace(std::move(flight));
        startCalendarResolver(*ticket);
    }

    void startCalendarResolver(const graf::windows::CalendarJoinWork& ticket) {
        using namespace graf::windows;
        calendarFlight_->work = ticket;
        if (!calendarCurrent()) { // No worker was dispatched; drain only this ticket.
            (void)calendarJoin_.complete(ticket, {}, std::chrono::steady_clock::now());
            calendarFlight_->work.reset(); publishCalendarResult(); return;
        }
        try {
            DesktopHttpConfig config;
            config.baseOrigin = calendarFlight_->context.origin; config.workspaceId = calendarFlight_->context.workspace;
            config.sessionToken = calendarFlight_->context.sessionToken; config.confirmedIdentity = capture_->currentAccount();
            config.cancellation = ticket.cancellation;
            std::packaged_task<CalendarJoinResolution()> task([config = std::move(config),
                event = calendarJoin_.eventId(), deadline = ticket.deadline] {
                return DesktopHttpTransport(config).calendarJoinTarget(event, deadline);
            });
            auto future = task.get_future();
            calendarResolverThread_ = std::thread(std::move(task)); // Never detach or capture this.
            calendarResolverFuture_ = std::move(future);
        } catch (...) {
            (void)calendarJoin_.complete(ticket, calendarFlight_->context, std::chrono::steady_clock::now());
            calendarFlight_->work.reset(); failCalendarJoin(CalendarJoinReason::dependencyUnavailable);
        }
    }

    void startCalendarSDK(graf::windows::CalendarJoinWorkKind kind) {
        using namespace graf::windows;
        if (!calendarCurrent()) { publishCalendarResult(); return; }
        const auto ticket = calendarJoin_.work(calendarFlight_->id, kind, calendarFlight_->context, std::chrono::steady_clock::now());
        if (!ticket) return;
        calendarFlight_->work = ticket;
        const auto current = [this] { return calendarCurrent(); };
        const auto result = kind == CalendarJoinWorkKind::query ? calendarLauncher_.query(calendarFlight_->https, current) :
            calendarLauncher_.launch(calendarFlight_->https,
                calendarFlight_->browser ? CalendarLauncherMode::browser : CalendarLauncherMode::native, current);
        if (result == CalendarLauncherStart::started) return;
        if (calendarLauncher_.busy()) { failCalendarJoin(CalendarJoinReason::dependencyUnavailable); return; }
        const bool applicable = calendarJoin_.complete(*ticket, calendarFlight_->context, std::chrono::steady_clock::now());
        calendarFlight_->work.reset();
        if (!applicable || !calendarCurrent()) { publishCalendarResult(); return; }
        if (calendarFlight_->browser) failCalendarJoin(CalendarJoinReason::launchFailed);
        else offerCalendarBrowserRecovery();
    }

    void offerCalendarBrowserRecovery() {
        offerCalendarDialog(false);
    }

    void offerCalendarDialog(bool retry) {
        using namespace graf::windows;
        const auto current = [this, retry] { return retry ? calendarRetryCurrent() : calendarCurrent(); };
        if (!current()) { publishCalendarResult(); return; }
        if (retry) calendarFlight_->retryOffered = true; // One decision per failed attempt, even on rejected dispatch.
        std::optional<CalendarJoinWork> ticket;
        try {
            ticket = retry ? calendarJoin_.retryDialog(calendarFlight_->id, calendarFlight_->context, std::chrono::steady_clock::now()) :
                calendarJoin_.work(calendarFlight_->id, CalendarJoinWorkKind::dialog,
                    calendarFlight_->context, std::chrono::steady_clock::now());
        } catch (...) { cancelCalendarJoin(); return; }
        if (!ticket && retry) cancelCalendarJoin();
        if (!ticket) return;
        calendarFlight_->work = ticket; calendarFlight_->https.clear();
        calendarFlight_->retryDialog = retry;
        calendarFlight_->confirmedAt.reset(); calendarFlight_->hideRequested = false;
        try {
            openMainWindow();
            calendarDialog_ = ContentDialog(); calendarDialog_.XamlRoot(root_.XamlRoot());
            calendarDialog_.RequestedTheme(shellIsDark_ ? ElementTheme::Dark : ElementTheme::Light);
            calendarDialog_.Title(box_value(retry ? L"Не удалось открыть встречу" : L"Не удалось открыть приложение встречи"));
            calendarDialog_.Content(box_value(retry ?
                L"Проверьте подключение и повторите попытку. Если событие изменилось, обновите календарь." :
                L"Открыть встречу в браузере? GRAF заново проверит ссылку."));
            calendarDialog_.PrimaryButtonText(retry ? L"Повторить подключение" : L"Открыть в браузере");
            calendarDialog_.CloseButtonText(L"Отмена");
            calendarDialog_.DefaultButton(ContentDialogButton::Close);
            const auto alive = alive_;
            calendarDialog_.PrimaryButtonClick([this, alive, retry, ticket = *ticket](auto const&, auto const&) {
                if (!alive->load() || calendarCalling_ || !calendarFlight_ || !calendarFlight_->work ||
                    calendarFlight_->work->operationId != ticket.operationId || calendarFlight_->work->workId != ticket.workId ||
                    calendarFlight_->confirmedAt || calendarFlight_->hideRequested) return;
                const CustodyMutationScope call(calendarCalling_);
                if (!(retry ? calendarRetryCurrent() : calendarCurrent())) return;
                const auto click = std::chrono::steady_clock::now(); // Includes later UI dispatch/animation delay.
                if (retry && !calendarJoin_.confirmRetry(ticket, calendarFlight_->context, click)) return;
                calendarFlight_->confirmedAt = click;
            });
            if (!current()) {
                (void)calendarJoin_.complete(*ticket, {}, std::chrono::steady_clock::now());
                calendarFlight_->work.reset(); calendarDialog_ = nullptr; publishCalendarResult(); return;
            }
            calendarDialogOperation_ = calendarDialog_.ShowAsync();
            if (!calendarDialogOperation_) throw std::runtime_error("calendar dialog unavailable");
            if (!current()) { calendarFlight_->hideRequested = false; cancelCalendarJoin(); }
        } catch (...) {
            if (calendarDialogOperation_) { failCalendarJoin(CalendarJoinReason::launchFailed); return; }
            calendarDialog_ = nullptr;
            (void)calendarJoin_.complete(*ticket, calendarFlight_->context, std::chrono::steady_clock::now());
            calendarFlight_->work.reset();
            if (retry) cancelCalendarJoin(); else failCalendarJoin(CalendarJoinReason::launchFailed);
        }
    }

    void pollCalendarJoin() {
        using namespace graf::windows;
        if (!calendarFlight_ || calendarCalling_) return;
        const CustodyMutationScope call(calendarCalling_);
        // current() may itself turn the first deadline tick into a failed
        // attempt. Recheck its fresh menu reservation before revoking Retry.
        if (!calendarCurrent() && !calendarRetryCurrent()) cancelCalendarJoin();
        publishCalendarResult();
        if (calendarFlight_->work) {
            const auto ticket = *calendarFlight_->work;
            if (ticket.kind == CalendarJoinWorkKind::resolver && calendarResolverThread_.joinable()) {
                const auto status = WaitForSingleObject(calendarResolverThread_.native_handle(), 0);
                if (status == WAIT_FAILED) failCalendarJoin(CalendarJoinReason::dependencyUnavailable);
                else if (status == WAIT_OBJECT_0) {
                    // A ready future is not thread exit; the native thread handle
                    // is signalled only after its callable/resources have exited.
                    calendarResolverThread_.join();
                    CalendarJoinResolution result;
                    try { result = calendarResolverFuture_.get(); } catch (...) {}
                    const bool applicable = calendarJoin_.complete(ticket, calendarFlight_->context, std::chrono::steady_clock::now());
                    calendarFlight_->work.reset();
                    if (applicable && calendarCurrent()) {
                        if (result.state != CalendarJoinResolutionState::resolved || !result.target) {
                            const auto reason = result.state == CalendarJoinResolutionState::authRequired ? CalendarJoinReason::authRequired :
                                result.state == CalendarJoinResolutionState::eventUnavailable ? CalendarJoinReason::eventUnavailable :
                                result.state == CalendarJoinResolutionState::invalidTarget ? CalendarJoinReason::invalidTarget :
                                CalendarJoinReason::dependencyUnavailable;
                            failCalendarJoin(reason);
                            if (reason == CalendarJoinReason::authRequired && calendarAuthCurrent(calendarFlight_->context, calendarFlight_->interactionEpoch)) {
                                if (cabinet_) cabinet_->webView().bindUserTimeAccount({}, {}, {}, {}, 0);
                                capture_->setAuthSessionToken({});
                                if (reminders_) reminders_->invalidate();
                                if (cabinet_) (void)cabinet_->open(cabinet_->webView().signInUrl());
                            }
                        } else if (const auto https = CalendarMeetingOpener::validatedHTTPS(result.target->httpsUrl)) {
                            calendarFlight_->https = *https;
                            if (result.authExpiresAt && cabinet_) cabinet_->webView().extendAuthCookieExpiry(calendarFlight_->context.sessionToken, *result.authExpiresAt);
                            if (calendarJoin_.result().state == CalendarJoinState::resolving)
                                (void)calendarJoin_.opening(calendarFlight_->id, calendarFlight_->context, std::chrono::steady_clock::now());
                            publishCalendarResult();
                            if (calendarCurrent()) {
                                if (!CalendarMeetingOpener::nativeTarget(*https)) calendarFlight_->browser = true;
                                startCalendarSDK(calendarFlight_->browser ? CalendarJoinWorkKind::launch : CalendarJoinWorkKind::query);
                            }
                        } else failCalendarJoin(CalendarJoinReason::invalidTarget);
                    }
                }
            } else if (ticket.kind == CalendarJoinWorkKind::query || ticket.kind == CalendarJoinWorkKind::launch) {
                const auto result = calendarLauncher_.poll();
                if (result.state == CalendarLauncherPollState::indeterminate) failCalendarJoin(CalendarJoinReason::dependencyUnavailable);
                else if (result.state == CalendarLauncherPollState::completed) {
                    const bool applicable = calendarJoin_.complete(ticket, calendarFlight_->context, std::chrono::steady_clock::now());
                    calendarFlight_->work.reset();
                    if (applicable && calendarCurrent()) {
                        if (ticket.kind == CalendarJoinWorkKind::query) {
                            if (result.outcome == CalendarLauncherOutcome::available) startCalendarSDK(CalendarJoinWorkKind::launch);
                            else if (result.outcome == CalendarLauncherOutcome::appNotInstalled) {
                                calendarFlight_->browser = true; startCalendarSDK(CalendarJoinWorkKind::launch);
                            } else offerCalendarBrowserRecovery();
                        } else if (result.outcome == CalendarLauncherOutcome::launched) {
                            const auto context = calendarFlight_->context;
                            const auto epoch = calendarFlight_->interactionEpoch;
                            const auto intent = calendarFlight_->native;
                            if (calendarJoin_.finish(calendarFlight_->id, CalendarJoinState::handedOff, CalendarJoinReason::none,
                                context, std::chrono::steady_clock::now())) {
                                if (intent && reminders_ && capture_ && reminders_->completeAction(intent->target, intent->action,
                                    reminderWallTime(), capture_->indicator().visible) && intent->action == NoticeAction::joinAndRecord) {
                                    recordCapture([this, context, epoch, target = intent->target] {
                                        return calendarAuthCurrent(context, epoch) && reminders_ && capture_ &&
                                            reminders_->handoffRecordingCurrent(target, reminderWallTime(), capture_->indicator().visible) &&
                                            std::chrono::steady_clock::now() < context.actionExpiresAt;
                                    });
                                }
                                publishCalendarResult();
                            }
                        } else if (calendarFlight_->browser) failCalendarJoin(CalendarJoinReason::launchFailed);
                        else offerCalendarBrowserRecovery();
                    }
                }
            } else if (ticket.kind == CalendarJoinWorkKind::dialog && calendarDialogOperation_) {
                try {
                    const auto status = calendarDialogOperation_.Status();
                    if (status == winrt::Windows::Foundation::AsyncStatus::Completed || status == winrt::Windows::Foundation::AsyncStatus::Error) {
                        auto result = ContentDialogResult::None;
                        try { if (status == winrt::Windows::Foundation::AsyncStatus::Completed) result = calendarDialogOperation_.GetResults(); } catch (...) {}
                        calendarDialogOperation_ = nullptr; calendarDialog_ = nullptr;
                        const bool applicable = calendarJoin_.complete(ticket, calendarFlight_->context, std::chrono::steady_clock::now());
                        calendarFlight_->work.reset();
                        if (calendarFlight_->retryDialog) {
                            if (result == ContentDialogResult::Primary && calendarFlight_->confirmedAt &&
                                !calendarFlight_->hideRequested && calendarRetryCurrent()) {
                                const auto resolver = calendarJoin_.retry(calendarFlight_->id, newSessionId(),
                                    calendarFlight_->context, std::chrono::steady_clock::now());
                                if (resolver) {
                                    calendarFlight_->id = resolver->operationId;
                                    calendarFlight_->browser = false; calendarFlight_->retryDialog = false;
                                    calendarFlight_->retryOffered = false; calendarFlight_->hideRequested = false;
                                    calendarFlight_->confirmedAt.reset(); calendarFlight_->https.clear();
                                    publishCalendarResult();
                                    startCalendarResolver(*resolver);
                                } else cancelCalendarJoin();
                            } else cancelCalendarJoin();
                        } else if (applicable && calendarCurrent()) {
                            if (result == ContentDialogResult::Primary && calendarFlight_->confirmedAt) {
                                const auto resolver = calendarJoin_.recover(calendarFlight_->id, calendarFlight_->context, *calendarFlight_->confirmedAt);
                                calendarFlight_->browser = true;
                                if (resolver) startCalendarResolver(*resolver);
                            } else cancelCalendarJoin();
                        }
                    } else if (status != winrt::Windows::Foundation::AsyncStatus::Started) failCalendarJoin(CalendarJoinReason::dependencyUnavailable);
                } catch (...) { failCalendarJoin(CalendarJoinReason::dependencyUnavailable); } // Unknown drain: retain owned handle/ticket.
            }
        }
        publishCalendarResult();
        if (calendarJoin_.result().state == CalendarJoinState::failed && calendarFlight_->menu &&
            !calendarFlight_->retryOffered && !calendarFlight_->work && !calendarResolverThread_.joinable() &&
            !calendarLauncher_.busy() && !calendarDialogOperation_ && calendarRetryCurrent())
            offerCalendarDialog(true); // Actual old drain precedes new owned failure UI.
        if (!calendarJoin_.busy() && !calendarResolverThread_.joinable() && !calendarLauncher_.busy() && !calendarDialogOperation_)
            calendarFlight_.reset();
    }

    void refreshMeetingReminders() {
        if (!reminders_ || !capture_ || shuttingDown_ || capture_->updateAdmissionBlocked()) return;
        const auto generation = capture_->authGeneration();
        const auto now = GetTickCount64();
        if (reminderRejectedGeneration_ && *reminderRejectedGeneration_ == generation &&
            lastReminderRequest_ && now - lastReminderRequest_ < 30000) return;
        reminderRejectedGeneration_.reset();
        const auto account = capture_->currentAccount();
        if (!account) {
            if (!reminders_->owner().empty()) reminders_->invalidate();
            refreshLocalNotificationSettings();
            return;
        }
        reminders_->bind(account->userId, account->workspaceId, graf::windows::DesktopHttpConfig{}.baseOrigin);
        refreshLocalNotificationSettings();
        if (!interactionPermit().allowed) return;
        if (reminderFuture_.valid() && reminderFuture_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            graf::windows::CalendarReminderResponse response;
            try { response = reminderFuture_.get(); } catch (...) {}
            const auto intent = reminderFlightAction_; reminderFlightAction_.reset();
            const auto request = std::move(reminderRequestIdentity_);
            reminderRequestIdentity_ = {};
            if (request.matches(capture_->authGeneration(), reminders_->epoch(), capture_->authSessionToken()) &&
                (!reminderCancellation_ || !reminderCancellation_->load())) {
                if (const auto expiry = response.renewedSessionExpiry(static_cast<std::int64_t>(reminderWallTime()));
                    expiry && cabinet_) cabinet_->webView().extendAuthCookieExpiry(request.sessionToken, *expiry);
                if (response.snapshot && reminders_->update(std::move(*response.snapshot), request.epoch)) {
                    if (intent) {
                        if (intent->action == graf::windows::NoticeAction::record &&
                            reminders_->completeAction(intent->target, intent->action, reminderWallTime(), capture_->indicator().visible)) recordCapture();
                        else localActionNotice_ = L"Встреча изменилась или запись уже идёт. Проверьте календарь GRAF.";
                    }
                } else {
                    reminders_->calendarFailed();
                    if (intent) localActionNotice_ = L"Не удалось подтвердить встречу. Проверьте подключение и календарь GRAF.";
                    if (response.status == 401 || response.status == 403) {
                        reminders_->invalidate(); reminderRejectedGeneration_ = generation;
                        pendingReminderAction_.reset(); return;
                    }
                }
            }
        }
        if (!reminderFuture_.valid() && (!lastReminderRequest_ || now - lastReminderRequest_ >= 30000 || pendingReminderAction_)) {
            lastReminderRequest_ = now;
            graf::windows::DesktopHttpConfig config;
            config.sessionToken = capture_->authSessionToken(); config.workspaceId = account->workspaceId;
            config.confirmedIdentity = account;
            config.scopedAccount = graf::windows::DeletionScope{account->userId, account->workspaceId};
            reminderCancellation_ = std::make_shared<std::atomic_bool>(false); config.cancellation = reminderCancellation_;
            reminderRequestIdentity_ = {generation, reminders_->epoch(), config.sessionToken};
            reminderFlightAction_ = pendingReminderAction_; pendingReminderAction_.reset();
            std::packaged_task<graf::windows::CalendarReminderResponse()> task([config = std::move(config)] {
                const auto response = graf::windows::DesktopHttpTransport(config).notificationContext(*config.scopedAccount);
                const auto context = response.accepted() ? graf::windows::DesktopApiClient::decodeNotificationContext(response.body) : std::nullopt;
                if (!context || context->userId != config.confirmedIdentity->userId || context->workspaceId != config.workspaceId)
                    return graf::windows::CalendarReminderResponse{response.status, std::nullopt};
                auto result = graf::windows::DesktopApiClient::calendarReminders(config);
                result.inheritAuthExpiry(response.authExpiresAt);
                return result;
            });
            try { auto future = task.get_future(); std::thread(std::move(task)).detach(); reminderFuture_ = std::move(future); }
            catch (...) { reminders_->calendarFailed(); reminderFlightAction_.reset(); reminderRequestIdentity_ = {}; }
        }
        reminders_->reconcile(reminderWallTime(), std::chrono::steady_clock::now(), capture_->indicator().visible);
    }

    void refreshNativeState() {
        pollCalendarJoin(); // Drain never depends on interactionPermit/account/admission.
        if (!capture_ || shuttingDown_) return;
        refreshUpdateWindow();
        if (exitRequested_) {
            capture_->pollHealth();
            if (shellExitJobsDrained()) capture_->shutdown();
            capture_->pollUploads(); // Drain ACK/cancelled work even though new actions are closed.
            pollLocalRecordingRemoval();
            pollDeletionSelection();
            if (exitWorkDrained()) window_.Close();
            return;
        }
        const CustodyMutationScope mutation(shellMutations_);
        refreshNotificationInteraction(); // before workers or any card can accept an old decision
        if (announcedAppearance_ == "system" && systemThemeIsDark() != shellIsDark_)
            applyCabinetAppearance("system");
        applyPendingActivation();
        if (!capture_->updateAdmissionBlocked() && attribution_ && capture_->currentAccount() &&
            attributionAccountGeneration_ != capture_->authGeneration()) {
            // Only a server-confirmed account marks the optional attribution.
            // Record an attempt per generation; failed analytics storage never
            // retries on every UI tick or blocks the connected account.
            attributionAccountGeneration_ = capture_->authGeneration();
            try { (void)attribution_->markAccountConnected(attributionNow()); } catch (...) {}
        }
        capture_->pollHealth();
        capture_->tickNotice();
        if (capture_->indicator().state == graf::windows::SessionState::recording && recordingStartedAt_ == 0) {
            recordingStartedAt_ = GetTickCount64();
        }
        refreshShellPalette(shellIsDark_);
        if (cabinet_) {
            backButton_.IsEnabled(cabinet_->webView().canGoBack());
            forwardButton_.IsEnabled(cabinet_->webView().canGoForward());
        }
        const auto now = GetTickCount64();
        if (lastStateTick_ && now - lastStateTick_ > 5000) capture_->recover(graf::windows::RecoveryTrigger::wake);
        lastStateTick_ = now;
        // The ordinary cadence, held back while the server is asking for a pause:
        // a 429 answered with Retry-After must not be followed by a retry the
        // server already refused.
        if (now - lastUploadRecovery_ >= 30000 && capture_->uploadDeferralRemainingMs() == 0) {
            capture_->recover(graf::windows::RecoveryTrigger::scheduled);
            lastUploadRecovery_ = now;
        }
        // The server asks this device to remove the local copies of a meeting it
        // deleted. The pass runs at most once a minute, and only while nothing else
        // owns the files.
        if (now - lastLocalPurge_ >= 60000) {
            lastLocalPurge_ = now;
            startLocalPurgePass();
        }
        capture_->pollUploads();
        pollLocalRecordingSend();
        pollLocalRecordingRemoval();
        pollDeletionSelection();
        updateLocalRecordings();
        pollLocalPlayback();
        if (now - lastReadinessCheck_ >= 2000) {
            capture_->refreshReadiness();
            lastReadinessCheck_ = now;
        }
        capture_->refreshPermission();
        refreshAutomaticRecording();
        bindNotificationContext();
        reconcileRecordingProblems();
        refreshSelectedRecording();
        if (interactionPermit().allowed)
            (void)capture_->notificationCard().presentPendingShort(std::chrono::steady_clock::now());
        refreshMeetingReminders();
        if (localActionNotice_ != previousLocalActionNotice_) {
            previousLocalActionNotice_ = localActionNotice_;
            attentionExpansionDismissed_ = false;
        }
        const bool drainTimeout = capture_->indicator().state == graf::windows::SessionState::stopping &&
            capture_->indicator().reason == graf::windows::ReasonCode::finalizationFailed;
        if (drainTimeout && !lastDrainTimeout_) attentionExpansionDismissed_ = false;
        lastDrainTimeout_ = drainTimeout;
        if (!hasInspectorAttention()) attentionExpansionDismissed_ = false;
        const auto& snapshot = capture_->indicator();
        const bool active = snapshot.visible;
        const auto& finalization = capture_->finalization();
        diagnosticsButton_.Visibility(!active && !capture_->diagnostics().empty() ? Visibility::Visible : Visibility::Collapsed);
        std::wstring outcome;
        if (snapshot.state == graf::windows::SessionState::stopping &&
            snapshot.reason == graf::windows::ReasonCode::finalizationFailed) {
            outcome = L"Не удалось завершить запись за 5 секунд. Ожидаем безопасного завершения обработки.";
        } else if (snapshot.state == graf::windows::SessionState::failed) {
            // Причина называется прямо: отказ в доступе к микрофону, отключённое
            // устройство и нехватка места требуют разных действий человека.
            outcome = graf::windows::recordingFailureText(
                graf::windows::effectiveFailureReason(snapshot.reason, capture_->microphonePermissionGranted()),
                finalization.trustedPrefixRetained);
        }
        else if (snapshot.state == graf::windows::SessionState::savedLocal) outcome = L"Запись сохранена на этом компьютере.";
        if (!localActionNotice_.empty()) {
            if (!outcome.empty()) outcome += L"\n";
            outcome += localActionNotice_;
        }
        captureOutcomeText_.Text(outcome);
        captureOutcomeText_.Visibility(outcome.empty() ? Visibility::Collapsed : Visibility::Visible);
        updateMicrophoneChoices();
        microphonePicker_.IsEnabled(!active);
        microphoneSourceText_.Text(microphoneSettingError_.empty() ? capture_->sourceSummary() : microphoneSettingError_);
        privacyNotice_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
        if (recordingStripRow_) {
            recordingStripRow_.Height(GridLengthHelper::FromValueAndType(
                active ? 44.0 : 0.0, GridUnitType::Pixel));
        }
        const bool permissionMissing = !capture_->microphonePermissionGranted();
        captureStatus_.Text(winrt::to_hstring(snapshot.statusText));
        const bool paused = snapshot.state == graf::windows::SessionState::paused;
        const auto privacySummary = capture_->privacyActionSummary();
        readinessText_.Text(active && !privacySummary.empty() ? privacySummary : active ? (paused ? L"Микрофон на паузе. Системный звук продолжает записываться."
                                                             : L"Общий системный звук и локальный микрофон")
                                   : capture_->readinessSummary());
        recordButton_.Visibility(active ? Visibility::Collapsed : Visibility::Visible);
        recordButton_.IsEnabled(canStartRecording());
        permissionButton_.Visibility(!active && permissionMissing ? Visibility::Visible : Visibility::Collapsed);
        custodyStatus_.Text(capture_->custodySummary());
        recordingStrip_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
        recordingStripText_.Text(winrt::to_hstring(snapshot.statusText +
            (paused ? " · Микрофон на паузе"
                    : " · Системный звук и микрофон")));
        if (active && recordingStartedAt_ != 0) {
            const auto seconds = (GetTickCount64() - recordingStartedAt_) / 1000;
            const auto timer = std::to_wstring(seconds / 60) + L":" + (seconds % 60 < 10 ? L"0" : L"") + std::to_wstring(seconds % 60);
            recordingStripText_.Text(std::wstring(recordingStripText_.Text().c_str()) + L" · " + timer);
        }
        setAccessible(recordingStripText_, std::wstring(recordingStripText_.Text().c_str()));
        if (active && !recordingIndicatorAvailable() && !ensureRecordingIndicator()) {
            // A failed background surface must not hide the remaining native
            // Stop. Do not stop capture or activate the meeting's foreground.
            window_.AppWindow().Show(false);
            if (mainWindowHandle_ && IsIconic(mainWindowHandle_)) ShowWindow(mainWindowHandle_, SW_SHOWNOACTIVATE);
        }
        if (indicatorWindow_) {
            indicatorText_.Text(recordingStripText_.Text());
            setAccessible(indicatorText_, std::wstring(recordingStripText_.Text().c_str()));
            if (active && !indicatorWindow_.AppWindow().IsVisible()) indicatorWindow_.AppWindow().Show(false);
            else if (!active && indicatorWindow_.AppWindow().IsVisible()) indicatorWindow_.AppWindow().Hide();
        }
        setAccessible(captureStatus_, std::wstring(captureStatus_.Text().c_str()));
        setAccessible(compactStatus_, L"Статус записи: " + std::wstring(captureStatus_.Text().c_str()));
        compactStatus_.Symbol(paused ? Symbol::Pause : snapshot.state == graf::windows::SessionState::degraded ? Symbol::Important : Symbol::Microphone);
        recordingStripStop_.IsEnabled(active);
        if (tray_) {
            tray_->setState(snapshot, canStartRecording(), exitRequested_, capture_->privacyPending());
            tray_->setTheme(shellIsDark_);
            const auto upcoming = reminders_ ? reminders_->upcoming() : std::nullopt;
            const auto& zone = cabinet_ ? cabinet_->webView().preferredUserTimeZone() : std::string{};
            tray_->setCalendarState(reminders_ ? reminders_->upcomingRows(reminderWallTime(), zone) : std::nullopt,
                capture_->authGeneration(), cabinet_ ? cabinet_->webView().userTimeRevision() : 0,
                upcoming && upcoming->showUpcomingTime, upcoming && upcoming->showUpcomingTitle);
            std::vector<std::wstring> history;
            const auto& entries = capture_->notificationCard().history();
            for (const auto& entry : entries) {
                const auto instant = std::chrono::system_clock::to_time_t(entry.occurredAt);
                std::tm local{};
                wchar_t time[32]{};
                if (localtime_s(&local, &instant) == 0) std::wcsftime(time, 32, L"%H:%M", &local);
                history.push_back(std::wstring(time) + L" — " +
                    std::wstring(graf::windows::RecordingNoticePresenter::historyMessage(entry.kind)));
            }
            tray_->setNotificationState(capture_->notificationCard().visible(), std::move(history));
        }
        refreshTrayAvailability();
        pauseButton_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
        stopButton_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
        if (meters_) {
            meters_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
            if (active) {
                const auto levels = capture_->audioLevels();
                updateMeter(microphoneMeter_, microphoneMeterFill_, paused ? 0.0F : levels.microphone);
                updateMeter(systemRenderMeter_, systemRenderMeterFill_, levels.systemRender);
            } else {
                updateMeter(microphoneMeter_, microphoneMeterFill_, 0.0F);
                updateMeter(systemRenderMeter_, systemRenderMeterFill_, 0.0F);
            }
        }
        if (active) pauseButton_.Content(box_value(capture_->privacyPending() ? L"Подождите…" :
            snapshot.state == graf::windows::SessionState::paused ? L"Продолжить" : L"Пауза"));
        pauseButton_.IsEnabled(!capture_->privacyPending() && (snapshot.state == graf::windows::SessionState::recording || paused));
        setAccessible(pauseButton_, paused ? L"Продолжить запись локального микрофона" : L"Поставить локальный микрофон на паузу");
        if (compactRecordButton_) compactRecordButton_.IsEnabled(canStartRecording());
        if (compactRecordButton_) compactRecordButton_.Visibility(active ? Visibility::Collapsed : Visibility::Visible);
        if (compactAttentionButton_) {
            compactAttentionButton_.Visibility(hasInspectorAttention() ? Visibility::Visible : Visibility::Collapsed);
        }
        updateInspectorVisibility();
    }

    static void updateMeter(Grid const& track, Border const& fill, float level) {
        if (!track || !fill) return;
        const auto bounded = std::max(0.0F, std::min(1.0F, level));
        fill.Width(track.ActualWidth() * bounded);
    }

    void updateMicrophoneChoices() {
        std::string key = capture_->selectedMicrophone();
        for (const auto& input : capture_->microphones()) key += "\n" + input.stableId + "\n" + input.friendlyName;
        if (key == microphoneChoicesKey_ && microphonePicker_.Items().Size() != 0) return;
        updatingMicrophonePicker_ = true;
        microphonePicker_.Items().Clear();
        auto add = [this](std::wstring label, const std::string& identity) {
            ComboBoxItem item;
            item.Content(box_value(label));
            item.Tag(box_value(winrt::to_hstring(identity)));
            microphonePicker_.Items().Append(item);
        };
        add(L"По умолчанию Windows", {});
        int selected = 0;
        for (const auto& input : capture_->microphones()) {
            add(deviceDisplayName(input.friendlyName), input.stableId);
            if (input.stableId == capture_->selectedMicrophone()) selected = static_cast<int>(microphonePicker_.Items().Size()) - 1;
        }
        if (!capture_->selectedMicrophone().empty() && selected == 0) {
            add(L"Выбранный микрофон недоступен", capture_->selectedMicrophone());
            selected = static_cast<int>(microphonePicker_.Items().Size()) - 1;
        }
        microphonePicker_.SelectedIndex(selected);
        microphoneChoicesKey_ = std::move(key);
        updatingMicrophonePicker_ = false;
    }

    Window window_{nullptr};
    Window indicatorWindow_{nullptr};
    TextBlock indicatorText_{nullptr};
    Button indicatorStop_{nullptr};
    winrt::Microsoft::UI::Xaml::XamlTypeInfo::XamlControlsXamlMetaDataProvider xamlMetadata_;
    Grid root_{nullptr};
    RowDefinition recordingStripRow_{nullptr};
    Grid content_{nullptr};
    Grid meetingsSurface_{nullptr};
    WebView2 webView_{nullptr};
    Button backButton_{nullptr};
    Button forwardButton_{nullptr};
    Border expandedInspector_{nullptr};
    Border compactInspector_{nullptr};
    ColumnDefinition inspectorColumn_{nullptr};
    Button inspectorToggle_{nullptr};
    Button expandedInspectorToggle_{nullptr};
    SymbolIcon compactStatus_{nullptr};
    Button compactRecordButton_{nullptr};
    Button compactAttentionButton_{nullptr};
    Border recordingStrip_{nullptr};
    TextBlock recordingStripText_{nullptr};
    Button recordingStripStop_{nullptr};
    TextBlock custodyStatus_{nullptr};
    ContentControl selectedRecordingPanel_{nullptr};
    TextBlock selectedRecordingStatus_{nullptr};
    Button selectedLocalRemovalButton_{nullptr};
    std::uint64_t selectedRecordingRevision_ = 0;
    std::optional<ProblemTarget> selectedRecording_, presentedProblem_;
    std::vector<ProblemTarget> pendingProblems_; // at most 256, current context only
    graf::windows::NotificationPreferenceStore problemStore_ = graf::windows::NotificationPreferenceStore::native();
    std::uint64_t problemContextEpoch_ = 0, problemAuthGeneration_ = 0;
    std::string selectedRecordingDisplayKey_;
    std::string selectedLocalRecordingId_;
    Window settingsWindow_{nullptr};
    struct PlaybackRequest {
        graf::windows::WebView2Host::LocalRecordingRequest request;
        std::uint64_t epoch = 0;
    };
    std::optional<PlaybackRequest> pendingPlayback_, playbackRequest_;
    struct PendingLocalAction {
        std::variant<graf::windows::WebView2Host::LocalRecordingRequest, ProblemTarget> source;
        std::uint64_t epoch = 0, ticket = 0;
        std::uint64_t selectionRevision = 0;
    };
    static_assert(std::is_nothrow_move_constructible_v<PendingLocalAction> && std::is_nothrow_move_assignable_v<PendingLocalAction>);
    std::optional<PendingLocalAction> pendingManualSend_, pendingLocalRemoval_;
    Window playbackWindow_{nullptr};
    StackPanel playbackPanel_{nullptr};
    TextBlock playbackStatus_{nullptr}, playbackTime_{nullptr};
    Button playbackButton_{nullptr};
    Slider playbackSeek_{nullptr};
    std::uint64_t playbackWindowGeneration_ = 0;
    bool playbackAuthorized_ = false, updatingPlaybackSeek_ = false;
    DispatcherQueueTimer stateTimer_{nullptr};
    std::unique_ptr<graf::windows::WindowsTray> tray_;
    HWND mainWindowHandle_ = nullptr;
    bool permissionDialogOpen_ = false;
    bool inspectorExpanded_ = false;
    bool attentionExpansionDismissed_ = false;
    Border localFallback_{nullptr};
    bool webViewAttached_ = false;
    TextBlock captureStatus_{nullptr};
    TextBlock captureOutcomeText_{nullptr};
    ULONGLONG recordingStartedAt_ = 0;
    TextBlock readinessText_{nullptr};
    Button diagnosticsButton_{nullptr};
    ComboBox microphonePicker_{nullptr};
    TextBlock microphoneSourceText_{nullptr};
    TextBlock privacyNotice_{nullptr};
    std::string microphoneChoicesKey_;
    std::wstring microphoneSettingError_;
    bool updatingMicrophonePicker_ = false;
    ULONGLONG lastReadinessCheck_ = 0;
    StackPanel meters_{nullptr};
    Grid microphoneMeter_{nullptr};
    Border microphoneMeterFill_{nullptr};
    Grid systemRenderMeter_{nullptr};
    Border systemRenderMeterFill_{nullptr};
    Button permissionButton_{nullptr};
    TextBlock runtimeText_{nullptr};
    TextBlock trayFailureText_{nullptr};
    TextBlock fallbackCabinetTitle_{nullptr};
    TextBlock fallbackCabinetDetail_{nullptr};
    Button fallbackCabinetAction_{nullptr};
    TextBlock autoRecordDetail_{nullptr};
    Button recordButton_{nullptr};
    Button pauseButton_{nullptr};
    Button stopButton_{nullptr};
    std::unique_ptr<NativeCapture> capture_;
    std::unique_ptr<graf::windows::ProductAttributionHandoffStore> attribution_;
    std::optional<std::uint64_t> attributionAccountGeneration_;
    bool attributionSignInRequested_ = false;
    bool lastDrainTimeout_ = false;
    std::unique_ptr<graf::windows::MeetingReminderPresenter> reminders_;
    std::vector<std::pair<std::string, CheckBox>> localNotificationToggles_;
    ComboBox localNotificationOffset_{nullptr};
    Button localNotificationTest_{nullptr};
    TextBlock localNotificationStatus_{nullptr};
    bool updatingLocalNotifications_ = false;
    std::uint64_t localNotificationEpoch_ = 0;
    std::uint64_t notificationInteractionEpoch_ = 0;
    bool notificationInteractionAllowed_ = false;
    struct CalendarFlight {
        std::uint64_t id = 0, interactionEpoch = 0;
        graf::windows::CalendarJoinContext context;
        std::optional<graf::windows::WebView2Host::CalendarJoinRequest> document;
        std::optional<ReminderIntent> native;
        std::optional<graf::windows::UpcomingMeetingRow> menu;
        std::optional<graf::windows::CalendarJoinWork> work;
        std::string https;
        bool browser = false;
        bool hideRequested = false;
        bool retryDialog = false, retryOffered = false;
        std::optional<std::chrono::steady_clock::time_point> confirmedAt;
        graf::windows::CalendarJoinResult reported{graf::windows::CalendarJoinState::resolving};
    };
    graf::windows::CalendarJoinOperation calendarJoin_;
    graf::windows::CalendarNativeLauncher calendarLauncher_;
    std::optional<CalendarFlight> calendarFlight_;
    std::thread calendarResolverThread_;
    std::future<graf::windows::CalendarJoinResolution> calendarResolverFuture_;
    ContentDialog calendarDialog_{nullptr};
    winrt::Windows::Foundation::IAsyncOperation<ContentDialogResult> calendarDialogOperation_{nullptr};
    std::size_t calendarCalling_ = 0;
    std::optional<ReminderIntent> pendingReminderAction_, reminderFlightAction_;
    std::future<graf::windows::CalendarReminderResponse> reminderFuture_;
    std::shared_ptr<std::atomic_bool> reminderCancellation_;
    graf::windows::ReminderRequestIdentity reminderRequestIdentity_;
    std::optional<std::uint64_t> reminderRejectedGeneration_;
    ULONGLONG lastReminderRequest_ = 0;
    std::unique_ptr<graf::windows::CabinetWindow> cabinet_;
    std::shared_ptr<std::atomic_bool> alive_ = std::make_shared<std::atomic_bool>(true);
    std::wstring localActionNotice_;
    std::wstring previousLocalActionNotice_;
    bool localActionDialogOpen_ = false;
    graf::windows::WindowsAppUpdateController appUpdate_;
    Window updateWindow_{nullptr};
    StackPanel updateContent_{nullptr};
    TextBlock updateDetail_{nullptr};
    Button updateCheckButton_{nullptr};
    Button updateInstallButton_{nullptr};
    Button updateCancelButton_{nullptr};
    std::size_t shellMutations_ = 0;
    bool updateBadgeVisible_ = false;
    bool shuttingDown_ = false;
    ULONGLONG lastStateTick_ = 0;
    bool exitRequested_ = false;
    Button trayExitButton_{nullptr};
    ULONGLONG lastUploadRecovery_ = 0;
    // The appearance the cabinet asked for. The app starts with the system one,
    // which is what macOS shows before the page announces its own.
    // Объявление кабинета как есть и решённая тема: «system» — это не тема, а
    // указание спросить систему.
    std::string announcedAppearance_ = "system";
    bool shellIsDark_ = true;
    bool mainWindowSized_ = false;
    Grid settingsContent_{nullptr};
    StackPanel indicatorPanel_{nullptr};
    std::size_t deletionSelectionsInFlight_ = 0;
    graf::windows::CustodyString deletionRequestId_;
    std::uint64_t deletionDocumentGeneration_ = 0, deletionJobId_ = 0;
    std::optional<graf::windows::NativeCapture::DeletionCompletion> deletionReply_;
    std::size_t deletionReplyCalling_ = 0;
    ULONGLONG lastLocalPurge_ = 0;
    graf::windows::VerifiedTargetRegistry verifiedTargets_{graf::windows::VerifiedTargetRegistry::bundled()};
    graf::windows::AutomaticRecordingPolicy automaticPolicy_{verifiedTargets_};
    bool rememberAutomaticChoice_ = false;
    std::string automaticPromptId_;
    ComboBox bulkAutomaticPreference_{nullptr};
    TextBlock automaticSettingsError_{nullptr};
    std::vector<std::pair<graf::windows::VerifiedTargetIdentity, ComboBox>> automaticPreferencePickers_;
    bool updatingAutomaticPreferences_ = false;
    bool automaticPreferenceError_ = false;
    graf::windows::TargetDetectionSnapshot detectionSnapshot_;
    std::future<graf::windows::TargetDetectionSnapshot> detectionFuture_;
    graf::windows::DetectionClock::time_point lastDetectionRequest_{};
    graf::windows::DetectionClock::time_point detectionNotBefore_{};
    std::string automaticPromptTargetKey_;
    std::uint64_t automaticPromptGeneration_ = 0;
};

} // namespace

namespace {

int verifyAudioBackendForInstalledPackage() noexcept {
    UINT32 packageFullNameLength = 0;
    if (GetCurrentPackageFullName(&packageFullNameLength, nullptr) != ERROR_INSUFFICIENT_BUFFER) {
        return 2;
    }
    try {
        const auto processor = graf::windows::GrafAEC3WebRtcAdapter::create();
        // Distinct success code prevents an old executable's normal/mutex
        // exit (0) from being mistaken for execution of this self-check.
        return processor && processor->ready() ? 73 : 2;
    } catch (...) {
        return 2;
    }
}

} // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    // Local package verification: no devices, UI, profile, files or network.
    // create() executes the real reverse-before-microphone 10 ms self-check.
    // Check the process command line and MSIX launch payload; packaged shell
    // activation may provide arguments outside GetCommandLineW().
    int argumentCount = 0;
    auto arguments = CommandLineToArgvW(GetCommandLineW(), &argumentCount);
    if (!arguments) return 2;
    const bool verifyAudioBackend = argumentCount == 2 &&
        std::wstring_view(arguments[1]) == L"--verify-audio-backend";
    LocalFree(arguments);
    if (verifyAudioBackend) {
        return verifyAudioBackendForInstalledPackage();
    }
    try {
        winrt::init_apartment(winrt::apartment_type::single_threaded);
        using winrt::Microsoft::Windows::AppLifecycle::AppInstance;
        const auto current = AppInstance::GetCurrent();
        const auto activation = current.GetActivatedEventArgs();
        if (activation.Kind() == winrt::Microsoft::Windows::AppLifecycle::ExtendedActivationKind::Launch) {
            const auto launch = activation.Data().try_as<
                winrt::Windows::ApplicationModel::Activation::ILaunchActivatedEventArgs>();
            if (launch && launch.Arguments() == L"--verify-audio-backend") {
                return verifyAudioBackendForInstalledPackage();
            }
        }
        // Seed the cold event and subscribe before publishing this instance.
        // A newer redirected handoff must never be overwritten by the cold one.
        receiveActivation(activation);
        const auto token = current.Activated([](auto const&, auto const& args) { receiveActivation(args); });
        const auto instance = AppInstance::FindOrRegisterForKey(L"GRAF.Windows.Desktop");
        if (!instance.IsCurrent()) {
            current.Activated(token);
            redirectActivation(instance, activation);
            return 0;
        }
        winrt::Microsoft::UI::Xaml::Application::Start([](auto&&) {
            winrt::make<GrafApp>();
        });
        current.Activated(token);
        return 0;
    } catch (const winrt::hresult_error& error) {
        MessageBoxW(nullptr, error.message().c_str(), L"GRAF startup error", MB_OK | MB_ICONERROR);
        return static_cast<int>(error.code().value);
    } catch (...) {
        MessageBoxW(nullptr, L"Unknown GRAF startup error", L"GRAF startup error", MB_OK | MB_ICONERROR);
        return 1;
    }
}

#else

int main() { return 0; }

#endif
