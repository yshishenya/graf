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
    updated_deduped_issue_body,
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


def test_deduped_issue_update_refreshes_generated_counters_only() -> None:
    report = build_server_redacted_report(safe_report_payload())
    existing = build_github_issue_draft(
        report,
        affected_count=1,
        safe_affected_identities=("old_identity",),
        github_issue_number=123,
    ).body.replace("Пользовательская проблема из GRAF", "Ручная заметка. Пользовательская проблема из GRAF")

    updated = updated_deduped_issue_body(
        existing,
        report,
        affected_count=6,
        safe_affected_identities=("new_a", "new_b"),
        github_issue_number=123,
    )

    assert "Ручная заметка" in updated
    assert "Affected count: `6`" in updated
    assert "new_a, new_b" in updated
    assert "old_identity" not in updated


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
async def test_github_issue_client_validates_private_repo_and_required_labels() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/yshishenya/crisp":
            return httpx.Response(200, json={"private": True})
        if request.url.path == "/repos/yshishenya/crisp/labels":
            return httpx.Response(200, json=[{"name": "needs-triage"}])
        return httpx.Response(404, json={})

    client = GitHubIssueClient(token="server-token", transport=httpx.MockTransport(handler))

    with pytest.raises(GitHubIssueClientError, match="support_incident.configuration_invalid"):
        await client.validate_repository_ready(owner="yshishenya", repo="crisp")


@pytest.mark.asyncio
async def test_github_issue_client_rejects_wrong_or_public_repo_before_issue_mutation() -> None:
    client = GitHubIssueClient(token="server-token")

    with pytest.raises(GitHubIssueClientError, match="support_incident.configuration_invalid"):
        await client.repo_is_private(owner="other", repo="crisp")

    async def public_repo(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"private": False})

    client = GitHubIssueClient(token="server-token", transport=httpx.MockTransport(public_repo))
    with pytest.raises(GitHubIssueClientError, match="support_incident.configuration_invalid"):
        await client.validate_repository_ready(owner="yshishenya", repo="crisp")


@pytest.mark.asyncio
async def test_github_issue_client_maps_failure_to_safe_reason() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "bad credentials"})

    client = GitHubIssueClient(token="server-token", transport=httpx.MockTransport(handler))

    with pytest.raises(GitHubIssueClientError, match="support_incident.configuration_invalid") as exc:
        await client.repo_is_private(owner="yshishenya", repo="crisp")

    assert exc.value.status_code == 403
    assert "server-token" not in str(exc.value)


@pytest.mark.asyncio
async def test_github_issue_client_maps_rate_limit_to_dependency_failure() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"message": "rate limit"})

    client = GitHubIssueClient(token="server-token", transport=httpx.MockTransport(handler))

    with pytest.raises(GitHubIssueClientError, match="support_incident.github_unavailable") as exc:
        await client.repo_is_private(owner="yshishenya", repo="crisp")

    assert exc.value.status_code == 429
