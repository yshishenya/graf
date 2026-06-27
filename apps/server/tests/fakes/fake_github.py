from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from twobrain_rec_server.support.github_issues import (
    REQUIRED_SUPPORT_LABELS,
    GitHubIssueClientError,
    GitHubIssueDraft,
)


@dataclass
class FakeGitHubIssueClient:
    repo_private: bool = True
    failure_reason_code: str | None = None
    missing_required_labels: tuple[str, ...] = ()
    next_issue_number: int = 123
    created_issues: list[dict[str, Any]] = field(default_factory=list)
    updated_issues: list[dict[str, Any]] = field(default_factory=list)

    async def validate_repository_ready(self, *, owner: str, repo: str) -> None:
        self._assert_repo(owner, repo)
        if self.failure_reason_code:
            raise GitHubIssueClientError(self.failure_reason_code)
        if not self.repo_private or self.missing_required_labels:
            raise GitHubIssueClientError("support_incident.configuration_invalid")

    async def repo_is_private(self, *, owner: str, repo: str) -> bool:
        self._assert_repo(owner, repo)
        return self.repo_private

    async def label_names(self, *, owner: str, repo: str) -> set[str]:
        self._assert_repo(owner, repo)
        return set(REQUIRED_SUPPORT_LABELS) - set(self.missing_required_labels)

    async def get_issue(self, *, owner: str, repo: str, issue_number: int) -> dict[str, Any]:
        self._assert_repo(owner, repo)
        for issue in [*self.updated_issues, *self.created_issues]:
            if issue["number"] == issue_number:
                return issue
        return {"number": issue_number, "body": ""}

    async def create_issue(self, *, owner: str, repo: str, draft: GitHubIssueDraft) -> dict[str, Any]:
        self._assert_repo(owner, repo)
        if self.failure_reason_code:
            raise GitHubIssueClientError(self.failure_reason_code)
        issue = self._issue_payload(draft, self.next_issue_number)
        self.next_issue_number += 1
        self.created_issues.append(issue)
        return issue

    async def update_issue(
        self,
        *,
        owner: str,
        repo: str,
        issue_number: int,
        draft: GitHubIssueDraft,
    ) -> dict[str, Any]:
        self._assert_repo(owner, repo)
        if self.failure_reason_code:
            raise GitHubIssueClientError(self.failure_reason_code)
        issue = self._issue_payload(draft, issue_number)
        self.updated_issues.append(issue)
        return issue

    def _issue_payload(self, draft: GitHubIssueDraft, issue_number: int) -> dict[str, Any]:
        return {
            "number": issue_number,
            "html_url": f"https://github.com/yshishenya/crisp/issues/{issue_number}",
            "title": draft.title,
            "body": draft.body,
            "labels": list(draft.labels),
        }

    def _assert_repo(self, owner: str, repo: str) -> None:
        if owner != "yshishenya" or repo != "crisp":
            raise GitHubIssueClientError("support_incident.configuration_invalid")
