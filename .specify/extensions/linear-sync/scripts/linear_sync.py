#!/usr/bin/env python3
"""Spec Kit <-> Linear sync helper.

This script is intentionally conservative. It can always produce a dry-run
report from local Spec Kit files, and it mutates Linear only when --apply and
LINEAR_API_KEY are present.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TASK_RE = re.compile(
    r"^- \[(?P<done>[ Xx])\] (?P<task>T\d{3})(?: (?P<parallel>\[P\]))?"
    r"(?: (?P<story>\[US\d+\]))? (?P<title>.+)$"
)
GITHUB_ISSUE_RE = re.compile(r"(?:^|\s)#(?P<number>\d+)(?=$|[^\d])")
ENV_KEYS = {
    "LINEAR_API_KEY",
    "LINEAR_TEAM_KEY",
    "LINEAR_PRODUCT_NAME",
    "LINEAR_PROJECT_TEMPLATE",
    "LINEAR_PROJECT_NAME",
    "SPECKIT_PRODUCT_NAME",
}


@dataclass
class Task:
    task_id: str
    title: str
    done: bool
    story: str
    area: str
    source_line: int
    github_issue: int | None = None
    linear_issue: str | None = None


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()


def find_repo_root(start: Path) -> Path:
    try:
        top = run(["git", "rev-parse", "--show-toplevel"], start)
        return Path(top)
    except Exception:
        cur = start.resolve()
        for candidate in [cur, *cur.parents]:
            if (candidate / ".specify").exists():
                return candidate
        raise SystemExit("linear-sync: Spec Kit project root not found")


def load_dotenv(root: Path) -> None:
    """Load local .env values without overriding already exported env vars."""
    env_path = root / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in ENV_KEYS or os.environ.get(key):
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


def discover_feature_dir(root: Path, feature: str | None) -> Path:
    specs = root / "specs"
    if not specs.exists():
        raise SystemExit("linear-sync: specs/ directory not found")

    matches = []
    for path in specs.iterdir():
        if not path.is_dir():
            continue
        if feature and path.name.startswith(f"{feature}-"):
            matches.append(path)
        elif not feature and (path / "tasks.md").exists():
            matches.append(path)

    if feature and not matches:
        raise SystemExit(f"linear-sync: feature {feature} not found under specs/")
    if not feature:
        matches = sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        raise SystemExit("linear-sync: no feature with tasks.md found")
    return matches[0]


def parse_tasks(tasks_path: Path) -> list[Task]:
    tasks: list[Task] = []
    for line_number, line in enumerate(tasks_path.read_text(encoding="utf-8").splitlines(), 1):
        match = TASK_RE.match(line)
        if not match:
            continue
        title = match.group("title").strip()
        github_match = GITHUB_ISSUE_RE.search(title)
        area = infer_area(title)
        tasks.append(
            Task(
                task_id=match.group("task"),
                title=title,
                done=match.group("done").upper() == "X",
                story=(match.group("story") or "").strip("[]"),
                area=area,
                source_line=line_number,
                github_issue=int(github_match.group("number")) if github_match else None,
            )
        )
    return tasks


def infer_area(title: str) -> str:
    lowered = title.lower()
    checks = [
        ("auth", ("auth", "identity", "user", "device", "session")),
        ("backend", ("server", "api", "fastapi", "postgres", "database", "migration")),
        ("storage", ("minio", "storage", "object", "upload")),
        ("macos", ("macos", "swift", "app", "desktop")),
        ("security", ("secret", "redaction", "permission", "tenant", "privacy")),
        ("docs", ("docs/", "readme", "prd", "status", "document")),
        ("validation", ("test", "validate", "quickstart", "evidence")),
    ]
    for area, needles in checks:
        if any(needle in lowered for needle in needles):
            return area
    return "general"


def load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "features": {}}

    # The first version writes JSON-compatible YAML, so stdlib JSON can read it.
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {"version": 1, "features": {}}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise SystemExit(
            "linear-sync: .specify/linear.yml exists but is not in the managed JSON-compatible format"
        )


def save_mapping(path: Path, mapping: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def feature_number(feature_dir: Path) -> str:
    return feature_dir.name.split("-", 1)[0]


def feature_title(feature_dir: Path) -> str:
    raw = feature_dir.name.split("-", 1)[1].replace("-", " ") if "-" in feature_dir.name else feature_dir.name
    return " ".join(word.capitalize() for word in raw.split())


def infer_product_name(root: Path) -> str:
    env_value = os.environ.get("LINEAR_PRODUCT_NAME") or os.environ.get("SPECKIT_PRODUCT_NAME")
    if env_value:
        return env_value

    candidates = [
        root / "AGENTS.md",
        root / "docs" / "current-product-status.md",
        root / "docs" / "prd-voice-layer-final.md",
    ]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in (
            r"Product:\s*`?([^`\n]+?)`?\s*(?:\n|$)",
            r"Product:\s*([^,\n]+)",
            r"#\s+([^#\n]+)",
        ):
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip()
                value = value.strip("`").strip()
                if value and len(value) <= 80:
                    return value

    slug = repo_slug(root)
    if slug:
        return slug.split("/", 1)[1]
    return root.name


def linear_project_name(root: Path, feature_dir: Path) -> str:
    explicit = os.environ.get("LINEAR_PROJECT_NAME")
    if explicit:
        return explicit
    product = infer_product_name(root)
    feature = feature_number(feature_dir)
    title = feature_title(feature_dir)
    template = os.environ.get("LINEAR_PROJECT_TEMPLATE", "{product} / {feature} {title}")
    return template.format(product=product, feature=feature, title=title, feature_dir=feature_dir.name)


def repo_slug(root: Path) -> str:
    try:
        remote = run(["git", "remote", "get-url", "origin"], root)
    except Exception:
        return ""
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", remote)
    if not match:
        return ""
    return f"{match.group(1)}/{match.group(2)}"


def linear_request(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    token = os.environ.get("LINEAR_API_KEY")
    if not token:
        raise SystemExit("linear-sync: LINEAR_API_KEY is required for --apply")

    request = urllib.request.Request(
        "https://api.linear.app/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": "spec-kit-ext-linear-sync/0.1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"linear-sync: Linear API HTTP {exc.code}: {body}") from exc
    if payload.get("errors"):
        raise SystemExit(f"linear-sync: Linear API error: {payload['errors']}")
    return payload["data"]


def get_linear_context(project_name: str) -> dict[str, Any]:
    team_key = os.environ.get("LINEAR_TEAM_KEY", "")
    query = """
    query SyncContext {
      teams {
        nodes {
          id
          key
          name
          states { nodes { id name type } }
          labels { nodes { id name } }
        }
      }
      projects {
        nodes { id name url }
      }
    }
    """
    data = linear_request(query, {})
    teams = data["teams"]["nodes"]
    projects = data["projects"]["nodes"]

    team = next((item for item in teams if item["key"] == team_key), None) if team_key else None
    if not team and len(teams) == 1:
        team = teams[0]
    if not team:
        raise SystemExit("linear-sync: set LINEAR_TEAM_KEY to choose a Linear team")

    project = None
    if project_name:
        project = next((item for item in projects if item["name"] == project_name), None)

    done_state = next((state for state in team["states"]["nodes"] if state["type"] == "completed"), None)
    todo_state = next((state for state in team["states"]["nodes"] if state["type"] == "unstarted"), None)

    return {
        "team": team,
        "project": project,
        "project_name": project_name,
        "done_state": done_state,
        "todo_state": todo_state,
    }


def ensure_linear_project(context: dict[str, Any]) -> dict[str, Any]:
    if context.get("project"):
        return context["project"]

    project_name = context.get("project_name")
    if not project_name:
        raise SystemExit("linear-sync: Linear project name is empty")

    query = """
    mutation CreateProject($input: ProjectCreateInput!) {
      projectCreate(input: $input) {
        success
        project { id name url }
      }
    }
    """
    variables = {"input": {"name": project_name, "teamIds": [context["team"]["id"]]}}
    data = linear_request(query, variables)
    project = data["projectCreate"]["project"]
    context["project"] = project
    return project


def linear_issue_snapshot(identifier: str) -> dict[str, Any] | None:
    query = """
    query IssueByIdentifier($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        url
        state { id name type }
        project { id name url }
      }
    }
    """
    try:
        data = linear_request(query, {"id": identifier})
    except SystemExit:
        raise
    return data.get("issue")


def create_linear_issue(context: dict[str, Any], feature: str, task: Task, github_repo: str) -> dict[str, str]:
    title = f"[{feature}][{task.task_id}] {russian_title(feature, task)}"
    description = russian_description(feature, task, github_repo)
    project = ensure_linear_project(context)
    variables: dict[str, Any] = {
        "input": {
            "teamId": context["team"]["id"],
            "projectId": project["id"],
            "title": title,
            "description": description,
        }
    }
    if task.done and context.get("done_state"):
        variables["input"]["stateId"] = context["done_state"]["id"]
    elif context.get("todo_state"):
        variables["input"]["stateId"] = context["todo_state"]["id"]

    query = """
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id identifier url title }
      }
    }
    """
    data = linear_request(query, variables)
    issue = data["issueCreate"]["issue"]
    return {"id": issue["id"], "identifier": issue["identifier"], "url": issue["url"]}


def russian_title(feature: str, task: Task) -> str:
    area = {
        "auth": "авторизация и доступ",
        "backend": "серверная часть",
        "storage": "хранение данных",
        "macos": "macOS-приложение",
        "security": "безопасность",
        "docs": "документация",
        "validation": "проверка качества",
        "general": "реализация",
    }.get(task.area, "реализация")
    story = f", {task.story}" if task.story else ""
    return f"Выполнить задачу {task.task_id}: {area}{story}"[:180]


def russian_description(feature: str, task: Task, github_repo: str) -> str:
    paths = re.findall(r"`([^`]+)`", task.title)
    lines = [
        "## Что нужно сделать",
        "Выполнить задачу из Spec Kit и довести ее до проверяемого результата.",
        "",
        "## Контекст",
        f"Фича: {feature}",
        f"Задача Spec Kit: {task.task_id}",
        f"Строка в tasks.md: {task.source_line}",
    ]
    if task.story:
        lines.append(f"User story: {task.story}")
    if paths:
        lines.extend(["", "## Затронутые файлы"])
        lines.extend(f"- `{path}`" for path in paths[:8])
    if task.github_issue and github_repo:
        lines.extend(["", "## Связи", f"GitHub issue: https://github.com/{github_repo}/issues/{task.github_issue}"])
    lines.extend(
        [
            "",
            "## Критерии приемки",
            "- Задача выполнена в коде или документации.",
            "- В tasks.md задача отмечена как выполненная только после проверки evidence.",
            "- Если есть блокер, в комментарии понятно написано, что именно нужно решить.",
        ]
    )
    return "\n".join(lines)


def ensure_feature_mapping(mapping: dict[str, Any], feature: str, feature_dir: Path, github_repo: str) -> dict[str, Any]:
    features = mapping.setdefault("features", {})
    entry = features.setdefault(
        feature,
        {
            "name": feature_dir.name,
            "github_repo": github_repo,
            "tasks": {},
        },
    )
    entry.setdefault("name", feature_dir.name)
    entry.setdefault("github_repo", github_repo)
    entry.setdefault("tasks", {})
    return entry


def cmd_init(root: Path, args: argparse.Namespace) -> int:
    feature_dir = discover_feature_dir(root, args.feature) if args.feature else None
    mapping_path = root / ".specify" / "linear.yml"
    mapping = load_mapping(mapping_path)
    mapping.setdefault("version", 1)
    mapping.setdefault("team_key", os.environ.get("LINEAR_TEAM_KEY", ""))
    mapping.setdefault("product_name", infer_product_name(root))
    mapping.setdefault("project_template", os.environ.get("LINEAR_PROJECT_TEMPLATE", "{product} / {feature} {title}"))
    if feature_dir:
        mapping.setdefault("project_name", linear_project_name(root, feature_dir))
    mapping.setdefault("language", "ru")
    mapping.setdefault("plain_language", True)
    mapping.setdefault("features", {})
    if args.apply:
        save_mapping(mapping_path, mapping)
        print(f"Создан или обновлен файл {mapping_path.relative_to(root)}")
    else:
        print("Dry-run: будет создан или обновлен .specify/linear.yml")
        print(json.dumps(mapping, ensure_ascii=False, indent=2))
    return 0


def cmd_sync(root: Path, args: argparse.Namespace, mode: str) -> int:
    feature_dir = discover_feature_dir(root, args.feature)
    feature = feature_number(feature_dir)
    project_name = linear_project_name(root, feature_dir)
    tasks = parse_tasks(feature_dir / "tasks.md")
    mapping_path = root / ".specify" / "linear.yml"
    mapping = load_mapping(mapping_path)
    github_repo = repo_slug(root)
    feature_entry = ensure_feature_mapping(mapping, feature, feature_dir, github_repo)
    feature_entry.setdefault("linear_project_name", project_name)
    task_map = feature_entry.setdefault("tasks", {})

    planned_create: list[Task] = []
    for task in tasks:
        existing = task_map.setdefault(task.task_id, {})
        existing.setdefault("title", task.title)
        existing.setdefault("source_line", task.source_line)
        existing.setdefault("done", task.done)
        if task.github_issue:
            existing.setdefault("github_issue", task.github_issue)
        if not existing.get("linear_issue"):
            planned_create.append(task)

    print(f"Фича: {feature_dir.name}")
    print(f"Linear Project: {project_name}")
    print(f"Задач в tasks.md: {len(tasks)}")
    print(f"Без Linear issue: {len(planned_create)}")

    if mode == "validate":
        context = get_linear_context(project_name) if args.apply else None
        if context and not context.get("project"):
            raise SystemExit(f"linear-sync: Linear Project not found for validation: {project_name}")
        return validate(tasks, task_map, context)

    if mode == "import":
        print("Import-mode: существующие связи сохранены, новые Linear issues не создаются без --apply-sync.")
        if args.apply:
            save_mapping(mapping_path, mapping)
            print(f"Mapping обновлен: {mapping_path.relative_to(root)}")
        return 0

    if not args.apply:
        for task in planned_create[:25]:
            print(f"DRY-RUN create Linear issue: [{feature}][{task.task_id}] {russian_title(feature, task)}")
        if len(planned_create) > 25:
            print(f"...и еще {len(planned_create) - 25}")
        print("Чтобы применить изменения, запусти с --apply и LINEAR_API_KEY.")
        return 0

    context = get_linear_context(project_name)
    project = ensure_linear_project(context)
    feature_entry["linear_project_id"] = project["id"]
    feature_entry["linear_project_name"] = project["name"]
    if project.get("url"):
        feature_entry["linear_project_url"] = project["url"]
    print(f"Linear Project готов: {project['name']}")

    for task in planned_create:
        issue = create_linear_issue(context, feature, task, github_repo)
        task_map[task.task_id]["linear_issue"] = issue["identifier"]
        task_map[task.task_id]["linear_url"] = issue["url"]
        print(f"Создан Linear issue {issue['identifier']}: {issue['url']}")

    save_mapping(mapping_path, mapping)
    print(f"Mapping обновлен: {mapping_path.relative_to(root)}")
    return 0


def validate(tasks: list[Task], task_map: dict[str, Any], context: dict[str, Any] | None) -> int:
    problems = 0
    task_ids = {task.task_id for task in tasks}
    expected_project = context.get("project") if context else None
    for task in tasks:
        entry = task_map.get(task.task_id, {})
        if not entry.get("linear_issue"):
            print(f"Нужно связать Linear issue: {task.task_id} — {task.title}")
            problems += 1
            continue

        if context:
            issue = linear_issue_snapshot(entry["linear_issue"])
            if not issue:
                print(f"Linear issue не найден: {task.task_id} — {entry['linear_issue']}")
                problems += 1
                continue
            if expected_project and (not issue.get("project") or issue["project"]["id"] != expected_project["id"]):
                actual = issue.get("project", {}).get("name") if issue.get("project") else "без проекта"
                print(
                    f"Linear issue не в нужном проекте: {task.task_id} — "
                    f"{entry['linear_issue']} сейчас в '{actual}', ожидается '{expected_project['name']}'"
                )
                problems += 1
            if task.done and issue.get("state", {}).get("type") != "completed":
                print(f"Linear issue открыт, хотя tasks.md уже [X]: {task.task_id} — {entry['linear_issue']}")
                problems += 1
    for task_id in sorted(set(task_map) - task_ids):
        print(f"Лишняя связь в mapping без задачи в tasks.md: {task_id}")
        problems += 1
    if problems:
        print(f"Проверка завершена: найдено проблем: {problems}")
        return 1
    print("Проверка завершена: mapping чистый.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Spec Kit tasks with Linear")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "import", "sync", "validate"):
        p = sub.add_parser(name)
        p.add_argument("--feature", help="Feature number, e.g. 013")
        p.add_argument("--apply", action="store_true", help="Apply changes instead of dry-run")

    args = parser.parse_args()
    root = find_repo_root(Path.cwd())
    load_dotenv(root)

    if args.command == "init":
        return cmd_init(root, args)
    if args.command in {"import", "sync", "validate"}:
        return cmd_sync(root, args, args.command)
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
