# Контракт B019

`claim-feature.py --json` возвращает next_available и mode=github-checked только после полного чтения точных markers. `--offline --json` даёт offline-draft без сети. `--allocate --branch <N-slug> --slug <slug>` перепроверяет то же предложение под shared lock; stale N отклоняется без нового issue.

Начальный N = max(spec IDs текущего проекта минус явно согласованные
out_of_sequence_spec_ids)+1, при пустом множестве —1. Пока N занят любым
spec/ref/claim/GitHub, увеличить N. Исключение влияет только на начало,
никогда на занятость. Никакого ограничения999 и переименования известных IDs.
Политика читается из .specify/feature-numbering.json, отсутствие сохраняет
прежнее поведение; ошибка чтения/формата останавливает предложение/allocation.
Explicit claim (--feature-id) не выбирает начало последовательности и сохраняет
прежние проверки занятости, повтор/upgrade draft и запись claim/pointer.

Refs: полные heads/remotes; число только в последнем segment `NNN-slug`; codex/turn-diffs, codex/captures, graf-release и timestamp names не занимают последовательные IDs. Tags/internal refs не входят.

Оболочки используют этот JSON, не собственный max refs, если local allocator доступен и не выключен действующим skip-флагом.
