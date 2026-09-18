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
    stopWorkers();
    joinDispatcher();
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
    // Новая запись начинается без прошлых ограничений: причина живёт одну сессию.
    microphoneDegraded_ = false;
    renderDegraded_ = false;
    degradedReason_ = ReasonCode::none;
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
        const bool startupExpired = failure == ReasonCode::none && state == SessionState::starting &&
            std::chrono::steady_clock::now() >= startupDeadline_;
        if (startupExpired) {
            // Истёк срок запуска: виноват не «отключившийся» источник, а тот,
            // который так и не поднялся. Человеку нужен точный адрес проблемы.
            failure = renderWorker_ && renderWorker_->ready() ? ReasonCode::microphoneEndpointUnavailable
                                                              : ReasonCode::renderEndpointUnavailable;
        }
        // Системный звук — главный источник встречи. Если он поднялся, а
        // микрофон молчит (нет устройства, нет доступа, устройство занято),
        // запись продолжается без голоса, а не обрывается.
        const bool hasLiveSource = sourceUsable(startupExpired);
        if (failure != ReasonCode::none && hasLiveSource) {
            // Кто отказал — тот и назван: причина уходит в текст для человека и
            // в саму запись, чтобы ограничение было видно и после остановки.
            bool microphoneFault = sourceDead(microphoneWorker_.get(), true);
            if (!microphoneFault && !sourceDead(renderWorker_.get(), false)) {
                // Никто не отказал явно: значит истёк срок запуска, и виноват
                // тот источник, который так и не дал звук.
                microphoneFault = !sourceProducing(microphoneWorker_.get(), true);
            }
            auto reason = failure;
            if (startupExpired || failure == ReasonCode::endpointInvalidated) {
                // «Источник пропал» без имени бесполезно: человеку нужно знать,
                // что чинить — микрофон или устройство воспроизведения.
                reason = microphoneFault ? ReasonCode::microphoneEndpointUnavailable
                                         : ReasonCode::renderEndpointUnavailable;
            }
            if (microphoneFault) {
                microphoneDegraded_ = true;
                if (microphoneWorker_) microphoneWorker_->stop();
            } else {
                renderDegraded_ = true;
                if (renderWorker_) renderWorker_->stop();
            }
            degradedReason_ = reason;
            (void)session_.markDegraded(reason);
            // Без этого системный звук не попадёт в запись: пакеты принимаются
            // только после готовности источников.
            acceptingBatches_.store(true);
            indicator_.publish(session_.state(), session_.reason());
            return {TransitionStatus::accepted, session_.state(), session_.reason()};
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
    stopReason_ = reason;
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
    requestDispatcherStop();
    if (!dispatchFinished_.load(std::memory_order_acquire)) {
        std::lock_guard<std::mutex> dispatchLock(dispatchMutex_);
        if (dispatchBusy_.load(std::memory_order_acquire) || !pendingBatches_.empty())
            return {TransitionStatus::idempotent, session_.state(), session_.reason()};
    }
    joinDispatcher();
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
        const auto result = finalizer_
            ? finalizer_(failure, stopReason_)
            : std::optional<CaptureFinalization>{CaptureFinalization{}};
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
        finalization_.shortRecordingDiscarded = false;
        if (finalization_.reason == ReasonCode::none) finalization_.reason = failure;
    }
    if (degradedReason_ != ReasonCode::none && finalization_.degradedReason == ReasonCode::none) {
        // Ограниченная запись сохраняется: причина едет с записью, а не вместо неё.
        finalization_.degradedReason = degradedReason_;
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

bool WindowsCaptureSessionController::sourceDead(const WasapiCaptureWorker* worker, bool isMicrophone) const noexcept {
    if (worker == nullptr) return true;
    if (isMicrophone && microphoneDegraded_) return true;
    if (!isMicrophone && renderDegraded_) return true;
    if (worker->finished()) return true;
    return reasonForWorkerError(worker->lastError(), isMicrophone) != ReasonCode::none;
}

bool WindowsCaptureSessionController::sourceProducing(const WasapiCaptureWorker* worker, bool isMicrophone) const noexcept {
    if (sourceDead(worker, isMicrophone)) return false;
    // Источник считается пишущим, только если он уже дал звук: молчащий
    // источник — это и есть отказ, ради которого запись ограничивается.
    return worker->ready() || worker->clockDiagnostics().startupDiscardedFrames > 0;
}

bool WindowsCaptureSessionController::sourceUsable(bool startupExpired) const noexcept {
    const bool starting = session_.state() == SessionState::starting;
    const auto usable = [&](const WasapiCaptureWorker* worker, bool isMicrophone) {
        if (sourceDead(worker, isMicrophone)) return false;
        // Истёк срок запуска: годится только тот источник, который уже дал звук.
        if (startupExpired) return sourceProducing(worker, isMicrophone);
        // Запись идёт: источник обязан писать, иначе запись выйдет пустой.
        if (!starting) return sourceProducing(worker, isMicrophone);
        // Источник ещё поднимается: ему дают договорить.
        return true;
    };
    return usable(renderWorker_.get(), false) || usable(microphoneWorker_.get(), true);
}

ReasonCode WindowsCaptureSessionController::captureFailureReason() const noexcept {
    const auto pending = captureFault_.load();
    if (pending != ReasonCode::none) return pending;
    const std::pair<const WasapiCaptureWorker*, bool> workers[] = {
        {renderWorker_.get(), false}, {microphoneWorker_.get(), true}};
    for (const auto& [worker, isMicrophone] : workers) {
        // Ограничение уже учтено: повторно оно запись не обрывает.
        if (isMicrophone && microphoneDegraded_) continue;
        if (!isMicrophone && renderDegraded_) continue;
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
    acceptingBatches_.store(false);
    if (renderWorker_) renderWorker_->stop();
    if (microphoneWorker_) microphoneWorker_->stop();
    requestDispatcherStop();
}

bool WindowsCaptureSessionController::enqueueBatch(AudioBatch batch) {
    // Synthetic lifecycle tests use an empty callback marker. Real workers only
    // publish normalized non-empty batches, so keep that marker synchronous.
    if (batch.samples.empty()) return handleBatch(std::move(batch));
    if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none) return true;
    {
        std::lock_guard<std::mutex> lock(dispatchMutex_);
        if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none || dispatchStopRequested_)
            return true;
        if (pendingBatches_.size() >= maxPendingBatches_) return false;
        pendingBatches_.push_back(std::move(batch));
    }
    dispatchCondition_.notify_one();
    return true;
}

