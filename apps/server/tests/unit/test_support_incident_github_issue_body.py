import httpx
import pytest

from tests.unit.test_support_incident_redaction import safe_report_payload
from twobrain_rec_server.support.github_issues import (
    GENERATED_END,
    GENERATED_START,
    GitHubIssueClient,
    GitHubIssueClientError,
    build_github_issue_draft,
    replace_generated_issue_metadata,
)
from twobrain_rec_server.support.redaction import build_server_redacted_report


def test_issue_draft_uses_private_support_canon_and_full_safe_json() -> None:
    report = build_server_redacted_report(safe_report_payload())
    draft = build_github_issue_draft(
        report,
        affected_count=5,
        safe_affected_identities=("affected_a", "affected_b", "affected_c", "affected_d", "affected_e", "extra"),
        github_issue_number=123,
    )

    assert draft.title.startswith("[061][P1][support/custody] Пользовательская проблема:")
    assert set(draft.labels) >= {
        "needs-triage",
        "feature:061",
        "type:bug",
        "priority:P1",
        "area:macos",
        "area:api",
        "area:privacy",
        "source:user-report",
        "privacy:metadata-only",
    }
    sections = [
        "## Кратко",
        "## Контекст",
        "## Проблема",
        "## Проверенные факты",
        "## Границы задачи",
        "## Критерии приемки",
        "## Что проверить перед закрытием",
        "## Заметки по реализации",
        "## Ссылки",
    ]
    assert [draft.body.index(section) for section in sections] == sorted(
        draft.body.index(section) for section in sections
    )
    assert GENERATED_START in draft.body
    assert GENERATED_END in draft.body
    assert "```json" in draft.body
    assert '"redaction_state": "metadata_only"' in draft.body
    assert "retained indefinitely in this private GitHub issue" in draft.body
    assert "extra" not in draft.body
    assert "/Users/" not in draft.body
    assert "token=redacted" not in draft.body


def test_metadata_block_replacement_preserves_human_sections() -> None:
    report = build_server_redacted_report(safe_report_payload())
    draft = build_github_issue_draft(report, affected_count=1)
    existing = draft.body.replace(
        "Нужно проверить custody/upload blocker",
        "Команда поддержки уже добавила ручной контекст. Нужно проверить custody/upload blocker",
    ).replace('"affected_identity_fingerprint"', '"old_field"')

    updated = replace_generated_issue_metadata(existing, draft)

    assert "Команда поддержки уже добавила ручной контекст" in updated
    assert '"affected_identity_fingerprint"' in updated
    assert '"old_field"' not in updated


@pytest.mark.asyncio
async def test_github_issue_client_sends_safe_issue_payload_without_leaking_token() -> None:
    report = build_server_redacted_report(safe_report_payload())
    draft = build_github_issue_draft(report)
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers.get("authorization")
        body = await request.aread()
        assert b"server-token" not in body
        return httpx.Response(201, json={"number": 123, "html_url": "https://github.com/yshishenya/crisp/issues/123"})

    client = GitHubIssueClient(token="server-token", transport=httpx.MockTransport(handler))
    response = await client.create_issue(owner="yshishenya", repo="crisp", draft=draft)

    assert captured == {
        "path": "/repos/yshishenya/crisp/issues",
        "authorization": "Bearer server-token",
    }
    assert response["number"] == 123


@pytest.mark.asyncio
async def test_github_issue_client_maps_failure_to_safe_reason() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "bad credentials"})

    client = GitHubIssueClient(token="server-token", transport=httpx.MockTransport(handler))

    with pytest.raises(GitHubIssueClientError, match="support_incident.github_unavailable") as exc:
        await client.repo_is_private(owner="yshishenya", repo="crisp")

    assert exc.value.status_code == 403
    assert "server-token" not in str(exc.value)
