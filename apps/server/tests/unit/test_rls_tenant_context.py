from __future__ import annotations

from uuid import UUID

import pytest

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.rls import RLS_ALLOWED_MAINTENANCE_OPERATIONS
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.tenant_context import (
    AuthCallbackLookupContext,
    AuthReferralLookupContext,
    AuthReferralUserLookupContext,
    AuthSessionLookupContext,
    MaintenanceTenantContext,
    ReferralLandingLookupContext,
    SharedWithMeLookupContext,
    ShareInvitationLookupContext,
    TenantDatabaseContext,
    WorkspaceAuthContext,
    auth_referral_lookup_settings,
    auth_referral_user_lookup_settings,
    auth_session_lookup_settings,
    referral_landing_lookup_settings,
    share_invitation_lookup_settings,
    shared_with_me_lookup_settings,
    tenant_context_from_scope,
    tenant_context_settings,
)


def test_tenant_context_from_scope_maps_all_trusted_fields() -> None:
    auth_session_id = UUID("50000000-0000-0000-0000-000000000001")
    upload_session_id = UUID("60000000-0000-0000-0000-000000000001")
    scope = TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
        auth_session_id=auth_session_id,
        upload_session_id=upload_session_id,
    )

    context = tenant_context_from_scope(scope)

    assert context == TenantDatabaseContext(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
        auth_session_id=auth_session_id,
        upload_session_id=upload_session_id,
        context_kind="request",
    )


def test_tenant_context_settings_are_postgres_guc_strings() -> None:
    context = TenantDatabaseContext(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
        context_kind="worker",
    )

    assert tenant_context_settings(context) == {
        "app.organization_id": str(ORG_ID),
        "app.workspace_id": str(WORKSPACE_ID),
        "app.user_id": str(USER_ID),
        "app.device_id": str(DEVICE_ID),
        "app.context_kind": "worker",
    }


def test_tenant_context_rejects_unknown_context_kind() -> None:
    with pytest.raises(ValueError, match="context_kind"):
        TenantDatabaseContext(
            organization_id=ORG_ID,
            workspace_id=WORKSPACE_ID,
            user_id=USER_ID,
            context_kind="debug_bypass",
        )


def test_auth_context_helpers_reject_wrong_context_kind() -> None:
    with pytest.raises(ValueError, match="auth_session_lookup"):
        AuthSessionLookupContext(session_token_hash="hash", context_kind="maintenance")
    with pytest.raises(ValueError, match="auth_public"):
        WorkspaceAuthContext(workspace_id=WORKSPACE_ID, context_kind="request")
    with pytest.raises(ValueError, match="auth_callback_lookup"):
        AuthCallbackLookupContext(state_nonce="state", context_kind="auth_public")
    with pytest.raises(ValueError, match="auth_referral_lookup"):
        AuthReferralLookupContext(
            workspace_id=WORKSPACE_ID,
            user_id=USER_ID,
            token_hash="a" * 64,
            context_kind="auth_public",
        )


def test_auth_referral_lookup_context_is_token_scoped() -> None:
    context = AuthReferralLookupContext(
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        token_hash="a" * 64,
    )
    assert auth_referral_lookup_settings(context) == {
        "app.context_kind": "auth_referral_lookup",
        "app.workspace_id": str(WORKSPACE_ID),
        "app.user_id": str(USER_ID),
        "app.referral_token_hash": "a" * 64,
    }
    with pytest.raises(ValueError, match="lowercase hex"):
        AuthReferralLookupContext(
            workspace_id=WORKSPACE_ID,
            user_id=USER_ID,
            token_hash="A" * 64,
        )


def test_auth_referral_user_lookup_context_is_invitee_only() -> None:
    context = AuthReferralUserLookupContext(user_id=USER_ID)
    assert auth_referral_user_lookup_settings(context) == {
        "app.context_kind": "auth_referral_user_lookup",
        "app.user_id": str(USER_ID),
    }


def test_referral_landing_lookup_context_is_token_only() -> None:
    context = ReferralLandingLookupContext(token_hash="b" * 64)
    assert referral_landing_lookup_settings(context) == {
        "app.context_kind": "referral_landing_lookup",
        "app.referral_token_hash": "b" * 64,
    }


def test_maintenance_context_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="maintenance operation"):
        MaintenanceTenantContext(
            operation_name="ad_hoc_browse_everything",
            actor_id="operator",
            reason_category="diagnostics",
            feature_area="security",
        )


def test_allowed_maintenance_operations_match_contract() -> None:
    assert "auth_session_lookup" not in RLS_ALLOWED_MAINTENANCE_OPERATIONS
    assert (
        MaintenanceTenantContext(
            operation_name="production_smoke_setup",
            actor_id="seed_smoke_identity.py",
            reason_category="smoke_setup",
            feature_area="deployment",
        ).operation_name
        == "production_smoke_setup"
    )
    assert (
        MaintenanceTenantContext(
            operation_name="operator_diagnostics",
            actor_id="operator",
            reason_category="diagnostics",
            feature_area="security",
        ).operation_name
        == "operator_diagnostics"
    )
    assert (
        MaintenanceTenantContext(
            operation_name="outcome_initial_baseline_reconciliation",
            actor_id="operator",
            reason_category="initial_baseline_reconciliation",
            feature_area="outcomes",
        ).operation_name
        == "outcome_initial_baseline_reconciliation"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("actor_id", ""),
        ("reason_category", " "),
        ("feature_area", ""),
    ),
)
def test_maintenance_context_rejects_blank_metadata(field: str, value: str) -> None:
    payload = {
        "operation_name": "operator_diagnostics",
        "actor_id": "operator",
        "reason_category": "diagnostics",
        "feature_area": "security",
        field: value,
    }
    with pytest.raises(ValueError, match=field):
        MaintenanceTenantContext(**payload)


def test_auth_session_lookup_context_sets_only_token_hash_and_kind() -> None:
    context = AuthSessionLookupContext(session_token_hash="token-hash")

    assert auth_session_lookup_settings(context) == {
        "app.context_kind": "auth_session_lookup",
        "app.auth_session_token_hash": "token-hash",
    }


def test_share_invitation_lookup_context_is_bound_to_workspace_and_nonce() -> None:
    context = ShareInvitationLookupContext(
        workspace_id=WORKSPACE_ID,
        continuation_nonce="continuation-state",
    )

    assert share_invitation_lookup_settings(context) == {
        "app.context_kind": "share_invitation_lookup",
        "app.workspace_id": str(WORKSPACE_ID),
        "app.share_invitation_continuation_nonce": "continuation-state",
    }


def test_shared_with_me_lookup_context_sets_only_user_and_kind() -> None:
    context = SharedWithMeLookupContext(user_id=USER_ID)

    assert shared_with_me_lookup_settings(context) == {
        "app.context_kind": "shared_with_me_lookup",
        "app.user_id": str(USER_ID),
    }


def test_shared_with_me_lookup_context_rejects_other_kind() -> None:
    with pytest.raises(ValueError, match="shared_with_me_lookup"):
        SharedWithMeLookupContext(user_id=USER_ID, context_kind="request")
