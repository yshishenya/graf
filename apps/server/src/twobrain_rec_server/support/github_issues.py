from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

GENERATED_START = "<!-- support-incident-generated:start -->"
GENERATED_END = "<!-- support-incident-generated:end -->"

REQUIRED_SUPPORT_LABELS = (
    "needs-triage",
    "feature:061",
    "type:bug",
    "area:macos",
    "area:api",
    "area:privacy",
    "source:user-report",
    "privacy:metadata-only",
)
REQUIRED_REPO_OWNER = "yshishenya"
REQUIRED_REPO_NAME = "crisp"


class GitHubIssueClientError(RuntimeError):
    def __init__(self, reason_code: str, *, status_code: int | None = None) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class GitHubIssueDraft:
    title: str
    body: str
    labels: tuple[str, ...]
    priority: str


@dataclass(frozen=True, slots=True)
class GitHubIssueClient:
    token: str
    base_url: str = "https://api.github.com"
    timeout_seconds: float = 4.0
    transport: httpx.AsyncBaseTransport | None = None

    async def validate_repository_ready(self, *, owner: str, repo: str) -> None:
        _validate_target_repo(owner=owner, repo=repo)
        if not await self.repo_is_private(owner=owner, repo=repo):
            raise GitHubIssueClientError("support_incident.configuration_invalid")
        missing = sorted(set(REQUIRED_SUPPORT_LABELS) - await self.label_names(owner=owner, repo=repo))
        if missing:
            raise GitHubIssueClientError("support_incident.configuration_invalid")

    async def repo_is_private(self, *, owner: str, repo: str) -> bool:
        _validate_target_repo(owner=owner, repo=repo)
        data = await self._request_json("GET", f"/repos/{owner}/{repo}")
        return bool(data.get("private"))

    async def label_names(self, *, owner: str, repo: str) -> set[str]:
        _validate_target_repo(owner=owner, repo=repo)
        data = await self._request_json("GET", f"/repos/{owner}/{repo}/labels?per_page=100")
        if not isinstance(data, list):
            raise GitHubIssueClientError("support_incident.github_unavailable")
        return {str(item.get("name")) for item in data if isinstance(item, dict) and item.get("name")}

    async def create_issue(self, *, owner: str, repo: str, draft: GitHubIssueDraft) -> dict[str, Any]:
        _validate_target_repo(owner=owner, repo=repo)
        return await self._request_json(
            "POST",
            f"/repos/{owner}/{repo}/issues",
            json={
                "title": draft.title,
                "body": draft.body,
                "labels": list(draft.labels),
            },
        )

    async def update_issue(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        draft: GitHubIssueDraft,
    ) -> dict[str, Any]:
        _validate_target_repo(owner=owner, repo=repo)
        return await self._request_json(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/{issue_number}",
            json={
                "title": draft.title,
                "body": draft.body,
                "labels": list(draft.labels),
            },
        )

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                timeout=httpx.Timeout(self.timeout_seconds),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                transport=self.transport,
            ) as client:
                response = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise GitHubIssueClientError("support_incident.github_unavailable") from exc
        except httpx.RequestError as exc:
            raise GitHubIssueClientError("support_incident.github_unavailable") from exc
        if response.status_code >= 400:
            raise GitHubIssueClientError(
                _response_reason_code(response),
                status_code=response.status_code,
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise GitHubIssueClientError("support_incident.github_unavailable") from exc
        if not isinstance(data, dict | list):
            raise GitHubIssueClientError("support_incident.github_unavailable")
        return data


def build_github_issue_draft(
    report: Mapping[str, Any],
    *,
    affected_count: int = 1,
    safe_affected_identities: tuple[str, ...] | list[str] = (),
    github_issue_number: int | None = None,
) -> GitHubIssueDraft:
    priority = priority_for_report(report)
    labels = (
        *REQUIRED_SUPPORT_LABELS,
        f"priority:{priority}",
    )
    problem_code = str(report.get("problem_code") or "unknown")
    title = (
        f"[061][{priority}][support/custody] "
        f"Пользовательская проблема: {_human_problem_summary(problem_code)} ({problem_code})"
    )
    body = _issue_body(
        report,
        affected_count=affected_count,
        safe_affected_identities=tuple(safe_affected_identities)[:5],
        github_issue_number=github_issue_number,
    )
    return GitHubIssueDraft(title=title, body=body, labels=labels, priority=priority)


def replace_generated_issue_metadata(existing_body: str, draft: GitHubIssueDraft) -> str:
    new_block = _extract_generated_block(draft.body)
    start = existing_body.find(GENERATED_START)
    end = existing_body.find(GENERATED_END)
    if start == -1 or end == -1 or end < start:
        return draft.body
    return existing_body[:start] + new_block + existing_body[end + len(GENERATED_END) :]


def updated_deduped_issue_body(
    existing_body: str,
    report: Mapping[str, Any],
    *,
    affected_count: int,
    safe_affected_identities: tuple[str, ...] | list[str],
    github_issue_number: int,
) -> str:
    draft = build_github_issue_draft(
        report,
        affected_count=affected_count,
        safe_affected_identities=safe_affected_identities,
        github_issue_number=github_issue_number,
    )
    return replace_generated_issue_metadata(existing_body, draft)


def priority_for_report(report: Mapping[str, Any]) -> str:
    data_loss_risk = str(report.get("data_loss_risk") or "").lower()
    if data_loss_risk in {"probable", "high", "confirmed"}:
        return "P0"
    if report.get("server_copy_known") is False or str(report.get("retry_class")) == "terminal":
        return "P1"
    return "P2"


def _issue_body(
    report: Mapping[str, Any],
    *,
    affected_count: int,
    safe_affected_identities: tuple[str, ...],
    github_issue_number: int | None,
) -> str:
    issue_number = str(github_issue_number) if github_issue_number is not None else "new"
    return f"""## Кратко

Пользовательская проблема из 2brain Rec: локальная запись не была отправлена автоматически. Отчет metadata-only, без аудио, транскрипта, raw paths, токенов, signed URL и private meeting content.

## Контекст

- Фича: `061-support-incident-reporting`
- Приоритет: `{priority_for_report(report)}`
- Область: `support/custody`
- Spec tasks: runtime support incident
- Источник: user report
- Гейт: support triage
- Связанные issues:

## Проблема

Нужно проверить custody/upload blocker по safe metadata-only отчету и понять, может ли поддержка или разработка помочь пользователю.

## Проверенные факты

{_generated_block(
        report,
        affected_count=affected_count,
        safe_affected_identities=safe_affected_identities,
        issue_number=issue_number,
    )}

## Границы задачи

Входит:
- Проверить пользовательскую проблему по safe metadata-only отчету.
- Учесть dedupe и affected_count.

Не входит:
- Восстановление записи без доказанного server/local состояния.
- Изменение server-owned WebView meeting list.
- Публикация данных в публичный GitHub.

## Критерии приемки

- [ ] GitHub issue body содержит только allowed metadata.
- [ ] Поддержка или разработчик классифицировали проблему.
- [ ] Пользователю не обещано восстановление записи без proof.

## Что проверить перед закрытием

- [ ] Full metadata-only JSON остается в private issue или вручную отредактирован по owner-controlled privacy policy.
- [ ] Linked private incident record matches this GitHub issue number.
- [ ] No raw paths, tokens, signed URLs, transcript text, audio, email/name, or private meeting content is present.

## Заметки по реализации

Full metadata-only issue details are retained indefinitely in this private GitHub issue for support/developer agent triage.

## Ссылки

- Spec: `specs/061-support-incident-reporting/spec.md`
- Plan: `specs/061-support-incident-reporting/plan.md`
- Tasks: `specs/061-support-incident-reporting/tasks.md`
- Связано:
"""


def _generated_block(
    report: Mapping[str, Any],
    *,
    affected_count: int,
    safe_affected_identities: tuple[str, ...],
    issue_number: str,
) -> str:
    report_json = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    return f"""
{GENERATED_START}
- Номер для пользователя: `CUST-{issue_number}`
- Problem code: `{report.get("problem_code", "unknown")}`
- Dedupe key: `{report.get("dedupe_key", "unknown")}`
- Affected count: `{affected_count}`
- Safe affected identities: {", ".join(safe_affected_identities) if safe_affected_identities else "none"}

Full safe metadata-only report:

```json
{report_json}
```
{GENERATED_END}
"""


def _extract_generated_block(body: str) -> str:
    start = body.find(GENERATED_START)
    end = body.find(GENERATED_END)
    if start == -1 or end == -1 or end < start:
        return ""
    return body[start : end + len(GENERATED_END)]


def _human_problem_summary(problem_code: str) -> str:
    lowered = problem_code.lower()
    if "access" in lowered or "policy" in lowered:
        return "нужна проверка доступа или политики"
    if "retention" in lowered or "expired" in lowered:
        return "автоматическая отправка уже не выполнится"
    return "локальная запись требует проверки поддержки"


def _validate_target_repo(*, owner: str, repo: str) -> None:
    if owner != REQUIRED_REPO_OWNER or repo != REQUIRED_REPO_NAME:
        raise GitHubIssueClientError("support_incident.configuration_invalid")


def _response_reason_code(response: httpx.Response) -> str:
    if response.status_code in {401, 403, 404, 422}:
        return "support_incident.configuration_invalid"
    return "support_incident.github_unavailable"
