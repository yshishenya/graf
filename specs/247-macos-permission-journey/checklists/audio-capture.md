# Requirements review: audio-capture

Reviewer-owned, generated unchecked.

- [x] CHK001 FR-005/007 запрещают запрос до нажатия и capture из настройки?
- [x] CHK002 FR-005/006 определяют timeout, stale, revoke и защищенный restart?
- [x] CHK003 FR-008 сохраняет system-audio-first, три правила и 8-секундный ask?

## Независимая проверка требований — 2026-09-06

Reviewer: permission_design_review. Проверены spec.md, plan.md, research.md, data-model.md, contracts/permission-ui.md и quickstart.md. Все три пункта пройдены на уровне требований. FR-001/005/007 отделяют явный запрос от пассивной проверки и не возобновляют запись после настройки. FR-005/006 задают предел 8 секунд, единственный актуальный результат, повторную проверку после await, восстановление stale и protected-work guard. FR-008, Scope и Constitution Check плана сохраняют system-audio-first, три правила и восьмисекундный ask. Контракт дополнительно запрещает queued detector start во время sheet/request/probe.

Блокеров требований нет. В реализации проверить, что повторный запуск после таймаута не позволяет старому ответу перезаписать новый, а защита перезапуска учитывает незавершённую операцию проверки наряду с запросом. Отметки означают согласованность требований, а не доказательство работы реального ScreenCaptureKit или сохранности конкретной записи.
