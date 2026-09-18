from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40

BODY = """## Кратко

Описание.

## Feature identity

- Feature ID: 271
- Spec task IDs: `T037`
- Exact source SHA: `%s`
""" % ("b" * 40)


def harness(tmp_path: Path, *, conclusion: str | None, body: str = BODY) -> tuple[Path, Path]:
    """Build a repository scratch copy with a stubbed gh, and return paths."""
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(ROOT / "scripts" / "sync-pr-metadata.py", scripts / "sync-pr-metadata.py")

    state = tmp_path / "state.json"
    state.write_text(json.dumps({"body": body}), encoding="utf-8")

    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    runs = []
    if conclusion is not None:
        runs.append({"name": "governance-fast", "status": "completed", "conclusion": conclusion})
    check_runs = tmp_path / "check-runs.json"
    check_runs.write_text(json.dumps({"check_runs": runs}), encoding="utf-8")

    gh = bin_dir / "gh"
    gh.write_text(
        "#!/usr/bin/env python3\n"
        "import json, pathlib, sys\n"
        f"state_path = pathlib.Path({str(state)!r})\n"
        f"runs_path = pathlib.Path({str(check_runs)!r})\n"
        "args = sys.argv[1:]\n"
        "joined = ' '.join(args)\n"
        "if 'check-runs' in joined:\n"
        "    print(runs_path.read_text())\n"
        "elif '-X PATCH' in joined:\n"
        "    body = None\n"
        "    for index, item in enumerate(args):\n"
        "        if item.startswith('-F') and index + 1 < len(args):\n"
        "            value = args[index + 1]\n"
        "            if value.startswith('body=@'):\n"
        "                body = pathlib.Path(value[len('body=@'):]).read_text()\n"
        "    state = json.loads(state_path.read_text())\n"
        "    state['body'] = body\n"
        "    state_path.write_text(json.dumps(state))\n"
        "    print('7211')\n"
        "elif 'pulls/' in joined:\n"
        "    state = json.loads(state_path.read_text())\n"
        f"    print(json.dumps({{'head': {{'sha': {SHA!r}}}, 'body': state['body']}}))\n"
        "else:\n"
        "    print('{}')\n",
        encoding="utf-8",
    )
    gh.chmod(0o755)
    return bin_dir, state


def run(tmp_path: Path, bin_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "scripts/sync-pr-metadata.py", "7211", *extra],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )


def test_updates_body_only_after_the_code_proof_completed(tmp_path: Path) -> None:
    """Описание обновляется после доказательства, иначе проверка не пройдёт."""
    bin_dir, state = harness(tmp_path, conclusion="success")

    result = run(tmp_path, bin_dir, "--wait-seconds", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "conclusion=success" in result.stdout, result.stdout
    body = json.loads(state.read_text(encoding="utf-8"))["body"]
    assert f"- Exact source SHA: `{SHA}`" in body, body
    assert "b" * 40 not in body, body


def test_refuses_to_update_body_without_a_successful_proof(tmp_path: Path) -> None:
    """Неуспешное доказательство — это стоп, а не повод обновить описание."""
    bin_dir, state = harness(tmp_path, conclusion="failure")

    result = run(tmp_path, bin_dir, "--wait-seconds", "1")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "not successful" in result.stderr, result.stderr
    body = json.loads(state.read_text(encoding="utf-8"))["body"]
    assert body == BODY, "описание изменено без доказательства"


def test_refuses_when_no_proof_was_requested_at_all(tmp_path: Path) -> None:
    """Отсутствующее доказательство — тоже стоп: ждать нечего."""
    bin_dir, state = harness(tmp_path, conclusion=None)

    result = run(tmp_path, bin_dir, "--wait-seconds", "1", "--poll-seconds", "1")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "conclusion=missing" in result.stdout, result.stdout
    assert json.loads(state.read_text(encoding="utf-8"))["body"] == BODY


def test_reports_unchanged_when_the_body_already_carries_the_sha(tmp_path: Path) -> None:
    """Повторный запуск не трогает описание и ничего не ломает."""
    body = BODY.replace("b" * 40, SHA)
    bin_dir, state = harness(tmp_path, conclusion="success", body=body)

    result = run(tmp_path, bin_dir, "--wait-seconds", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "pr_metadata=unchanged" in result.stdout, result.stdout
    assert json.loads(state.read_text(encoding="utf-8"))["body"] == body
