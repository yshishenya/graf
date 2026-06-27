from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from twobrain_rec_server.support.github_issues import GitHubIssueDraft


@dataclass
class FakeGitHubIssueClient:
    repo_private: bool = True
    next_issue_number: int = 123
    created_issues: list[dict[str, Any]] = field(default_factory=list)
    updated_issues: list[dict[str, Any]] = field(default_factory=list)

    async def repo_is_private(self, *, owner: str, repo: str) -> bool:
        self._assert_repo(owner, repo)
        return self.repo_private

    async def create_issue(self, *, owner: str, repo: str, draft: GitHubIssueDraft) -> dict[str, Any]:
        self._assert_repo(owner, repo)
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
            raise AssertionError("support incidents must target yshishenya/crisp")
