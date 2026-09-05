#ifdef _WIN32

#include "Audio/RecordingAudioTimeline.h"
#include "Audio/WasapiEndpointEnumerator.h"
#include "Capture/WindowsCaptureSessionController.h"
#include "Permissions/WindowsReadinessGate.h"
#include "Recording/V5LocalRecordingWriter.h"
#include "MeetingDetection/AutomaticRecordingPolicy.h"
#include "MeetingDetection/VerifiedTargetRegistry.h"
#include "Permissions/WindowsPermissionRecovery.h"
#include "Shell/CabinetWindow.h"
#include "Shell/CustodyStatusProjection.h"
#include "Shell/WindowsTray.h"
#include "Upload/DesktopUploadQueueService.h"
#include "Upload/DesktopUploadRecoveryScheduler.h"
#include "Upload/DesktopHttpTransport.h"
#include "../Native/GrafAEC3/GrafAEC3WebRtcAdapter.h"

#include <windows.h>
#include <knownfolders.h>
#include <appmodel.h>
#include <combaseapi.h>
#include <shlobj.h>
#include <shellapi.h>
#include <winreg.h>

#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Xaml.Controls.Primitives.h>
#include <winrt/Microsoft.UI.Xaml.Automation.h>
#include <winrt/Microsoft.UI.Xaml.Media.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#include <winrt/Microsoft.UI.Windowing.h>
#include <winrt/Windows.ApplicationModel.Activation.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Graphics.h>
#include <winrt/Windows.UI.h>
#include <winrt/Windows.UI.Text.h>
#include <microsoft.ui.xaml.window.h>

#include <mfapi.h>
#include <mftransform.h>

#include <filesystem>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <iterator>
#include <memory>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {

using namespace winrt;
using namespace winrt::Microsoft::UI::Xaml;
using namespace winrt::Microsoft::UI::Xaml::Controls;
using namespace winrt::Microsoft::UI::Xaml::Media;
using winrt::Windows::UI::Text::FontWeight;
using winrt::Windows::UI::Text::FontWeights;
using winrt::Microsoft::UI::Dispatching::DispatcherQueueTimer;

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

constexpr std::uint32_t kShellBackground = 0x0A0A0B;
constexpr std::uint32_t kShellRail = 0x121214;
constexpr std::uint32_t kShellSurface = 0x1C1C1F;
constexpr std::uint32_t kShellAccent = 0x8C73FF;
constexpr std::uint32_t kShellMuted = 0xA9ABB4;
constexpr std::uint32_t kShellDanger = 0xFF6B6B;
constexpr std::uint32_t kShellSuccess = 0x56D39B;

SolidColorBrush color(std::uint32_t rgb) {
    return SolidColorBrush(winrt::Windows::UI::ColorHelper::FromArgb(
        255, static_cast<std::uint8_t>((rgb >> 16) & 0xff),
        static_cast<std::uint8_t>((rgb >> 8) & 0xff), static_cast<std::uint8_t>(rgb & 0xff)));
}

void styleText(TextBlock const& text, std::uint32_t foreground, double size = 13.0,
               FontWeight weight = FontWeights::Normal()) {
    text.Foreground(color(foreground));
    text.FontSize(size);
    text.FontWeight(weight);
    text.TextWrapping(TextWrapping::Wrap);
}

void setAccessible(DependencyObject const& element, std::wstring name, std::wstring help = {}) {
    element.SetValue(winrt::Microsoft::UI::Xaml::Automation::AutomationProperties::NameProperty(), box_value(name));
    if (!help.empty()) {
        element.SetValue(winrt::Microsoft::UI::Xaml::Automation::AutomationProperties::HelpTextProperty(), box_value(help));
    }
}

Button styledButton(std::wstring label, bool primary = false, bool destructive = false) {
    auto button = Button();
    button.Content(box_value(label));
    button.MinHeight(36);
    button.Padding(Thickness{14, 0, 14, 0});
    button.Foreground(color(0xFFFFFF));
    button.Background(color(primary ? kShellAccent : destructive ? kShellDanger : 0x26282C));
    button.BorderBrush(color(primary ? kShellAccent : destructive ? kShellDanger : 0x30343A));
    button.BorderThickness(Thickness{1, 1, 1, 1});
    return button;
}

Border card(UIElement const& child, double padding = 14.0) {
    // ponytail: square cards avoid a WinUI 3 non-packaged compositor crash;
    // restore rounded corners after a packaged UI smoke proves the fix.
    auto result = Border();
    result.Child(child);
    result.Padding(Thickness{padding, padding, padding, padding});
    result.Background(color(kShellSurface));
    result.BorderBrush(color(0x303238));
    result.BorderThickness(Thickness{1, 1, 1, 1});
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
    auto result = localAppData() / "GRAF" / "recordings";
    std::error_code error;
    std::filesystem::create_directories(result, error);
    return error ? std::filesystem::path{} : result;
}

bool readMicrophoneConsent(std::wstring_view suffix, bool& found) noexcept {
    constexpr wchar_t base[] = L"Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\microphone";
    std::wstring path(base);
    path.append(suffix);
    wchar_t value[32]{};
    DWORD bytes = sizeof(value);
    DWORD type = 0;
    const auto result = RegGetValueW(HKEY_CURRENT_USER, path.c_str(), L"Value",
                                     RRF_RT_REG_SZ, &type, value, &bytes);
    found = result == ERROR_SUCCESS;
    return found && _wcsicmp(value, L"Allow") == 0;
}

bool microphonePrivacyGranted() noexcept {
    bool found = false;
    const auto nonPackaged = readMicrophoneConsent(L"\\NonPackaged", found);
    if (found) return nonPackaged;
    return readMicrophoneConsent({}, found);
}

float rmsLevel(const std::vector<float>& samples) noexcept {
    if (samples.empty()) return 0.0F;
    long double sum = 0.0L;
    for (const auto sample : samples) {
        const auto bounded = std::max(-1.0F, std::min(1.0F, sample));
        sum += static_cast<long double>(bounded) * bounded;
    }
    return static_cast<float>(std::min(1.0L, std::sqrt(sum / samples.size())));
}

