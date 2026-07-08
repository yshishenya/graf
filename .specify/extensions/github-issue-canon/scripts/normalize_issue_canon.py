#!/usr/bin/env python3
from __future__ import annotations

import re
import sys

from issue_canon_common import (
    LEGACY_TITLE_RE,
    REQUIRED_SECTIONS,
    TASK_RE,
    TITLE_RE,
    current_feature,
    is_speckit_issue,
    label_names,
    list_open_issues,
    repo_root,
    repo_slug,
    run,
)


def infer_priority(body: str, title: str) -> str:
    match = re.search(r"\bP[0-3]\b", body + "\n" + title)
    return match.group(0) if match else "P1"


def infer_area(body: str, title: str) -> str:
    text = (title + "\n" + body).lower()
    candidates = [
        ("auth", ["auth", "tenant", "device", "permission", "доступ", "пользователь"]),
        ("contract", ["openapi", "contract", "schema", "problem response", "контракт", "схема"]),
        ("docs", ["quickstart", "docs", "documentation", "prd", "документ", "changelog"]),
        ("infra", ["docker", "compose", "migration", "runtime", "readiness", "инфра", "деплой"]),
        ("storage", ["minio", "object", "storage", "artifact", "хранилище", "артефакт"]),
        ("tests", ["test", "pytest", "coverage", "fake", "тест", "провер"]),
        ("security", ["security", "privacy", "redaction", "audit", "безопас", "приват"]),
        ("macos", ["macos", "driver", "audio", "аудио", "запись"]),
        ("ux", ["ux", "ui", "accessibility"]),
        ("ingest", ["ingest", "upload", "finalize", "session", "range", "загрузка"]),
    ]
    for area, needles in candidates:
        if any(needle in text for needle in needles):
            return area
    return "ingest"


def infer_type(body: str, title: str) -> str:
    text = (title + "\n" + body).lower()
    if "test" in text or "coverage" in text or "тест" in text or "провер" in text:
        return "type:test-gap"
    if "docs" in text or "quickstart" in text or "documentation" in text or "документ" in text:
        return "type:docs"
    if "hardening" in text or "security" in text or "privacy" in text or "безопас" in text or "приват" in text:
        return "type:hardening"
    return "type:bug"


def first_task_id(body: str, title: str) -> str:
    match = TASK_RE.search(body)
    if match:
        return match.group(0)
    match = re.match(r"^\s*(T\d{3})\s*:", title)
    if match:
        return match.group(1)
    match = TASK_RE.search(title)
    return match.group(0) if match else "T000"


def clean_outcome(title: str) -> str:
    cleaned = re.sub(r"^012 hackathon (remediation|additional):\s*", "", title, flags=re.I).strip()
    cleaned = re.sub(r"^T\d{3}\s*:\s*", "", cleaned).strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else "Закрыть Spec Kit задачу"


def canonical_title(issue: dict, default_feature: str | None) -> str:
    title = issue.get("title") or ""
    if TITLE_RE.match(title):
        return title
    body = issue.get("body") or ""
    legacy = LEGACY_TITLE_RE.match(title)
    if legacy:
        feature = legacy.group("feature")
        priority = legacy.group("priority")
        area = legacy.group("area")
        outcome = clean_outcome(legacy.group("outcome"))
    else:
        feature = default_feature or "000"
        feature_match = re.search(r"(?:Feature:\s*`?|Фича:\s*`?|specs/)(\d{3})", body)
        if feature_match:
            feature = feature_match.group(1)
        priority = infer_priority(body, title)
        area = infer_area(body, title)
        outcome = clean_outcome(title)
    task = first_task_id(body, title)
    return f"[{feature}][{priority}][{area}] {task}: {outcome}"