void WindowsCaptureSessionController::dispatchLoop() noexcept {
    while (true) {
        AudioBatch batch;
        {
            std::unique_lock<std::mutex> lock(dispatchMutex_);
            dispatchCondition_.wait(lock, [this] {
                return dispatchStopRequested_ || !pendingBatches_.empty();
            });
            if (pendingBatches_.empty()) {
                if (dispatchStopRequested_) break;
                continue;
            }
            batch = std::move(pendingBatches_.front());
            pendingBatches_.pop_front();
            dispatchBusy_.store(true, std::memory_order_release);
        }
        if (!processBatch(std::move(batch))) {
            dispatchBusy_.store(false, std::memory_order_release);
            latchFault(ReasonCode::clockDiscontinuity);
            acceptingBatches_.store(false);
            if (renderWorker_) renderWorker_->stop();
            if (microphoneWorker_) microphoneWorker_->stop();
            std::lock_guard<std::mutex> lock(dispatchMutex_);
            pendingBatches_.clear();
            dispatchStopRequested_ = true;
            dispatchCondition_.notify_all();
            break;
        }
        dispatchBusy_.store(false, std::memory_order_release);
    }
    dispatchBusy_.store(false, std::memory_order_release);
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
    if (!acceptingBatches_.load() || captureFault_.load() != ReasonCode::none) return true;
    (void)processBatch(std::move(batch));
    return true;
}

bool WindowsCaptureSessionController::processBatch(AudioBatch batch) {
    if (!batchSink_) return false;
    std::lock_guard<std::mutex> lock(captureMutex_);
    bool accepted = true;
    try {
        accepted = batchSink_(std::move(batch));
        if (!accepted) latchFault(ReasonCode::clockDiscontinuity);
    } catch (...) {
        accepted = false;
        latchFault(ReasonCode::finalizationFailed);
    }
    return accepted;
}

} // namespace graf::windows