bool readUserSetting(std::wstring_view name, bool fallback) noexcept {
    constexpr wchar_t key[] = L"Software\\GRAF\\Windows\\MeetingDetection";
    DWORD value = 0;
    DWORD bytes = sizeof(value);
    DWORD type = 0;
    const auto result = RegGetValueW(HKEY_CURRENT_USER, key, std::wstring(name).c_str(),
                                     RRF_RT_REG_DWORD, &type, &value, &bytes);
    return result == ERROR_SUCCESS ? value != 0 : fallback;
}

void writeUserSetting(std::wstring_view name, bool value) noexcept {
    constexpr wchar_t key[] = L"Software\\GRAF\\Windows\\MeetingDetection";
    HKEY handle = nullptr;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, key, 0, nullptr, 0, KEY_SET_VALUE, nullptr, &handle, nullptr) != ERROR_SUCCESS) {
        return;
    }
    const DWORD stored = value ? 1U : 0U;
    RegSetValueExW(handle, std::wstring(name).c_str(), 0, REG_DWORD,
                   reinterpret_cast<const BYTE*>(&stored), sizeof(stored));
    RegCloseKey(handle);
}

std::string newSessionId() {
    GUID guid{};
    if (SUCCEEDED(CoCreateGuid(&guid))) {
        wchar_t buffer[39]{};
        if (StringFromGUID2(guid, buffer, static_cast<int>(std::size(buffer))) == 39) {
            std::string result;
            result.reserve(36);
            for (const auto character : std::wstring_view(buffer + 1, 36)) {
                result.push_back(static_cast<char>(character));
            }
            return result;
        }
    }
    return "windows-" + std::to_string(GetCurrentProcessId()) + "-" +
        std::to_string(GetTickCount64());
}

class UnavailableAec3 final : public graf::windows::IAec3Processor {
public:
    bool process(const float*, const float*, float*) noexcept override { return false; }
};

struct AecSelection {
    std::shared_ptr<graf::windows::IAec3Processor> processor;
    bool ready = false;
};

AecSelection selectAec() {
    auto native = graf::windows::GrafAEC3WebRtcAdapter::create();
    if (native != nullptr) {
        return {std::shared_ptr<graf::windows::IAec3Processor>(std::move(native)), true};
    }
    return {std::make_shared<UnavailableAec3>(), false};
}

bool mediaFoundationAacReady() noexcept {
    if (FAILED(MFStartup(MF_VERSION))) return false;
    MFT_REGISTER_TYPE_INFO outputType{MFMediaType_Audio, MFAudioFormat_AAC};
    IMFActivate** activations = nullptr;
    UINT32 activationCount = 0;
    const auto result = MFTEnumEx(
        MFT_CATEGORY_AUDIO_ENCODER,
        MFT_ENUM_FLAG_SYNCMFT | MFT_ENUM_FLAG_LOCALMFT | MFT_ENUM_FLAG_SORTANDFILTER,
        nullptr, &outputType, &activations, &activationCount);
    for (UINT32 index = 0; index < activationCount; ++index) {
        if (activations[index] != nullptr) activations[index]->Release();
    }
    CoTaskMemFree(activations);
    MFShutdown();
    return SUCCEEDED(result) && activationCount > 0;
}

class NativeCapture final {
public:
    struct AudioLevels {
        float microphone = 0.0F;
        float systemRender = 0.0F;
    };

    NativeCapture()
        : aecSelection_(selectAec()),
          aec_(aecSelection_.processor),
          custodyRoot_(localCustodyRoot()),
          queue_(custodyRoot_ / "desktop-upload-queue.v2", custodyRoot_),
          transport_({"https://rec.2brain.pro", {}, "windows-desktop", "windows-feature-200", 4 * 1024 * 1024,
                      [this] { return authSessionToken_; }}),
          scheduler_(queue_, [this](const graf::windows::UploadCustodyItem& item) {
              return transport_.upload(item);
          }),
          aacEncoderReady_(mediaFoundationAacReady()) {
        createRecordingPipeline();
        (void)queue_.load();
        (void)scheduler_.run(graf::windows::RecoveryTrigger::launch);
        const auto endpoints = enumerator_.snapshot();
        if (!endpoints.ok()) return;
        graf::windows::WasapiEndpointSnapshot render;
        graf::windows::WasapiEndpointSnapshot microphone;
        for (const auto& endpoint : endpoints.endpoints) {
            if (endpoint.flow == graf::windows::WasapiDataFlow::render && endpoint.isDefault) render = endpoint;
            if (endpoint.flow == graf::windows::WasapiDataFlow::capture &&
                graf::windows::WasapiEndpointEnumerator::isAllowedMicrophone(endpoint) &&
                (microphone.stableId.empty() || (!microphone.isDefault && endpoint.isDefault))) {
                microphone = endpoint;
            }
        }
        if (!render.stableId.empty() && !microphone.stableId.empty()) controller_->setEndpoints(render, microphone);
        readiness_.recordingPolicyAllowed = true;
        readiness_.microphoneEndpointReady = !microphone.stableId.empty();
        readiness_.renderEndpointReady = !render.stableId.empty();
        const auto supportsSampleRate = [](std::uint32_t sampleRate) {
            return sampleRate >= 8'000 && sampleRate <= 192'000;
        };
        readiness_.formatNormalizationReady = supportsSampleRate(render.sampleRate) &&
            supportsSampleRate(microphone.sampleRate) && render.channels > 0 && microphone.channels > 0;
        readiness_.microphonePermissionGranted = microphonePrivacyGranted();
        readiness_.aecReady = aecSelection_.ready;
        readiness_.storageWritable = !custodyRoot_.empty();
        readiness_.webViewRuntimeReady = false;
        readiness_.aacEncoderReady = aacEncoderReady_;
    }

    [[nodiscard]] graf::windows::TransitionResult record() {
        refreshReadiness();
        return controller_->record(readiness_);
    }
    void refreshPermission() noexcept { readiness_.microphonePermissionGranted = microphonePrivacyGranted(); }
    void setAuthSessionToken(std::string token) { authSessionToken_ = std::move(token); }
    [[nodiscard]] const std::string& authSessionToken() const noexcept { return authSessionToken_; }
    [[nodiscard]] bool microphonePermissionGranted() const noexcept { return readiness_.microphonePermissionGranted; }
    [[nodiscard]] std::size_t recover(graf::windows::RecoveryTrigger trigger) {
        return scheduler_.run(trigger);
    }
    [[nodiscard]] graf::windows::TransitionResult pause() { return controller_->pause(); }
    [[nodiscard]] graf::windows::TransitionResult resume() { return controller_->resume(); }
    [[nodiscard]] graf::windows::TransitionResult stop() { return controller_->stop(); }
    [[nodiscard]] const graf::windows::RecordingIndicatorSnapshot& indicator() const noexcept {
        return controller_->indicator().snapshot();
    }
    [[nodiscard]] AudioLevels audioLevels() const noexcept {
        return {microphoneLevel_.load(std::memory_order_relaxed),
                systemRenderLevel_.load(std::memory_order_relaxed)};
    }

