#pragma once

#include "../Audio/AudioTypes.h"
#include "../Audio/WasapiCaptureWorker.h"
#include "../Core/WindowsDesktopSession.h"
#include "../Permissions/WindowsReadinessGate.h"
#include "../Shell/RecordingIndicator.h"

#include <functional>
#include <memory>
#include <string>

namespace graf::windows {

struct CaptureFinalization {
    bool savedLocal = false;
    ReasonCode reason = ReasonCode::none;
};

class WindowsCaptureSessionController final {
public:
    using BatchSink = std::function<bool(AudioBatch)>;
    using Finalizer = std::function<CaptureFinalization()>;

    WindowsCaptureSessionController(std::string sessionId, BatchSink batchSink = {},
                                    Finalizer finalizer = {});
    ~WindowsCaptureSessionController();

    WindowsCaptureSessionController(const WindowsCaptureSessionController&) = delete;
    WindowsCaptureSessionController& operator=(const WindowsCaptureSessionController&) = delete;

    void setEndpoints(WasapiEndpointSnapshot render, WasapiEndpointSnapshot microphone);
    [[nodiscard]] TransitionResult record(const ReadinessInputs& readiness);
    [[nodiscard]] TransitionResult pause();
    [[nodiscard]] TransitionResult resume();
    [[nodiscard]] TransitionResult stop();

    [[nodiscard]] const WindowsDesktopSession& session() const noexcept { return session_; }
    [[nodiscard]] const RecordingIndicator& indicator() const noexcept { return indicator_; }

private:
    [[nodiscard]] bool startWorkers();
    void stopWorkers() noexcept;
    void handleBatch(AudioBatch batch);
    void handleStop();

    WindowsDesktopSession session_;
    BatchSink batchSink_;
    Finalizer finalizer_;
    RecordingIndicator indicator_;
    std::unique_ptr<WasapiCaptureWorker> renderWorker_;
    std::unique_ptr<WasapiCaptureWorker> microphoneWorker_;
};

} // namespace graf::windows
