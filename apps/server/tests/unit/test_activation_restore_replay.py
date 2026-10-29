"""Finite operator cases must not turn a withdrawal into replay permission."""

from datetime import UTC, datetime

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
