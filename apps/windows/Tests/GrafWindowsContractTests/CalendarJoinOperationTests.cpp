#include "../../RecApp/Shell/CalendarJoinOperation.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>

using namespace graf::windows;
using Op = CalendarJoinOperation;
using Clock = Op::Clock;
using State = CalendarJoinState;
using Reason = CalendarJoinReason;
using Kind = CalendarJoinWorkKind;
constexpr auto eventId = "ABCDEFAB-1234-4567-89AB-ABCDEFABCDEF";
constexpr auto requestId = "01234567-1234-4567-89ab-0123456789ab";
const auto now = Clock::time_point{} + std::chrono::seconds(100);

CalendarJoinContext context() {
    return {"https://example.org", "synthetic-owner", "synthetic-workspace", "synthetic-token",
        1, CalendarJoinSource::document, 2, "synthetic-nonce", Clock::time_point::max()};
}

void oneFlightAndDrain() {
    Op op;
    const auto ctx = context();
    const auto resolver = op.begin(eventId, requestId, ctx, now);
    assert(resolver && op.busy() && op.result().state == State::resolving);
    assert(op.eventId() == "abcdefab-1234-4567-89ab-abcdefabcdef");
    auto native = ctx; native.source = CalendarJoinSource::nativeAction; native.sourceIdentity = "synthetic-action";
    assert(!op.begin(eventId, requestId, native, now));
    assert(!op.opening(resolver->operationId, ctx, now)); // initial work still pending
    op.cancel(resolver->operationId);
    assert(op.result().state == State::cancelled && resolver->cancellation->load() && op.busy());
    assert(!op.begin(eventId, requestId, ctx, now));
    assert(!op.complete(*resolver, ctx, now)); // drain, never apply a cancelled result
    assert(!op.busy());
    const auto next = op.begin(eventId, requestId, ctx, now);
    assert(next && next->operationId != resolver->operationId);
    assert(!op.complete(*resolver, ctx, now) && op.busy());
    op.cancel(resolver->operationId); // old UI callback cannot cancel new flight
    assert(op.result().state == State::resolving && !next->cancellation->load());
    assert(op.complete(*next, ctx, now));
    assert(op.opening(next->operationId, ctx, now));
    const auto launch = op.work(next->operationId, Kind::launch, ctx, now);
    assert(launch && !op.finish(next->operationId, State::handedOff, Reason::none, ctx, now));
    assert(op.complete(*launch, ctx, now));
    assert(op.finish(next->operationId, State::handedOff, Reason::none, ctx, now) && !op.busy());
}

void everyContextFence() {
    for (unsigned field = 0; field < 9; ++field) {
        Op op; const auto ctx = context(); const auto resolver = op.begin(eventId, requestId, ctx, now);
        auto changed = ctx;
        switch (field) {
        case 0: changed.origin += ".other"; break;
        case 1: changed.owner += "-other"; break;
        case 2: changed.workspace += "-other"; break;
        case 3: changed.sessionToken += "-other"; break;
        case 4: ++changed.authGeneration; break;
        case 5: changed.source = CalendarJoinSource::nativeAction; break;
        case 6: ++changed.sourceEpoch; break;
        case 7: changed.sourceIdentity += "-other"; break;
        case 8: changed.actionExpiresAt = now + std::chrono::seconds(1); break;
        }
        assert(!op.current(resolver->operationId, changed, now));
        assert(op.result().state == State::cancelled && op.result().reason == Reason::stale && op.busy());
        assert(!op.complete(*resolver, changed, now) && !op.busy());
        assert(!op.opening(resolver->operationId, ctx, now));
    }
}

