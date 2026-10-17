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
    static void execute(const std::shared_ptr<Flight>& flight, const WorkerHandler& worker);
    void apply(const UploadCustodyItem& item, const DesktopTransportResult& result);
    DesktopUploadQueueService& queue_;
    std::uint32_t maxAttempts_;
    SessionExpiryHandler sessionExpiryHandler_;
    std::shared_ptr<Flight> flight_;
    // Wall-clock-independent pause: a sleep or a clock change must not shorten it.
    std::chrono::steady_clock::time_point deferredUntil_{};
};

} // namespace graf::windows
