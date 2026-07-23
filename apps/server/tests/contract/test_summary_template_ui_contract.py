from pathlib import Path

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.cabinet import create_outcome_ready_meeting, seed_cabinet_meetings
from twobrain_rec_server.db.models import ProcessingResult, Workspace, WorkspaceMembership
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_processing_result

SERVER_ROOT = Path(__file__).resolve().parents[2]
CABINET_JS = SERVER_ROOT / "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
MEETING_TEMPLATE = (
    SERVER_ROOT
    / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html"
)
SETTINGS_TEMPLATE = (
    SERVER_ROOT
    / "src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html"
)


def test_summary_selector_keeps_auto_four_recommendations_and_all_formats(client) -> None:
    meeting_id = seed_cabinet_meetings(client).ready_id

    response = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert response.status_code == 200
    html = response.text
    listbox = html.split('id="summary-format-listbox"', 1)[1].split("</div>", 1)[0]
    assert 'data-summary-format-button aria-haspopup="listbox"' in html
    assert 'data-summary-format-listbox data-recommended-limit="4" role="listbox"' in html
    assert listbox.count("data-summary-format-option") == 4
    assert ">Авто</button>" in listbox
    assert "Все форматы…" in listbox
    assert 'role="option"' in listbox
    assert 'aria-selected="true"' in listbox


def test_personal_template_management_lives_in_settings_not_quick_selector(client) -> None:
    settings = client.get("/settings", headers=auth_headers())

    assert settings.status_code == 200
    html = settings.text
    quick_source = MEETING_TEMPLATE.read_text(encoding="utf-8")
    settings_source = SETTINGS_TEMPLATE.read_text(encoding="utf-8")
    assert 'id="summary-formats"' in html
    assert "data-summary-template-create" in html
    assert "data-summary-template-copy" in html
    assert "data-summary-template-form" in html
    assert "data-summary-template-create" not in quick_source
    for action in ("duplicate", "archive", "DELETE", "PATCH"):
        assert action in CABINET_JS.read_text(encoding="utf-8")
    assert "Создать формат" in settings_source
    assert html.count("data-summary-default-template") == 1
    assert "Формат по умолчанию" in html


def test_candidate_ui_preserves_current_notes_until_explicit_accept() -> None:
    script = CABINET_JS.read_text(encoding="utf-8")

    assert "Текущие итоги остаются на месте" in script
    assert "Текущие итоги сохранены" in script
    assert 'text: "Использовать"' in script
    assert 'text: "Оставить текущие"' in script
    assert "expected_current_outcome_set_id: currentOutcomeSetId" in script
    assert '/${candidate.candidate_id}/${accept ? "accept" : "reject"}' in script
    assert "window.location.reload()" in script
    assert "JSON.stringify({" in script
    assert "template: activeTemplate" in script
    assert 'text: "Обновить страницу"' in script


def test_format_selection_uses_the_rendered_accepted_revision_and_starts_temporal(client) -> None:
    meeting_id = create_outcome_ready_meeting(client)

    async def generate_baseline():
        async with client.app_state["sessionmaker"]() as db:
            result = await db.scalar(
                select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
            )
            assert result is not None
            outcome_set = await ensure_outcomes_for_processing_result(db, result=result)
            await db.commit()
            return outcome_set.id

    accepted_id = client.portal.call(generate_baseline)
    page = client.get(f"/meetings/{meeting_id}", headers=auth_headers())

    assert page.status_code == 200
    assert f'data-current-outcome-set-id="{accepted_id}"' in page.text

    temporal = FakeTemporalClient()
    client.app.state.settings.outcome_generation_enabled = True
    client.app.state.outcome_temporal_client = temporal
    response = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/summary-candidates",
        headers=auth_headers(),
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
            "expected_current_outcome_set_id": str(accepted_id),
        },
    )

    assert response.status_code == 202
    assert response.json()["state"] == "generating"
    assert response.json()["current_outcome_set_id"] == str(accepted_id)
    assert len(temporal.starts) == 1
    started = next(iter(temporal.starts.values()))
    assert started["payload"]["template_key"] == "graf-meeting-minutes-v1"


