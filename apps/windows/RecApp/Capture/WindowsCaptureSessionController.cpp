#include "WindowsCaptureSessionController.h"

#include "CaptureReasonMapping.h"

#include <limits>

namespace graf::windows {

CaptureClockDiagnostics WindowsCaptureSessionController::clockDiagnostics(AudioSource source) const noexcept {
    const auto& worker = source == AudioSource::systemRender ? renderWorker_ : microphoneWorker_;
    return worker ? worker->clockDiagnostics() : CaptureClockDiagnostics{};
}

WindowsCaptureSessionController::WindowsCaptureSessionController(std::string sessionId, BatchSink batchSink,
                                                                 Finalizer finalizer,
                                                                 MicrophonePauseHandler microphonePauseHandler,
                                                                 PrivacyCheckpoint privacyCheckpoint)
    : session_(std::move(sessionId)), batchSink_(std::move(batchSink)), finalizer_(std::move(finalizer)),
      microphonePauseHandler_(std::move(microphonePauseHandler)), privacyCheckpoint_(std::move(privacyCheckpoint)),
      indicator_([this] { (void)stop(); }) {}

WindowsCaptureSessionController::~WindowsCaptureSessionController() {
    (void)drainAbandonedCapture();
}

ReasonCode WindowsCaptureSessionController::drainAbandonedCapture() noexcept {
    acceptingBatches_.store(false, std::memory_order_release);
    stopWorkers();
    for (auto* worker : {renderWorker_.get(), microphoneWorker_.get()})
        if (worker) worker->joinStopped();
    const bool hadDispatcher = dispatchThread_.joinable();
    joinDispatcher();
    if (hadDispatcher && sourceEndsProcessed_.load(std::memory_order_acquire) != 3)
        latchFault(ReasonCode::finalizationFailed);
    if (drainDeadline_ != std::chrono::steady_clock::time_point{}) {
        for (const auto* worker : {renderWorker_.get(), microphoneWorker_.get()})
            if (worker && worker->finishedAt() > drainDeadline_) drainTimedOut_ = true;
        std::lock_guard<std::mutex> lock(captureMutex_);
        if (dispatchCompletedAt_ > drainDeadline_ || sinkCompletedAt_ > drainDeadline_)
            drainTimedOut_ = true;
    }
    // Read after native completion and before deleting device diagnostics.
    return drainTimedOut_ ? ReasonCode::finalizationFailed : captureFailureReason();
}

void WindowsCaptureSessionController::setEndpoints(WasapiEndpointSnapshot render,
                                                    WasapiEndpointSnapshot microphone) {
    // A second Record must not replace live workers before readiness rejects it.
    if (session_.state() != SessionState::idle) return;
    renderWorker_ = std::make_unique<WasapiCaptureWorker>(std::move(render), true);
    microphoneWorker_ = std::make_unique<WasapiCaptureWorker>(std::move(microphone), false);
    microphoneWorker_->microphonePrivacyEpoch_ = &microphonePrivacyEpoch_;
}

TransitionResult WindowsCaptureSessionController::record(const ReadinessInputs& readiness, StartGuard startGuard) {
    const auto checked = session_.beginReadinessCheck();
    if (!checked.accepted()) return checked;
    startGuard_ = std::move(startGuard);
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
    return requestPrivacy(true);
}

TransitionResult WindowsCaptureSessionController::resume() {
    return requestPrivacy(false);
}

std::optional<WindowsCaptureSessionController::PrivacyTime>
WindowsCaptureSessionController::privacyTime() const noexcept {
    const auto wall = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    const auto monotonic = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - recordingClockStart_).count();
    if (recordingClockStart_ == std::chrono::steady_clock::time_point{} || wall < 0 || monotonic < 0)
        return std::nullopt;
    return PrivacyTime{static_cast<std::uint64_t>(wall), static_cast<std::uint64_t>(monotonic)};
}

TransitionResult WindowsCaptureSessionController::requestPrivacy(bool pause) {
    (void)pollHealth();
    if (privacyPending_) return {TransitionStatus::idempotent, session_.state(), privacyError_};
    if (session_.state() != (pause ? SessionState::recording : SessionState::paused))
        return {TransitionStatus::rejected, session_.state(), session_.reason()};
    const auto time = privacyTime();
    if (!privacyCheckpoint_ || !dispatchThread_.joinable() || !time) {
        privacyError_ = ReasonCode::storageUnavailable;
        return {TransitionStatus::rejected, session_.state(), privacyError_};
    }
    {
        std::lock_guard<std::mutex> boundary(dispatchMutex_);
        if (microphonePrivacyEpoch_.load(std::memory_order_relaxed) == std::numeric_limits<std::uint64_t>::max())
            return {TransitionStatus::rejected, session_.state(), ReasonCode::queueOverflow};
        if (!acceptingBatches_.load() || dispatchStopRequested_)
            return {TransitionStatus::rejected, session_.state(), session_.reason()};
        privacyCommand_ = PrivacyCommand{pause, *time};
    }
    privacyPending_ = true;
    privacyError_ = ReasonCode::none;
    dispatchCondition_.notify_one();
    return {TransitionStatus::idempotent, session_.state(), ReasonCode::none};
}

