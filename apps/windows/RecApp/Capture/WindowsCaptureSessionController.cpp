#include "WindowsCaptureSessionController.h"

#include "CaptureReasonMapping.h"

namespace graf::windows {

CaptureClockDiagnostics WindowsCaptureSessionController::clockDiagnostics(AudioSource source) const noexcept {
    const auto& worker = source == AudioSource::systemRender ? renderWorker_ : microphoneWorker_;
    return worker ? worker->clockDiagnostics() : CaptureClockDiagnostics{};
}

WindowsCaptureSessionController::WindowsCaptureSessionController(std::string sessionId, BatchSink batchSink,
                                                                 Finalizer finalizer,
                                                                 MicrophonePauseHandler microphonePauseHandler)
    : session_(std::move(sessionId)), batchSink_(std::move(batchSink)), finalizer_(std::move(finalizer)),
      microphonePauseHandler_(std::move(microphonePauseHandler)),
      indicator_([this] { (void)stop(); }) {}

WindowsCaptureSessionController::~WindowsCaptureSessionController() {
    acceptingBatches_.store(false, std::memory_order_release);
    stopWorkers();
    // Join while the callback fence/mutex/sink still exist. Normally UI polling
    // has already observed completion; forced destruction can wait for native COM.
    renderWorker_.reset();
    microphoneWorker_.reset();
    joinDispatcher();
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
    if (!startWorkers()) return stop(RecordingStopReason::interruption);
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
        const bool startupExpired = failure == ReasonCode::none && state == SessionState::starting &&
            std::chrono::steady_clock::now() >= startupDeadline_;
        if (startupExpired) {
            // Истёк срок запуска: виноват не «отключившийся» источник, а тот,
            // который так и не поднялся. Человеку нужен точный адрес проблемы.
            failure = renderWorker_ && renderWorker_->ready() ? ReasonCode::microphoneEndpointUnavailable
                                                              : ReasonCode::renderEndpointUnavailable;
        }
        if (failure != ReasonCode::none) {
            latchFault(failure);
            (void)session_.markDegraded(failure);
            indicator_.publish(session_.state(), session_.reason());
            // A fault-driven stop must never be classified as a deliberate one.
            return stop(RecordingStopReason::interruption);
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

TransitionResult WindowsCaptureSessionController::stop(RecordingStopReason reason) {
    const auto beforeStop = captureFailureReason();
    const auto requested = session_.stop();
    if (requested.status != TransitionStatus::accepted) return requested;
    // Latch only after the transition was accepted, so an idempotent repeat
    // cannot overwrite the reason the original stop was classified with.
    // Stop is the linearization point for capture delivery: callbacks already
    // accepted before it may drain, but a callback that races with or follows
    // Stop must never append another batch to the dispatcher.
    acceptingBatches_.store(false, std::memory_order_release);
    stopReason_ = reason;
    drainDeadline_ = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    indicator_.publish(session_.state(), session_.reason());
    // Latch unexpected worker termination before the deliberate shutdown.
    if (beforeStop != ReasonCode::none) latchFault(beforeStop);
    stopWorkers();
    // Enqueue under the same mutex as data: a producer that accepted before
    // Stop finishes its insertion first; all later callbacks are fenced out.
    // EOS need not wait for UI polling or native cleanup. Finalization still
    // waits for both workers as well as dispatcher/sink completion below.
    if (!sourceEndsEnqueued_) {
        if (dispatchThread_.joinable()) {
            const auto renderQueued = enqueueSourceEnd(AudioSource::systemRender);
            const auto microphoneQueued = enqueueSourceEnd(AudioSource::microphone);
            if (!renderQueued || !microphoneQueued) latchFault(ReasonCode::queueOverflow);
        }
        sourceEndsEnqueued_ = true;
    }
    requestDispatcherStop();
    const auto result = finishStop();
    return {TransitionStatus::accepted, result.state, result.reason};
}

void WindowsCaptureSessionController::markDrainTimedOut() {
    // Do not overwrite the original source/sink fault. Timeout is independently
    // sticky through writer polling, while ownership remains behind the fences.
    drainTimedOut_ = true;
    finalization_.reason = ReasonCode::finalizationFailed;
    indicator_.publish(session_.state(), ReasonCode::finalizationFailed);
}

TransitionResult WindowsCaptureSessionController::finishStop() {
    if (pollingFinalizer_) return {TransitionStatus::idempotent, session_.state(), session_.reason()};
    // Sample before inspecting a pending fence. A UI scheduling pause between
    // observing it and returning must not turn an on-time completion into a fault.
    const auto observedAt = std::chrono::steady_clock::now();
    const auto pendingDrain = [this, observedAt] {
        if (session_.state() == SessionState::stopping && observedAt >= drainDeadline_) {
            // Keep the active lease and memory until all completion fences.
            // Publish failure without a terminal state that would release them.
            markDrainTimedOut();
        }
        return TransitionResult{TransitionStatus::idempotent, session_.state(),
            finalization_.reason == ReasonCode::none ? session_.reason() : finalization_.reason};
    };
    for (const auto* worker : {renderWorker_.get(), microphoneWorker_.get()}) {
        if (worker && !worker->finished()) return pendingDrain();
        if (worker && session_.state() == SessionState::stopping && worker->finishedAt() > drainDeadline_)
            markDrainTimedOut();
    }
    // Only the thread's completion fence permits joining. An empty queue and
    // idle sink alone do not mean the dispatcher has returned yet.
    if (!dispatchFinished_.load(std::memory_order_acquire)) return pendingDrain();
    if (dispatchThread_.joinable() && sourceEndsProcessed_.load(std::memory_order_acquire) != 3)
        latchFault(ReasonCode::finalizationFailed);
    joinDispatcher();
    // Also fence direct/synthetic producers, without making UI Stop wait on a
    // sink. A later poll retries after its in-flight call returns.
    std::unique_lock<std::mutex> lock(captureMutex_, std::try_to_lock);
    if (!lock.owns_lock()) return pendingDrain();
    if (session_.state() == SessionState::stopping &&
        (dispatchCompletedAt_ > drainDeadline_ || sinkCompletedAt_ > drainDeadline_)) {
        markDrainTimedOut();
    }
    const auto failure = drainTimedOut_ ? ReasonCode::finalizationFailed : captureFailureReason();
    if (session_.state() == SessionState::stopping) {
        (void)session_.beginFinalizing();
        indicator_.publish(session_.state(), failure == ReasonCode::none ? session_.reason() : failure);
    }
    pollingFinalizer_ = true;
    try {
        const auto result = finalizer_
            ? finalizer_(failure, stopReason_)
            : std::optional<CaptureFinalization>{CaptureFinalization{}};
        if (!result) {
            pollingFinalizer_ = false;
            return {TransitionStatus::idempotent, session_.state(),
                failure == ReasonCode::none ? session_.reason() : failure};
        }
        finalization_ = *result;
    } catch (...) {
        finalization_ = {false, ReasonCode::finalizationFailed};
    }
    pollingFinalizer_ = false;
    if (drainTimedOut_) finalization_.reason = ReasonCode::finalizationFailed;
    if (failure != ReasonCode::none) {
        finalization_.savedLocal = false;
        finalization_.shortRecordingDiscarded = false;
        if (finalization_.reason == ReasonCode::none) finalization_.reason = failure;
    }
    // A discarded short recording is a deliberate, successful outcome: nothing
    // is stored, no capture error is registered, and the session ends blocked
    // (the same terminal truth macOS writes into the manifest).
    const auto result = finalization_.shortRecordingDiscarded
        ? session_.block(ReasonCode::none)
        : (finalization_.savedLocal && finalization_.reason == ReasonCode::none
            ? session_.saveLocal()
            : session_.fail(finalization_.reason == ReasonCode::none
                ? ReasonCode::finalizationFailed : finalization_.reason));
    stopReason_ = RecordingStopReason::interruption;
    indicator_.publish(session_.state(), session_.reason());
    return result;
}

bool WindowsCaptureSessionController::startWorkers() {
    if (!renderWorker_ || !microphoneWorker_ || !batchSink_) {
        latchFault(ReasonCode::endpointInvalidated);
        return false;
    }
    if (dispatchThread_.joinable()) joinDispatcher();
    {
        std::lock_guard<std::mutex> lock(dispatchMutex_);
        pendingBatches_.clear();
        dispatchStopRequested_ = false;
        sourceEndsEnqueued_ = false;
        sourceEndsProcessed_.store(0, std::memory_order_release);
        dispatchCompletedAt_ = {};
        dispatchFinished_.store(false, std::memory_order_release);
        dispatchBusy_.store(false, std::memory_order_release);
    }
    try {
        dispatchThread_ = std::thread([this] { dispatchLoop(); });
    } catch (...) {
        dispatchFinished_.store(true, std::memory_order_release);
        latchFault(ReasonCode::queueOverflow);
        return false;
    }
    const auto callback = [this](AudioBatch batch) { return enqueueBatch(std::move(batch)); };
    const std::pair<WasapiCaptureWorker*, bool> workers[] = {
        {renderWorker_.get(), false}, {microphoneWorker_.get(), true}};
    for (const auto& [worker, isMicrophone] : workers) {
        const auto error = worker->start(callback);
        if (error != CaptureWorkerError::none) latchFault(reasonForWorkerError(error, isMicrophone));
        if (captureFault_.load() != ReasonCode::none) return false;
    }
    return true;
}

ReasonCode WindowsCaptureSessionController::captureFailureReason() const noexcept {
    const auto pending = captureFault_.load();
    if (pending != ReasonCode::none) return pending;
    const std::pair<const WasapiCaptureWorker*, bool> workers[] = {
        {renderWorker_.get(), false}, {microphoneWorker_.get(), true}};
    for (const auto& [worker, isMicrophone] : workers) {
        if (worker == nullptr) continue;
        const auto error = reasonForWorkerError(worker->lastError(), isMicrophone);
        if (error != ReasonCode::none) return error;
        const auto state = session_.state();
        if ((state == SessionState::starting || state == SessionState::recording ||
             state == SessionState::paused || state == SessionState::degraded) && worker->finished())
            return ReasonCode::endpointInvalidated;
    }
    return ReasonCode::none;
}

void WindowsCaptureSessionController::stopWorkers() noexcept {
    if (renderWorker_) renderWorker_->stop();
    if (microphoneWorker_) microphoneWorker_->stop();
}

bool WindowsCaptureSessionController::enqueueBatch(AudioBatch batch) {
    // An empty batch is never a lifecycle signal. EOS has its own typed queue
    // item, so malformed/placeholder audio cannot reach the timeline.
    if (batch.samples.empty()) return false;
    if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none) return true;
    {
        std::lock_guard<std::mutex> lock(dispatchMutex_);
        if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none || dispatchStopRequested_)
            return true;
        if (pendingBatches_.size() >= maxDataBatches_) {
            latchFault(ReasonCode::queueOverflow);
            acceptingBatches_.store(false);
            return false;
        }
        pendingBatches_.emplace_back(std::move(batch));
    }
    dispatchCondition_.notify_one();
    return true;
}

bool WindowsCaptureSessionController::enqueueSourceEnd(AudioSource source) {
    std::lock_guard<std::mutex> lock(dispatchMutex_);
    if (pendingBatches_.size() >= maxPendingBatches_) return false;
    pendingBatches_.emplace_back(SourceEndOfStream{source});
    dispatchCondition_.notify_one();
    return true;
}

void WindowsCaptureSessionController::dispatchLoop() noexcept {
    bool sinkFailed = false;
    while (true) {
        DispatchItem item;
        {
            std::unique_lock<std::mutex> lock(dispatchMutex_);
            dispatchCondition_.wait(lock, [this] {
                return dispatchStopRequested_ || !pendingBatches_.empty();
            });
            if (pendingBatches_.empty()) {
                if (dispatchStopRequested_) break;
                continue;
            }
            item = std::move(pendingBatches_.front());
            pendingBatches_.pop_front();
            dispatchBusy_.store(true, std::memory_order_release);
        }
        if (std::holds_alternative<SourceEndOfStream>(item)) {
            // The queue position itself is the completion fence. The finalizer
            // runs only after both typed EOS items and all earlier batches have
            // crossed the dispatcher.
            const auto source = std::get<SourceEndOfStream>(item).source;
            const auto bit = source == AudioSource::systemRender ? std::uint8_t{1} : std::uint8_t{2};
            sourceEndsProcessed_.fetch_or(bit, std::memory_order_release);
            dispatchBusy_.store(false, std::memory_order_release);
            continue;
        }
        if (!sinkFailed && !processBatch(std::move(std::get<AudioBatch>(item)))) {
            dispatchBusy_.store(false, std::memory_order_release);
            latchFault(ReasonCode::clockDiscontinuity);
            acceptingBatches_.store(false);
            if (renderWorker_) renderWorker_->stop();
            if (microphoneWorker_) microphoneWorker_->stop();
            // No later audio may pass a failed sink, but typed EOS must still
            // cross this dispatcher before the UI can finalize the prefix.
            sinkFailed = true;
        }
        dispatchBusy_.store(false, std::memory_order_release);
    }
    dispatchBusy_.store(false, std::memory_order_release);
    dispatchCompletedAt_ = std::chrono::steady_clock::now();
    dispatchFinished_.store(true, std::memory_order_release);
}

void WindowsCaptureSessionController::requestDispatcherStop() noexcept {
    {
        std::lock_guard<std::mutex> lock(dispatchMutex_);
        dispatchStopRequested_ = true;
    }
    dispatchCondition_.notify_all();
}

void WindowsCaptureSessionController::joinDispatcher() noexcept {
    requestDispatcherStop();
    if (dispatchThread_.joinable()) dispatchThread_.join();
    dispatchBusy_.store(false, std::memory_order_release);
    dispatchFinished_.store(true, std::memory_order_release);
}

void WindowsCaptureSessionController::latchFault(ReasonCode reason) noexcept {
    auto expected = ReasonCode::none;
    (void)captureFault_.compare_exchange_strong(expected, reason);
}

bool WindowsCaptureSessionController::handleBatch(AudioBatch batch) {
    // This path is retained only for synchronous test/device adapters. It is
    // not a lifecycle marker and cannot accept malformed empty audio.
    if (batch.samples.empty()) return false;
    if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none) return true;
    // Synchronous test/device adapters keep their original fire-and-report
    // contract: processBatch latches a sink fault for the UI poll, while the
    // producer itself is not made to interpret the terminal state.
    (void)processBatch(std::move(batch), true);
    return true;
}

bool WindowsCaptureSessionController::processBatch(AudioBatch batch, bool requireAccepting) {
    if (batch.samples.empty()) {
        latchFault(ReasonCode::formatNormalizationUnavailable);
        return false;
    }
    if (!batchSink_) return false;
    std::lock_guard<std::mutex> lock(captureMutex_);
    // Direct producers can have waited behind a sink while UI Stop fenced
    // delivery. Recheck under the same mutex used by finalization.
    if (requireAccepting && (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none)) return true;
    bool accepted = true;
    try {
        accepted = batchSink_(std::move(batch));
        if (!accepted) latchFault(ReasonCode::clockDiscontinuity);
    } catch (...) {
        accepted = false;
        latchFault(ReasonCode::finalizationFailed);
    }
    sinkCompletedAt_ = std::chrono::steady_clock::now();
    return accepted;
}

} // namespace graf::windows
