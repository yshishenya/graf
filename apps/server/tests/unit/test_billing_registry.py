import pytest
from twobrain_rec_server.billing.registry import (
    RegistryInputError,
    RegistryPart,
    assess_registry_completeness,
    build_registry_gap,
    import_registry_reports,
    registry_parts_complete,
    summarize_registry_csv,
)


def test_registry_summary_keeps_metadata_only_identity() -> None:
    summary = summarize_registry_csv(
        "payment_id,amount\nprovider-secret,790.00\n",
        registry_kind="payments",
        environment="test",
        required_columns=("payment_id", "amount"),
    )
    assert summary.registry_kind == "payments"
    assert summary.row_count == 1
    assert len(summary.content_sha256) == 64
    assert not hasattr(summary, "payment_id")


def test_registry_rejects_missing_columns_and_malformed_rows() -> None:
    with pytest.raises(RegistryInputError, match="columns"):
        summarize_registry_csv(
            "payment_id\npay-1\n",
            registry_kind="payments",
            environment="test",
            required_columns=("payment_id", "amount"),
        )
    with pytest.raises(RegistryInputError, match="width"):
        summarize_registry_csv(
            "payment_id,amount\npay-1\n",
            registry_kind="payments",
            environment="test",
            required_columns=("payment_id", "amount"),
        )


def test_registry_part_completeness_is_explicit() -> None:
    assert registry_parts_complete(required_parts=("payments", "refunds"), observed_parts={"payments"}) is False
    assert registry_parts_complete(required_parts=("payments", "refunds"), observed_parts={"payments", "refunds"}) is True


def test_registry_keeps_payment_and_refund_reports_separate_with_metadata_only_identity() -> None:
    summary = summarize_registry_csv(
        "refund_id,amount\nref-1,790.00\n",
        registry_kind="refunds",
        environment="production",
        required_columns=("refund_id", "amount"),
        shop_id="shop-1",
        report_date="2026-08-07",
        schema_version="v1",
        language="ru-RU",
        config_version="cfg-1",
        part_name="part-01",
    )
    assert summary.registry_kind == "refunds"
    assert summary.part_name == "part-01"
    assert not hasattr(summary, "refund_id")
    with pytest.raises(RegistryInputError, match="kind"):
        summarize_registry_csv(
            "id\n1\n",
            registry_kind="combined",
            environment="production",
            required_columns=("id",),
        )


def test_registry_completeness_hash_and_owned_gap_are_deterministic() -> None:
    completeness = assess_registry_completeness(
        registry_kind="payments",
        required_parts=("part-01", "part-02"),
        observed_parts=("part-01",),
    )
    assert completeness.complete is False
    assert completeness.missing_parts == ("part-02",)
    assert len(completeness.completeness_sha256) == 64
    empty = assess_registry_completeness(
        registry_kind="refunds",
        required_parts=("part-01",),
        observed_parts=(),
        expected_empty_parts=("part-01",),
    )
    assert empty.complete is True
    gap = build_registry_gap(
        registry_kind="payments",
        environment="production",
        report_date="2026-08-07",
        reason="missing_part",
        owner="billing-ops",
        evidence_sha256="a" * 64,
    )
    assert gap.owner == "billing-ops"
    assert gap.state == "detected"
    with pytest.raises(RegistryInputError, match="hash"):
        build_registry_gap(
            registry_kind="payments",
            environment="production",
            report_date="2026-08-07",
            reason="missing_part",
            owner="billing-ops",
            evidence_sha256="provider-id",
        )


def test_registry_import_keeps_payment_refund_set_and_emits_metadata_gap() -> None:
    imported = import_registry_reports(
        (
            RegistryPart("part-01", "payment_id,amount\npay-1,790.00\n"),
        ),
        registry_kind="payments",
        environment="production",
        required_parts=("part-01", "part-02"),
        required_columns=("payment_id", "amount"),
        report_date="2026-08-07",
        owner="billing-ops",
    )
    assert imported.completeness.missing_parts == ("part-02",)
    assert len(imported.summaries) == 1
    assert imported.gaps[0].reason == "missing_part"
    assert not hasattr(imported, "payment_id")


def test_registry_import_accepts_configured_empty_part_without_gap() -> None:
    imported = import_registry_reports(
        (
            RegistryPart("part-01", "refund_id,amount\n", expected_empty=True),
        ),
        registry_kind="refunds",
        environment="production",
        required_parts=("part-01",),
        required_columns=("refund_id", "amount"),
        report_date="2026-08-07",
        owner="billing-ops",
    )
    assert imported.completeness.complete
    assert imported.gaps == ()


def test_registry_import_rejects_rows_in_configured_empty_part() -> None:
    with pytest.raises(RegistryInputError, match="expected-empty"):
        import_registry_reports(
            (RegistryPart("part-01", "refund_id,amount\nref-1,1.00\n", expected_empty=True),),
            registry_kind="refunds",
            environment="production",
            required_parts=("part-01",),
            required_columns=("refund_id", "amount"),
            report_date="2026-08-07",
            owner="billing-ops",
        )