    [[nodiscard]] std::wstring custodySummary() const {
        std::size_t pending = 0;
        std::size_t needsAuth = 0;
        std::size_t uploaded = 0;
        for (const auto& item : queue_.items()) {
            switch (item.status) {
            case graf::windows::UploadQueueStatus::pending:
            case graf::windows::UploadQueueStatus::retry:
            case graf::windows::UploadQueueStatus::uploading:
                ++pending;
                break;
            case graf::windows::UploadQueueStatus::needsAuth:
                ++needsAuth;
                break;
            case graf::windows::UploadQueueStatus::uploaded:
                ++uploaded;
                break;
            case graf::windows::UploadQueueStatus::quarantined:
                break;
            }
        }
        if (needsAuth != 0) return L"Нужен вход — локальные записи ждут отправки";
        if (pending != 0) return L"В очереди: " + std::to_wstring(pending) + L" · отправляем автоматически";
        if (uploaded != 0) return L"Все локальные записи отправлены";
        return L"Локальная очередь пуста";
    }

    [[nodiscard]] std::size_t custodyAttentionCount() const noexcept {
        std::size_t count = 0;
        for (const auto& item : queue_.items()) {
            if (item.status == graf::windows::UploadQueueStatus::needsAuth ||
                item.status == graf::windows::UploadQueueStatus::quarantined) {
                ++count;
            }
        }
        return count;
    }

    [[nodiscard]] std::wstring readinessSummary() const {
        const auto gate = graf::windows::WindowsReadinessGate::evaluate(readiness_);
        if (gate.recordingReady) return L"Микрофон и системный звук готовы";
        for (std::size_t index = 0; index < gate.blockerCount; ++index) {
            switch (gate.blockers[index]) {
            case graf::windows::ReasonCode::microphonePermissionDenied: return L"Разрешите доступ к микрофону в настройках Windows";
            case graf::windows::ReasonCode::microphoneEndpointUnavailable: return L"Микрофон не найден или недоступен";
            case graf::windows::ReasonCode::renderEndpointUnavailable: return L"Устройство вывода не найдено";
            case graf::windows::ReasonCode::formatNormalizationUnavailable: return L"Формат устройства пока не поддерживается";
            case graf::windows::ReasonCode::aecUnavailable: return L"Обработка эха ещё не установлена";
            case graf::windows::ReasonCode::storageUnavailable: return L"Нет доступа к локальному хранилищу";
            default: break;
            }
        }
        return L"Проверяем готовность записи";
    }

private:
    void createRecordingPipeline() {
        sessionId_ = newSessionId();
        timeline_ = std::make_shared<graf::windows::RecordingAudioTimeline>(*aec_);
        writer_ = std::make_shared<graf::windows::V5LocalRecordingWriter>(
            custodyRoot_, custodyRoot_ / sessionId_);
        controller_ = std::make_unique<graf::windows::WindowsCaptureSessionController>(
            sessionId_,
            [this](graf::windows::AudioBatch batch) {
                const auto level = rmsLevel(batch.samples);
                if (batch.source == graf::windows::AudioSource::microphone) {
                    microphoneLevel_.store(level, std::memory_order_relaxed);
                } else {
                    systemRenderLevel_.store(level, std::memory_order_relaxed);
                }
                if (!timeline_->push(std::move(batch))) return false;
                for (const auto& frame : timeline_->takeFrames()) {
                    if (!writer_->append(frame)) return false;
                }
                return true;
            },
            [this]() -> graf::windows::CaptureFinalization {
                for (const auto& frame : timeline_->takeFrames()) {
                    if (!writer_->append(frame)) return {false, graf::windows::ReasonCode::storageUnavailable};
                }
                if (!timeline_->healthy()) return {false, graf::windows::ReasonCode::aecUnavailable};
                const auto result = writer_->finalize();
                if (!result.ok()) return {false, graf::windows::ReasonCode::finalizationFailed};
                if (!queue_.enqueue({sessionId_, sessionId_, sessionId_, result.packageDirectory,
                                     graf::windows::UploadQueueStatus::pending, {}, 0, {}})) {
                    return {false, graf::windows::ReasonCode::storageUnavailable};
                }
                (void)scheduler_.run(graf::windows::RecoveryTrigger::launch);
                return {true, graf::windows::ReasonCode::none};
            },
            [this](bool paused) { timeline_->setMicrophonePaused(paused); });
    }

    void refreshReadiness() {
        const auto endpoints = enumerator_.snapshot();
        graf::windows::WasapiEndpointSnapshot render;
        graf::windows::WasapiEndpointSnapshot microphone;
        if (endpoints.ok()) {
            for (const auto& endpoint : endpoints.endpoints) {
                if (endpoint.flow == graf::windows::WasapiDataFlow::render && endpoint.isDefault) render = endpoint;
                if (endpoint.flow == graf::windows::WasapiDataFlow::capture &&
                    graf::windows::WasapiEndpointEnumerator::isAllowedMicrophone(endpoint) &&
                    (microphone.stableId.empty() || (!microphone.isDefault && endpoint.isDefault))) {
                    microphone = endpoint;
                }
            }
        }
        if (!render.stableId.empty() && !microphone.stableId.empty()) {
            controller_->setEndpoints(render, microphone);
        }
        const auto supportsSampleRate = [](std::uint32_t sampleRate) {
            return sampleRate >= 8'000 && sampleRate <= 192'000;
        };
        readiness_.microphoneEndpointReady = !microphone.stableId.empty();
        readiness_.renderEndpointReady = !render.stableId.empty();
        readiness_.formatNormalizationReady = supportsSampleRate(render.sampleRate) &&
            supportsSampleRate(microphone.sampleRate) && render.channels > 0 && microphone.channels > 0;
        readiness_.microphonePermissionGranted = microphonePrivacyGranted();
    }