void resolverAndRecoveryBudgets() {
    Op op; auto ctx = context();
    ctx.source = CalendarJoinSource::nativeAction; ctx.sourceIdentity = "synthetic-action";
    ctx.actionExpiresAt = now + std::chrono::seconds(90);
    const auto resolver = op.begin(eventId, requestId, ctx, now);
    assert(resolver && resolver->deadline == now + std::chrono::seconds(15));
    assert(op.complete(*resolver, ctx, now + std::chrono::seconds(1)));
    assert(op.opening(resolver->operationId, ctx, now + std::chrono::seconds(1)));
    const auto dialog = op.work(resolver->operationId, Kind::dialog, ctx, now + std::chrono::seconds(2));
    assert(dialog && !op.recover(resolver->operationId, ctx, now + std::chrono::seconds(20)));
    assert(op.current(resolver->operationId, ctx, now + std::chrono::seconds(30))); // no OS/dialog 15s timeout
    assert(op.complete(*dialog, ctx, now + std::chrono::seconds(30)));
    const auto fresh = op.recover(resolver->operationId, ctx, now + std::chrono::seconds(30));
    assert(fresh && fresh->workId != resolver->workId && fresh->deadline == now + std::chrono::seconds(45));
    assert(op.result().state == State::opening && op.busy());
    assert(!op.complete(*resolver, ctx, now + std::chrono::seconds(31)) && op.busy());
    assert(op.current(fresh->operationId, ctx, fresh->deadline - std::chrono::nanoseconds(1)));
    assert(!op.current(fresh->operationId, ctx, fresh->deadline));
    assert(op.result().state == State::failed && op.result().reason == Reason::dependencyUnavailable && op.busy());
    assert(!op.complete(*fresh, ctx, fresh->deadline) && !op.busy());
    assert(!op.recover(fresh->operationId, ctx, fresh->deadline)); // terminal cannot revive

    Op expires; const auto first = expires.begin(eventId, requestId, ctx, now);
    assert(expires.complete(*first, ctx, now) && expires.opening(first->operationId, ctx, now));
    assert(expires.recover(first->operationId, ctx, now + std::chrono::seconds(89)));
    assert(!expires.current(first->operationId, ctx, ctx.actionExpiresAt)); // fresh budget does not extend action
    assert(expires.result().state == State::cancelled && expires.busy());

    Op timeout; const auto work = timeout.begin(eventId, requestId, context(), now);
    assert(!timeout.complete(*work, context(), work->deadline));
    assert(timeout.result().state == State::failed && !timeout.busy());
    assert(!timeout.opening(work->operationId, context(), work->deadline));
    Op invalid; assert(!invalid.begin("bad", requestId, context(), now));
    assert(!invalid.begin(eventId, "bad", context(), now));
    ctx.actionExpiresAt = now; assert(!invalid.begin(eventId, requestId, ctx, now));
}

void ticketAndClockBounds() {
    Op op; const auto ctx = context();
    const auto original = op.begin(eventId, requestId, ctx, now);
    assert(original);
    for (unsigned field = 0; field < 3; ++field) {
        auto changed = *original;
        if (field == 0) changed.kind = Kind::launch;
        else if (field == 1) changed.deadline += std::chrono::nanoseconds(1);
        else changed.cancellation = std::make_shared<std::atomic_bool>(false);
        assert(!op.complete(changed, ctx, now) && op.busy());
        assert(op.result().state == State::resolving && !original->cancellation->load());
    }
    assert(op.complete(*original, ctx, now));
    Op limit; const auto max = Clock::time_point::max();
    const auto last = limit.begin(eventId, requestId, ctx, max - std::chrono::seconds(1));
    assert(last && last->deadline == max);
    assert(limit.current(last->operationId, ctx, max - std::chrono::nanoseconds(1)));
    assert(!limit.complete(*last, ctx, max) && !limit.busy());
    assert(limit.result().state == State::cancelled && last->cancellation->load());
}

