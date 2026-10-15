#pragma once
#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <string_view>

namespace graf::windows {
enum class CalendarJoinSource { document, nativeAction };
enum class CalendarJoinState { idle, resolving, opening, handedOff, failed, cancelled };
enum class CalendarJoinReason { none, busy, notReady, stale, authRequired, eventUnavailable,
    dependencyUnavailable, invalidTarget, launchFailed, cancelled };
enum class CalendarJoinWorkKind { resolver, query, launch, dialog };

// Trusted native snapshot only, never populated directly from web payload.
struct CalendarJoinContext {
    std::string origin, owner, workspace, sessionToken;
    std::uint64_t authGeneration = 0;
    CalendarJoinSource source = CalendarJoinSource::document;
    std::uint64_t sourceEpoch = 0;
    std::string sourceIdentity; // document nonce OR native action identity
    std::chrono::steady_clock::time_point actionExpiresAt = std::chrono::steady_clock::time_point::max();
};
struct CalendarJoinResult {
    CalendarJoinState state = CalendarJoinState::idle;
    CalendarJoinReason reason = CalendarJoinReason::none;
};
struct CalendarJoinWork {
    std::uint64_t operationId = 0, workId = 0;
    CalendarJoinWorkKind kind = CalendarJoinWorkKind::resolver;
    std::chrono::steady_clock::time_point deadline;
    std::shared_ptr<const std::atomic_bool> cancellation;
};

// One UI-thread instance shared by cabinet/menu/card. No I/O or launch authority.
// Adapter must retain each ticket until actual worker/OS/dialog completion; this
// helper cannot prove completion or substitute for fresh authorization/URL checks.
class CalendarJoinOperation final {
public:
    using Clock = std::chrono::steady_clock;
    CalendarJoinOperation() = default;
    CalendarJoinOperation(const CalendarJoinOperation&) = delete;
    CalendarJoinOperation& operator=(const CalendarJoinOperation&) = delete;
    ~CalendarJoinOperation();
    [[nodiscard]] std::optional<CalendarJoinWork> begin(std::string eventId, std::string requestId,
        CalendarJoinContext context, Clock::time_point acceptedAt, bool menuRetry = false);
    [[nodiscard]] bool current(std::uint64_t id, const CalendarJoinContext&, Clock::time_point) noexcept;
    // Call only after matching actual completion or a rejected dispatch. An OS
    // startFailed with no obtained handle ends only its synchronous dispatch
    // scope (bridge §10), never proof of no OS side effect or automatic retry.
    // False means drain-only: no result/launch/auth/Record effect may be applied.
    [[nodiscard]] bool complete(const CalendarJoinWork&, const CalendarJoinContext&, Clock::time_point) noexcept;
    [[nodiscard]] bool opening(std::uint64_t id, const CalendarJoinContext&, Clock::time_point) noexcept;
    [[nodiscard]] std::optional<CalendarJoinWork> work(std::uint64_t id, CalendarJoinWorkKind,
        const CalendarJoinContext&, Clock::time_point) noexcept;
    // Explicit confirmed browser recovery only; keeps original request/action expiry.
    [[nodiscard]] std::optional<CalendarJoinWork> recover(std::uint64_t id,
        const CalendarJoinContext&, Clock::time_point confirmedAt) noexcept;
    // Trusted menu caller only. Failed attempts never become current again;
    // the reservation owns the explicit Retry decision after actual old drain.
    [[nodiscard]] bool retryCurrent(std::uint64_t id, const CalendarJoinContext&, Clock::time_point) noexcept;
    [[nodiscard]] std::optional<CalendarJoinWork> retryDialog(std::uint64_t id,
        const CalendarJoinContext&, Clock::time_point);
    [[nodiscard]] bool confirmRetry(const CalendarJoinWork&, const CalendarJoinContext&, Clock::time_point) noexcept;
    // Requires matching dialog drain AND its recorded Primary click. New IDs,
    // same original source/expiry, resolver budget starts at that click.
    [[nodiscard]] std::optional<CalendarJoinWork> retry(std::uint64_t id, std::string requestId,
        const CalendarJoinContext&, Clock::time_point);
    [[nodiscard]] bool finish(std::uint64_t id, CalendarJoinState, CalendarJoinReason,
        const CalendarJoinContext&, Clock::time_point) noexcept;
    void cancel(std::uint64_t id) noexcept;
    [[nodiscard]] bool busy() const noexcept;
    [[nodiscard]] CalendarJoinResult result() const noexcept { return result_; }
    [[nodiscard]] const std::string& eventId() const noexcept { return eventId_; }
    [[nodiscard]] const std::string& requestId() const noexcept { return requestId_; }
private:
    [[nodiscard]] std::optional<CalendarJoinWork> makeWork(CalendarJoinWorkKind, Clock::time_point) noexcept;
    [[nodiscard]] bool matchesWork(const CalendarJoinWork&) const noexcept;
    void terminal(CalendarJoinState, CalendarJoinReason) noexcept;
    CalendarJoinContext context_;
    CalendarJoinResult result_;
    std::string eventId_, requestId_;
    std::uint64_t operationId_ = 0, workId_ = 0;
    std::shared_ptr<std::atomic_bool> cancellation_;
    std::optional<CalendarJoinWork> work_;
    bool retryAllowed_ = false;
    std::optional<Clock::time_point> retryConfirmedAt_;
};
}
