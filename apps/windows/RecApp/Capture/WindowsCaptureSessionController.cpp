#include "WindowsCaptureSessionController.h"

namespace graf::windows {

WindowsCaptureSessionController::WindowsCaptureSessionController(std::string sessionId, BatchSink batchSink,
                                                                 Finalizer finalizer,
                                                                 MicrophonePauseHandler microphonePauseHandler)
    : session_(std::move(sessionId)), batchSink_(std::move(batchSink)), finalizer_(std::move(finalizer)),
      microphonePauseHandler_(std::move(microphonePauseHandler)),
      indicator_([this] { handleStop(); }) {}

WindowsCaptureSessionController::~WindowsCaptureSessionController() { stopWorkers(); }

void WindowsCaptureSessionController::setEndpoints(WasapiEndpointSnapshot render,
                                                    WasapiEndpointSnapshot microphone) {
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
    captureFaulted_.store(false);
    if (!session_.markReady().accepted() || !session_.beginStart().accepted() || !startWorkers() ||
        captureFaulted_.load()) {
        stopWorkers();
        const auto failed = session_.fail(ReasonCode::endpointInvalidated);
        indicator_.publish(session_.state(), session_.reason());
        return failed;
    }
    TransitionResult started;
    {
        std::lock_guard<std::mutex> lock(captureMutex_);
        started = session_.startRecording();
    }
    indicator_.publish(session_.state(), session_.reason());
    return started;
}

TransitionResult WindowsCaptureSessionController::pause() {
    std::lock_guard<std::mutex> lock(captureMutex_);
    const auto result = session_.pause();
    if (result.accepted()) {
        if (microphonePauseHandler_) microphonePauseHandler_(true);
        indicator_.publish(session_.state(), session_.reason());
    }
    return result;
}

TransitionResult WindowsCaptureSessionController::resume() {
    std::lock_guard<std::mutex> lock(captureMutex_);
    const auto result = session_.resume();
    if (result.accepted()) {
        if (microphonePauseHandler_) microphonePauseHandler_(false);
        indicator_.publish(session_.state(), session_.reason());
    }
    return result;
}

TransitionResult WindowsCaptureSessionController::stop() {
    TransitionResult requested;
    {
        std::lock_guard<std::mutex> lock(captureMutex_);
        requested = session_.stop();
        if (requested.status == TransitionStatus::accepted) captureFaulted_.store(true);
    }
    if (requested.status == TransitionStatus::rejected) return requested;
    if (requested.status == TransitionStatus::idempotent) return requested;
    stopWorkers();
    indicator_.publish(session_.state(), session_.reason());
    if (!session_.beginFinalizing().accepted()) return {TransitionStatus::rejected, session_.state(), session_.reason()};
    const auto finalized = finalizer_ ? finalizer_() : CaptureFinalization{};
    const auto result = finalized.savedLocal ? session_.saveLocal() : session_.fail(
        finalized.reason == ReasonCode::none ? ReasonCode::finalizationFailed : finalized.reason);
    indicator_.publish(session_.state(), session_.reason());
    return result;
}

bool WindowsCaptureSessionController::startWorkers() {
    if (!renderWorker_ || !microphoneWorker_) return false;
    const auto callback = [this](AudioBatch batch) { return handleBatch(std::move(batch)); };
    if (renderWorker_->start(callback) != CaptureWorkerError::none) return false;
    if (captureFaulted_.load()) {
        renderWorker_->stop();
        return false;
    }
    if (microphoneWorker_->start(callback) != CaptureWorkerError::none) {
        renderWorker_->stop();
        return false;
    }
    return true;
}

void WindowsCaptureSessionController::stopWorkers() noexcept {
    if (renderWorker_) renderWorker_->stop();
    if (microphoneWorker_) microphoneWorker_->stop();
}

bool WindowsCaptureSessionController::handleBatch(AudioBatch batch) {
    if (captureFaulted_.load()) return false;
    std::lock_guard<std::mutex> lock(captureMutex_);
    if (captureFaulted_.load()) return false;
    if (batchSink_ && !batchSink_(std::move(batch))) {
        captureFaulted_.store(true);
        (void)session_.markDegraded(ReasonCode::clockDiscontinuity);
        indicator_.publish(session_.state(), session_.reason());
        return false;
    }
    return true;
}

void WindowsCaptureSessionController::handleStop() { (void)stop(); }

} // namespace graf::windows
