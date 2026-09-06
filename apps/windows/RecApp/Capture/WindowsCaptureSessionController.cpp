#include "WindowsCaptureSessionController.h"

namespace graf::windows {
namespace {

ReasonCode workerReason(CaptureWorkerError error) noexcept {
    switch (error) {
    case CaptureWorkerError::none: return ReasonCode::none;
    case CaptureWorkerError::unsupportedFormat: return ReasonCode::formatNormalizationUnavailable;
    case CaptureWorkerError::bufferOverflow: return ReasonCode::queueOverflow;
    default: return ReasonCode::endpointInvalidated;
    }
}

} // namespace

WindowsCaptureSessionController::WindowsCaptureSessionController(std::string sessionId, BatchSink batchSink,
                                                                 Finalizer finalizer,
                                                                 MicrophonePauseHandler microphonePauseHandler)
    : session_(std::move(sessionId)), batchSink_(std::move(batchSink)), finalizer_(std::move(finalizer)),
      microphonePauseHandler_(std::move(microphonePauseHandler)),
      indicator_([this] { (void)stop(); }) {}

WindowsCaptureSessionController::~WindowsCaptureSessionController() {
    stopWorkers();
    // Join while the callback fence/mutex/sink still exist. Normally UI polling
    // has already observed completion; forced destruction can wait for native COM.
    renderWorker_.reset();
    microphoneWorker_.reset();
}

void WindowsCaptureSessionController::setEndpoints(WasapiEndpointSnapshot render,
                                                    WasapiEndpointSnapshot microphone) {
    // A second Record must not replace live workers before readiness rejects it.
    if (session_.state() != SessionState::idle) return;
    renderWorker_ = std::make_unique<WasapiCaptureWorker>(std::move(render), true);
    microphoneWorker_ = std::make_unique<WasapiCaptureWorker>(std::move(microphone), false);
}

TransitionResult WindowsCaptureSessionController::record(const ReadinessInputs& readiness) {
    const auto checked = session_.beginReadinessCheck();
    if (!checked.accepted()) return checked;
    const auto gate = WindowsReadinessGate::evaluate(readiness);
    if (!gate.recordingReady) {
        const auto blocked = session_.block(gate.blockers[0]);
        indicator_.publish(session_.state(), session_.reason());
        return blocked;
    }
    (void)session_.markReady();
    const auto starting = session_.beginStart();
    indicator_.publish(session_.state(), session_.reason());
    acceptingBatches_.store(false);
    startupDeadline_ = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    if (!startWorkers()) return stop();
    return starting;
}

TransitionResult WindowsCaptureSessionController::pause() {
    (void)pollHealth();
    std::lock_guard<std::mutex> lock(captureMutex_);
    const auto result = session_.pause();
    if (result.accepted()) {
        if (microphonePauseHandler_) microphonePauseHandler_(true);
        indicator_.publish(session_.state(), session_.reason());
    }
    return result;
}

TransitionResult WindowsCaptureSessionController::resume() {
    (void)pollHealth();
    std::lock_guard<std::mutex> lock(captureMutex_);
    const auto result = session_.resume();
    if (result.accepted()) {
        if (microphonePauseHandler_) microphonePauseHandler_(false);
        indicator_.publish(session_.state(), session_.reason());
    }
    return result;
}

TransitionResult WindowsCaptureSessionController::pollHealth() {
    const auto state = session_.state();
    if (state == SessionState::stopping || state == SessionState::finalizing) return finishStop();
    if (state == SessionState::starting || state == SessionState::recording ||
        state == SessionState::paused || state == SessionState::degraded) {
        auto failure = captureFailureReason();
        if (failure == ReasonCode::none && state == SessionState::starting &&
            std::chrono::steady_clock::now() >= startupDeadline_) failure = ReasonCode::endpointInvalidated;
        if (failure != ReasonCode::none) {
            latchFault(failure);
            (void)session_.markDegraded(failure);
            indicator_.publish(session_.state(), session_.reason());
            return stop();
        }
        if (state == SessionState::starting && renderWorker_->ready() && microphoneWorker_->ready()) {
            const auto started = session_.startRecording();
            indicator_.publish(session_.state(), session_.reason());
            acceptingBatches_.store(true);
            return started;
        }
    }
    return {TransitionStatus::idempotent, session_.state(), session_.reason()};
}

TransitionResult WindowsCaptureSessionController::stop() {
    const auto beforeStop = captureFailureReason();
    const auto requested = session_.stop();
    if (requested.status != TransitionStatus::accepted) return requested;
    indicator_.publish(session_.state(), session_.reason());
    // Latch unexpected worker termination before the deliberate shutdown.
    if (beforeStop != ReasonCode::none) latchFault(beforeStop);
    stopWorkers();
    const auto result = finishStop();
    return {TransitionStatus::accepted, result.state, result.reason};
}

TransitionResult WindowsCaptureSessionController::finishStop() {
    if (pollingFinalizer_) return {TransitionStatus::idempotent, session_.state(), session_.reason()};
    for (const auto* worker : {renderWorker_.get(), microphoneWorker_.get()}) {
        if (worker && !worker->finished()) return {TransitionStatus::idempotent, session_.state(), session_.reason()};
    }
    // Also fence direct/synthetic producers, without making UI Stop wait on a
    // sink. A later poll retries after its in-flight call returns.
    std::unique_lock<std::mutex> lock(captureMutex_, std::try_to_lock);
    if (!lock.owns_lock()) return {TransitionStatus::idempotent, session_.state(), session_.reason()};
    const auto failure = captureFailureReason();
    if (session_.state() == SessionState::stopping) {
        (void)session_.beginFinalizing();
        indicator_.publish(session_.state(), session_.reason());
    }
    pollingFinalizer_ = true;
    try {
        const auto result = finalizer_ ? finalizer_(failure) : std::optional<CaptureFinalization>{CaptureFinalization{}};
        if (!result) {
            pollingFinalizer_ = false;
            return {TransitionStatus::idempotent, session_.state(), session_.reason()};
        }
        finalization_ = *result;
    } catch (...) {
        finalization_ = {false, ReasonCode::finalizationFailed};
    }
    pollingFinalizer_ = false;
    if (failure != ReasonCode::none) {
        finalization_.savedLocal = false;
        if (finalization_.reason == ReasonCode::none) finalization_.reason = failure;
    }
    const auto result = finalization_.savedLocal && finalization_.reason == ReasonCode::none
        ? session_.saveLocal()
        : session_.fail(finalization_.reason == ReasonCode::none
            ? ReasonCode::finalizationFailed : finalization_.reason);
    indicator_.publish(session_.state(), session_.reason());
    return result;
}

bool WindowsCaptureSessionController::startWorkers() {
    if (!renderWorker_ || !microphoneWorker_ || !batchSink_) {
        latchFault(ReasonCode::endpointInvalidated);
        return false;
    }
    const auto callback = [this](AudioBatch batch) { return handleBatch(std::move(batch)); };
    for (auto* worker : {renderWorker_.get(), microphoneWorker_.get()}) {
        const auto error = worker->start(callback);
        if (error != CaptureWorkerError::none) latchFault(workerReason(error));
        if (captureFault_.load() != ReasonCode::none) return false;
    }
    return true;
}

ReasonCode WindowsCaptureSessionController::captureFailureReason() const noexcept {
    const auto pending = captureFault_.load();
    if (pending != ReasonCode::none) return pending;
    for (const auto* worker : {renderWorker_.get(), microphoneWorker_.get()}) {
        if (worker == nullptr) continue;
        const auto error = workerReason(worker->lastError());
        if (error != ReasonCode::none) return error;
        const auto state = session_.state();
        if ((state == SessionState::starting || state == SessionState::recording ||
             state == SessionState::paused || state == SessionState::degraded) && worker->finished())
            return ReasonCode::endpointInvalidated;
    }
    return ReasonCode::none;
}

void WindowsCaptureSessionController::stopWorkers() noexcept {
    acceptingBatches_.store(false);
    if (renderWorker_) renderWorker_->stop();
    if (microphoneWorker_) microphoneWorker_->stop();
}

void WindowsCaptureSessionController::latchFault(ReasonCode reason) noexcept {
    auto expected = ReasonCode::none;
    (void)captureFault_.compare_exchange_strong(expected, reason);
}

bool WindowsCaptureSessionController::handleBatch(AudioBatch batch) {
    if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none) return true;
    std::lock_guard<std::mutex> lock(captureMutex_);
    // Do not manufacture a worker overflow for a callback during shutdown.
    if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none) return true;
    try {
        if (!batchSink_(std::move(batch))) latchFault(ReasonCode::clockDiscontinuity);
    } catch (...) {
        latchFault(ReasonCode::finalizationFailed);
    }
    return true;
}

} // namespace graf::windows
