from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def abandon_function() -> str:
    script = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    start = script.index("abandon_unpublished_candidate() {")
    end = script.index("\ntrap cleanup_unpublished_release EXIT", start)
    return script[start:end]


def run_abandon(tmp_path: Path, candidate: Path) -> subprocess.CompletedProcess[str]:
    harness = tmp_path / "harness.sh"
    harness.write_text(
        "set -euo pipefail\n"
        f"candidate_file={str(candidate)!r}\n"
        'tag="v2099.01.01.1"\n'
        f"{abandon_function()}\n"
        "abandon_unpublished_candidate\n",
        encoding="utf-8",
    )
    return subprocess.run(
        ["bash", str(harness)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )


def test_release_abandons_frozen_candidate_after_failed_release(tmp_path: Path) -> None:
    """Провалившийся выпуск оставляет отметку об отмене, не трогая саму запись.

    Замороженный кандидат неизменяем и рядом лежит файл с его контрольной
    суммой. Отметка об отмене пишется отдельным файлом, иначе повторный запуск
    после провала упирался бы в стену до ручной расчистки.
    """
    candidate = tmp_path / "rc-20260918T000000Z-abcdef123456.json"
    frozen = json.dumps(
        {"candidate_id": "rc-20260918T000000Z-abcdef123456", "status": "frozen"},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    candidate.write_text(frozen, encoding="utf-8")
    identity = tmp_path / (".%s.identity.json" % candidate.name)
    identity.write_text('{"digest": "sha256:abc"}\n', encoding="utf-8")

    result = run_abandon(tmp_path, candidate)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "release_cleanup=abandoned_candidate" in result.stderr
    record_path = tmp_path / (".%s.abandoned.json" % candidate.name)
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["candidate_id"] == "rc-20260918T000000Z-abcdef123456"
    assert record["release_tag"] == "v2099.01.01.1"
    assert record["candidate_digest"] == '{"digest": "sha256:abc"}'
    # Неизменяемая запись и её удостоверение остаются нетронутыми.
    assert candidate.read_text(encoding="utf-8") == frozen
    assert identity.read_text(encoding="utf-8") == '{"digest": "sha256:abc"}\n'


def test_release_does_not_abandon_non_frozen_candidate(tmp_path: Path) -> None:
    """Опубликованный кандидат — история, а не брошенная работа."""
    candidate = tmp_path / "rc-20260918T000000Z-abcdef123456.json"
    candidate.write_text(
        json.dumps({"candidate_id": "rc-1", "status": "go"}) + "\n", encoding="utf-8"
    )

    result = run_abandon(tmp_path, candidate)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / (".%s.abandoned.json" % candidate.name)).exists()


def test_release_abandon_is_idempotent(tmp_path: Path) -> None:
    """Повторная уборка не переписывает уже поставленную отметку."""
    candidate = tmp_path / "rc-20260918T000000Z-abcdef123456.json"
    candidate.write_text(
        json.dumps({"candidate_id": "rc-1", "status": "frozen"}) + "\n", encoding="utf-8"
    )
    record_path = tmp_path / (".%s.abandoned.json" % candidate.name)
    record_path.write_text('{"reason": "первая отметка"}\n', encoding="utf-8")

    result = run_abandon(tmp_path, candidate)

    assert result.returncode == 0, result.stdout + result.stderr
    assert record_path.read_text(encoding="utf-8") == '{"reason": "первая отметка"}\n'
