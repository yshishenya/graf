# Проверка O14: обзор запросов удаления — 01.11.2026

Исходная F140/T077/#4932, high-risk-product/active Spec Kit slice. До кода:
семь согласованных оригиналов, собственное полное чтение с51 проверенным
исходным диапазоном/46call IDs, восстановленные целые применимые зависимости;
независимый checklist10/0, scoped analyze6requirements/1task/100%/0findings,
canon ensure/singleOPEN4932/validate243 PASS. Исторический пропуск до PR7884
не исправлен. Все87 исходных полных task lines/T077[ ] сохранены.

Реализация: один _deletion_inventory и одна SQL-агрегация state/count
MeetingDeletionRequest в прежнем monitoring.py, вызов из fair-use collector.
Root source fair_use_reviews,meeting_deletion_requests; nested deletion/source
meeting_deletion_requests. Четыре известных состояния и одна unknown группа,
без фильтра дня/времён и частных полей. Request count отдельно от fair-use.
Оба partial; artifact/deadline/jobs/reaction неизвестны. active_purge_complete
не доказывает фактическую очистку или срок, backup/local/MediaScribe/post-egress;
Generation Call/Langfuse/Temporal остаются по операторской политике.

Проверки из owned apps/server/.venv с PYTHONPATH=src:.; __file__ указывает
на эту owned копию. RED3ImportError и REDPG1 прежнего source сохранены.
Окончательный профиль:

- unit deletion_inventory или fair_use_inventory:6PASS,0FAIL/ERROR/SKIP,0.05с;
  3 новых случая и3 затронутых прежних.
- PostgreSQL/CLI deletion_inventory/fair_use_inventory плюс identity/SETROLE:
  9PASS,0FAIL/ERROR/SKIP,46.81с;3 новых и6 затронутых прежних.
- Всего15 уникальных финальных случаев,6 новых+9 затронутых. Два прежних
  warning,0SAWarning. Прежние независимые наборы не повторялись/не суммировались.

Настоящая PG17 мигрированная схема с ENABLE/FORCE RLS, NOT NULL/defaultrequested;
отдельная defensive NULL/unknown SQL VALUES без ослабления схемы; реальные CLI
и новый процесс, разные дни/два RR снимка/поздний commit, состояния/приоритеты,
future/infinity/NULL dates без чтения, приватные sentinels/no-write fingerprint,
safe schema failure, READ ONLY RR до первого hook, запрещённые роли/SET ROLE/
контекст/mutation подтверждены. Своё временное окружение удалено finally,
список контейнеров совпал с исходным; чужой31.10/Dev/AIRIS сохранены.

Внешний f140-t077-deletion-implementation-validation-20261101.json содержит
11 frozen inputs,4 пары XML/log с hashes, nodeids и историю. Final pytest
returncode0 наблюдался напрямую. RED shell tail не сохранял returncode pytest;
его исход подтверждён XML/log и не выдаётся за окончательный PASS.

Process/governance/context/fragments/Ruff/diff PASS. Независимый code review,
его сверка converge и GitHub exact SHA/base gates обязательны далее. Нет
Full/CD/релиза/Dev/рабочих данных; T077/#4932/полныйO6/T070/58gaps/сроки и
финансовые/приватностные/ручные/выпускные критерии остаются открытыми.
