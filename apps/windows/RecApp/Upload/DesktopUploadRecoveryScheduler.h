#pragma once

#include "DesktopHttpTransport.h"
#include "DesktopUploadQueueService.h"

#include <chrono>
#include <cstdint>
#include <functional>

namespace graf::windows {

enum class RecoveryTrigger {
    launch,
    activation,
    authRecovered,
    networkRecovered,
    wake,
    scheduled,
};

class DesktopUploadRecoveryScheduler final {
public:
    using Cancellation = std::shared_ptr<const std::atomic_bool>;
    // Custom executors must own all captured state, never UI/queue references.
    using WorkerHandler = std::function<DesktopTransportResult(const UploadCustodyItem&, Cancellation)>;

    // Only values cross the UI boundary. Native inspections belong to the
    // storage/network workers, never this retained scheduler flight.
    struct ProtectedFlight {
        ProtectedDesktopHttpConfig config;
        RecoveryTrigger trigger = RecoveryTrigger::scheduled;
        std::uint64_t epoch = 0;
        std::uint32_t maxAttempts = 8;
        std::shared_ptr<std::atomic_bool> cancelled = std::allocate_shared<std::atomic_bool>(CustodyAllocator<std::atomic_bool>{}, false);
        std::shared_ptr<const ProtectedUploadQueueValue> snapshot;
        CustodyVector<std::size_t> selected;
        std::optional<std::size_t> manualIndex;
        bool confirmUnowned = false;
        std::shared_ptr<const ProtectedDesktopTransportResult> fallback = std::allocate_shared<ProtectedDesktopTransportResult>(CustodyAllocator<ProtectedDesktopTransportResult>{});
        std::atomic_bool done{false}, leaseReleased{false};
    };
    using ProtectedWorker = std::function<bool(std::size_t)>;
    [[nodiscard]] std::shared_ptr<ProtectedFlight> beginProtected(RecoveryTrigger, ProtectedDesktopHttpConfig, std::uint64_t epoch);
    // Called only by the storage worker, after prepare commit/adoption. Each
    // step performs one upload and waits for its result commit/adoption.
    [[nodiscard]] static bool launchProtected(const std::shared_ptr<ProtectedFlight>&, ProtectedWorker,
        std::function<void()> completed);
    void retireProtected() noexcept;

    explicit DesktopUploadRecoveryScheduler(DesktopUploadQueueService& queue, std::uint32_t maxAttempts = 8);
    ~DesktopUploadRecoveryScheduler();
    DesktopUploadRecoveryScheduler(const DesktopUploadRecoveryScheduler&) = delete;
    DesktopUploadRecoveryScheduler& operator=(const DesktopUploadRecoveryScheduler&) = delete;

    // All methods are UI-owner-thread only. A completed flight remains busy
    // until drained; neither the worker nor cancel/destruction writes the ledger.
    [[nodiscard]] bool startAsync(RecoveryTrigger trigger, DesktopHttpConfig config);
    [[nodiscard]] bool startAsync(RecoveryTrigger trigger, WorkerHandler worker);
    [[nodiscard]] std::size_t drain();
    void cancel() noexcept;
    [[nodiscard]] bool busy() const noexcept;
    // Server-requested pause after a 429. No flight starts before it elapses, so
    // the client stops asking while the server is asking it to wait.
    void deferFor(std::uint32_t seconds) noexcept;
    // The server renewed the session while answering and named the new deadline.
    // Called on the owner thread with that deadline, so the shell can carry it to
    // the cabinet's own session cookie. Never called with a deadline the server
    // did not name.
    using SessionExpiryHandler = std::function<void(std::int64_t)>;
    void setSessionExpiryHandler(SessionExpiryHandler handler) { sessionExpiryHandler_ = std::move(handler); }
    [[nodiscard]] std::uint64_t deferralRemainingMs() const noexcept;

private:
    struct Flight;
    [[nodiscard]] bool prepare(RecoveryTrigger trigger);
    static void execute(const std::shared_ptr<Flight>& flight, WorkerHandler worker);
    void apply(const UploadCustodyItem& item, const DesktopTransportResult& result);
    DesktopUploadQueueService& queue_;
    std::uint32_t maxAttempts_;
    SessionExpiryHandler sessionExpiryHandler_;
    std::shared_ptr<Flight> flight_;
    std::shared_ptr<ProtectedFlight> protectedFlight_;
    // Wall-clock-independent pause: a sleep or a clock change must not shorten it.
    std::chrono::steady_clock::time_point deferredUntil_{};
};

} // namespace graf::windows
