"""Finite operator cases must not turn a withdrawal into replay permission."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BASIS_WITHDRAWAL_STATE_FILE_ENV,
    LegalBasisLifecycleError,
    parse_disposition_cases,
    read_basis_withdrawal_register,
)

NOW = datetime(2026, 10, 29, 15, tzinfo=UTC)
CASE = (
    "disposition_case case_ref=case_synthetic decision_ref=decision_synthetic "
    "scope=account_closure selector_ref=00000000-0000-0000-0000-000000000001 "
    "owner_role=operator reason=account_closed decided_at=2026-10-29T10:00:00Z "
    "due_at=2026-10-30T10:00:00Z stage=accepted"
)


def parse(line=CASE, version="2"):
    return parse_disposition_cases(f"legal_basis_state_version={version}\n{line}\n", now=NOW)


def test_exact_cases_and_applied_results():
    case, = parse()
    assert case.scope == "account_closure"
    assert case.due_at > case.decided_at
    applied, = parse(CASE.replace("stage=accepted", "stage=applied") +
                     " applied_at=2026-10-29T11:00:00Z rows_affected=3")
    assert applied.rows_affected == 3
    category, = parse(CASE.replace("scope=account_closure", "scope=activation_milestone_decisions")
                      .replace("selector_ref=00000000-0000-0000-0000-000000000001", "selector_ref=all"))
    assert category.selector_ref == "all"


@pytest.mark.parametrize("line,version", [
    (CASE, "1"), (CASE, "9"),
    (CASE + " unknown=value", "2"),
    (CASE + " owner_role=another", "2"),
    (CASE + "\n" + CASE, "2"),
    (CASE.replace("stage=accepted", "stage=unknown"), "2"),
    (CASE.replace("stage=accepted", "stage=applied"), "2"),
    (CASE.replace("due_at=2026-10-30T10:00:00Z", "due_at=2026-10-28T10:00:00Z"), "2"),
    (CASE.replace("decided_at=2026-10-29T10:00:00Z", "decided_at=2026-10-29T10:00:00"), "2"),
    (CASE.replace("selector_ref=00000000-0000-0000-0000-000000000001", "selector_ref=all"), "2"),
    (CASE.replace("stage=accepted", "stage=applied") +
     " applied_at=2026-10-29T11:00:00Z rows_affected=true", "2"),
    (CASE.replace("stage=accepted", "stage=applied") +
     " applied_at=2026-10-29T09:00:00Z rows_affected=0", "2"),
    ("legal_basis_state_version=2\n" + CASE, "2"),
])
def test_incomplete_or_ambiguous_case_is_refused(line, version):
    with pytest.raises(LegalBasisLifecycleError):
        parse(line, version)


def test_version2_reader_separates_cases_and_withdrawals(tmp_path):
    path = tmp_path / "register"
    withdrawal = ("basis_withdrawal level=attribution_profiles state=withdrawn "
                  "withdrawn_at=2026-10-28 reason=purpose_ended")
    path.write_text(f"legal_basis_state_version=2\n{CASE}\n{withdrawal}\n")
    register = read_basis_withdrawal_register({BASIS_WITHDRAWAL_STATE_FILE_ENV: str(path)})
    assert not register.file_errors
    assert len(register.withdrawals) == 1
    assert register.withdrawal("attribution_profiles").reason == "purpose_ended"
    path.write_text(path.read_text() + "unknown_record value=unknown\n")
    register = read_basis_withdrawal_register({BASIS_WITHDRAWAL_STATE_FILE_ENV: str(path)})
    assert register.file_errors == ("legal_basis_record_invalid",)


@pytest.mark.parametrize("damage", [" unknown=value", " owner_role=other", "\ninvalid_token"])
def test_damaged_case_does_not_hide_withdrawal_or_permit_write(tmp_path, damage):
    from twobrain_rec_server.product_analytics.legal_basis_gate import legal_basis_write_gate

    path = tmp_path / "register"
    path.write_text("legal_basis_state_version=2\nbasis_withdrawal level=attribution_profiles "
                    "state=withdrawn withdrawn_at=2026-10-28 reason=purpose_ended\n" + CASE + damage)
    environ = {BASIS_WITHDRAWAL_STATE_FILE_ENV: str(path)}
    assert read_basis_withdrawal_register(environ).file_errors
    assert not legal_basis_write_gate("attribution_profiles", settings=object(), environ=environ).allowed


def source_row(state="completed"):
    return dict(id=UUID("00000000-0000-0000-0000-000000000001"),
                account_id=UUID("00000000-0000-0000-0000-000000000002"), state=state,
                requested_at=NOW-timedelta(days=8), finalize_at=NOW-timedelta(days=1),
                finalized_at=NOW-timedelta(hours=1), canceled_at=None,
                purged_at=(NOW-timedelta(hours=1)).isoformat(), purged_count="3", purged_type="number")


def test_source_finalizer_result_allows_a_new_replay_intent_and_idempotent_applied():
    from twobrain_rec_server.product_analytics.restore_replay import source_replay_accounts

    row = source_row()
    # A new replay decision may follow the original purge and affect zero rows.
    intent = CASE.replace("decided_at=2026-10-29T10:00:00Z", "decided_at=2026-10-29T14:30:00Z")
    for line in (intent, intent.replace("stage=accepted", "stage=applied") +
                 " applied_at=2026-10-29T14:45:00Z rows_affected=0"):
        accounts, categories, late = source_replay_accounts([row], parse(line), required_categories=set(), now=NOW)
        assert accounts == {row["account_id"]} and not categories and late == 0


@pytest.mark.parametrize("change", [
    {"requested_at": NOW+timedelta(seconds=1)},
    {"finalize_at": NOW-timedelta(days=9)},
    {"finalize_at": NOW},
    {"finalized_at": NOW+timedelta(seconds=1)},
    {"purged_at": (NOW-timedelta(days=2)).isoformat()},
    {"purged_at": None}, {"purged_type": "string"}, {"purged_count": "-1"},
    {"canceled_at": NOW}, {"requested_at": NOW.replace(tzinfo=None)},
])
def test_source_completed_requires_consistent_authoritative_result(change):
    from twobrain_rec_server.product_analytics.restore_replay import (
        ReplayHold,
        source_replay_accounts,
    )

    with pytest.raises(ReplayHold):
        source_replay_accounts([{**source_row(), **change}], parse(), required_categories=set(), now=NOW)


def test_source_completion_boundaries_and_exact_case_coverage():
    from twobrain_rec_server.product_analytics.restore_replay import (
        ReplayHold,
        source_replay_accounts,
    )

    row = {**source_row(), "finalize_at": NOW, "purged_at": NOW.isoformat(), "finalized_at": NOW}
    assert source_replay_accounts([row], parse(), required_categories=set(), now=NOW)[0] == {row["account_id"]}
    for rows, cases, withdrawn in (([row], (), False), ([], parse(), False), ([], (), True),
                                   ([{**row, "state": "finalizing"}], parse(), False)):
        with pytest.raises(ReplayHold):
            source_replay_accounts(rows, cases, required_categories={"activation_milestone_decisions"} if withdrawn else set(), now=NOW)


@pytest.mark.parametrize("state", ["scheduled", "canceled"])
def test_source_pending_and_canceled_have_their_own_timeline(state):
    from twobrain_rec_server.product_analytics.restore_replay import (
        ReplayHold,
        source_replay_accounts,
    )

    row = {**source_row(state), "finalize_at": NOW+timedelta(days=1), "finalized_at": None,
           "purged_at": None, "purged_count": None, "purged_type": None,
           "canceled_at": NOW if state == "canceled" else None}
    assert source_replay_accounts([row], (), required_categories=set(), now=NOW) == (set(), [], 0)
    for changes in ({"finalize_at": NOW}, {"requested_at": NOW+timedelta(seconds=1)},
                    {"finalized_at": NOW}, {"purged_count": "0"},
                    {"canceled_at": NOW+timedelta(seconds=1)}):
        with pytest.raises(ReplayHold):
            source_replay_accounts([{**row, **changes}], (), required_categories=set(), now=NOW)


def test_source_category_requires_a_result_and_preserves_observed_lateness():
    from twobrain_rec_server.product_analytics.restore_replay import (
        ReplayHold,
        source_replay_accounts,
    )

    category = CASE.replace("scope=account_closure", "scope=activation_milestone_decisions").replace(
        "selector_ref=00000000-0000-0000-0000-000000000001", "selector_ref=all")
    for due in ("2026-10-30T10:00:00Z", "2026-10-29T10:00:00Z"):
        for stage in ("accepted", "failed"):
            line = category.replace("2026-10-30T10:00:00Z", due).replace("stage=accepted", "stage="+stage)
            with pytest.raises(ReplayHold):
                source_replay_accounts([], parse(line), required_categories=set(), now=NOW)
    for due, late in (("2026-10-30T10:00:00Z", 0), ("2026-10-29T10:00:00Z", 1)):
        line = category.replace("2026-10-30T10:00:00Z", due).replace("stage=accepted", "stage=applied")
        cases = parse(line + " applied_at=2026-10-29T11:00:00Z rows_affected=0")
        assert source_replay_accounts([], cases, required_categories={"activation_milestone_decisions"}, now=NOW) == (set(), list(cases), late)


@pytest.mark.parametrize("scope", ["anonymous_page_aggregate", "visit_attribution",
                                    "client_acquisition_attribute", "activation_milestone_decisions"])
def test_every_local_scope_is_parsed_and_replayed(scope):
    from twobrain_rec_server.product_analytics.restore_replay import replay_accounts

    line = CASE.replace("scope=account_closure", "scope="+scope).replace(
        "selector_ref=00000000-0000-0000-0000-000000000001", "selector_ref=all")
    cases = parse(line)
    assert replay_accounts([], cases, required_categories={scope}, now=NOW) == (set(), list(cases))


def test_local_withdrawals_require_every_category_even_when_empty():
    from twobrain_rec_server.product_analytics.restore_replay import (
        ReplayHold,
        replay_accounts,
        withdrawn_local_categories,
    )

    text = ("legal_basis_state_version=2\nbasis_withdrawal level=attribution_profiles "
            "state=withdrawn withdrawn_at=2026-10-28 reason=purpose_ended\n")
    required = withdrawn_local_categories(text)
    both = text + ("basis_withdrawal level=anonymous_aggregate state=withdrawn "
                   "withdrawn_at=2026-10-28 reason=purpose_ended\n")
    assert withdrawn_local_categories(both) == required | {"anonymous_page_aggregate"}
    assert required == {"client_acquisition_attribute", "visit_attribution", "activation_milestone_decisions"}
    with pytest.raises(ReplayHold, match="category_case_missing"):
        replay_accounts([], (), required_categories=required, now=NOW)


@pytest.mark.parametrize("damage", [
    {"acquisition_purged_at": None}, {"acquisition_purged_count": None},
    {"acquisition_purged_type": "string"}, {"acquisition_purged_count": "-1"},
    {"acquisition_purged_count": str(2**63)}, {"acquisition_purged_at": NOW.isoformat()},
    {"acquisition_purged_at": (NOW-timedelta(days=2)).isoformat()},
    {"acquisition_purged_at": NOW.replace(tzinfo=None).isoformat()},
])
def test_present_acquisition_result_is_independent_and_complete(damage):
    from twobrain_rec_server.product_analytics.restore_replay import (
        ReplayHold,
        source_replay_accounts,
    )

    row = {**source_row(), "acquisition_present": True,
           "acquisition_purged_at": (NOW-timedelta(hours=1)).isoformat(),
           "acquisition_purged_count": "0", "acquisition_purged_type": "number"}
    assert source_replay_accounts([row], parse(), required_categories=set(), now=NOW)[0] == {row["account_id"]}
    with pytest.raises(ReplayHold):
        source_replay_accounts([{**row, **damage}], parse(), required_categories=set(), now=NOW)
