from twobrain_rec_server.billing.registry import (
    RegistryInputError,
    assess_registry_completeness,
    build_registry_gap,
    summarize_registry_csv,
)


def test_payments_and_refunds_have_independent_complete_reports() -> None:
    payments = summarize_registry_csv(
        "payment_id,amount\npay-1,790.00\n",
        registry_kind="payments",
        environment="test",
        required_columns=("payment_id", "amount"),
        part_name="part-01",
    )
    refunds = summarize_registry_csv(
        "refund_id,amount\nref-1,790.00\n",
        registry_kind="refunds",
        environment="test",
        required_columns=("refund_id", "amount"),
        part_name="part-01",
    )
    assert payments.registry_kind == "payments"
    assert refunds.registry_kind == "refunds"
    assert payments.content_sha256 != refunds.content_sha256


def test_missing_duplicate_and_expected_empty_parts_are_deterministic() -> None:
    incomplete = assess_registry_completeness(
        registry_kind="payments",
        required_parts=("part-01", "part-02"),
        observed_parts=("part-01", "part-01"),
    )
    assert incomplete.missing_parts == ("part-02",)
    assert incomplete.duplicate_parts == ("part-01",)
    expected_empty = assess_registry_completeness(
        registry_kind="refunds",
        required_parts=("part-01",),
        observed_parts=(),
        expected_empty_parts=("part-01",),
    )
    assert expected_empty.complete


def test_gap_is_owned_by_metadata_only_evidence() -> None:
    gap = build_registry_gap(
        registry_kind="refunds",
        environment="production",
        report_date="2026-08-07",
        reason="missing_part",
        owner="billing-ops",
        evidence_sha256="b" * 64,
    )
    assert gap.owner == "billing-ops"
    assert gap.state == "detected"
    assert not hasattr(gap, "provider_refund_id")
    try:
        build_registry_gap(
            registry_kind="refunds",
            environment="production",
            report_date="2026-08-07",
            reason="missing_part",
            owner="billing-ops",
            evidence_sha256="provider-ref",
        )
    except RegistryInputError:
        pass
    else:
        raise AssertionError("provider identifiers must not be accepted as gap evidence")
