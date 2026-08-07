from twobrain_rec_server.billing.catalog import FREE_PROCESSING_SECONDS, plan_descriptor
from twobrain_rec_server.billing.entitlements import entitlement_for_plan, processing_admission


def test_paid_plans_are_unlimited_for_processing_but_not_for_storage() -> None:
    personal = plan_descriptor("personal")
    assert personal.processing_mode == "unlimited"
    assert personal.storage_bytes == 2_000_000_000
    assert FREE_PROCESSING_SECONDS == 18_000


def test_free_can_process_without_audio_archive_and_paid_has_no_minute_cap() -> None:
    free = entitlement_for_plan(plan_code="free")
    assert processing_admission(
        entitlement=free,
        committed_free_seconds=17_999,
        accepted_seconds=1,
        save_audio=False,
    ) == (True, "free_without_audio_archive")
    paid = entitlement_for_plan(plan_code="personal")
    assert processing_admission(
        entitlement=paid,
        committed_free_seconds=FREE_PROCESSING_SECONDS,
        accepted_seconds=86_400,
        save_audio=True,
    ) == (True, "paid_unlimited")