void menuRetryOwnership() {
    auto ctx = context(); ctx.source = CalendarJoinSource::nativeAction;
    ctx.actionExpiresAt = now + std::chrono::seconds(90);
    constexpr auto nextRequest = "01234567-1234-4567-89ab-0123456789ac";
    Op invalid; assert(!invalid.begin(eventId, requestId, context(), now, true));
    Op op; const auto old = op.begin(eventId, requestId, ctx, now, true);
    assert(old && op.finish(old->operationId, State::failed, Reason::launchFailed, ctx, now));
    assert(op.busy() && old->cancellation->load());
    assert(!op.retryDialog(old->operationId, ctx, now)); // old work still owned
    assert(!op.complete(*old, ctx, now) && op.busy()); // failed result is drain-only
    assert(!op.current(old->operationId, ctx, now));
    assert(!op.begin(eventId, requestId, ctx, now)); // no admission gap
    assert(!op.retry(old->operationId, nextRequest, ctx, now)); // no explicit dialog decision
    const auto dialog = op.retryDialog(old->operationId, ctx, now);
    assert(dialog && !dialog->cancellation->load() && dialog->cancellation != old->cancellation);
    auto forged = *dialog; ++forged.workId;
    assert(!op.confirmRetry(forged, ctx, now));
    const auto click = now + std::chrono::seconds(3);
    assert(op.confirmRetry(*dialog, ctx, click));
    assert(!op.confirmRetry(*dialog, ctx, click + std::chrono::seconds(1))); // first click owns budget
    assert(!op.retry(old->operationId, nextRequest, ctx, click)); // dialog not drained
    assert(!op.complete(forged, ctx, click) && op.busy());
    assert(!op.complete(*dialog, ctx, click + std::chrono::seconds(2)) && op.busy());
    assert(!op.retry(old->operationId, requestId, ctx, click + std::chrono::seconds(2)));
    assert(!op.retry(old->operationId, "bad", ctx, click + std::chrono::seconds(2)));
    assert(!op.retry(old->operationId, nextRequest, ctx, click - std::chrono::nanoseconds(1)));
    const auto fresh = op.retry(old->operationId, nextRequest, ctx, click + std::chrono::seconds(2));
    assert(fresh && fresh->operationId != old->operationId && fresh->workId != dialog->workId);
    assert(fresh->deadline == click + std::chrono::seconds(15));
    assert(op.requestId() == nextRequest && op.eventId() == "abcdefab-1234-4567-89ab-abcdefabcdef");
    assert(dialog->cancellation->load() && !fresh->cancellation->load() && op.busy());
    op.cancel(old->operationId);
    assert(!op.complete(*dialog, ctx, click) && !op.confirmRetry(*dialog, ctx, click));
    assert(op.current(fresh->operationId, ctx, click + std::chrono::seconds(14)));
    assert(!op.complete(*fresh, ctx, fresh->deadline) && op.busy());
    const auto again = op.retryDialog(fresh->operationId, ctx, fresh->deadline);
    assert(again); // each NEW failed attempt permits its own explicit decision
    op.cancel(fresh->operationId);
    assert(op.result().state == State::failed && op.busy() && again->cancellation->load());
    assert(!op.complete(*again, ctx, fresh->deadline) && !op.busy());
}

