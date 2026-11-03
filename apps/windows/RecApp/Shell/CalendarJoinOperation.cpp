#include "CalendarJoinOperation.h"
#include "../Upload/DesktopApiClient.h"
#include <limits>

namespace graf::windows {
namespace {
bool terminalState(CalendarJoinState state) noexcept {
    return state == CalendarJoinState::handedOff || state == CalendarJoinState::failed || state == CalendarJoinState::cancelled;
}
bool sameContext(const CalendarJoinContext& a, const CalendarJoinContext& b) noexcept {
    return a.origin == b.origin && a.owner == b.owner && a.workspace == b.workspace && a.sessionToken == b.sessionToken &&
        a.authGeneration == b.authGeneration && a.source == b.source && a.sourceEpoch == b.sourceEpoch &&
        a.sourceIdentity == b.sourceIdentity && a.actionExpiresAt == b.actionExpiresAt;
}
bool normalizeId(std::string& id) {
    if (DesktopApiClient::calendarJoinTargetPath(id).empty()) return false;
    for (auto& c : id) if (c >= 'A' && c <= 'F') c = static_cast<char>(c + ('a' - 'A'));
    return true;
}
CalendarJoinOperation::Clock::time_point resolverDeadline(CalendarJoinOperation::Clock::time_point acceptedAt) noexcept {
    using Clock = CalendarJoinOperation::Clock;
    const auto budget = std::chrono::seconds(15);
    return acceptedAt <= Clock::time_point::max() - budget ? acceptedAt + budget : Clock::time_point::max();
}
}

CalendarJoinOperation::~CalendarJoinOperation() {
    if (cancellation_) cancellation_->store(true);
}
bool CalendarJoinOperation::busy() const noexcept {
    return result_.state != CalendarJoinState::idle && (!terminalState(result_.state) || work_ || retryAllowed_);
}
void CalendarJoinOperation::terminal(CalendarJoinState state, CalendarJoinReason reason) noexcept {
    result_ = {state, reason};
    if (state != CalendarJoinState::failed) retryAllowed_ = false;
    retryConfirmedAt_.reset();
    if (cancellation_) cancellation_->store(true);
    if (!work_ && !retryAllowed_) context_.sessionToken.clear();
}
std::optional<CalendarJoinWork> CalendarJoinOperation::makeWork(CalendarJoinWorkKind kind, Clock::time_point now) noexcept {
    if (workId_ == std::numeric_limits<std::uint64_t>::max()) {
        retryAllowed_ = false;
        terminal(CalendarJoinState::failed, CalendarJoinReason::dependencyUnavailable); return std::nullopt;
    }
    const auto deadline = kind == CalendarJoinWorkKind::resolver ? resolverDeadline(now) : Clock::time_point::max();
    work_ = CalendarJoinWork{operationId_, ++workId_, kind, deadline, cancellation_};
    return work_;
}
std::optional<CalendarJoinWork> CalendarJoinOperation::begin(std::string event, std::string request,
    CalendarJoinContext context, Clock::time_point now, bool menuRetry) {
    if (busy() || operationId_ == std::numeric_limits<std::uint64_t>::max() ||
        workId_ == std::numeric_limits<std::uint64_t>::max() || !normalizeId(event) || !normalizeId(request) ||
        context.origin.empty() || context.owner.empty() || context.workspace.empty() || context.sessionToken.empty() ||
        context.sourceIdentity.empty() || now >= context.actionExpiresAt ||
        (context.source != CalendarJoinSource::document && context.source != CalendarJoinSource::nativeAction) ||
        (menuRetry && context.source != CalendarJoinSource::nativeAction)) return std::nullopt;
    auto cancellation = std::make_shared<std::atomic_bool>(false); // allocate before mutating admission
    context_ = std::move(context); eventId_ = std::move(event); requestId_ = std::move(request);
    cancellation_ = std::move(cancellation); ++operationId_;
    retryAllowed_ = menuRetry; retryConfirmedAt_.reset();
    result_ = {CalendarJoinState::resolving, CalendarJoinReason::none};
    return makeWork(CalendarJoinWorkKind::resolver, now);
}
bool CalendarJoinOperation::current(std::uint64_t id, const CalendarJoinContext& context, Clock::time_point now) noexcept {
    if (!id || id != operationId_ || result_.state == CalendarJoinState::idle || terminalState(result_.state)) return false;
    if (!sameContext(context_, context) || now >= context_.actionExpiresAt) {
        terminal(CalendarJoinState::cancelled, CalendarJoinReason::stale); return false;
    }
    if (work_ && work_->kind == CalendarJoinWorkKind::resolver && now >= work_->deadline) {
        terminal(CalendarJoinState::failed, CalendarJoinReason::dependencyUnavailable); return false;
    }
    return true;
}
bool CalendarJoinOperation::matchesWork(const CalendarJoinWork& ticket) const noexcept {
    return work_ && ticket.operationId == work_->operationId && ticket.workId == work_->workId &&
        ticket.kind == work_->kind && ticket.deadline == work_->deadline && ticket.cancellation == work_->cancellation;
}
bool CalendarJoinOperation::complete(const CalendarJoinWork& ticket, const CalendarJoinContext& context, Clock::time_point now) noexcept {
    if (!matchesWork(ticket)) return false;
    const bool applicable = current(ticket.operationId, context, now); // check deadline BEFORE drain
    if (retryAllowed_ && result_.state == CalendarJoinState::failed)
        (void)retryCurrent(ticket.operationId, context, now);
    work_.reset();
    if (!applicable && !retryAllowed_) context_.sessionToken.clear();
    return applicable;
}
bool CalendarJoinOperation::opening(std::uint64_t id, const CalendarJoinContext& context, Clock::time_point now) noexcept {
    if (!current(id, context, now) || work_ || result_.state != CalendarJoinState::resolving) return false;
    result_.state = CalendarJoinState::opening; return true;
}
std::optional<CalendarJoinWork> CalendarJoinOperation::work(std::uint64_t id, CalendarJoinWorkKind kind,
    const CalendarJoinContext& context, Clock::time_point now) noexcept {
    if (!current(id, context, now) || work_ || result_.state != CalendarJoinState::opening ||
        (kind != CalendarJoinWorkKind::query && kind != CalendarJoinWorkKind::launch && kind != CalendarJoinWorkKind::dialog)) return std::nullopt;
    return makeWork(kind, now);
}
std::optional<CalendarJoinWork> CalendarJoinOperation::recover(std::uint64_t id,
    const CalendarJoinContext& context, Clock::time_point now) noexcept {
    if (!current(id, context, now) || work_ || result_.state != CalendarJoinState::opening) return std::nullopt;
    return makeWork(CalendarJoinWorkKind::resolver, now);
}
bool CalendarJoinOperation::retryCurrent(std::uint64_t id, const CalendarJoinContext& context, Clock::time_point now) noexcept {
    if (!id || id != operationId_ || !retryAllowed_ || result_.state != CalendarJoinState::failed) return false;
    if (!sameContext(context_, context) || now >= context_.actionExpiresAt) { cancel(id); return false; }
    return true;
}
std::optional<CalendarJoinWork> CalendarJoinOperation::retryDialog(std::uint64_t id,
    const CalendarJoinContext& context, Clock::time_point now) {
    if (!retryCurrent(id, context, now) || work_ || retryConfirmedAt_) return std::nullopt;
    auto cancellation = std::make_shared<std::atomic_bool>(false);
    cancellation_ = std::move(cancellation);
    return makeWork(CalendarJoinWorkKind::dialog, now);
}
bool CalendarJoinOperation::confirmRetry(const CalendarJoinWork& ticket,
    const CalendarJoinContext& context, Clock::time_point clickedAt) noexcept {
    if (!matchesWork(ticket) || ticket.kind != CalendarJoinWorkKind::dialog || !ticket.cancellation ||
        ticket.cancellation->load() || retryConfirmedAt_ ||
        !retryCurrent(ticket.operationId, context, clickedAt)) return false;
    retryConfirmedAt_ = clickedAt; return true;
}
std::optional<CalendarJoinWork> CalendarJoinOperation::retry(std::uint64_t id, std::string request,
    const CalendarJoinContext& context, Clock::time_point now) {
    if (!retryCurrent(id, context, now) || work_ || !retryConfirmedAt_ || now < *retryConfirmedAt_ ||
        now >= resolverDeadline(*retryConfirmedAt_) || operationId_ == std::numeric_limits<std::uint64_t>::max() ||
        workId_ == std::numeric_limits<std::uint64_t>::max() || !normalizeId(request) || request == requestId_) return std::nullopt;
    auto cancellation = std::make_shared<std::atomic_bool>(false); // prepare before replacing the failed attempt
    const auto click = *retryConfirmedAt_;
    if (cancellation_) cancellation_->store(true);
    cancellation_ = std::move(cancellation); requestId_ = std::move(request); ++operationId_;
    retryConfirmedAt_.reset(); result_ = {CalendarJoinState::resolving, CalendarJoinReason::none};
    return makeWork(CalendarJoinWorkKind::resolver, click);
}
bool CalendarJoinOperation::finish(std::uint64_t id, CalendarJoinState state, CalendarJoinReason reason,
    const CalendarJoinContext& context, Clock::time_point now) noexcept {
    if (!current(id, context, now)) return false;
    if (state == CalendarJoinState::handedOff) {
        if (work_ || result_.state != CalendarJoinState::opening || reason != CalendarJoinReason::none) return false;
    } else if (state == CalendarJoinState::failed) {
        if (reason != CalendarJoinReason::authRequired && reason != CalendarJoinReason::eventUnavailable &&
            reason != CalendarJoinReason::dependencyUnavailable && reason != CalendarJoinReason::invalidTarget &&
            reason != CalendarJoinReason::launchFailed) return false;
    } else if (state == CalendarJoinState::cancelled) {
        if (reason != CalendarJoinReason::stale && reason != CalendarJoinReason::cancelled) return false;
    } else return false;
    terminal(state, reason); return true;
}
void CalendarJoinOperation::cancel(std::uint64_t id) noexcept {
    if (id && id == operationId_ && result_.state == CalendarJoinState::failed && retryAllowed_) {
        retryAllowed_ = false; retryConfirmedAt_.reset();
        if (cancellation_) cancellation_->store(true);
        if (!work_) context_.sessionToken.clear();
    }
    if (id && id == operationId_ && result_.state != CalendarJoinState::idle && !terminalState(result_.state))
        terminal(CalendarJoinState::cancelled, CalendarJoinReason::cancelled);
}
}