bool WindowsCaptureSessionController::applyPrivacyBoundary(bool pause) {
    std::lock_guard<std::mutex> lock(captureMutex_);
    {
        std::lock_guard<std::mutex> boundary(dispatchMutex_);
        const auto epoch = microphonePrivacyEpoch_.load(std::memory_order_relaxed);
        // Stop wins even if OPEN was already durably published during its race.
        if (!acceptingBatches_.load() || dispatchStopRequested_ || captureFault_.load() != ReasonCode::none ||
            epoch == std::numeric_limits<std::uint64_t>::max() || static_cast<bool>(epoch & 1U) == pause) return false;
        lastSuppressedSequence_ = lastAcceptedSequence_;
        microphonePrivacyEpoch_.store(epoch + 1, std::memory_order_release);
    }
    if (microphonePauseHandler_) microphonePauseHandler_(pause);
    return true;
}

bool WindowsCaptureSessionController::processPrivacy(const PrivacyCommand& command) noexcept {
    PrivacyCompletion completion{command.pause};
    const auto publish = [&] {
        std::lock_guard<std::mutex> lock(dispatchMutex_);
        privacyCompletion_ = completion;
    };
    try {
        if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none) { publish(); return true; }
        if (command.pause) {
            const auto saved = privacyCheckpoint_(true, command.time.wallMs, command.time.monotonicMs);
            if (!saved.committed || saved.fatal) {
                completion.reason = ReasonCode::storageUnavailable;
                if (saved.fatal) latchFault(completion.reason);
                publish(); return !saved.fatal;
            }
            completion.applied = applyPrivacyBoundary(true);
        } else {
            const auto time = privacyTime();
            if (!time) { completion.reason = ReasonCode::clockDiscontinuity; publish(); return true; }
            completion.applied = applyPrivacyBoundary(false);
            if (completion.applied) {
                completion.done = false; publish(); // UI may publish Resume while CLOSE is pending.
                const auto saved = privacyCheckpoint_(false, time->wallMs, time->monotonicMs);
                completion.done = true;
                if (!saved.committed) completion.reason = ReasonCode::storageUnavailable;
                if (saved.fatal) { latchFault(ReasonCode::storageUnavailable); publish(); return false; }
            }
        }
        if (!completion.applied) completion.reason = ReasonCode::queueOverflow;
    } catch (...) {
        completion.done = true; completion.reason = ReasonCode::finalizationFailed;
        latchFault(completion.reason); publish(); return false;
    }
    publish(); return true;
}

void WindowsCaptureSessionController::adoptPrivacyCompletion() {
    std::optional<PrivacyCompletion> completion;
    {
        std::lock_guard<std::mutex> lock(dispatchMutex_);
        completion = privacyCompletion_; privacyCompletion_.reset();
    }
    if (!completion || !privacyPending_) return;
    if (completion->done) privacyPending_ = false;
    privacyError_ = completion->reason;
    if (completion->applied && session_.state() == (completion->pause ? SessionState::recording : SessionState::paused)) {
        if (completion->pause) (void)session_.pause(); else (void)session_.resume();
        indicator_.publish(session_.state(), session_.reason());
    }
}

TransitionResult WindowsCaptureSessionController::pollHealth() {
    if (checkingStart_) return {TransitionStatus::idempotent, session_.state(), session_.reason()};
    adoptPrivacyCompletion();
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
            // The only transition that opens audio delivery, including polls
            // from pause/resume. Until this point even ready workers drop audio;
            // the writer has nothing to persist or recover after a crash.
            checkingStart_ = true;
            bool allowed = false;
            try { allowed = !startGuard_ || startGuard_(session_.sessionId()); }
            catch (...) {} // A failed check never grants capture or logs its payload.
            checkingStart_ = false;
            if (!allowed || session_.state() != SessionState::starting)
                return stop(RecordingStopReason::interruption);
            const auto started = session_.startRecording();
            indicator_.publish(session_.state(), session_.reason());
            if (started.accepted()) {
                recordingClockStart_ = std::chrono::steady_clock::now();
                acceptingBatches_.store(true, std::memory_order_release);
            }
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
    {
        std::lock_guard<std::mutex> lock(dispatchMutex_);
        // Shared admission fence with applyPrivacyBoundary: either its epoch
        // was accepted first, or Stop prevents it. Never wait on capture/IO.
        acceptingBatches_.store(false, std::memory_order_release);
        privacyStopTime_ = privacyTime();
        privacyCommand_.reset(); privacyCompletion_.reset();
    }
    privacyPending_ = false;
    stopReason_ = reason;
    drainDeadline_ = std::chrono::steady_clock::now() + std::chrono::seconds(5);
    // Latch unexpected worker termination before the deliberate shutdown.
    if (beforeStop != ReasonCode::none) latchFault(beforeStop);
    try { indicator_.publish(session_.state(), session_.reason()); }
    catch (...) { latchFault(ReasonCode::queueOverflow); }
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
    try {
        const auto result = finishStop();
        return {TransitionStatus::accepted, result.state, result.reason};
    } catch (...) {
        latchFault(ReasonCode::queueOverflow);
        return {TransitionStatus::accepted, session_.state(), captureFault_.load()};
    }
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
        lastAcceptedSequence_ = lastSuppressedSequence_ = 0;
        microphonePrivacyEpoch_.store(0, std::memory_order_release);
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

std::optional<WindowsCaptureSessionController::QueuedBatch>
WindowsCaptureSessionController::stampBatch(AudioBatch batch) {
    if (lastAcceptedSequence_ == std::numeric_limits<std::uint64_t>::max()) {
        latchFault(ReasonCode::queueOverflow);
        acceptingBatches_.store(false);
        return std::nullopt;
    }
    return QueuedBatch{std::move(batch), ++lastAcceptedSequence_};
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
        auto queued = stampBatch(std::move(batch));
        if (!queued) return false;
        pendingBatches_.emplace_back(std::move(*queued));
    }
    dispatchCondition_.notify_one();
    return true;
}