void menuRetryFences() {
    constexpr auto nextRequest = "01234567-1234-4567-89ab-0123456789ac";
    for (unsigned field = 0; field < 11; ++field) {
        auto ctx = context(); ctx.source = CalendarJoinSource::nativeAction;
        ctx.actionExpiresAt = now + std::chrono::seconds(20);
        Op op; const auto old = op.begin(eventId, requestId, ctx, now, true);
        assert(op.finish(old->operationId, State::failed, Reason::launchFailed, ctx, now));
        assert(!op.complete(*old, ctx, now));
        const auto dialog = op.retryDialog(old->operationId, ctx, now);
        assert(dialog && op.confirmRetry(*dialog, ctx, now));
        auto changed = ctx; auto finishAt = now;
        switch (field) {
        case 0: changed.origin += ".other"; break;
        case 1: changed.owner += "-other"; break;
        case 2: changed.workspace += "-other"; break;
        case 3: changed.sessionToken += "-other"; break;
        case 4: ++changed.authGeneration; break;
        case 5: changed.source = CalendarJoinSource::document; break;
        case 6: ++changed.sourceEpoch; break;
        case 7: changed.sourceIdentity += "-other"; break;
        case 8: changed.actionExpiresAt += std::chrono::seconds(1); break;
        case 9: finishAt = ctx.actionExpiresAt; break;
        case 10: finishAt = now + std::chrono::seconds(15); break;
        }
        assert(!op.complete(*dialog, changed, finishAt));
        assert(!op.retry(old->operationId, nextRequest, changed, finishAt));
        op.cancel(old->operationId);
        assert(!op.busy() && op.result().state == State::failed);
    }
    auto ctx = context(); ctx.source = CalendarJoinSource::nativeAction;
    Op cancelled; const auto old = cancelled.begin(eventId, requestId, ctx, now, true);
    assert(cancelled.finish(old->operationId, State::failed, Reason::launchFailed, ctx, now));
    cancelled.cancel(old->operationId);
    assert(cancelled.busy() && !cancelled.retryCurrent(old->operationId, ctx, now));
    assert(!cancelled.complete(*old, ctx, now) && !cancelled.busy());
    Op oldDialog; const auto resolver = oldDialog.begin(eventId, requestId, ctx, now, true);
    assert(oldDialog.complete(*resolver, ctx, now) && oldDialog.opening(resolver->operationId, ctx, now));
    const auto browser = oldDialog.work(resolver->operationId, Kind::dialog, ctx, now);
    assert(browser && oldDialog.finish(resolver->operationId, State::failed, Reason::launchFailed, ctx, now));
    assert(!oldDialog.confirmRetry(*browser, ctx, now)); // Failed browser dialog is not a new Retry decision.
    assert(!oldDialog.complete(*browser, ctx, now) && oldDialog.busy());
    oldDialog.cancel(resolver->operationId); assert(!oldDialog.busy());
}

void menuFirstDeadlineTick() {
    auto ctx = context(); ctx.source = CalendarJoinSource::nativeAction;
    ctx.actionExpiresAt = now + std::chrono::seconds(90);
    Op op; auto resolver = op.begin(eventId, requestId, ctx, now, true);
    for (unsigned attempt = 0; attempt < 2; ++attempt) {
        assert(resolver && op.result().state == State::resolving);
        const auto tick = resolver->deadline;
        // The host's ordered first-poll decision, bound by its source-wiring assertion.
        if (!op.current(resolver->operationId, ctx, tick) && !op.retryCurrent(resolver->operationId, ctx, tick))
            op.cancel(resolver->operationId);
        assert(op.result().state == State::failed && op.busy() && resolver->cancellation->load());
        assert(!op.retryDialog(resolver->operationId, ctx, tick)); // Worker is not drained by timeout.
        assert(!op.complete(*resolver, ctx, tick) && op.busy());
        const auto dialog = op.retryDialog(resolver->operationId, ctx, tick);
        const auto click = tick + std::chrono::seconds(1);
        assert(dialog && op.confirmRetry(*dialog, ctx, click));
        assert(!op.complete(*dialog, ctx, click) && op.busy());
        if (attempt == 0) resolver = op.retry(resolver->operationId,
            "01234567-1234-4567-89ab-0123456789ac", ctx, click);
        else { op.cancel(resolver->operationId); assert(!op.busy()); }
    }
    for (bool expired : {false, true}) {
        Op revoked; const auto work = revoked.begin(eventId, requestId, ctx, now, true);
        const auto tick = expired ? ctx.actionExpiresAt : work->deadline;
        const auto currentContext = expired ? ctx : CalendarJoinContext{}; // Host proves source unavailable.
        if (!revoked.current(work->operationId, currentContext, tick) &&
            !revoked.retryCurrent(work->operationId, currentContext, tick)) revoked.cancel(work->operationId);
        assert(revoked.result().state == State::cancelled && revoked.busy());
        assert(!revoked.complete(*work, currentContext, tick) && !revoked.busy());
        assert(!revoked.retryDialog(work->operationId, ctx, tick));
    }
}

int main() {
    oneFlightAndDrain(); everyContextFence(); resolverAndRecoveryBudgets(); ticketAndClockBounds();
    menuRetryOwnership(); menuRetryFences(); menuFirstDeadlineTick();
    std::puts("CalendarJoinOperationTests passed; state/fence only, not adapter completion proof");
}
