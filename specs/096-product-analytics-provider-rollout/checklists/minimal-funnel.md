# Независимая проверка требований минимальной воронки

- [x] CHK001 Текущий режим и замена исторического broad capture однозначны. [Spec §Уточнение режима 2026-10-03]
- [x] CHK002 Согласие конкретного пользователя отделено от operator approval, auth и client claim. [FR-030/031]
- [x] CHK003 Неизвестные/устаревшие/отозванные состояния fail-closed; policy copy неизменна. [FR-030; plan шаг1]
- [x] CHK004 Источник user identity аутентифицирован и смена аккаунта имеет сброс. [FR-031; plan шаг2; T106]
- [x] CHK005 HTTP receipt, ingestion и дедупликация различены; provider failure допускает повтор. [FR-032/033; quickstart текущего среза]
- [x] CHK006 NoIP/no-content/no-secret/no-autocapture/replay/direct egress границы проверяемы. [Spec §Уточнение режима; FR-033/034; acceptance]
- [x] CHK007 Retention365 и purge разделены; readiness proofs не фабрикуются. [FR-034; plan шаг4/блокеры выпуска]
- [x] CHK008 Изолированные тесты, default-off и release/access blockers явно записаны. [Spec acceptance; plan шаг5/блокеры выпуска; T109]

Отметки подтверждают качество требований текущего среза, а не реализацию, ingestion или production readiness. Независимый отчет: [minimal-funnel-review.md](../minimal-funnel-review.md).