bool WindowsCaptureSessionController::enqueueSourceEnd(AudioSource source) noexcept {
    std::lock_guard<std::mutex> lock(dispatchMutex_);
    if (pendingBatches_.size() >= maxPendingBatches_) return false;
    try { pendingBatches_.emplace_back(SourceEndOfStream{source}); }
    catch (...) { return false; } // Stop still requests dispatcher completion; missing EOS is a fault.
    dispatchCondition_.notify_one();
    return true;
}

void WindowsCaptureSessionController::dispatchLoop() noexcept {
    bool sinkFailed = false;
    while (true) {
        DispatchItem item;
        std::optional<PrivacyCommand> privacy;
        {
            std::unique_lock<std::mutex> lock(dispatchMutex_);
            dispatchCondition_.wait(lock, [this] {
                return dispatchStopRequested_ || privacyCommand_ || !pendingBatches_.empty();
            });
            if (privacyCommand_) {
                privacy = privacyCommand_; privacyCommand_.reset();
            } else if (pendingBatches_.empty()) {
                if (dispatchStopRequested_) break;
                continue;
            } else {
                item = std::move(pendingBatches_.front());
                pendingBatches_.pop_front();
            }
            dispatchBusy_.store(true, std::memory_order_release);
        }
        if (privacy) {
            if (!sinkFailed && !processPrivacy(*privacy)) {
                sinkFailed = true; acceptingBatches_.store(false); stopWorkers();
            }
            dispatchBusy_.store(false, std::memory_order_release);
            continue;
        }
        if (std::holds_alternative<SourceEndOfStream>(item)) {
            // The queue position itself is the completion fence. The finalizer
            // runs only after both typed EOS items and all earlier batches have
            // crossed the dispatcher.
            const auto source = std::get<SourceEndOfStream>(item).source;
            const auto bit = source == AudioSource::systemRender ? std::uint8_t{1} : std::uint8_t{2};
            const auto previousEnds = sourceEndsProcessed_.load();
            if (previousEnds != 3 && (previousEnds | bit) == 3 && privacyCheckpoint_ &&
                recordingClockStart_ != std::chrono::steady_clock::time_point{}) {
                try {
                    // Accepted Stop time, not worker completion or a temporary Resume.
                    if (!privacyStopTime_ || privacyCheckpoint_(false, privacyStopTime_->wallMs,
                        privacyStopTime_->monotonicMs).fatal) latchFault(ReasonCode::storageUnavailable);
                } catch (...) { latchFault(ReasonCode::storageUnavailable); }
            }
            sourceEndsProcessed_.fetch_or(bit, std::memory_order_release);
            dispatchBusy_.store(false, std::memory_order_release);
            continue;
        }
        if (!sinkFailed && !processBatch(std::move(std::get<QueuedBatch>(item)))) {
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
    std::optional<QueuedBatch> queued;
    {
        std::lock_guard<std::mutex> lock(dispatchMutex_);
        if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none || dispatchStopRequested_)
            return true;
        queued = stampBatch(std::move(batch));
    }
    if (queued) (void)processBatch(std::move(*queued), true);
    return true;
}

bool WindowsCaptureSessionController::processBatch(QueuedBatch queued, bool requireAccepting) {
    auto& batch = queued.batch;
    if (batch.samples.empty()) {
        latchFault(ReasonCode::formatNormalizationUnavailable);
        return false;
    }
    if (!batchSink_) return false;
    std::lock_guard<std::mutex> lock(captureMutex_);
    // Direct producers can have waited behind a sink while UI Stop fenced
    // delivery. Recheck under the same mutex used by finalization.
    if (requireAccepting && (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none)) return true;
    if (batch.source == AudioSource::microphone) {
        std::lock_guard<std::mutex> boundary(dispatchMutex_);
        const auto epoch = microphonePrivacyEpoch_.load(std::memory_order_relaxed);
        batch.microphoneSuppressed = batch.microphoneSuppressed || (epoch & 1U) ||
            (batch.microphonePrivacyEpoch && *batch.microphonePrivacyEpoch != epoch) ||
            queued.sequence <= lastSuppressedSequence_;
    }
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
