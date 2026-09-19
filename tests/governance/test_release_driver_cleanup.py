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


def test_release_driver_guards_the_prep_commit_against_no_changes() -> None:
    """Повтор выпуска с уже влитой подготовкой не должен обрываться молча.

    Если прошлая попытка влила подготовку в мастер, собирать нечего. Раньше
    здесь стоял незащищённый `git commit`: при отсутствии изменений он
    завершался с ошибкой, а `set -e` убивал выпуск без единого объяснения.
    """
    script = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")

    guard = script.index("if git diff --cached --quiet; then")
    commit = script.index('git commit -m "Подготовка релиза')

    assert guard < commit, "проверка на отсутствие изменений должна идти до commit"
    assert "release_prep=already_merged" in script, "нет понятного отчёта о готовом состоянии"
    assert "--from train" in script[guard:commit], "нет команды продолжения выпуска"


def test_train_collects_prs_in_parallel_and_reports_skips() -> None:
    """Сетевые проверки поезда вынесены в повторяемый параллельный помощник."""
    script = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")
    collector = (ROOT / "scripts" / "collect_release_train.py").read_text(encoding="utf-8")

    assert "collect_release_train.py" in script
    assert "ThreadPoolExecutor" in collector
    assert "нет успешной проверки governance-fast" in collector
    assert "нет merge commit" in collector
    assert "ThreadPoolExecutor" in collector


def test_public_release_resume_does_not_delete_existing_tag() -> None:
    """A retry after public release must not treat the tag as disposable cleanup."""
    script = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")

    assert "release_was_public_before_run" in script
    assert "release_public=already_published" in script
    assert "already exists and is public; refusing to reuse it" not in script


def test_release_retargets_a_stale_draft_to_the_current_source() -> None:
    """Старый черновик не должен прикрепить выпуск к прошлой подготовке."""
    script = (ROOT / "scripts" / "release.sh").read_text(encoding="utf-8")

    assert 'gh release view "$tag" --json isDraft,targetCommitish' in script
    assert 'release_draft=retargeted tag=%s from=%s to=%s' in script
    assert 'gh release edit "$tag" --draft --title' in script
    assert 'release_public=already_published' in script


def test_remote_deploy_retries_git_fetch_before_failing() -> None:
    """Обрыв SSH/GitHub на удалённом fetch не должен отменять всю выкладку."""
    script = (ROOT / "infra/scripts/cd-remote.sh").read_text(encoding="utf-8")

    assert "fetch_remote_origin_retry() {" in script
    assert "deploy_remote_fetch_attempts=" in script
    assert "remote git fetch attempt" in script
    assert "remote git fetch failed after 5 attempts" in script


def test_validator_prints_the_real_reason(tmp_path: Path) -> None:
    """Общая фраза бесполезна: оператору нужна причина.

    Обработчик ошибок печатал только «current complete GitHub proof could not
    be verified», скрывая и отсутствующее доказательство, и сетевой сбой, и
    расхождение поезда с диапазоном выпуска.
    """
    result = subprocess.run(
        [
            "python3",
            "scripts/validate-pr-checks.py",
            "--repository",
            "not-a-repo",
            "--source-sha",
            "a" * 40,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0, result.stdout + result.stderr
    assert "could not be verified" in result.stderr, result.stderr
    assert "reason:" in result.stderr, result.stderr
    assert "invalid release source" in result.stderr, result.stderr