    graf::windows::WasapiEndpointEnumerator enumerator_;
    AecSelection aecSelection_;
    std::shared_ptr<graf::windows::IAec3Processor> aec_;
    std::string sessionId_;
    std::shared_ptr<graf::windows::RecordingAudioTimeline> timeline_;
    std::filesystem::path custodyRoot_;
    std::shared_ptr<graf::windows::V5LocalRecordingWriter> writer_;
    graf::windows::DesktopUploadQueueService queue_;
    graf::windows::DesktopHttpTransport transport_;
    graf::windows::DesktopUploadRecoveryScheduler scheduler_;
    std::unique_ptr<graf::windows::WindowsCaptureSessionController> controller_;
    graf::windows::ReadinessInputs readiness_;
    std::string authSessionToken_;
    bool aacEncoderReady_ = false;
    std::atomic<float> microphoneLevel_{0.0F};
    std::atomic<float> systemRenderLevel_{0.0F};
};

class GrafApp : public ApplicationT<GrafApp> {
public:
    void OnLaunched(LaunchActivatedEventArgs const&) {
        window_ = Window();
        root_ = Grid();
        root_.Background(color(kShellBackground));
        window_.Content(root_);
        bool shellReady = false;
        try {
            buildShell();
            window_.AppWindow().Title(L"GRAF");
            // Keep the whole native rail reachable on a compact Windows
            // display; the web cabinet remains responsive inside this shell.
            window_.AppWindow().Resize(winrt::Windows::Graphics::SizeInt32{1080, 620});
            capture_ = std::make_unique<NativeCapture>();
            refreshNativeState();
            shellReady = true;
        } catch (const winrt::hresult_error& error) {
            showStartupError(error.message().c_str());
        } catch (...) {
            showStartupError(L"Не удалось инициализировать Windows shell");
        }
        window_.Closed([this](auto const&, auto const&) {
            if (stateTimer_) stateTimer_.Stop();
            if (capture_) (void)capture_->stop();
            tray_.reset();
        });
        if (!shellReady) {
            window_.Activate();
            return;
        }
        window_.Activated([this](auto const&, auto const&) {
            if (!mainWindowHandle_) {
                mainWindowHandle_ = nativeWindowHandle(window_);
                if (!mainWindowHandle_) mainWindowHandle_ = FindWindowW(nullptr, L"GRAF");
            }
            window_.Content().DispatcherQueue().TryEnqueue([this] { initializeWebView(); });
        });
        stateTimer_ = window_.Content().DispatcherQueue().CreateTimer();
        stateTimer_.Interval(winrt::Windows::Foundation::TimeSpan{25000000});
        stateTimer_.Tick([this](auto const&, auto const&) {
            refreshNativeState();
        });
        stateTimer_.Start();
        window_.Activate();
        if (!mainWindowHandle_) {
            mainWindowHandle_ = nativeWindowHandle(window_);
            if (!mainWindowHandle_) mainWindowHandle_ = FindWindowW(nullptr, L"GRAF");
        }
        tray_ = std::make_unique<graf::windows::WindowsTray>(
            reinterpret_cast<std::uintptr_t>(mainWindowHandle_),
            [this] {
                if (mainWindowHandle_) {
                    ShowWindow(mainWindowHandle_, SW_RESTORE);
                    SetForegroundWindow(mainWindowHandle_);
                }
                if (window_) {
                    window_.Activate();
                }
            },
            [this] { stopCapture(); },
            [this] { if (window_) window_.Close(); });
        refreshNativeState();
        // Keep permission recovery inline in the inspector. A startup modal is
        // unnecessary here and is unreliable in non-packaged ARM64 WinUI.
    }

private:
    void buildShell() {
        root_.Background(color(kShellBackground));
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
        recordingStrip_.Background(color(0x342087));
        recordingStrip_.Padding(Thickness{16, 6, 12, 6});
        auto row = Grid();
        auto textColumn = ColumnDefinition();
        textColumn.Width(GridLengthHelper::FromValueAndType(1.0, GridUnitType::Star));
        row.ColumnDefinitions().Append(textColumn);
        auto actionColumn = ColumnDefinition();
        actionColumn.Width(GridLengthHelper::FromValueAndType(120.0, GridUnitType::Pixel));
        row.ColumnDefinitions().Append(actionColumn);
        recordingStripText_ = TextBlock();
        styleText(recordingStripText_, 0xFFFFFF, 13, FontWeights::SemiBold());
        recordingStripText_.VerticalAlignment(VerticalAlignment::Center);
        setAccessible(recordingStripText_, L"Идёт запись", L"Нативный индикатор записи GRAF");
        row.Children().Append(recordingStripText_);
        recordingStripStop_ = styledButton(L"Остановить", false, true);
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
        meetingsSurface_.Background(color(kShellBackground));
        webView_ = WebView2();
        webView_.HorizontalAlignment(HorizontalAlignment::Stretch);
        webView_.VerticalAlignment(VerticalAlignment::Stretch);
        meetingsSurface_.Children().Append(webView_);
        localFallback_ = Border();
        localFallback_.Background(color(kShellBackground));
        localFallback_.Padding(Thickness{24, 24, 24, 24});
        auto fallback = StackPanel();
        fallback.Spacing(18);
        auto heading = TextBlock();
        heading.Text(L"Записи");
        styleText(heading, 0xF0F2F6, 22, FontWeights::SemiBold());
        auto subtitle = TextBlock();
        subtitle.Text(L"Кабинет загрузится после входа. Нативная запись и локальная сохранность работают отдельно от веб-страницы.");
        styleText(subtitle, kShellMuted, 13);
        auto statusCard = StackPanel();
        statusCard.Spacing(8);
        fallbackCabinetTitle_ = TextBlock();
        fallbackCabinetTitle_.Text(L"Кабинет недоступен");
        styleText(fallbackCabinetTitle_, 0xF0F2F6, 15, FontWeights::SemiBold());
        fallbackCabinetDetail_ = TextBlock();
        fallbackCabinetDetail_.Text(L"Проверьте соединение или войдите снова — локальная запись не потеряется.");
        styleText(fallbackCabinetDetail_, kShellMuted, 13);
        statusCard.Children().Append(fallbackCabinetTitle_);
        statusCard.Children().Append(fallbackCabinetDetail_);
        fallback.Children().Append(heading);
        fallback.Children().Append(subtitle);
        fallback.Children().Append(card(statusCard));
        auto empty = StackPanel();
        empty.Spacing(8);
        auto emptyTitle = TextBlock();
        emptyTitle.Text(L"Записей пока нет");
        styleText(emptyTitle, 0xF0F2F6, 15, FontWeights::SemiBold());
        auto emptyDetail = TextBlock();
        emptyDetail.Text(L"Новая локальная запись появится здесь после завершения и будет отправлена автоматически.");
        styleText(emptyDetail, kShellMuted, 13);
        empty.Children().Append(emptyTitle);
        empty.Children().Append(emptyDetail);
        fallback.Children().Append(card(empty, 16));
        localFallback_.Child(fallback);
        localFallback_.Visibility(Visibility::Collapsed);
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
            showCabinetFallback(L"Кабинет недоступен", L"Проверьте WebView2 или соединение. Нативная запись остаётся доступной.");
        }
    }

    void buildInspector() {
        expandedInspector_ = Border();
        expandedInspector_.Background(color(kShellRail));
        auto scroll = ScrollViewer();
        auto body = StackPanel();
        body.Spacing(12);

        auto header = Grid();
        header.ColumnDefinitions().Append(ColumnDefinition());
        auto headerActionColumn = ColumnDefinition();
        headerActionColumn.Width(GridLengthHelper::FromValueAndType(36.0, GridUnitType::Pixel));
        header.ColumnDefinitions().Append(headerActionColumn);
        auto headerText = TextBlock();
        headerText.Text(L"Запись");
        styleText(headerText, 0xF0F2F6, 15, FontWeights::SemiBold());
        header.Children().Append(headerText);
        auto settingsButton = styledButton(L"⚙", false);
        settingsButton.Width(36);
        settingsButton.Padding(Thickness{0, 0, 0, 0});
        settingsButton.Click([this](auto const&, auto const&) { openCabinetSettings(); });
        setAccessible(settingsButton, L"Настройки");
        Grid::SetColumn(settingsButton, 1);
        header.Children().Append(settingsButton);
        body.Children().Append(header);
        auto captureCard = StackPanel();
        captureCard.Spacing(10);
        captureStatus_ = TextBlock();
        styleText(captureStatus_, 0xF0F2F6, 13, FontWeights::SemiBold());
        setAccessible(captureStatus_, L"Статус записи", L"Текущее состояние нативной записи GRAF");
        captureCard.Children().Append(captureStatus_);
        recordButton_ = styledButton(L"Начать запись", true);
        setAccessible(recordButton_, L"Начать запись системного звука");
        recordButton_.Click([this](auto const&, auto const&) { recordCapture(); });
        captureCard.Children().Append(recordButton_);
        pauseButton_ = styledButton(L"Пауза");
        setAccessible(pauseButton_, L"Поставить запись на паузу");
        pauseButton_.Click([this](auto const&, auto const&) {
            if (capture_->indicator().state == graf::windows::SessionState::paused) (void)capture_->resume();
            else (void)capture_->pause();
            refreshNativeState();
        });
        stopButton_ = styledButton(L"Остановить", false, true);
        setAccessible(stopButton_, L"Остановить запись");
        stopButton_.Click([this](auto const&, auto const&) { stopCapture(); });
        auto controls = StackPanel();
        controls.Orientation(Orientation::Horizontal);
        controls.Spacing(8);
        controls.Children().Append(pauseButton_);
        controls.Children().Append(stopButton_);
        captureCard.Children().Append(controls);
        readinessText_ = TextBlock();
        styleText(readinessText_, kShellMuted, 12);
        captureCard.Children().Append(readinessText_);
        auto meters = StackPanel();
        meters.Spacing(6);
        auto metersTitle = TextBlock();
        metersTitle.Text(L"Уровни звука");
        styleText(metersTitle, 0xD5D7DE, 12, FontWeights::SemiBold());
        meters.Children().Append(metersTitle);
        auto microphoneMeterLabel = TextBlock();
        microphoneMeterLabel.Text(L"Микрофон");
        styleText(microphoneMeterLabel, kShellMuted, 11);
        meters.Children().Append(microphoneMeterLabel);
        microphoneMeter_ = Grid();
        microphoneMeter_.Height(6);
        microphoneMeter_.Background(color(0x30343A));
        microphoneMeterFill_ = Border();
        microphoneMeterFill_.HorizontalAlignment(HorizontalAlignment::Left);
        microphoneMeterFill_.Height(6);
        microphoneMeterFill_.Width(0);
        microphoneMeterFill_.Background(color(kShellSuccess));
        microphoneMeter_.Children().Append(microphoneMeterFill_);
        setAccessible(microphoneMeter_, L"Уровень микрофона");
        meters.Children().Append(microphoneMeter_);
        auto systemMeterLabel = TextBlock();
        systemMeterLabel.Text(L"Системный звук");
        styleText(systemMeterLabel, kShellMuted, 11);
        meters.Children().Append(systemMeterLabel);
        systemRenderMeter_ = Grid();
        systemRenderMeter_.Height(6);
        systemRenderMeter_.Background(color(0x30343A));
        systemRenderMeterFill_ = Border();
        systemRenderMeterFill_.HorizontalAlignment(HorizontalAlignment::Left);
        systemRenderMeterFill_.Height(6);
        systemRenderMeterFill_.Width(0);
        systemRenderMeterFill_.Background(color(kShellAccent));
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
        autoRecord.Text(L"⌁  Автоопределение встреч");
        styleText(autoRecord, 0xD5D7DE, 12, FontWeights::SemiBold());
        autoRecord.Margin(Thickness{0, 4, 0, 0});
        captureCard.Children().Append(autoRecord);
        autoRecordDetail_ = TextBlock();
        autoRecordDetail_.Text(L"Спрашивать перед началом записи");
        styleText(autoRecordDetail_, kShellMuted, 12);
        captureCard.Children().Append(autoRecordDetail_);
        body.Children().Append(card(captureCard, 12));
        auto custody = StackPanel();
        custody.Spacing(6);
        auto custodyHeader = TextBlock();
        custodyHeader.Text(L"Локальная сохранность");
        styleText(custodyHeader, 0xF0F2F6, 13, FontWeights::SemiBold());
        custody.Children().Append(custodyHeader);
        auto custodyBody = StackPanel();
        custodyBody.Spacing(6);
        auto custodyTitle = TextBlock();
        custodyTitle.Text(L"Запись сначала сохраняется на этом компьютере");
        styleText(custodyTitle, 0xF0F2F6, 13, FontWeights::SemiBold());
        auto custodyDetail = TextBlock();
        custodyDetail.Text(L"После финализации отправим её автоматически. Если сеть или вход недоступны, пакет останется в очереди.");
        styleText(custodyDetail, kShellMuted, 12);
        custodyStatus_ = TextBlock();
        custodyStatus_.Text(L"Локальная очередь загружается…");
        styleText(custodyStatus_, kShellSuccess, 12, FontWeights::SemiBold());
        custodyBody.Children().Append(custodyTitle);
        custodyBody.Children().Append(custodyDetail);
        custodyBody.Children().Append(custodyStatus_);
        custody.Children().Append(custodyBody);
        body.Children().Append(card(custody, 12));

        runtimeText_ = TextBlock();
        runtimeText_.Text(L"WebView2: проверяем кабинет…");
        styleText(runtimeText_, kShellMuted, 11);
        body.Children().Append(runtimeText_);
        scroll.Content(body);
        expandedInspector_.Child(scroll);
        Grid::SetColumn(expandedInspector_, 1);
        content_.Children().Append(expandedInspector_);

        compactInspector_ = Border();
        compactInspector_.Background(color(kShellRail));
        auto compact = StackPanel();
        compact.HorizontalAlignment(HorizontalAlignment::Center);
        compact.Spacing(8);
        inspectorToggle_ = styledButton(L"‹");
        inspectorToggle_.Width(40);
        inspectorToggle_.Height(40);
        setAccessible(inspectorToggle_, L"Показать панель управления", L"Раскрывает правую панель GRAF");
        inspectorToggle_.Click([this](auto const&, auto const&) { toggleInspector(); });
        compact.Children().Append(inspectorToggle_);
        compactStatus_ = TextBlock();
        compactStatus_.Text(L"●");
        compactStatus_.FontSize(18);
        compactStatus_.Foreground(color(kShellMuted));
        setAccessible(compactStatus_, L"Статус записи");
        compact.Children().Append(compactStatus_);
        compactRecordButton_ = styledButton(L"●", true);
        compactRecordButton_.Width(40);
        compactRecordButton_.Height(40);
        setAccessible(compactRecordButton_, L"Начать запись");
        compactRecordButton_.Click([this](auto const&, auto const&) { recordCapture(); });
        compact.Children().Append(compactRecordButton_);
        compactAttentionButton_ = styledButton(L"!", false, true);
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
        host.setNavigationHandler([this](graf::windows::RouteEvaluation evaluation) {
            if (evaluation.decision == graf::windows::RouteDecision::allow && localFallback_) {
                localFallback_.Visibility(Visibility::Collapsed);
            }
        });
        host.setRuntimeHandler([this](graf::windows::WebRuntimeState state) {
            if (state == graf::windows::WebRuntimeState::unavailable) {
                showCabinetFallback(L"Кабинет недоступен", L"Проверьте WebView2 или соединение. Нативная запись остаётся доступной.");
                runtimeText_.Text(L"WebView2 недоступен · локальный режим");
            } else if (state == graf::windows::WebRuntimeState::authRequired) {
                localFallback_.Visibility(Visibility::Collapsed);
                runtimeText_.Text(L"Нужен вход · открываем кабинет");
            } else if (state == graf::windows::WebRuntimeState::ready) {
                if (capture_) (void)capture_->recover(graf::windows::RecoveryTrigger::authRecovered);
                if (capture_) (void)capture_->recover(graf::windows::RecoveryTrigger::networkRecovered);
                localFallback_.Visibility(Visibility::Collapsed);
                runtimeText_.Text(L"Кабинет GRAF открыт");
            }
        });
        host.setQuitHandler([this]() { if (window_) window_.Close(); });
        host.setAuthSessionHandler([this](std::string token) {
            if (capture_) capture_->setAuthSessionToken(std::move(token));
        });
        host.setWebMessageHandler([this](graf::windows::WebViewBridgeEnvelope message) {
            if (message.command == "request_native_settings" || message.command == "open_native_settings") {
                openNativeSettings();
            } else if (message.command == "request_diagnostics" || message.command == "open_native_diagnostics") {
                showDiagnostics();
            } else if (message.command == "request_runtime_repair") {
                ShellExecuteW(nullptr, L"open", L"https://developer.microsoft.com/microsoft-edge/webview2/",
                              nullptr, nullptr, SW_SHOWNORMAL);
            }
            // ack_display is intentionally side-effect free; the native state is authoritative.
        });
    }

    void showCabinetFallback(std::wstring title, std::wstring detail) {
        fallbackCabinetTitle_.Text(std::move(title));
        fallbackCabinetDetail_.Text(std::move(detail));
        localFallback_.Visibility(Visibility::Visible);
    }

    void openCabinetSettings() {
        openNativeSettings();
    }

    void openNativeSettings() {
        if (settingsWindow_) {
            settingsWindow_.Activate();
            return;
        }
        settingsWindow_ = Window();
        settingsWindow_.AppWindow().Title(L"Настройки GRAF");
        settingsWindow_.AppWindow().Resize(winrt::Windows::Graphics::SizeInt32{760, 500});
        auto settingsLayout = Grid();
        auto sidebarColumn = ColumnDefinition();
        sidebarColumn.Width(GridLengthHelper::FromValueAndType(176.0, GridUnitType::Pixel));
        settingsLayout.ColumnDefinitions().Append(sidebarColumn);
        settingsLayout.ColumnDefinitions().Append(ColumnDefinition());
        auto sidebar = Border();
        sidebar.Background(color(kShellRail));
        auto sidebarBody = StackPanel();
        sidebarBody.Spacing(18);
        auto back = styledButton(L"‹  Назад");
        back.HorizontalAlignment(HorizontalAlignment::Left);
        back.Click([this](auto const&, auto const&) { if (settingsWindow_) settingsWindow_.Close(); });
        setAccessible(back, L"Назад");
        sidebarBody.Children().Append(back);
        auto sidebarTitle = TextBlock();
        sidebarTitle.Text(L"Встречи");
        styleText(sidebarTitle, kShellMuted, 12, FontWeights::SemiBold());
        sidebarBody.Children().Append(sidebarTitle);
        auto sidebarPage = TextBlock();
        sidebarPage.Text(L"●  Автозапись");
        styleText(sidebarPage, 0xF0F2F6, 13, FontWeights::SemiBold());
        auto sidebarPageSurface = Border();
        sidebarPageSurface.Padding(Thickness{10, 8, 10, 8});
        sidebarPageSurface.Background(color(0x342087));
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
        title.Text(L"Настройки");
        styleText(title, 0xF0F2F6, 26, FontWeights::SemiBold());
        body.Children().Append(title);
        auto captureTitle = TextBlock();
        captureTitle.Text(L"Автозапись");
        styleText(captureTitle, 0xF0F2F6, 16, FontWeights::SemiBold());
        body.Children().Append(captureTitle);
        auto assisted = CheckBox();
        assisted.Content(box_value(L"Разрешить запуск записи после таймера"));
        assisted.IsChecked(readUserSetting(L"assisted_auto_start", false));
        assisted.Foreground(color(0xF0F2F6));
        setAccessible(assisted, L"Разрешить запуск записи после таймера",
                      L"Разрешает запуск после 8-секундного таймера, если действуют политика рабочего пространства и разрешения Windows");
        assisted.Checked([this](auto const&, auto const&) { writeUserSetting(L"assisted_auto_start", true); });
        assisted.Unchecked([this](auto const&, auto const&) { writeUserSetting(L"assisted_auto_start", false); });
        body.Children().Append(assisted);
        auto assistedDetail = TextBlock();
        assistedDetail.Text(L"Сейчас запуск возможен только для подтверждённых приложений и после всех проверок записи.");
        styleText(assistedDetail, kShellMuted, 12);
        body.Children().Append(assistedDetail);
        auto autoRecord = CheckBox();
        autoRecord.Content(box_value(L"Запрашивать запись"));
        autoRecord.IsChecked(readUserSetting(L"prompt_before_recording", true));
        autoRecord.Foreground(color(0xF0F2F6));
        setAccessible(autoRecord, L"Запрашивать запись",
                      L"Показывать подтверждение для обнаруженного подтверждённого приложения");
        autoRecord.Checked([this](auto const&, auto const&) { writeUserSetting(L"prompt_before_recording", true); });
        autoRecord.Unchecked([this](auto const&, auto const&) { writeUserSetting(L"prompt_before_recording", false); });
        body.Children().Append(autoRecord);
        auto promptDetail = TextBlock();
        promptDetail.Text(L"Если выключено, запросы не показываются и запись не запускается. Определение встреч продолжает работать.");
        styleText(promptDetail, kShellMuted, 12);
        body.Children().Append(promptDetail);
        auto applicationsTitle = TextBlock();
        applicationsTitle.Text(L"Приложения");
        styleText(applicationsTitle, 0xF0F2F6, 16, FontWeights::SemiBold());
        body.Children().Append(applicationsTitle);
        auto targetDescription = TextBlock();
        targetDescription.Text(L"Автозапись работает только для подтверждённых приложений Windows. Неизвестные процессы и обычное воспроизведение медиа не запускают запись.");
        styleText(targetDescription, kShellMuted, 12);
        body.Children().Append(targetDescription);
        auto targetStatus = TextBlock();
        targetStatus.Text(L"Проверенные приложения появятся после проверки издателя и исполняемого файла.");
        styleText(targetStatus, kShellMuted, 12);
        body.Children().Append(card(targetStatus, 12));
        auto permissionTitle = TextBlock();
        permissionTitle.Text(L"Разрешения Windows");
        styleText(permissionTitle, 0xF0F2F6, 16, FontWeights::SemiBold());
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
            if (cabinet_) (void)cabinet_->open("https://rec.2brain.pro/desktop/settings");
        });
        setAccessible(account, L"Открыть настройки аккаунта");
        body.Children().Append(account);
        auto note = TextBlock();
        note.Text(L"GRAF записывает общий микс выбранного устройства вывода и отдельный физический микрофон. Запись сначала сохраняется локально и отправляется после входа.");
        styleText(note, kShellMuted, 12);
        body.Children().Append(card(note, 12));
        scroll.Content(body);
        Grid::SetColumn(scroll, 1);
        settingsLayout.Children().Append(scroll);
        settingsWindow_.Content(settingsLayout);
        settingsWindow_.Closed([this](auto const&, auto const&) { settingsWindow_ = nullptr; });
        settingsWindow_.Activate();
    }

    void showPermissionOnboarding() {
        if (permissionDialogOpen_ || !root_.XamlRoot()) return;
        permissionDialogOpen_ = true;
        ContentDialog dialog;
        dialog.XamlRoot(root_.XamlRoot());
        dialog.RequestedTheme(ElementTheme::Dark);
        dialog.Title(box_value(L"Разрешите запись звука"));
        dialog.Content(box_value(L"Для записи встречи GRAF нужен доступ к микрофону. Системный звук захватывается через общий микс Windows без виртуального драйвера."));
        dialog.PrimaryButtonText(L"Открыть настройки");
        dialog.SecondaryButtonText(L"Повторить проверку");
        dialog.CloseButtonText(L"Позже");
        dialog.ShowAsync().Completed([this](auto const& operation, auto const&) {
            permissionDialogOpen_ = false;
            try {
                const auto result = operation.GetResults();
                if (result == ContentDialogResult::Primary) {
                    ShellExecuteW(nullptr, L"open", L"ms-settings:privacy-microphone", nullptr, nullptr, SW_SHOWNORMAL);
                } else if (result == ContentDialogResult::Secondary) {
                    refreshNativeState();
                }
            } catch (...) {
                permissionDialogOpen_ = false;
            }
        });
    }

    void showDiagnostics() {
        if (!root_.XamlRoot() || diagnosticsDialogOpen_) return;
        diagnosticsDialogOpen_ = true;
        ContentDialog dialog;
        dialog.XamlRoot(root_.XamlRoot());
        dialog.RequestedTheme(ElementTheme::Dark);
        dialog.Title(box_value(L"Диагностика GRAF"));
        dialog.Content(box_value(capture_ ? capture_->readinessSummary() : L"Нативное состояние недоступно"));
        dialog.CloseButtonText(L"Закрыть");
        dialog.ShowAsync().Completed([this](auto const&, auto const&) { diagnosticsDialogOpen_ = false; });
    }

    void recordCapture() {
        if (!capture_) return;
        const auto authToken = capture_->authSessionToken();
        auto result = capture_->record();
        if (result.status == graf::windows::TransitionStatus::accepted &&
            result.state == graf::windows::SessionState::blocked) {
            // A readiness block is terminal for one session object. Recreate it
            // after the user fixes Windows permissions/device state so the next
            // click does not require a restart of GRAF.
            capture_ = std::make_unique<NativeCapture>();
            capture_->setAuthSessionToken(authToken);
            result = capture_->record();
        }
        // A worker/endpoint failure leaves the session terminal by design. A
        // fresh native session makes retry possible after the device recovers;
        // readiness blocks keep their actionable reason in the current session.
        if (result.status == graf::windows::TransitionStatus::accepted &&
            result.state == graf::windows::SessionState::failed) {
            capture_ = std::make_unique<NativeCapture>();
            capture_->setAuthSessionToken(authToken);
        }
        refreshNativeState();
    }

    void stopCapture() {
        if (!capture_) return;
        const auto authToken = capture_->authSessionToken();
        const auto result = capture_->stop();
        if (result.status == graf::windows::TransitionStatus::accepted &&
            (result.state == graf::windows::SessionState::savedLocal ||
             result.state == graf::windows::SessionState::failed)) {
            capture_ = std::make_unique<NativeCapture>();
            capture_->setAuthSessionToken(authToken);
        }
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
            capture_->custodyAttentionCount() != 0;
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
            inspectorToggle_.Content(box_value(expanded ? L"›" : L"‹"));
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
        styleText(title, 0xF0F2F6, 22, FontWeights::SemiBold());
        auto message = TextBlock();
        message.Text(detail);
        styleText(message, kShellMuted, 13);
        error.Children().Append(title);
        error.Children().Append(message);
        root_.Children().Append(error);
    }

    void refreshNativeState() {
        if (!capture_) return;
        capture_->refreshPermission();
        if (!hasInspectorAttention()) attentionExpansionDismissed_ = false;
        const auto& snapshot = capture_->indicator();
        const bool active = snapshot.visible;
        if (recordingStripRow_) {
            recordingStripRow_.Height(GridLengthHelper::FromValueAndType(
                active ? 44.0 : 0.0, GridUnitType::Pixel));
        }
        const bool permissionMissing = !capture_->microphonePermissionGranted();
        captureStatus_.Text(winrt::to_hstring(snapshot.statusText));
        readinessText_.Text(active ? L"Системный звук и микрофон · индикатор включён" : capture_->readinessSummary());
        readinessText_.Foreground(color(active ? kShellSuccess : snapshot.state == graf::windows::SessionState::failed ? kShellDanger : kShellMuted));
        recordButton_.Visibility(active ? Visibility::Collapsed : Visibility::Visible);
        recordButton_.IsEnabled(!active && capture_->readinessSummary() == L"Микрофон и системный звук готовы");
        permissionButton_.Visibility(!active && permissionMissing ? Visibility::Visible : Visibility::Collapsed);
        custodyStatus_.Text(capture_->custodySummary());
        recordingStrip_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
        recordingStripText_.Text(winrt::to_hstring(snapshot.statusText + " · Системный звук и микрофон"));
        recordingStripStop_.IsEnabled(active);
        if (tray_) tray_->setRecording(active);
        pauseButton_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
        stopButton_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
        if (meters_) {
            meters_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
            if (active) {
                const auto levels = capture_->audioLevels();
                updateMeter(microphoneMeter_, microphoneMeterFill_, levels.microphone);
                updateMeter(systemRenderMeter_, systemRenderMeterFill_, levels.systemRender);
            } else {
                updateMeter(microphoneMeter_, microphoneMeterFill_, 0.0F);
                updateMeter(systemRenderMeter_, systemRenderMeterFill_, 0.0F);
            }
        }
        if (active) pauseButton_.Content(box_value(snapshot.state == graf::windows::SessionState::paused ? L"Продолжить" : L"Пауза"));
        if (compactStatus_) compactStatus_.Foreground(color(active ? kShellSuccess : snapshot.state == graf::windows::SessionState::failed ? kShellDanger : kShellMuted));
        if (compactRecordButton_) compactRecordButton_.IsEnabled(!active && capture_->readinessSummary() == L"Микрофон и системный звук готовы");
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

    Window window_{nullptr};
    Grid root_{nullptr};
    RowDefinition recordingStripRow_{nullptr};
    Grid content_{nullptr};
    Grid meetingsSurface_{nullptr};
    WebView2 webView_{nullptr};
    Border expandedInspector_{nullptr};
    Border compactInspector_{nullptr};
    ColumnDefinition inspectorColumn_{nullptr};
    Button inspectorToggle_{nullptr};
    TextBlock compactStatus_{nullptr};
    Button compactRecordButton_{nullptr};
    Button compactAttentionButton_{nullptr};
    Border recordingStrip_{nullptr};
    TextBlock recordingStripText_{nullptr};
    Button recordingStripStop_{nullptr};
    TextBlock custodyStatus_{nullptr};
    Window settingsWindow_{nullptr};
    DispatcherQueueTimer stateTimer_{nullptr};
    std::unique_ptr<graf::windows::WindowsTray> tray_;
    HWND mainWindowHandle_ = nullptr;
    bool permissionDialogOpen_ = false;
    bool diagnosticsDialogOpen_ = false;
    bool inspectorExpanded_ = false;
    bool attentionExpansionDismissed_ = false;
    Border localFallback_{nullptr};
    bool webViewAttached_ = false;
    TextBlock captureStatus_{nullptr};
    TextBlock readinessText_{nullptr};
    StackPanel meters_{nullptr};
    Grid microphoneMeter_{nullptr};
    Border microphoneMeterFill_{nullptr};
    Grid systemRenderMeter_{nullptr};
    Border systemRenderMeterFill_{nullptr};
    Button permissionButton_{nullptr};
    TextBlock runtimeText_{nullptr};
    TextBlock fallbackCabinetTitle_{nullptr};
    TextBlock fallbackCabinetDetail_{nullptr};
    TextBlock autoRecordDetail_{nullptr};
    Button recordButton_{nullptr};
    Button pauseButton_{nullptr};
    Button stopButton_{nullptr};
    std::unique_ptr<NativeCapture> capture_;
    std::unique_ptr<graf::windows::CabinetWindow> cabinet_;
};

} // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    try {
        winrt::init_apartment(winrt::apartment_type::single_threaded);
        winrt::Microsoft::UI::Xaml::Application::Start([](auto&&) {
            winrt::make<GrafApp>();
        });
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
