# Контракт B019

`claim-feature.py --json` возвращает next_available и mode=github-checked только после полного чтения точных markers. `--offline --json` даёт offline-draft без сети. `--allocate --branch <N-slug> --slug <slug>` перепроверяет то же предложение под shared lock; stale N отклоняется без нового issue.

Начальный N = max(spec IDs текущего проекта)+1, при пустых specs — 1. Пока N занят refs/claims/GitHub, увеличить N. Никакого ограничения до 999 и автоматического переименования известных IDs.

Refs: полные heads/remotes; число только в последнем segment `NNN-slug`; codex/turn-diffs, codex/captures, graf-release и timestamp names не занимают последовательные IDs. Tags/internal refs не входят.

Оболочки используют этот JSON, не собственный max refs, если local allocator доступен и не выключен действующим skip-флагом.
