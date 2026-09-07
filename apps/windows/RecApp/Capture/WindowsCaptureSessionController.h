#pragma once

#include "../Audio/AudioTypes.h"
#include "../Audio/WasapiCaptureWorker.h"
#include "../Core/WindowsDesktopSession.h"
#include "../Permissions/WindowsReadinessGate.h"
#include "../Shell/RecordingIndicator.h"

#include <functional>
#include <chrono>
#include <atomic>
#include <condition_variable>
#include <deque>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>

namespace graf::windows {

struct CaptureFinalization {
    bool savedLocal = false;
    ReasonCode reason = ReasonCode::none;
    bool trustedPrefixRetained = false;
};

class WindowsCaptureSessionController final {
public:
    using BatchSink = std::function<bool(AudioBatch)>;
    // UI-thread polling callback: nullopt means native writer work is pending.
    // The callback owns dispatch; it must not wait for that work on the UI thread.
    using Finalizer = std::function<std::optional<CaptureFinalization>(ReasonCode)>;
    using MicrophonePauseHandler = std::function<void(bool)>;

    WindowsCaptureSessionController(std::string sessionId, BatchSink batchSink = {},
                                    Finalizer finalizer = {},
                                    MicrophonePauseHandler microphonePauseHandler = {});
    ~WindowsCaptureSessionController();

    WindowsCaptureSessionController(const WindowsCaptureSessionController&) = delete;
    WindowsCaptureSessionController& operator=(const WindowsCaptureSessionController&) = delete;

    void setEndpoints(WasapiEndpointSnapshot render, WasapiEndpointSnapshot microphone);
    // Record returns starting; health polling promotes it only after both
    // endpoints are ready. Stop may return stopping while cancellation unwinds.
    // Continue polling until terminal: only the UI poll finalizes a pending Stop.
    [[nodiscard]] TransitionResult record(const ReadinessInputs& readiness);
    [[nodiscard]] TransitionResult pause();
    [[nodiscard]] TransitionResult resume();
    [[nodiscard]] TransitionResult stop();
    [[nodiscard]] TransitionResult pollHealth();

    // Commands, health polling and these views are UI-thread-only. Workers
    // serialize the sink and latch faults; they never mutate session/indicator.
    [[nodiscard]] const WindowsDesktopSession& session() const noexcept { return session_; }
    [[nodiscard]] const RecordingIndicator& indicator() const noexcept { return indicator_; }
    [[nodiscard]] const CaptureFinalization& finalization() const noexcept { return finalization_; }
    [[nodiscard]] CaptureClockDiagnostics clockDiagnostics(AudioSource source) const noexcept;

private:
    friend struct CaptureSessionTestPeer;
    [[nodiscard]] bool startWorkers();
    [[nodiscard]] ReasonCode captureFailureReason() const noexcept;
    void stopWorkers() noexcept;
    [[nodiscard]] bool enqueueBatch(AudioBatch batch);
    void dispatchLoop() noexcept;
    void requestDispatcherStop() noexcept;
    void joinDispatcher() noexcept;
    [[nodiscard]] TransitionResult finishStop();
    [[nodiscard]] bool handleBatch(AudioBatch batch);
    [[nodiscard]] bool processBatch(AudioBatch batch);
    void latchFault(ReasonCode reason) noexcept;

    WindowsDesktopSession session_;
    BatchSink batchSink_;
    Finalizer finalizer_;
    MicrophonePauseHandler microphonePauseHandler_;
    RecordingIndicator indicator_;
    std::unique_ptr<WasapiCaptureWorker> renderWorker_;
    std::unique_ptr<WasapiCaptureWorker> microphoneWorker_;
    CaptureFinalization finalization_;
    bool pollingFinalizer_ = false; // UI-thread-only reentrancy guard.
    std::chrono::steady_clock::time_point startupDeadline_{};
    std::atomic_bool acceptingBatches_{false};
    std::atomic<ReasonCode> captureFault_{ReasonCode::none};
    std::mutex captureMutex_;
    static constexpr std::size_t maxPendingBatches_ = 256;
    std::mutex dispatchMutex_;
    std::condition_variable dispatchCondition_;
    std::deque<AudioBatch> pendingBatches_;
    std::thread dispatchThread_;
    std::atomic_bool dispatchFinished_{true};
    std::atomic_bool dispatchBusy_{false};
    bool dispatchStopRequested_ = false;
};

} // namespace graf::windows