def test_summary_selector_keyboard_focus_and_candidate_projection_are_simple(client) -> None:
    script = CABINET_JS.read_text(encoding="utf-8")
    schema = client.get("/openapi.json").json()["components"]["schemas"]

    for key in ("ArrowUp", "ArrowDown", "Home", "End", "Escape"):
        assert key in script
    assert 'button.focus({ preventScroll: true })' in script
    assert "trapModalFocus(dialog, event)" in script
    states = set(schema["SummaryCandidateResponse"]["properties"]["state"]["enum"])
    assert states == {"generating", "ready", "accepted", "closed", "failed"}
    assert states.isdisjoint({"queued", "blocked_dependency", "candidate", "cancelled"})


def test_workspace_default_format_is_persisted_and_returned_by_list_api(client) -> None:
    headers = auth_headers()
    listed = client.get("/api/v1/cabinet/summary-templates", headers=headers)

    assert listed.status_code == 200
    assert listed.json()["default_template_key"] == "graf-auto-v1"
    assert listed.json()["can_manage_default"] is True

    changed = client.put(
        "/api/v1/cabinet/summary-templates/default",
        headers=headers,
        json={
            "template_key": "graf-meeting-minutes-v1",
            "template_id": None,
            "template_version": 1,
        },
    )
    reloaded = client.get("/api/v1/cabinet/summary-templates", headers=headers)

    assert changed.status_code == 200
    assert changed.json()["name"] == "Протокол встречи"
    assert reloaded.status_code == 200
    assert reloaded.json()["default_template_key"] == "graf-meeting-minutes-v1"

    async def load_workspace() -> Workspace:
        async with client.app_state["sessionmaker"]() as db:
            workspace = await db.get(Workspace, WORKSPACE_ID)
            assert workspace is not None
            return workspace

    workspace = client.portal.call(load_workspace)
    assert workspace.default_summary_template_key == "graf-meeting-minutes-v1"
    assert workspace.default_summary_template_id is None
    assert workspace.default_summary_template_version == 1


def test_only_workspace_owner_can_change_default_format(client) -> None:
    async def make_member() -> None:
        async with client.app_state["sessionmaker"]() as db:
            membership = await db.scalar(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == WORKSPACE_ID,
                    WorkspaceMembership.user_id == USER_ID,
                )
            )
            assert membership is not None
            membership.role = "member"
            await db.commit()

    client.portal.call(make_member)
    response = client.put(
        "/api/v1/cabinet/summary-templates/default",
        headers=auth_headers(),
        json={
            "template_key": "graf-outline-v1",
            "template_id": None,
            "template_version": 1,
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "summary_default_forbidden"


def test_workspace_default_rejects_personal_formats(client) -> None:
    headers = auth_headers()
    created = client.post(
        "/api/v1/cabinet/summary-templates",
        headers=headers,
        json={
            "name": "Мои итоги",
            "purpose": "Решения и следующие шаги",
            "sections": ["summary", "decisions", "action_items"],
            "output_language": "ru",
            "detail_level": "standard",
        },
    )
    assert created.status_code == 201
    personal = created.json()

    selected = client.put(
        "/api/v1/cabinet/summary-templates/default",
        headers=headers,
        json={
            "template_key": personal["template_key"],
            "template_id": personal["template_id"],
            "template_version": personal["version"],
        },
    )
    assert selected.status_code == 422
    assert selected.json()["code"] == "summary_default_requires_builtin"

    async def load_workspace() -> Workspace:
        async with client.app_state["sessionmaker"]() as db:
            workspace = await db.get(Workspace, WORKSPACE_ID)
            assert workspace is not None
            return workspace

    workspace = client.portal.call(load_workspace)
    assert workspace.default_summary_template_key == "graf-auto-v1"
    assert workspace.default_summary_template_id is None
    assert workspace.default_summary_template_version == 1


def test_default_format_contract_is_migrated_and_explicit(client) -> None:
    schema = client.get("/openapi.json").json()
    migration = (
        SERVER_ROOT
        / "src/twobrain_rec_server/db/migrations/versions/0031_recording_workflow_templates_sharing.py"
    ).read_text(encoding="utf-8")

    operation = schema["paths"]["/api/v1/cabinet/summary-templates/default"]["put"]
    assert operation["operationId"] == "updateDefaultSummaryTemplate"
    assert "can_manage_default" in schema["components"]["schemas"][
        "SummaryTemplateListResponse"
    ]["properties"]
    for field in (
        "default_summary_template_key",
        "default_summary_template_id",
        "default_summary_template_version",
        "fk_workspaces_default_summary_template",
    ):
        assert field in migration
