# T039 — длительность заменённой записи

Reviewer-owned: независимая проверка требований до кода; только reviewer отмечает пункты.

- [x] CHK001 Подтверждённый дефект и FR-019/020/025 однозначно задают отдельную длительность ревизии, current projection и fallback None без изменения захвата/обработки/прав.
- [x] CHK002 Все callers и писатели проверены; минимальный общий fix сохраняет initial/accepted immutable, Meeting, статусы/транзакции, source validation и stale409; повреждённая accepted B не переписывается SQL.
- [x] CHK003 RED→GREEN покрывает24/90, POST/retry/finalize/normalization/200/206/409, abort/expiry, late transcript и legacy None; native/CI/release/cleanup отдельно и не объявлены пройденными.

## Независимая проверка 2026-11-17

Требования T039 PASS: 3 отмечены, 0 открыто; CRITICAL0/HIGH0. Проверены текущие документы и исходники, включая все9 производственных вызовов persist_meeting и единственную запись длительности существующей ревизии. Проверки реализации, Dev, CI и выпуска этим не подтверждаются. Подробные основания и суммы документов: [review-t039-requirements.md](../review-t039-requirements.md).
