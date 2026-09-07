#ifdef _WIN32

#include "Audio/RecordingAudioTimeline.h"
#include "Audio/WasapiEndpointEnumerator.h"
#include "Capture/WindowsCaptureSessionController.h"
#include "Diagnostics/MetadataSafeDiagnostics.h"
#include "MeetingDetection/AutomaticRecordingPolicy.h"
#include "Permissions/WindowsReadinessGate.h"
#include "Recording/V5LocalRecordingWriter.h"
#include "Recording/LocalRecordingPackage.h"
#include "Storage/AtomicFileStore.h"
#include "Shell/CabinetWindow.h"
#include "Shell/WindowsTray.h"
#include "Shell/AutomaticRecordingPrompt.h"
#include "Upload/DesktopUploadQueueService.h"
#include "Upload/DesktopUploadRecoveryScheduler.h"
#include "Upload/DesktopHttpTransport.h"
#include "../Native/GrafAEC3/GrafAEC3WebRtcAdapter.h"

#include <windows.h>
#include <knownfolders.h>
#include <combaseapi.h>
#include <shlobj.h>
#include <shellapi.h>
#include <winreg.h>

// Win32 aliases otherwise rewrite projected WinUI methods such as GetClassName.
#ifdef GetClassName
#undef GetClassName
#endif
#ifdef GetCurrentTime
#undef GetCurrentTime
#endif

#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Xaml.Controls.Primitives.h>
#include <winrt/Microsoft.UI.Xaml.Automation.h>
#include <winrt/Microsoft.UI.Xaml.Media.h>
#include <winrt/Microsoft.UI.Xaml.Markup.h>
#include <winrt/Microsoft.UI.Xaml.XamlTypeInfo.h>
#include <winrt/Microsoft.UI.Dispatching.h>
#include <winrt/Microsoft.UI.Windowing.h>
#include <winrt/Windows.ApplicationModel.Activation.h>
#include <winrt/Windows.ApplicationModel.h>
#include <winrt/Windows.ApplicationModel.DataTransfer.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Graphics.h>
#include <winrt/Windows.System.Profile.h>
#include <winrt/Windows.UI.h>
#include <winrt/Windows.UI.Text.h>
#include <winrt/Windows.UI.Xaml.Interop.h>
#include <microsoft.ui.xaml.window.h>

#include <mfapi.h>
#include <mftransform.h>

#include <filesystem>
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <iterator>
#include <future>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <thread>
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