def extract_context_line(body: str, label: str) -> str | None:
    match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def canonical_body(issue: dict, title: str) -> str:
    body = issue.get("body") or ""
    missing = [section for section in REQUIRED_SECTIONS if section not in body]

    match = TITLE_RE.match(title)
    feature = match.group("feature") if match else "000"
    priority = match.group("priority") if match else infer_priority(body, title)
    area = match.group("area") if match else infer_area(body, title)
    task = match.group("task") if match else first_task_id(body, title)
    if not missing and task in body:
        return body
    if not missing:
        existing_tasks = extract_context_line(body, "Spec tasks") or extract_context_line(body, "Spec Kit tasks")
        if existing_tasks:
            updated_tasks = existing_tasks if task in existing_tasks else f"{existing_tasks}, {task}"
            updated = re.sub(
                r"^- Spec (?:Kit )?tasks:\s*.+$",
                f"- Spec tasks: {updated_tasks}",
                body,
                count=1,
                flags=re.MULTILINE,
            )
            if updated != body:
                return updated
        return re.sub(r"(## Контекст\s*\n\n)", rf"\1- Spec tasks: {task}\n", body, count=1)

    tasks = extract_context_line(body, "Spec tasks") or extract_context_line(body, "Spec Kit tasks")
    tasks = tasks or ", ".join(sorted(set(TASK_RE.findall(body)))) or task
    if task not in tasks:
        tasks = f"{tasks}, {task}"
    source = extract_context_line(body, "Source") or extract_context_line(body, "Источник") or "Spec Kit task-to-issue sync / review"
    gate = extract_context_line(body, "Gate") or extract_context_line(body, "Гейт") or ("blocks deployment" if "gate:deployment-blocker" in ",".join(label_names(issue)) else "blocks PR")

    summary = title
    if match:
        summary = match.group("outcome").strip()
    summary = summary[:1].upper() + summary[1:] if summary else "Закрыть Spec Kit задачу"

    original = body.strip() or "Исходное описание отсутствовало."
    return (
        "## Кратко\n\n"
        f"{summary}.\n\n"
        "## Контекст\n\n"
        f"- Фича: `{feature}`\n"
        f"- Приоритет: `{priority}`\n"
        f"- Область: `{area}`\n"
        f"- Spec tasks: {tasks}\n"
        f"- Источник: {source}\n"
        f"- Гейт: {gate}\n"
        "- Связанные issues:\n\n"
        "## Проблема\n\n"
        f"{original}\n\n"
        "## Проверенные факты\n\n"
        "- Требуется сверить с текущими `spec.md`, `plan.md` и `tasks.md`.\n"
        "- Требуется зафиксировать evidence перед закрытием.\n\n"
        "## Границы задачи\n\n"
        "Входит:\n"
        "- Выполнить связанную Spec Kit задачу.\n\n"
        "Не входит:\n"
        "- Расширять scope за пределы активной фичи без отдельного issue.\n\n"
        "## Критерии приемки\n\n"
        "- [ ] Связанная задача выполнена в указанных файлах.\n"
        "- [ ] Поведение соответствует spec/plan/contract.\n"
        "- [ ] Нет незадокументированных ограничений или скрытых follow-up.\n\n"
        "## Что проверить перед закрытием\n\n"
        "- [ ] Нужные тесты, smoke или ручная проверка пройдены.\n"
        "- [ ] Evidence записан в PR, issue comment или feature docs.\n"
        "- [ ] Связанный пункт в `tasks.md` отмечен `[X]` только после проверки.\n\n"
        "## Заметки по реализации\n\n"
        "- Сохрани исходный контекст выше в разделе `Проблема`, если issue был нормализован автоматически.\n\n"
        "## Ссылки\n\n"
        f"- Spec: `specs/{feature}-*/spec.md`\n"
        f"- Plan: `specs/{feature}-*/plan.md`\n"
        f"- Tasks: `specs/{feature}-*/tasks.md`\n"
        "- Связано:\n"
    )


def main() -> int:
    root = repo_root()
    slug = repo_slug(root)
    default_feature = current_feature(root)
    numbers = {int(arg.lstrip("#")) for arg in sys.argv[1:] if arg.strip()}
    issues = [issue for issue in list_open_issues(slug) if is_speckit_issue(issue)]
    if numbers:
        issues = [issue for issue in issues if issue["number"] in numbers]

    changed = []
    for issue in issues:
        title = canonical_title(issue, default_feature)
        labels = label_names(issue)
        match = TITLE_RE.match(title)
        add_labels = set()
        if match:
            add_labels.add(f"feature:{match.group('feature')}")
            add_labels.add(f"priority:{match.group('priority')}")
            area = match.group("area")
            area_root = area.split("/", 1)[0]
            if f"area:{area_root}" not in labels and f"area:{area}" not in labels:
                add_labels.add(f"area:{area_root}")
        if not any(label.startswith("type:") for label in labels):
            add_labels.add(infer_type(issue.get("body") or "", issue.get("title") or ""))
        args = ["gh", "issue", "edit", str(issue["number"]), "--repo", slug]
        base_arg_count = len(args)
        if title != issue.get("title"):
            args.extend(["--title", title])
        body = canonical_body(issue, title)
        if body != (issue.get("body") or ""):
            args.extend(["--body", body])
        new_labels = sorted(add_labels - labels)
        if new_labels:
            args.extend(["--add-label", ",".join(new_labels)])
        if len(args) > base_arg_count:
            run(args)
            changed.append(issue["number"])

    if changed:
        print("github-issue-canon: normalized issues " + ", ".join(f"#{n}" for n in changed))
    else:
        print("github-issue-canon: no issue normalization needed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
