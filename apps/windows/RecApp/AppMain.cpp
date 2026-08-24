#ifdef _WIN32

#include "Audio/RecordingAudioTimeline.h"
#include "Audio/WasapiEndpointEnumerator.h"
#include "Capture/WindowsCaptureSessionController.h"
#include "Recording/V5LocalRecordingWriter.h"
#include "Shell/CabinetWindow.h"

#include <windows.h>
#include <knownfolders.h>
#include <shlobj.h>

#include <winrt/Microsoft.UI.Xaml.h>
#include <winrt/Microsoft.UI.Xaml.Controls.h>
#include <winrt/Microsoft.UI.Xaml.Controls.Primitives.h>
#include <winrt/Microsoft.UI.Windowing.h>

#include <filesystem>
#include <memory>
#include <utility>

namespace {

using namespace winrt;
using namespace Microsoft::UI::Xaml;
using namespace Microsoft::UI::Xaml::Controls;

class UnavailableAec3 final : public graf::windows::IAec3Processor {
public:
    bool process(const float*, const float*, float*) noexcept override { return false; }
};

std::filesystem::path localCustodyRoot() {
    PWSTR raw = nullptr;
    if (FAILED(SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DEFAULT, nullptr, &raw)) || raw == nullptr) {
        return {};
    }
    std::filesystem::path result(raw);
    CoTaskMemFree(raw);
    result /= L"GRAF";
    result /= L"recordings";
    std::error_code error;
    std::filesystem::create_directories(result, error);
    return error ? std::filesystem::path{} : result;
}

struct NativeCapture final {
    NativeCapture()
        : aec_(std::make_shared<UnavailableAec3>()),
          timeline_(std::make_shared<graf::windows::RecordingAudioTimeline>(*aec_)),
          custodyRoot_(localCustodyRoot()),
          writer_(std::make_shared<graf::windows::V5LocalRecordingWriter>(
              custodyRoot_, custodyRoot_ / "windows-session")),
          controller_(std::make_unique<graf::windows::WindowsCaptureSessionController>(
              "windows-session",
              [timeline = timeline_, writer = writer_](graf::windows::AudioBatch batch) {
                  if (!timeline->push(std::move(batch))) return false;
                  for (const auto& frame : timeline->takeFrames()) {
                      if (!writer->append(frame)) return false;
                  }
                  return true;
              },
              [timeline = timeline_, writer = writer_]() {
                  for (const auto& frame : timeline->takeFrames()) {
                      if (!writer->append(frame)) return {false, graf::windows::ReasonCode::storageUnavailable};
                  }
                  if (!timeline->healthy()) return {false, graf::windows::ReasonCode::aecUnavailable};
                  const auto result = writer->finalize();
                  return {result.ok(), result.ok() ? graf::windows::ReasonCode::none :
                      graf::windows::ReasonCode::finalizationFailed};
              },
              [timeline = timeline_](bool paused) { timeline->setMicrophonePaused(paused); })) {
        const auto endpoints = enumerator_.snapshot();
        if (!endpoints.ok()) return;
        graf::windows::WasapiEndpointSnapshot render;
        graf::windows::WasapiEndpointSnapshot microphone;
        for (const auto& endpoint : endpoints.endpoints) {
            if (endpoint.flow == graf::windows::WasapiDataFlow::render && endpoint.isDefault) render = endpoint;
            if (endpoint.flow == graf::windows::WasapiDataFlow::capture &&
                graf::windows::WasapiEndpointEnumerator::isAllowedMicrophone(endpoint)) microphone = endpoint;
        }
        if (!render.stableId.empty() && !microphone.stableId.empty()) controller_->setEndpoints(render, microphone);
        readiness_.recordingPolicyAllowed = true;
        readiness_.microphoneEndpointReady = !microphone.stableId.empty();
        readiness_.renderEndpointReady = !render.stableId.empty();
        // The first native slice has no unverified resampler. Refuse device
        // formats outside the canonical 48 kHz timeline until the pinned
        // normalizer is validated on Windows hardware.
        readiness_.formatNormalizationReady = render.sampleRate == 48'000 &&
            microphone.sampleRate == 48'000;
        readiness_.microphonePermissionGranted = false;
        // No untreated-microphone fallback: without the pinned backend Record
        // remains visibly blocked until the approved AEC3 binding is available.
        readiness_.aecReady = false;
        readiness_.storageWritable = !custodyRoot_.empty();
        readiness_.webViewRuntimeReady = false;
        readiness_.aacEncoderReady = true;
    }

    [[nodiscard]] graf::windows::TransitionResult record() { return controller_->record(readiness_); }
    [[nodiscard]] graf::windows::TransitionResult pause() { return controller_->pause(); }
    [[nodiscard]] graf::windows::TransitionResult resume() { return controller_->resume(); }
    [[nodiscard]] graf::windows::TransitionResult stop() { return controller_->stop(); }
    [[nodiscard]] const graf::windows::RecordingIndicatorSnapshot& indicator() const noexcept {
        return controller_->indicator().snapshot();
    }

private:
    graf::windows::WasapiEndpointEnumerator enumerator_;
    std::shared_ptr<UnavailableAec3> aec_;
    std::shared_ptr<graf::windows::RecordingAudioTimeline> timeline_;
    std::filesystem::path custodyRoot_;
    std::shared_ptr<graf::windows::V5LocalRecordingWriter> writer_;
    std::unique_ptr<graf::windows::WindowsCaptureSessionController> controller_;
    graf::windows::ReadinessInputs readiness_;
};