void refreshShellPalette() {
    HIGHCONTRASTW contrast{sizeof(HIGHCONTRASTW)};
    const bool highContrast = SystemParametersInfoW(SPI_GETHIGHCONTRAST, sizeof(contrast), &contrast, 0) &&
        (contrast.dwFlags & HCF_HIGHCONTRASTON) != 0;
    static int previous = -1;
    if (!highContrast && previous == 0) return;
    const bool firstRun = previous < 0;
    previous = highContrast;
    // Current DesktopMeetingShellChrome tokens; Windows High Contrast owns its colors.
    struct Entry { const wchar_t* key; std::uint32_t rgb; int contrastColor; };
    const Entry entries[] = {
        {L"ApplicationPageBackgroundThemeBrush", 0x0A0A0B, COLOR_WINDOW},
        {L"LayerFillColorDefaultBrush", 0x121214, COLOR_WINDOW},
        {L"CardBackgroundFillColorDefaultBrush", 0x1C1C1F, COLOR_WINDOW},
        {L"CardStrokeColorDefaultBrush", 0x30343A, COLOR_WINDOWTEXT},
        {L"AccentFillColorDefaultBrush", 0x8C73FF, COLOR_HIGHLIGHT},
        {L"GrafRecordingStripBrush", 0x342087, COLOR_WINDOW}
    };
    auto resources = Application::Current().Resources();
    for (const auto& entry : entries) {
        const auto system = GetSysColor(entry.contrastColor);
        const auto value = winrt::Windows::UI::ColorHelper::FromArgb(255,
            highContrast ? GetRValue(system) : static_cast<BYTE>(entry.rgb >> 16),
            highContrast ? GetGValue(system) : static_cast<BYTE>(entry.rgb >> 8),
            highContrast ? GetBValue(system) : static_cast<BYTE>(entry.rgb));
        const auto key = box_value(entry.key);
        if (!firstRun && resources.HasKey(key)) {
            if (const auto brush = resources.Lookup(key).try_as<SolidColorBrush>()) {
                brush.Color(value);
                continue;
            }
        }
        resources.Insert(key, SolidColorBrush(value));
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

Brush themeBrush(std::wstring_view name) {
    return Application::Current().Resources().Lookup(box_value(hstring(name))).as<Brush>();
}

void styleText(TextBlock const& text, double size = 13.0,
               FontWeight weight = FontWeights::Normal()) {
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

Button styledButton(std::wstring label, bool primary = false) {
    auto button = Button();
    button.Content(box_value(label));
    button.MinHeight(36);
    button.Padding(Thickness{14, 0, 14, 0});
    if (primary) button.Style(Application::Current().Resources().Lookup(box_value(L"AccentButtonStyle")).as<Style>());
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
    auto result = appData / "GRAF" / "recordings";
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

std::string selectedMicrophonePreference() {
    wchar_t value[2048]{};
    DWORD bytes = sizeof(value);
    if (RegGetValueW(HKEY_CURRENT_USER, L"Software\\GRAF\\Windows\\Capture", L"Microphone",
                     RRF_RT_REG_SZ, nullptr, value, &bytes) != ERROR_SUCCESS) return {};
    return winrt::to_string(value);
}

bool saveMicrophonePreference(const std::string& identity) {
    HKEY key = nullptr;
    if (RegCreateKeyExW(HKEY_CURRENT_USER, L"Software\\GRAF\\Windows\\Capture", 0, nullptr, 0,
                        KEY_SET_VALUE, nullptr, &key, nullptr) != ERROR_SUCCESS) return false;
    const auto value = winrt::to_hstring(identity);
    const auto result = RegSetValueExW(key, L"Microphone", 0, REG_SZ,
        reinterpret_cast<const BYTE*>(value.c_str()), static_cast<DWORD>((value.size() + 1) * sizeof(wchar_t)));
    RegCloseKey(key);
    return result == ERROR_SUCCESS;
}

std::wstring deviceDisplayName(const std::string& name) {
    auto value = std::wstring(winrt::to_hstring(name).c_str());
    value.erase(std::remove_if(value.begin(), value.end(), [](wchar_t c) { return c < 32 || c == 127; }), value.end());
    if (value.size() > 96) value.resize(96);
    return value.empty() ? L"Устройство Windows" : value;
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
          custodyRoot_(localCustodyRoot()),
          queue_(custodyRoot_ / "desktop-upload-queue.v2", custodyRoot_),
          scheduler_(queue_) {
        createRecordingPipeline();
        (void)queue_.load();
        recover(graf::windows::RecoveryTrigger::launch);
        readiness_.aecReady = aecSelection_.ready;
        readiness_.storageWritable = !custodyRoot_.empty();
        readiness_.webViewRuntimeReady = false;
        readiness_.aacEncoderReady = mediaFoundationAacReady();
        refreshReadiness();
    }

    [[nodiscard]] graf::windows::TransitionResult record() {
        if (!indicator().visible && indicator().state != graf::windows::SessionState::idle) createRecordingPipeline();
        refreshReadiness();
        recordingAccount_ = currentAccount_;
        recordingEndpointIdentity_ = currentEndpointIdentity_;
        return controller_->record(readiness_);
    }
    void refreshPermission() noexcept { readiness_.microphonePermissionGranted = microphonePrivacyGranted(); }
    void setAuthSessionToken(std::string token) {
        if (authSessionToken_ == token) return;
        scheduler_.cancel();
        if (accountCancellation_) accountCancellation_->store(true);
        authSessionToken_ = std::move(token);
        ++authGeneration_;
        currentAccount_.reset();
        accountRetryAt_ = 0;
        recover(graf::windows::RecoveryTrigger::authRecovered);
    }
    [[nodiscard]] const std::string& authSessionToken() const noexcept { return authSessionToken_; }
    [[nodiscard]] const auto& currentAccount() const noexcept { return currentAccount_; }
    [[nodiscard]] auto authGeneration() const noexcept { return authGeneration_; }
    [[nodiscard]] bool microphonePermissionGranted() const noexcept { return readiness_.microphonePermissionGranted; }
    [[nodiscard]] bool recordingReady() const noexcept {
        return graf::windows::WindowsReadinessGate::evaluate(readiness_).recordingReady;
    }
    [[nodiscard]] const auto& readiness() const noexcept { return readiness_; }
    [[nodiscard]] const auto& microphones() const noexcept { return microphones_; }
    [[nodiscard]] const std::string& selectedMicrophone() const noexcept { return selectedMicrophone_; }
    [[nodiscard]] const std::wstring& sourceSummary() const noexcept { return sourceSummary_; }
    bool selectMicrophone(std::string identity) {
        if (indicator().visible || !saveMicrophonePreference(identity)) return false;
        selectedMicrophone_ = std::move(identity);
        refreshReadiness();
        return true;
    }
    void recover(graf::windows::RecoveryTrigger trigger) {
        if (shuttingDown_) return;
        if (!pendingRecovery_ || trigger == graf::windows::RecoveryTrigger::authRecovered) pendingRecovery_ = trigger;
    }
    void pollUploads() {
        (void)scheduler_.drain();
        pollAccount();
        if (!currentAccount_) return;
        if (shuttingDown_ || scheduler_.busy() || !pendingRecovery_) return;
        graf::windows::DesktopHttpConfig config;
        config.sessionToken = authSessionToken_;
        config.workspaceId = currentAccount_->workspaceId;
        // The workspace was verified by /auth/me. No fabricated device identity.
        const auto trigger = *pendingRecovery_;
        pendingRecovery_.reset();
        // Failed dispatch is retried by the bounded 30-second recovery timer;
        // an empty queue must not repeatedly requeue auth states on every UI tick.
        (void)scheduler_.startAsync(trigger, std::move(config));
    }
    void shutdown() {
        shuttingDown_ = true;
        pendingRecovery_.reset();
        scheduler_.cancel();
        if (accountCancellation_) accountCancellation_->store(true);
        (void)controller_->stop();
    }
    [[nodiscard]] graf::windows::TransitionResult pause() { return controller_->pause(); }
    [[nodiscard]] graf::windows::TransitionResult resume() { return controller_->resume(); }
    [[nodiscard]] graf::windows::TransitionResult stop() { return controller_->stop(); }
    void pollHealth() {
        (void)controller_->pollHealth();
        const auto& state = indicator();
        if (diagnosticsSessionId_ == sessionId_ ||
            (state.state != graf::windows::SessionState::savedLocal &&
             state.state != graf::windows::SessionState::failed &&
             state.state != graf::windows::SessionState::blocked)) return;
        // Terminal state is published only after worker completion. These are
        // real 10-ms blocks, never unsynchronized live timeline measurements.
        graf::windows::MetadataSnapshot snapshot;
        snapshot.appVersion = "development";
        snapshot.osBuild = "unknown";
#ifdef _M_ARM64
        snapshot.architecture = "ARM64";
#else
        snapshot.architecture = "x64";
#endif
        try {
            const auto version = winrt::Windows::ApplicationModel::Package::Current().Id().Version();
            snapshot.appVersion = std::to_string(version.Major) + "." + std::to_string(version.Minor) +
                "." + std::to_string(version.Build) + "." + std::to_string(version.Revision);
        } catch (...) {} // Unpackaged builds have no package version.
        try {
            const auto version = std::stoull(winrt::to_string(
                winrt::Windows::System::Profile::AnalyticsInfo::VersionInfo().DeviceFamilyVersion()));
            snapshot.osBuild = std::to_string((version >> 16) & 0xFFFF);
        } catch (...) {}
        snapshot.state = state.state;
        snapshot.reason = state.reason;
        snapshot.processedBlocks = timeline_->processedFrames();
        snapshot.writtenBlocks = writer_->frameCount();
        snapshot.durationMs = writer_->frameCount() * 10;
        snapshot.endpointIdentity = recordingEndpointIdentity_;
        snapshot.trustedPrefixRetained = controller_->finalization().trustedPrefixRetained;
        snapshot.renderClock = controller_->clockDiagnostics(graf::windows::AudioSource::systemRender);
        snapshot.microphoneClock = controller_->clockDiagnostics(graf::windows::AudioSource::microphone);
        lastDiagnostics_ = graf::windows::MetadataSafeDiagnostics::serialize(snapshot);
        diagnosticsSessionId_ = sessionId_;
    }
    [[nodiscard]] const std::string& diagnostics() const noexcept { return lastDiagnostics_; }
    [[nodiscard]] const auto& finalization() const noexcept { return controller_->finalization(); }
    [[nodiscard]] const graf::windows::RecordingIndicatorSnapshot& indicator() const noexcept {
        return controller_->indicator().snapshot();
    }
    [[nodiscard]] AudioLevels audioLevels() const noexcept {
        return {microphoneLevel_.load(std::memory_order_relaxed),
                systemRenderLevel_.load(std::memory_order_relaxed)};
    }

    [[nodiscard]] const auto& localItems() const noexcept { return queue_.items(); }
    [[nodiscard]] const auto& custodyRoot() const noexcept { return custodyRoot_; }
    [[nodiscard]] bool uploadsBusy() const noexcept { return scheduler_.busy(); }
    [[nodiscard]] std::optional<graf::windows::UploadCustodyItem> localItem(std::string_view id) const {
        if (queue_.quarantined()) return std::nullopt;
        for (const auto& item : queue_.items()) {
            if (item.localRecordingId != id) continue;
            if ((indicator().visible && item.sessionId == sessionId_) ||
                !graf::windows::AtomicFileStore::isWithinRoot(custodyRoot_, item.packageDirectory)) return std::nullopt;
            return item;
        }
        return std::nullopt;
    }
    bool sendLocalRecording(std::string_view id) {
        const auto item = localItem(id);
        if (!item || scheduler_.busy() || item->status == graf::windows::UploadQueueStatus::uploaded ||
            item->status == graf::windows::UploadQueueStatus::quarantined || !currentAccount_ ||
            item->ownerUserId != currentAccount_->userId || item->ownerWorkspaceId != currentAccount_->workspaceId) return false;
        if (!queue_.requestRetry(id)) return false;
        recover(graf::windows::RecoveryTrigger::scheduled);
        return true;
    }
    graf::windows::LocalCopyRemovalResult removeLocalCopy(std::string_view id, HWND owner) {
        if (indicator().visible || scheduler_.busy() || !localItem(id)) return graf::windows::LocalCopyRemovalResult::unsafePath;
        return queue_.removeLocalCopy(id, graf::windows::LocalPurgeProof::userConfirmedLocalCopy,
            [owner](const std::filesystem::path& path) {
                return graf::windows::DesktopLocalPurgeService::recycle(path, reinterpret_cast<std::uintptr_t>(owner));
            });
    }

    bool assignLocalOwner(std::string_view id, const graf::windows::DesktopAccountIdentity& expected, std::uint64_t generation) {
        return generation == authGeneration_ && currentAccount_ && !scheduler_.busy() &&
            currentAccount_->userId == expected.userId && currentAccount_->workspaceId == expected.workspaceId &&
            queue_.assignOwner(id, expected);
    }

    [[nodiscard]] std::wstring custodySummary() const {
        if (queue_.quarantined()) return L"Не удалось прочитать локальную очередь. Записи не объявлены отправленными.";
        std::size_t pending = 0;
        std::size_t needsAuth = 0;
        std::size_t uploaded = 0;
        std::size_t damaged = 0;
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
                ++damaged;
                break;
            }
        }
        if (damaged != 0) return L"Требуют проверки: " + std::to_wstring(damaged) + L". Локальные записи не отправлены.";
        if (needsAuth != 0) return L"Нужен вход — локальные записи ждут отправки";
        if (pending != 0 && authSessionToken_.empty()) return L"Локальные записи ждут входа в аккаунт.";
        if (pending != 0 && !currentAccount_) return L"Не удалось подтвердить аккаунт для отправки. Записи остаются на компьютере.";
        if (pending != 0) return L"В очереди: " + std::to_wstring(pending) +
            (scheduler_.busy() ? L" · проверяем отправку" : L" · сохранены на компьютере");
        if (uploaded != 0) return L"Все локальные записи отправлены";
        return L"Локальная очередь пуста";
    }

    [[nodiscard]] std::size_t custodyAttentionCount() const noexcept {
        std::size_t count = queue_.quarantined() ? 1 : 0;
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
            case graf::windows::ReasonCode::aacEncoderUnavailable: return L"Недоступен кодировщик AAC. Для Windows N установите Media Feature Pack и перезапустите GRAF.";
            default: break;
            }
        }
        return L"Проверяем готовность записи";
    }

private:
    void pollAccount() {
        if (accountFuture_.valid() && accountFuture_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            std::optional<graf::windows::DesktopAccountIdentity> result;
            try { result = accountFuture_.get(); } catch (...) {}
            if (accountRequestGeneration_ == authGeneration_) {
                currentAccount_ = std::move(result);
                accountRetryAt_ = GetTickCount64() + 30000;
            }
        }
        if (shuttingDown_ || authSessionToken_.empty() || currentAccount_ || accountFuture_.valid() || GetTickCount64() < accountRetryAt_) return;
        graf::windows::DesktopHttpConfig config;
        config.sessionToken = authSessionToken_;
        accountCancellation_ = std::make_shared<std::atomic_bool>(false);
        config.cancellation = accountCancellation_;
        std::packaged_task<std::optional<graf::windows::DesktopAccountIdentity>()> task([config = std::move(config)] {
            return graf::windows::DesktopHttpTransport(config).accountIdentity();
        });
        accountRequestGeneration_ = authGeneration_;
        try {
            auto future = task.get_future();
            std::thread(std::move(task)).detach();
            accountFuture_ = std::move(future);
        } catch (...) { accountRetryAt_ = GetTickCount64() + 30000; }
    }

    void createRecordingPipeline() {
        controller_.reset();
        sessionId_ = newSessionId();
        timeline_ = std::make_shared<graf::windows::RecordingAudioTimeline>(*aecSelection_.processor);
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
            [this](graf::windows::ReasonCode failure) -> std::optional<graf::windows::CaptureFinalization> {
                if (!finalizationFuture_.valid()) {
                    // Both capture workers have finished. The job owns only
                    // writer/timeline, never the UI, account, or upload queue.
                    std::packaged_task<graf::windows::V5WriterResult()> task(
                        [timeline = timeline_, writer = writer_, failure]() mutable {
                            for (const auto& frame : timeline->takeFrames()) {
                                if (!writer->append(frame)) {
                                    failure = graf::windows::ReasonCode::storageUnavailable;
                                    break;
                                }
                            }
                            if (!timeline->healthy() && failure == graf::windows::ReasonCode::none)
                                failure = graf::windows::ReasonCode::clockDiscontinuity;
                            return writer->finalize(failure);
                        });
                    auto future = task.get_future();
                    std::thread(std::move(task)).detach();
                    finalizationFuture_ = std::move(future);
                    return std::nullopt;
                }
                if (finalizationFuture_.wait_for(std::chrono::seconds(0)) != std::future_status::ready) return std::nullopt;
                const auto result = finalizationFuture_.get();
                failure = result.captureFailure;
                if (!result.normalPackage()) {
                    if (result.trustedPrefixRetained) {
                        (void)queue_.enqueue({sessionId_, sessionId_, sessionId_, result.packageDirectory,
                            graf::windows::UploadQueueStatus::quarantined, {}, 0, "capture_interrupted",
                            recordingAccount_ ? recordingAccount_->userId : "", recordingAccount_ ? recordingAccount_->workspaceId : ""});
                    }
                    return graf::windows::CaptureFinalization{false, failure == graf::windows::ReasonCode::none
                        ? graf::windows::ReasonCode::finalizationFailed : failure, result.trustedPrefixRetained};
                }
                if (!queue_.enqueue({sessionId_, sessionId_, sessionId_, result.packageDirectory,
                                     graf::windows::UploadQueueStatus::pending, {}, 0, {},
                                     recordingAccount_ ? recordingAccount_->userId : "", recordingAccount_ ? recordingAccount_->workspaceId : ""})) {
                    return graf::windows::CaptureFinalization{false, graf::windows::ReasonCode::storageUnavailable, true};
                }
                recover(graf::windows::RecoveryTrigger::launch);
                return graf::windows::CaptureFinalization{true, graf::windows::ReasonCode::none};
            },
            [this](bool paused) { timeline_->setMicrophonePaused(paused); });
    }

