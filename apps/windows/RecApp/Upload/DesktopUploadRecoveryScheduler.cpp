#include "DesktopUploadRecoveryScheduler.h"

#include <algorithm>
#include <cwctype>
#include <map>
#include <mutex>
#include <thread>
#include <utility>

namespace graf::windows {

namespace {
template<class Step> void executeSequence(std::size_t count, const std::atomic_bool& cancelled, Step step) {
    for (std::size_t index = 0; index < count && !cancelled.load(); ++index)
        if (!step(index)) break;
}
}

struct DesktopUploadRecoveryScheduler::Flight {
    std::shared_ptr<std::atomic_bool> cancelled = std::make_shared<std::atomic_bool>(false);
    std::atomic_bool done{false};
    std::atomic_bool leaseReleased{false};
    std::vector<UploadCustodyItem> items;
    std::vector<DesktopTransportResult> results;
};

DesktopUploadRecoveryScheduler::DesktopUploadRecoveryScheduler(DesktopUploadQueueService& queue, std::uint32_t maxAttempts)
    : queue_(queue), maxAttempts_(maxAttempts) {}

DesktopUploadRecoveryScheduler::~DesktopUploadRecoveryScheduler() {
    cancel();
    if (flight_) flight_->leaseReleased.store(true);
}

bool DesktopUploadRecoveryScheduler::prepare(RecoveryTrigger trigger) {
    if (busy() || queue_.quarantined()) return false;
    // The server asked for a pause, so nothing may start before it elapses: the
    // work is not refused, it is only early. A recovered sign-in is the one
    // event the server cannot be waiting for the client to notice.
    if (deferralRemainingMs() > 0 && trigger != RecoveryTrigger::authRecovered) return false;
    std::error_code error;
    auto key = std::filesystem::weakly_canonical(queue_.ledgerPath(), error).native();
    if (error || key.empty()) return false;
#ifdef _WIN32
    std::transform(key.begin(), key.end(), key.begin(), [](wchar_t c) { return static_cast<wchar_t>(std::towlower(c)); });
#endif
    // Keep the lease until a cancelled request unwinds, even if its scheduler
    // was destroyed. A replacement cannot run this ledger concurrently.
    static std::mutex leaseMutex;
    static std::map<decltype(key), std::weak_ptr<Flight>> leases;
    const std::lock_guard<std::mutex> lock(leaseMutex);
    for (auto it = leases.begin(); it != leases.end();) {
        const auto prior = it->second.lock();
        if (!prior || (prior->done.load(std::memory_order_acquire) && prior->leaseReleased.load())) it = leases.erase(it);
        else ++it;
    }
    if (leases.count(key)) return false;
    if (trigger == RecoveryTrigger::authRecovered && !queue_.requeueNeedsAuth()) return false;
    auto flight = std::make_shared<Flight>();
    // Apply the flight bound after excluding exhausted rows, so they cannot
    // hide a later row explicitly rearmed by the user.
    for (const auto& item : queue_.pendingItems(queue_.items().size())) {
        if (item.attempts >= maxAttempts_) {
            if (item.safeReason != "retry_budget_exhausted" &&
                !queue_.markRetry(item.localRecordingId, "retry_budget_exhausted")) return false;
            continue;
        }
        flight->items.push_back(item);
        if (flight->items.size() == 32) break;
    }
    if (flight->items.empty()) return false;
    flight->results.reserve(flight->items.size());
    leases[key] = flight;
    flight_ = std::move(flight);
    return true;
}

void DesktopUploadRecoveryScheduler::execute(const std::shared_ptr<Flight>& flight, WorkerHandler worker) {
    executeSequence(flight->items.size(), *flight->cancelled, [&](std::size_t index) {
        const auto& item = flight->items[index];
        DesktopTransportResult result;
        try {
            if (DesktopHttpTransport::ownerBlockReason(item, std::nullopt) == "local_owner_unclaimed")
                result = DesktopTransportResult{
                    DesktopTransportStatus::authRequired, std::nullopt, "local_owner_unclaimed", {}, 0, std::nullopt};
            else result = worker(item, flight->cancelled);
        } catch (...) {
            // Never copy raw transport exception/URL/token into custody state.
            result.status = DesktopTransportStatus::retryableFailure;
        }
        flight->results.push_back(std::move(result));
        return true;
    });
    worker = {}; // Captured native owners must finish teardown before drain/lease release.
    flight->done.store(true, std::memory_order_release);
}

bool DesktopUploadRecoveryScheduler::startAsync(RecoveryTrigger trigger, DesktopHttpConfig config) {
    if (busy()) return false;
    // Configuration (including the current session) is a value-only UI snapshot.
    return startAsync(trigger, [config = std::move(config)](const UploadCustodyItem& item, Cancellation cancellation) mutable {
        config.cancellation = std::move(cancellation);
        return DesktopHttpTransport(config).upload(item);
    });
}

bool DesktopUploadRecoveryScheduler::startAsync(RecoveryTrigger trigger, WorkerHandler worker) {
    if (!worker || !prepare(trigger)) return false;
    try {
        std::thread([flight = flight_, worker = std::move(worker)]() mutable { execute(flight, std::move(worker)); }).detach();
    } catch (...) {
        flight_.reset();
        return false;
    }
    return true;
}

std::shared_ptr<DesktopUploadRecoveryScheduler::ProtectedFlight> DesktopUploadRecoveryScheduler::beginProtected(
    RecoveryTrigger trigger, ProtectedDesktopHttpConfig config, std::uint64_t epoch) {
    if (busy() || (deferralRemainingMs() && trigger != RecoveryTrigger::authRecovered) ||
        !config.confirmedIdentity || config.sessionToken.empty()) return {};
    auto flight = std::allocate_shared<ProtectedFlight>(CustodyAllocator<ProtectedFlight>{});
    config.cancellation = flight->cancelled;
    flight->config = std::move(config); flight->epoch = epoch; flight->trigger = trigger; flight->maxAttempts = maxAttempts_;
    protectedFlight_ = flight;
    return flight;
}

bool DesktopUploadRecoveryScheduler::launchProtected(const std::shared_ptr<ProtectedFlight>& flight,
    ProtectedWorker worker, std::function<void()> completed) {
    if (!flight || !worker || !completed) return false;
    try {
        std::thread([flight, worker = std::move(worker), completed = std::move(completed)]() mutable {
            try { executeSequence(flight->selected.size(), *flight->cancelled, [&](std::size_t index) { return worker(index); }); }
            catch (...) { flight->cancelled->store(true); }
            worker = {}; // Last captured native context release stays on this worker.
            flight->done.store(true, std::memory_order_release);
            completed();
        }).detach();
        return true;
    } catch (...) { return false; } // Captured native owners unwind on the caller/storage worker.
}

void DesktopUploadRecoveryScheduler::retireProtected() noexcept {
    if (protectedFlight_ && protectedFlight_->done.load(std::memory_order_acquire) && protectedFlight_->leaseReleased.load())
        protectedFlight_.reset();
}

bool DesktopUploadRecoveryScheduler::busy() const noexcept { return static_cast<bool>(flight_) || static_cast<bool>(protectedFlight_); }

void DesktopUploadRecoveryScheduler::cancel() noexcept {
    if (flight_) flight_->cancelled->store(true);
    if (protectedFlight_) protectedFlight_->cancelled->store(true);
}

std::size_t DesktopUploadRecoveryScheduler::drain() {
    if (!flight_ || !flight_->done.load(std::memory_order_acquire)) return 0;
    auto flight = std::move(flight_);
    if (flight->cancelled->load()) {
        flight->leaseReleased.store(true);
        return 0;
    }
    std::size_t handled = 0;
    for (std::size_t index = 0; index < flight->results.size(); ++index) {
        const auto& item = flight->items[index];
        const auto current = std::find_if(queue_.items().begin(), queue_.items().end(), [&](const auto& value) {
            return value.localRecordingId == item.localRecordingId;
        });
        // UI actions (auth, deletion, quarantine) take precedence over stale work.
        if (current == queue_.items().end() || !sameUploadIdentity(*current, item)) continue;
        apply(item, flight->results[index]);
        ++handled;
    }
    flight->leaseReleased.store(true);
    return handled;
}

void DesktopUploadRecoveryScheduler::deferFor(std::uint32_t seconds) noexcept {
    if (seconds == 0) return;
    const auto until = std::chrono::steady_clock::now() + std::chrono::seconds(seconds);
    if (until > deferredUntil_) deferredUntil_ = until;
}

std::uint64_t DesktopUploadRecoveryScheduler::deferralRemainingMs() const noexcept {
    const auto now = std::chrono::steady_clock::now();
    if (deferredUntil_ <= now) return 0;
    return static_cast<std::uint64_t>(
        std::chrono::duration_cast<std::chrono::milliseconds>(deferredUntil_ - now).count());
}

void DesktopUploadRecoveryScheduler::apply(const UploadCustodyItem& item, const DesktopTransportResult& result) {
    if (!queue_.applyUploadResult(item.localRecordingId, result)) return;
    if (result.retryAfterSeconds > 0) deferFor(result.retryAfterSeconds);
    if (result.authExpiresAt && sessionExpiryHandler_) sessionExpiryHandler_(*result.authExpiresAt);
}

} // namespace graf::windows