class GrafApp final : public ApplicationT<GrafApp> {
public:
    void OnLaunched(LaunchActivatedEventArgs const&) override {
        window_ = Window();
        capture_ = std::make_unique<NativeCapture>();

        root_ = Grid();
        auto statusRow = RowDefinition();
        statusRow.Height(GridLengthHelper::FromValueAndType(44.0, GridUnitType::Pixel));
        auto webRow = RowDefinition();
        webRow.Height(GridLengthHelper::FromValueAndType(1.0, GridUnitType::Star));
        root_.RowDefinitions().Append(statusRow);
        root_.RowDefinitions().Append(webRow);

        auto status = StackPanel();
        status.Orientation(Orientation::Horizontal);
        status.Spacing(8.0);
        status.Padding(Thickness{12, 6, 12, 6});
        statusText_ = TextBlock();
        statusText_.Text(L"GRAF: нативное управление Windows готово");
        recordButton_ = Button();
        recordButton_.Content(box_value(L"Записать"));
        pauseButton_ = Button();
        pauseButton_.Content(box_value(L"Пауза"));
        stopButton_ = Button();
        stopButton_.Content(box_value(L"Остановить"));
        stopButton_.Visibility(Visibility::Collapsed);
        repairButton_ = Button();
        repairButton_.Content(box_value(L"Повторить кабинет"));
        repairButton_.Visibility(Visibility::Collapsed);
        status.Children().Append(statusText_);
        status.Children().Append(recordButton_);
        status.Children().Append(pauseButton_);
        status.Children().Append(stopButton_);
        status.Children().Append(repairButton_);
        Grid::SetRow(status, 0);
        root_.Children().Append(status);

        webView_ = WebView2();
        Grid::SetRow(webView_, 1);
        root_.Children().Append(webView_);
        window_.Content(root_);
        window_.AppWindow().Title(L"GRAF");

        recordButton_.Click([this](auto const&, auto const&) { (void)capture_->record(); refreshNativeState(); });
        pauseButton_.Click([this](auto const&, auto const&) {
            if (capture_->indicator().state == graf::windows::SessionState::paused) (void)capture_->resume();
            else (void)capture_->pause();
            refreshNativeState();
        });
        stopButton_.Click([this](auto const&, auto const&) { (void)capture_->stop(); refreshNativeState(); });
        repairButton_.Click([this](auto const&, auto const&) { recreateCabinet(); });
        configureCabinet();
        window_.Activate();
    }

private:
    void configureCabinet() {
        cabinet_ = std::make_unique<graf::windows::CabinetWindow>();
        auto& host = cabinet_->webView();
        host.setNavigationHandler([this](graf::windows::RouteEvaluation evaluation) {
            if (evaluation.decision == graf::windows::RouteDecision::allow) statusText_.Text(L"Кабинет GRAF открыт");
        });
        host.setRuntimeHandler([this](graf::windows::WebRuntimeState state) {
            if (state == graf::windows::WebRuntimeState::unavailable) {
                statusText_.Text(L"Кабинет недоступен. Нативная запись остаётся доступной.");
                repairButton_.Visibility(Visibility::Visible);
            } else if (state == graf::windows::WebRuntimeState::ready) {
                statusText_.Text(L"Кабинет GRAF открыт");
                repairButton_.Visibility(Visibility::Collapsed);
            }
        });
        host.setWebMessageHandler([this](graf::windows::WebViewBridgeEnvelope) {
            // Capture controls stay on the native surface; web messages have no
            // authority to start, stop, pause or access local files.
        });
        cabinet_->attach(webView_);
    }

    void recreateCabinet() {
        const auto oldWebView = webView_;
        if (oldWebView) root_.Children().Remove(oldWebView);
        webView_ = WebView2();
        Grid::SetRow(webView_, 1);
        root_.Children().Append(webView_);
        configureCabinet();
    }

    void refreshNativeState() {
        const auto& snapshot = capture_->indicator();
        statusText_.Text(winrt::to_hstring(snapshot.statusText));
        stopButton_.Visibility(snapshot.stopAvailable ? Visibility::Visible : Visibility::Collapsed);
        pauseButton_.IsEnabled(snapshot.visible);
    }

    Window window_{nullptr};
    Grid root_{nullptr};
    WebView2 webView_{nullptr};
    TextBlock statusText_{nullptr};
    Button recordButton_{nullptr};
    Button pauseButton_{nullptr};
    Button stopButton_{nullptr};
    Button repairButton_{nullptr};
    std::unique_ptr<NativeCapture> capture_;
    std::unique_ptr<graf::windows::CabinetWindow> cabinet_;
};

} // namespace

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    winrt::init_apartment(winrt::apartment_type::single_threaded);
    Microsoft::UI::Xaml::Application::Start([](auto&&) { winrt::make<GrafApp>(); });
    return 0;
}

#else

int main() { return 0; }

#endif