public:
    void refreshReadiness() {
        if (controller_->indicator().snapshot().visible) return;
        const auto endpoints = enumerator_.snapshot();
        graf::windows::WasapiEndpointSnapshot render;
        graf::windows::WasapiEndpointSnapshot microphone;
        microphones_.clear();
        if (endpoints.ok()) {
            for (const auto& endpoint : endpoints.endpoints) {
                if (endpoint.flow == graf::windows::WasapiDataFlow::render && endpoint.isDefault) render = endpoint;
                if (graf::windows::WasapiEndpointEnumerator::isAllowedMicrophone(endpoint)) {
                    microphones_.push_back(endpoint);
                    if (selectedMicrophone_.empty()
                            ? (microphone.stableId.empty() || (!microphone.isDefault && endpoint.isDefault))
                            : endpoint.stableId == selectedMicrophone_) microphone = endpoint;
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
        currentEndpointIdentity_ = microphone.stableId;
        readiness_.renderEndpointReady = !render.stableId.empty();
        readiness_.formatNormalizationReady = supportsSampleRate(render.sampleRate) &&
            supportsSampleRate(microphone.sampleRate) && render.channels > 0 && microphone.channels > 0;
        readiness_.microphonePermissionGranted = microphonePrivacyGranted();
        sourceSummary_ = microphone.stableId.empty()
            ? L"Выбранный микрофон недоступен. Подключите его или выберите другой."
            : L"Микрофон: " + deviceDisplayName(microphone.friendlyName);
        sourceSummary_ += render.stableId.empty() ? L" · Вывод недоступен"
            : L" · Системный звук: " + deviceDisplayName(render.friendlyName);
    }

private:
    graf::windows::WasapiEndpointEnumerator enumerator_;
    std::vector<graf::windows::WasapiEndpointSnapshot> microphones_;
    std::string selectedMicrophone_ = selectedMicrophonePreference();
    std::wstring sourceSummary_;
    std::string currentEndpointIdentity_;
    std::string recordingEndpointIdentity_;
    std::string diagnosticsSessionId_;
    std::string lastDiagnostics_;
    AecSelection aecSelection_;
    std::string sessionId_;
    std::shared_ptr<graf::windows::RecordingAudioTimeline> timeline_;
    std::filesystem::path custodyRoot_;
    std::shared_ptr<graf::windows::V5LocalRecordingWriter> writer_;
    std::future<graf::windows::V5WriterResult> finalizationFuture_;
    graf::windows::DesktopUploadQueueService queue_;
    graf::windows::DesktopUploadRecoveryScheduler scheduler_;
    std::optional<graf::windows::RecoveryTrigger> pendingRecovery_;
    bool shuttingDown_ = false;
    std::unique_ptr<graf::windows::WindowsCaptureSessionController> controller_;
    graf::windows::ReadinessInputs readiness_;
    std::string authSessionToken_;
    std::optional<graf::windows::DesktopAccountIdentity> currentAccount_;
    std::optional<graf::windows::DesktopAccountIdentity> recordingAccount_;
    std::future<std::optional<graf::windows::DesktopAccountIdentity>> accountFuture_;
    std::shared_ptr<std::atomic_bool> accountCancellation_;
    std::uint64_t authGeneration_ = 0;
    std::uint64_t accountRequestGeneration_ = 0;
    ULONGLONG accountRetryAt_ = 0;
    std::atomic<float> microphoneLevel_{0.0F};
    std::atomic<float> systemRenderLevel_{0.0F};
};

class GrafApp : public ApplicationT<GrafApp, winrt::Microsoft::UI::Xaml::Markup::IXamlMetadataProvider> {
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
        Resources().MergedDictionaries().Append(XamlControlsResources());
        refreshShellPalette();
        window_ = Window();
        root_ = Grid();
        root_.RequestedTheme(ElementTheme::Dark);
        root_.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
        window_.Content(root_);
        bool shellReady = false;
        try {
            buildShell();
            window_.AppWindow().Title(L"GRAF");
            // Keep the whole native rail reachable on a compact Windows
            // display; the web cabinet remains responsive inside this shell.
            window_.AppWindow().Resize(winrt::Windows::Graphics::SizeInt32{1080, 620});
            capture_ = std::make_unique<NativeCapture>();
            (void)ensureRecordingIndicator(false);
            refreshNativeState();
            shellReady = true;
        } catch (const winrt::hresult_error& error) {
            showStartupError(error.message().c_str());
        } catch (...) {
            showStartupError(L"Не удалось инициализировать Windows shell");
        }
        window_.AppWindow().Closing([this](auto const&, auto const& args) {
            if (capture_ && capture_->indicator().visible) {
                args.Cancel(true);
                requestExit();
            }
        });
        window_.Closed([this](auto const&, auto const&) {
            shuttingDown_ = true;
            alive_->store(false);
            automaticPolicy_.cancel();
            if (automaticPromptWindow_) automaticPromptWindow_.Close();
            if (cabinet_) cabinet_->webView().close();
            if (settingsWindow_) settingsWindow_.Close();
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
                if (mainWindowHandle_) {
                    ShowWindow(mainWindowHandle_, SW_RESTORE);
                    SetForegroundWindow(mainWindowHandle_);
                }
                if (window_) {
                    window_.Activate();
                }
            },
            [this] { stopCapture(); },
            [this] { requestExit(); },
            [this] { pauseResumeCapture(); });
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
            localMetadataRefreshRequested_ = true;
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
        auto retry = styledButton(L"Повторить загрузку");
        retry.Click([this](auto const&, auto const&) {
            localMetadataRefreshRequested_ = true;
            if (cabinet_) cabinet_->webView().reload();
            else initializeWebView();
        });
        setAccessible(retry, L"Повторить загрузку кабинета", L"Запись и локальная очередь не сбрасываются");
        fallback.Children().Append(retry);
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
        settingsButton.Click([this](auto const&, auto const&) { openNativeSettings(); });
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
        host.setNavigationHandler([this](graf::windows::RouteEvaluation evaluation) {
            if (evaluation.decision == graf::windows::RouteDecision::allow &&
                evaluation.kind == graf::windows::RouteKind::nativeSettings) {
                openNativeSettings();
                return;
            }
            if (evaluation.decision == graf::windows::RouteDecision::allow && localFallback_) {
                localFallback_.Visibility(Visibility::Collapsed);
            }
        });
        host.setRuntimeHandler([this](graf::windows::WebRuntimeState state) {
            if (state == graf::windows::WebRuntimeState::unavailable) {
                const auto detail = cabinet_->webView().failureDetail();
                showCabinetFallback(L"Не удалось открыть кабинет", L"Запись доступна отдельно. Повторите загрузку. " + std::wstring(winrt::to_hstring(detail).c_str()));
                runtimeText_.Text(L"Кабинет недоступен · локальная запись сохраняется на компьютере");
            } else if (state == graf::windows::WebRuntimeState::initializing) {
                showCabinetFallback(L"Загружаем кабинет…", L"Нативные управление записью и локальная очередь работают независимо.");
                runtimeText_.Text(L"Загружаем кабинет…");
            } else if (state == graf::windows::WebRuntimeState::authRequired) {
                localFallback_.Visibility(Visibility::Collapsed);
                runtimeText_.Text(L"Нужен вход · открываем кабинет");
            } else if (state == graf::windows::WebRuntimeState::ready) {
                if (capture_) (void)capture_->recover(graf::windows::RecoveryTrigger::authRecovered);
                localFallback_.Visibility(Visibility::Collapsed);
                runtimeText_.Text(L"Кабинет GRAF открыт");
            }
        });
        host.setQuitHandler([this]() { requestExit(); });
        host.setAuthSessionHandler([this](std::string token) {
            if (capture_) capture_->setAuthSessionToken(std::move(token));
        });
        host.setLocalRecordingHandler([this](std::string action, std::string id) {
            handleLocalRecording(action, id);
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
    }

    void updateLocalRecordings() {
        if (!cabinet_ || !capture_) return;
        std::string inventoryKey;
        for (const auto& item : capture_->localItems()) inventoryKey += item.localRecordingId + "\n";
        if (localScan_ && localScan_->done.load(std::memory_order_acquire)) {
            localMetadata_ = std::move(localScan_->packages);
            localMetadataKey_ = localScan_->key;
            localScan_.reset();
            ++localMetadataVersion_;
        }
        if (!localScan_ && (localMetadataRefreshRequested_ || inventoryKey != localMetadataKey_)) {
            localMetadataRefreshRequested_ = false;
            localScan_ = std::make_shared<LocalMetadataScan>();
            localScan_->key = inventoryKey;
            const auto scan = localScan_;
            const auto items = capture_->localItems();
            const auto root = capture_->custodyRoot();
            try { std::thread([scan, items, root] {
                try {
                    winrt::init_apartment(winrt::apartment_type::multi_threaded);
                    for (const auto& item : items) {
                        try { scan->packages.emplace_back(item.localRecordingId,
                            graf::windows::LocalRecordingPackage::inspect(item.packageDirectory, root)); }
                        catch (...) {} // Unreadable packages expose no playback capability.
                    }
                    winrt::uninit_apartment();
                } catch (...) {}
                scan->done.store(true, std::memory_order_release);
            }).detach(); } catch (...) {
                localScan_.reset();
                localMetadataKey_ = inventoryKey;
                localActionNotice_ = L"Не удалось проверить локальные файлы. Нажмите «Обновить кабинет», чтобы повторить.";
            }
        }
        const bool busy = capture_->uploadsBusy();
        const bool active = capture_->indicator().visible;
        std::string displayKey = inventoryKey + std::to_string(localMetadataVersion_) + (busy ? "B" : "-") + (active ? "A" : "-");
        for (const auto& item : capture_->localItems())
            displayKey += std::to_string(static_cast<int>(item.status)) + ":" + item.safeReason + "\n";
        if (displayKey == localDisplayKey_) return;
        localDisplayKey_ = std::move(displayKey);
        std::vector<graf::windows::WebViewLocalRecordingRow> rows;
        for (const auto& item : capture_->localItems()) {
            graf::windows::WebViewLocalRecordingRow row;
            row.id = item.localRecordingId;
            const auto metadata = std::find_if(localMetadata_.begin(), localMetadata_.end(),
                [&item](const auto& value) { return value.first == item.localRecordingId; });
            if (metadata != localMetadata_.end()) {
                row.durationSeconds = metadata->second.durationMs / 1000;
                row.canOpen = metadata->second.playbackAvailable;
            }
            using Status = graf::windows::UploadQueueStatus;
            switch (item.status) {
            case Status::pending: row.status = "Ожидает отправки"; break;
            case Status::uploading: row.status = "Отправляется"; break;
            case Status::retry:
                row.status = item.safeReason == "retry_budget_exhausted"
                    ? "Автоматические повторы остановлены · нажмите «Отправить»"
                    : "Ожидает повторной отправки";
                break;
            case Status::needsAuth:
                row.status = item.safeReason == "local_owner_unclaimed" ? "Подтвердите аккаунт для отправки" :
                    item.safeReason == "account_mismatch" ? "Нужен исходный аккаунт записи" :
                    item.safeReason == "account_identity_unavailable" ? "Не удалось подтвердить аккаунт" : "Войдите, чтобы отправить запись";
                break;
            case Status::uploaded: row.status = "Отправлено"; row.uploadComplete = true; break;
            case Status::quarantined: row.status = row.canOpen ? "Сохранена часть записи · не отправлена" : "Требует проверки · не отправлена"; break;
            }
            const bool known = capture_->localItem(row.id).has_value();
            row.canOpen = row.canOpen && known;
            row.canSend = known && !busy && (item.status == Status::pending || item.status == Status::retry || item.status == Status::needsAuth);
            row.canDelete = known && !busy && !active;
            rows.push_back(std::move(row));
        }
        cabinet_->webView().setLocalRecordings(std::move(rows));
    }

    void handleLocalRecording(const std::string& action, const std::string& id) {
        if (!capture_ || shuttingDown_) return;
        const auto item = capture_->localItem(id);
        if (!item) { localActionNotice_ = L"Запись недоступна. Обновите список."; return; }
        if (action == "send") {
            if (capture_->authSessionToken().empty()) {
                (void)cabinet_->open("https://rec.2brain.pro/login?next=/desktop/meetings");
                localActionNotice_ = L"Войдите в GRAF — запись остаётся на этом компьютере.";
            } else if (!capture_->currentAccount()) {
                localActionNotice_ = L"Сервер пока не подтвердил текущий аккаунт. Отправка приостановлена, запись сохранена локально.";
            } else if (item->ownerUserId.empty() && item->ownerWorkspaceId.empty()) {
                const auto expected = *capture_->currentAccount();
                const auto generation = capture_->authGeneration();
                confirmLocalAction(L"Отправить в текущий аккаунт?",
                    L"У выбранной локальной записи ещё нет подтверждённого владельца. Она будет закреплена за аккаунтом, открытым сейчас в кабинете, и отправлена на сервер GRAF.",
                    L"Подтвердить и отправить", [this, id, expected, generation] {
                        localActionNotice_ = capture_->assignLocalOwner(id, expected, generation) && capture_->sendLocalRecording(id)
                            ? L"Принадлежность сохранена. Запись добавлена в очередь отправки."
                            : L"Аккаунт или состояние записи изменились. Отправка отменена; проверьте аккаунт и повторите действие.";
                    });
            } else if (item->ownerUserId != capture_->currentAccount()->userId ||
                       item->ownerWorkspaceId != capture_->currentAccount()->workspaceId) {
                localActionNotice_ = L"Эта запись принадлежит другому аккаунту. Войдите в исходный аккаунт через меню профиля; запись остаётся на компьютере.";
            } else localActionNotice_ = capture_->sendLocalRecording(id) ? L"Запись добавлена в очередь отправки."
                : L"Отправка сейчас недоступна. Дождитесь завершения текущего действия.";
        } else if (action == "open") {
            const auto root = capture_->custodyRoot();
            const auto dispatcher = root_.DispatcherQueue();
            const auto alive = alive_;
            localActionNotice_ = L"Проверяем локальную запись…";
            try { std::thread([this, alive, dispatcher, item = *item, root] {
                bool playable = false;
                try {
                    winrt::init_apartment(winrt::apartment_type::multi_threaded);
                    playable = graf::windows::LocalRecordingPackage::inspect(item.packageDirectory, root).playbackAvailable;
                    winrt::uninit_apartment();
                } catch (...) {}
                dispatcher.TryEnqueue([this, alive, item, playable] {
                    if (!alive->load()) return;
                    const auto current = capture_->localItem(item.localRecordingId);
                    if (!playable || !current || current->packageDirectory != item.packageDirectory) {
                        localActionNotice_ = L"Файл прослушивания повреждён или недоступен. Локальная запись не удалена.";
                        return;
                    }
                    const auto file = item.packageDirectory / "meeting-review.m4a";
                    const auto result = reinterpret_cast<INT_PTR>(ShellExecuteW(mainWindowHandle_, L"open", file.c_str(), nullptr, nullptr, SW_SHOWNORMAL));
                    localActionNotice_ = result > 32 ? L"Запись открыта в проигрывателе Windows." : L"Не удалось открыть проигрыватель. Установите приложение для M4A.";
                });
            }).detach(); } catch (...) {
                localActionNotice_ = L"Не удалось начать проверку файла. Повторите открытие записи.";
            }
        } else if (action == "delete") {
            if (capture_->uploadsBusy() || capture_->indicator().visible) {
                localActionNotice_ = L"Дождитесь завершения записи или отправки, затем удалите локальную копию.";
                return;
            }
            confirmLocalAction(L"Удалить локальную запись?",
                L"Локальная копия выбранной записи будет перемещена в Корзину Windows. Уже отправленная запись на сервере не изменится.",
                L"Переместить в Корзину", [this, id] {
                    const auto result = capture_->removeLocalCopy(id, mainWindowHandle_);
                    localActionNotice_ = result == graf::windows::LocalCopyRemovalResult::removed
                        ? L"Локальная копия больше не хранится в GRAF. Если файл был на диске, он перемещён в Корзину Windows."
                        : L"Не удалось удалить локальную копию. Проверьте очередь и Корзину; повторная отправка приостановлена.";
                });
        }
    }

    void confirmLocalAction(hstring title, hstring body, hstring button, std::function<void()> confirmed) {
        if (localActionDialogOpen_) return;
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
                        if (operation.GetResults() == ContentDialogResult::Primary) confirmed();
                        updateLocalRecordings();
                    } catch (...) { localActionNotice_ = L"Не удалось завершить действие с локальной записью."; }
                });
            });
        } catch (...) { localActionDialogOpen_ = false; localActionNotice_ = L"Закройте другое диалоговое окно и повторите действие."; }
    }

    void showCabinetFallback(std::wstring title, std::wstring detail) {
        fallbackCabinetTitle_.Text(std::move(title));
        fallbackCabinetDetail_.Text(std::move(detail));
        localFallback_.Visibility(Visibility::Visible);
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
        settingsLayout.RequestedTheme(ElementTheme::Dark);
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
        settingsWindow_.Closed([this](auto const&, auto const&) {
            settingsWindow_ = nullptr;
            bulkAutomaticPreference_ = nullptr;
            automaticPreferencePickers_.clear();
            automaticSettingsError_ = nullptr;
        });
        settingsWindow_.Activate();
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
        const auto failed = automaticPreferenceError_ || settings.preferenceWriteFailed;
        automaticSettingsError_.Text(failed ? L"Настройки не сохранены. Предыдущий выбор продолжает действовать." : L"");
        automaticSettingsError_.Visibility(failed ? Visibility::Visible : Visibility::Collapsed);
    }

    graf::windows::AutomaticRecordingPrerequisites automaticPrerequisites() const {
        graf::windows::AutomaticRecordingPrerequisites result;
        result.capture = capture_->readiness();
        result.recordingAlreadyActive = capture_->indicator().visible;
        result.visibleIndicatorAvailable = indicatorWindow_ && indicatorText_;
        result.oneActionStopAvailable = result.visibleIndicatorAvailable && indicatorStop_ && indicatorStop_.IsEnabled();
        result.suppressed = shuttingDown_ || exitRequested_ || permissionDialogOpen_ || localActionDialogOpen_;
        return result;
    }

    void refreshAutomaticRecording() {
        if (detectionFuture_.valid() && detectionFuture_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try { detectionSnapshot_ = detectionFuture_.get(); }
            catch (...) { detectionSnapshot_ = {}; }
        }
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
        if (!decision.shouldStart || !automaticPrerequisites().allowsStart()) return;
        const auto key = graf::windows::VerifiedTargetRegistry::identityKey(automaticPolicy_.target());
        const auto target = std::find_if(detectionSnapshot_.observations.begin(), detectionSnapshot_.observations.end(), [&](const auto& item) {
            return graf::windows::VerifiedTargetRegistry::identityKey(item.identity) == key &&
                graf::windows::WindowsTargetDetector::isPromptCandidate(item, verifiedTargets_);
        });
        if (target == detectionSnapshot_.observations.end() || !ensureRecordingIndicator()) return;
        const auto result = capture_->record();
        if (result.accepted() && (result.state == graf::windows::SessionState::starting ||
                                  result.state == graf::windows::SessionState::recording)) {
            recordingStartedAt_ = 0;
            automaticPolicy_.captureAccepted();
        } else {
            automaticPolicy_.cancel();
        }
    }

    void updateAutomaticPrompt() {
        const auto view = graf::windows::AutomaticRecordingPrompt::view(automaticPolicy_);
        const auto key = graf::windows::VerifiedTargetRegistry::identityKey(automaticPolicy_.target());
        if (automaticPromptWindow_ && automaticPromptTargetKey_ != key) automaticPromptWindow_.Close();
        if (!view.visible) {
            if (automaticPromptWindow_) automaticPromptWindow_.Close();
            return;
        }
        if (!automaticPromptWindow_) {
            automaticPromptWindow_ = Window();
            automaticPromptTargetKey_ = key;
            const auto generation = ++automaticPromptGeneration_;
            automaticPromptWindow_.AppWindow().Title(L"Автозапись GRAF");
            automaticPromptWindow_.AppWindow().Resize(winrt::Windows::Graphics::SizeInt32{520, 300});
            StackPanel content;
            content.RequestedTheme(ElementTheme::Dark);
            content.Background(themeBrush(L"ApplicationPageBackgroundThemeBrush"));
            content.Padding(Thickness{24, 20, 24, 20});
            content.Spacing(14);
            auto title = TextBlock();
            title.Text(winrt::to_hstring(view.title));
            styleText(title, 20, FontWeights::SemiBold());
            content.Children().Append(title);
            automaticPromptText_ = TextBlock();
            styleText(automaticPromptText_, 14);
            content.Children().Append(automaticPromptText_);
            rememberAutomaticChoice_ = CheckBox();
            rememberAutomaticChoice_.Content(box_value(winrt::to_hstring(view.rememberChoiceLabel)));
            rememberAutomaticChoice_.IsChecked(false);
            content.Children().Append(rememberAutomaticChoice_);
            StackPanel actions;
            actions.Orientation(Orientation::Horizontal);
            actions.Spacing(8);
            auto start = styledButton(std::wstring(winrt::to_hstring(view.primaryAction).c_str()), true);
            start.Click([this, generation, key](auto const&, auto const&) {
                if (!automaticPromptWindow_ || automaticPromptGeneration_ != generation || automaticPolicy_.state() != graf::windows::AutomaticPromptState::countdown ||
                    graf::windows::VerifiedTargetRegistry::identityKey(automaticPolicy_.target()) != key) return;
                const auto checked = rememberAutomaticChoice_.IsChecked();
                const auto decision = automaticPolicy_.recordNow(checked && checked.Value(), detectionSnapshot_, automaticPrerequisites());
                automaticPreferenceError_ = automaticPolicy_.settings().preferenceWriteFailed;
                startAutomaticRecording(decision);
                refreshAutomaticSettings();
                refreshNativeState();
            });
            auto refuse = styledButton(std::wstring(winrt::to_hstring(view.secondaryAction).c_str()));
            refuse.Click([this, generation, key](auto const&, auto const&) {
                if (!automaticPromptWindow_ || automaticPromptGeneration_ != generation || automaticPolicy_.state() != graf::windows::AutomaticPromptState::countdown ||
                    graf::windows::VerifiedTargetRegistry::identityKey(automaticPolicy_.target()) != key) return;
                const auto checked = rememberAutomaticChoice_.IsChecked();
                (void)automaticPolicy_.refuse(checked && checked.Value());
                automaticPreferenceError_ = automaticPolicy_.settings().preferenceWriteFailed;
                refreshAutomaticSettings();
                refreshNativeState();
            });
            actions.Children().Append(start);
            actions.Children().Append(refuse);
            content.Children().Append(actions);
            automaticPromptWindow_.Content(content);
            automaticPromptWindow_.Closed([this, generation, key](auto const&, auto const&) {
                if (automaticPromptGeneration_ != generation) return;
                if (automaticPolicy_.state() == graf::windows::AutomaticPromptState::countdown &&
                    graf::windows::VerifiedTargetRegistry::identityKey(automaticPolicy_.target()) == key) automaticPolicy_.cancel();
                automaticPromptWindow_ = nullptr;
                automaticPromptText_ = nullptr;
                rememberAutomaticChoice_ = nullptr;
            });
            automaticPromptWindow_.Activate();
        }
        const auto description = deviceDisplayName(view.applicationName) + L". " +
            std::wstring(winrt::to_hstring(view.accessibleDescription).c_str());
        automaticPromptText_.Text(description);
        setAccessible(automaticPromptText_, description);
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

    void recordCapture() {
        if (exitRequested_ || !capture_ || capture_->indicator().visible || !ensureRecordingIndicator()) return;
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

    void requestExit() {
        if (!window_ || shuttingDown_) return;
        if (!capture_ || !capture_->indicator().visible) { window_.Close(); return; }
        exitRequested_ = true;
        automaticPolicy_.cancel();
        (void)capture_->stop();
        // Keep the window/indicator alive until UI polling finalizes the local
        // package and queue after both native workers have actually stopped.
    }

    bool ensureRecordingIndicator(bool show = true) {
        try {
            if (!indicatorWindow_) {
                indicatorWindow_ = Window();
                indicatorWindow_.AppWindow().Title(L"Запись — GRAF");
                indicatorWindow_.AppWindow().SetPresenter(winrt::Microsoft::UI::Windowing::AppWindowPresenterKind::CompactOverlay);
                indicatorWindow_.AppWindow().Resize(winrt::Windows::Graphics::SizeInt32{360, 150});
                auto panel = StackPanel();
                panel.RequestedTheme(ElementTheme::Dark);
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
            indicatorWindow_.Activate();
            if (!indicatorWindow_.AppWindow().IsVisible() || !indicatorStop_.IsEnabled() ||
                indicatorStop_.Visibility() != Visibility::Visible) throw winrt::hresult_error(E_FAIL);
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
        root_.Children().Append(error);
    }

    void refreshNativeState() {
        if (!capture_ || shuttingDown_) return;
        capture_->pollHealth();
        if (exitRequested_ && !capture_->indicator().visible) { window_.Close(); return; }
        if (capture_->indicator().state == graf::windows::SessionState::recording && recordingStartedAt_ == 0) {
            recordingStartedAt_ = GetTickCount64();
        }
        refreshShellPalette();
        if (cabinet_) {
            backButton_.IsEnabled(cabinet_->webView().canGoBack());
            forwardButton_.IsEnabled(cabinet_->webView().canGoForward());
        }
        const auto now = GetTickCount64();
        if (lastStateTick_ && now - lastStateTick_ > 5000) capture_->recover(graf::windows::RecoveryTrigger::wake);
        lastStateTick_ = now;
        if (now - lastUploadRecovery_ >= 30000) {
            capture_->recover(graf::windows::RecoveryTrigger::scheduled);
            lastUploadRecovery_ = now;
        }
        capture_->pollUploads();
        updateLocalRecordings();
        if (now - lastReadinessCheck_ >= 2000) {
            capture_->refreshReadiness();
            lastReadinessCheck_ = now;
        }
        capture_->refreshPermission();
        refreshAutomaticRecording();
        if (localActionNotice_ != previousLocalActionNotice_) {
            previousLocalActionNotice_ = localActionNotice_;
            attentionExpansionDismissed_ = false;
        }
        if (!hasInspectorAttention()) attentionExpansionDismissed_ = false;
        const auto& snapshot = capture_->indicator();
        const bool active = snapshot.visible;
        const auto& finalization = capture_->finalization();
        diagnosticsButton_.Visibility(!active && !capture_->diagnostics().empty() ? Visibility::Visible : Visibility::Collapsed);
        std::wstring outcome;
        if (snapshot.state == graf::windows::SessionState::failed) outcome = finalization.trustedPrefixRetained
            ? L"Запись прервана. Подтверждённый фрагмент сохранён локально, но не отправлен. Проверьте устройство перед новой записью."
            : L"Не удалось сохранить запись. Проверьте устройство и свободное место перед новой попыткой.";
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
        readinessText_.Text(active ? (paused ? L"Микрофон на паузе. Системный звук продолжает записываться." : L"Общий системный звук и локальный микрофон") : capture_->readinessSummary());
        recordButton_.Visibility(active ? Visibility::Collapsed : Visibility::Visible);
        recordButton_.IsEnabled(!active && capture_->recordingReady());
        permissionButton_.Visibility(!active && permissionMissing ? Visibility::Visible : Visibility::Collapsed);
        custodyStatus_.Text(capture_->custodySummary());
        recordingStrip_.Visibility(active ? Visibility::Visible : Visibility::Collapsed);
        recordingStripText_.Text(winrt::to_hstring(snapshot.statusText + (paused ? " · Микрофон на паузе" : " · Системный звук и микрофон")));
        if (active && recordingStartedAt_ != 0) {
            const auto seconds = (GetTickCount64() - recordingStartedAt_) / 1000;
            const auto timer = std::to_wstring(seconds / 60) + L":" + (seconds % 60 < 10 ? L"0" : L"") + std::to_wstring(seconds % 60);
            recordingStripText_.Text(std::wstring(recordingStripText_.Text().c_str()) + L" · " + timer);
        }
        setAccessible(recordingStripText_, std::wstring(recordingStripText_.Text().c_str()));
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
        if (tray_) tray_->setState(snapshot);
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
        if (active) pauseButton_.Content(box_value(snapshot.state == graf::windows::SessionState::paused ? L"Продолжить" : L"Пауза"));
        pauseButton_.IsEnabled(snapshot.state == graf::windows::SessionState::recording || paused);
        setAccessible(pauseButton_, paused ? L"Продолжить запись локального микрофона" : L"Поставить локальный микрофон на паузу");
        if (compactRecordButton_) compactRecordButton_.IsEnabled(!active && capture_->recordingReady());
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
    Window settingsWindow_{nullptr};
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
    TextBlock autoRecordDetail_{nullptr};
    Button recordButton_{nullptr};
    Button pauseButton_{nullptr};
    Button stopButton_{nullptr};
    std::unique_ptr<NativeCapture> capture_;
    std::unique_ptr<graf::windows::CabinetWindow> cabinet_;
    struct LocalMetadataScan {
        std::atomic_bool done{false};
        std::string key;
        std::vector<std::pair<std::string, graf::windows::LocalRecordingPackageSnapshot>> packages;
    };
    std::shared_ptr<std::atomic_bool> alive_ = std::make_shared<std::atomic_bool>(true);
    std::shared_ptr<LocalMetadataScan> localScan_;
    std::vector<std::pair<std::string, graf::windows::LocalRecordingPackageSnapshot>> localMetadata_;
    std::string localMetadataKey_;
    std::string localDisplayKey_;
    std::uint64_t localMetadataVersion_ = 0;
    bool localMetadataRefreshRequested_ = false;
    std::wstring localActionNotice_;
    std::wstring previousLocalActionNotice_;
    bool localActionDialogOpen_ = false;
    bool shuttingDown_ = false;
    ULONGLONG lastStateTick_ = 0;
    bool exitRequested_ = false;
    ULONGLONG lastUploadRecovery_ = 0;
    graf::windows::VerifiedTargetRegistry verifiedTargets_{graf::windows::VerifiedTargetRegistry::bundled()};
    graf::windows::AutomaticRecordingPolicy automaticPolicy_{verifiedTargets_};
    Window automaticPromptWindow_{nullptr};
    TextBlock automaticPromptText_{nullptr};
    CheckBox rememberAutomaticChoice_{nullptr};
    ComboBox bulkAutomaticPreference_{nullptr};
    TextBlock automaticSettingsError_{nullptr};
    std::vector<std::pair<graf::windows::VerifiedTargetIdentity, ComboBox>> automaticPreferencePickers_;
    bool updatingAutomaticPreferences_ = false;
    bool automaticPreferenceError_ = false;
    graf::windows::TargetDetectionSnapshot detectionSnapshot_;
    std::future<graf::windows::TargetDetectionSnapshot> detectionFuture_;
    graf::windows::DetectionClock::time_point lastDetectionRequest_{};
    std::string automaticPromptTargetKey_;
    std::uint64_t automaticPromptGeneration_ = 0;
};

} // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    try {
        winrt::handle instance{CreateMutexW(nullptr, FALSE, L"Local\\GRAF.Windows.Desktop")};
        if (!instance) return 1;
        if (GetLastError() == ERROR_ALREADY_EXISTS) {
            if (const auto window = FindWindowW(nullptr, L"GRAF")) {
                ShowWindow(window, SW_RESTORE);
                SetForegroundWindow(window);
            }
            return 0;
        }
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
