from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta

try:
    from temporalio import workflow
    from temporalio.workflow import ActivityCancellationType
except Exception:  # pragma: no cover - import fallback for docs/unit tests without worker runtime
    workflow = None
    ActivityCancellationType = None

PROCESSING_ACTIVITY_MAX_ATTEMPTS = 6
PROCESSING_WAIT_CONTINUE_AS_NEW_CHECKS = 32
NORMALIZATION_WAIT_FALLBACK_SECONDS = 900


def processing_retry_policy():
    from temporalio.common import RetryPolicy

    return RetryPolicy(
        initial_interval=timedelta(seconds=15),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=2),
        maximum_attempts=PROCESSING_ACTIVITY_MAX_ATTEMPTS,
    )


if workflow is not None:

    @workflow.defn
    class MediaScribeProcessingWorkflow:
        def __init__(self) -> None:
            self._manual_check_requested = False

        @workflow.signal
        async def request_manual_check(self) -> None:
            self._manual_check_requested = True

        @workflow.update(name="request_manual_check")
        async def request_manual_check_update(self) -> dict[str, str]:
            self._manual_check_requested = True
            return {"status": "accepted"}

        @workflow.run
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            if not workflow.patched("processing-recovery-v1"):
                return await workflow.execute_activity(
                    "run_processing_pipeline_activity",
                    payload,
                    schedule_to_close_timeout=timedelta(hours=4),
                    heartbeat_timeout=timedelta(seconds=60),
                    retry_policy=processing_retry_policy(),
                )
            step_payload = dict(payload)
            step_payload["single_step"] = "true"
            bounded_wait_history = workflow.patched("processing-wait-continue-as-new-v1")
            cancellation_type = (
                ActivityCancellationType.WAIT_CANCELLATION_COMPLETED
                if workflow.patched("processing-cancellation-v1")
                else ActivityCancellationType.TRY_CANCEL
            )
            wait_checks = 0

            def continue_after_wait() -> None:
                nonlocal wait_checks
                wait_checks += 1
                if bounded_wait_history and (
                    wait_checks >= PROCESSING_WAIT_CONTINUE_AS_NEW_CHECKS
                    or workflow.info().is_continue_as_new_suggested()
                ):
                    workflow.continue_as_new(payload)

            while True:
                # Clear only immediately before the next check. A signal/update
                # received while the activity is running must wake the next
                # same-job check instead of being cleared after the activity.
                self._manual_check_requested = False
                result = await workflow.execute_activity(
                    "run_processing_pipeline_activity",
                    step_payload,
                    schedule_to_close_timeout=timedelta(minutes=20),
                    heartbeat_timeout=timedelta(seconds=60),
                    retry_policy=processing_retry_policy(),
                    cancellation_type=cancellation_type,
                )
                status = result.get("processing_status")
                if status == "normalization_pending":
                    delay = None
                    next_attempt_at = result.get("next_attempt_at")
                    if isinstance(next_attempt_at, str):
                        try:
                            due_at = datetime.fromisoformat(next_attempt_at)
                            if due_at.tzinfo is not None:
                                delay = int((due_at - workflow.now()).total_seconds())
                        except ValueError:
                            pass
                    if delay is None:
                        try:
                            delay = int(
                                result.get(
                                    "next_poll_seconds",
                                    str(NORMALIZATION_WAIT_FALLBACK_SECONDS),
                                )
                            )
                        except (TypeError, ValueError):
                            delay = NORMALIZATION_WAIT_FALLBACK_SECONDS
                    delay = max(5, min(delay, NORMALIZATION_WAIT_FALLBACK_SECONDS))
                    with suppress(TimeoutError):
                        await workflow.wait_condition(
                            lambda: self._manual_check_requested,
                            timeout=timedelta(seconds=delay),
                            timeout_summary="manual upload normalization readiness",
                        )
                    continue_after_wait()
                    continue
                if status == "blocked_unknown":
                    # A lost upload response is not a terminal workflow. The
                    # activity schedules a same-key lookup when it is safe;
                    # manual reconciliation can wake the same durable wait.
                    try:
                        delay = max(5, min(int(result.get("next_poll_seconds", "")), 900))
                    except (TypeError, ValueError):
                        delay = None
                    with suppress(TimeoutError):
                        await workflow.wait_condition(
                            lambda: self._manual_check_requested,
                            **({"timeout": timedelta(seconds=delay)} if delay is not None else {}),
                            timeout_summary="manual same-key reconciliation",
                        )
                    continue_after_wait()
                    continue
                if status == "failed_retryable" and result.get("reason_code") in {
                    "processing_retry_deadline_exceeded",
                    "mediascribe_poll_limit_exceeded",
                }:
                    # Watchdog expiry is not provider failure. Keep the durable
                    # workflow open for a manual same-job check without polling.
                    await workflow.wait_condition(
                        lambda: self._manual_check_requested,
                        timeout_summary="manual provider processing check",
                    )
                    continue_after_wait()
                    continue
                if status not in {"polling", "waiting_retry", "submitted", "importing"}:
                    return result
                try:
                    delay = max(5, min(int(result.get("next_poll_seconds", "30")), 900))
                except (TypeError, ValueError):
                    delay = 30
                with suppress(TimeoutError):
                    await workflow.wait_condition(
                        lambda: self._manual_check_requested,
                        timeout=timedelta(seconds=delay),
                        timeout_summary="next provider processing check",
                    )
                continue_after_wait()

else:

    class MediaScribeProcessingWorkflow:
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return payload
