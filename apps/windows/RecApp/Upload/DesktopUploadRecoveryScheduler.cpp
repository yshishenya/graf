#include "DesktopUploadRecoveryScheduler.h"

#include <algorithm>
#include <cwctype>
#include <map>
#include <mutex>
#include <thread>
#include <utility>

namespace graf::windows {

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

void DesktopUploadRecoveryScheduler::execute(const std::shared_ptr<Flight>& flight, const WorkerHandler& worker) {
    for (const auto& item : flight->items) {
        if (flight->cancelled->load()) break;
        DesktopTransportResult result;
        try {
            if (DesktopHttpTransport::ownerBlockReason(item, std::nullopt) == "local_owner_unclaimed")
                result = {DesktopTransportStatus::authRequired, std::nullopt, "local_owner_unclaimed"};
            else result = worker(item, flight->cancelled);
        } catch (...) {
            // Never copy raw transport exception/URL/token into custody state.
            result.status = DesktopTransportStatus::retryableFailure;
        }
        flight->results.push_back(std::move(result));
    }
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
        std::thread([flight = flight_, worker = std::move(worker)] { execute(flight, worker); }).detach();
    } catch (...) {
        flight_.reset();
        return false;
    }
    return true;
}

bool DesktopUploadRecoveryScheduler::busy() const noexcept { return static_cast<bool>(flight_); }

void DesktopUploadRecoveryScheduler::cancel() noexcept {
    if (flight_) flight_->cancelled->store(true);
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
        if (current == queue_.items().end() || current->directoryId != item.directoryId ||
            current->sessionId != item.sessionId || current->packageDirectory != item.packageDirectory ||
            current->ownerUserId != item.ownerUserId || current->ownerWorkspaceId != item.ownerWorkspaceId ||
            current->status != item.status || current->attempts != item.attempts) continue;
        apply(item, flight->results[index]);
        ++handled;
    }
    flight->leaseReleased.store(true);
    return handled;
}

void DesktopUploadRecoveryScheduler::apply(const UploadCustodyItem& item, const DesktopTransportResult& result) {
    if (queue_.quarantined()) return;
    if (result.serverTruth && result.serverTruth->localRecordingId == item.localRecordingId)
        (void)queue_.reconcile(*result.serverTruth);
    switch (result.status) {
    case DesktopTransportStatus::uploaded:
        (void)queue_.markUploaded(item.localRecordingId);
        break;
    case DesktopTransportStatus::authRequired:
        (void)queue_.markNeedsAuth(item.localRecordingId, result.safeReason.empty() ? "auth_required" : result.safeReason);
        break;
    case DesktopTransportStatus::invalidPackage:
        (void)queue_.markQuarantined(item.localRecordingId, "invalid_package");
        break;
    case DesktopTransportStatus::serverRejected:
        (void)queue_.markRetry(item.localRecordingId, "server_rejected");
        break;
    case DesktopTransportStatus::unsupportedPlatform:
        (void)queue_.markRetry(item.localRecordingId, "unsupported_platform");
        break;
    case DesktopTransportStatus::retryableFailure:
        (void)queue_.markRetry(item.localRecordingId, "transport_unavailable");
        break;
    }
}

} // namespace graf::windows
