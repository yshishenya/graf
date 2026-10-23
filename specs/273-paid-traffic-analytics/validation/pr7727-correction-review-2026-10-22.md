# PR #7727 — независимое ревью двух исправлений T116/T118

Дата: 2026-10-22. **PASS проверенного локального исправления**.
Блокирующих дефектов в объявленном срезе не обнаружено.
Это не приёмка работающего T118, включения аналитики или production.

## Проверенные байты и границы

Рабочая копия `/Users/yshishenya/.codex/worktrees/f8bf/crisp`, ветка
`codex/273-external-monitor`, базовый HEAD
`aac22c63efd3d4d77bebc0cc6525a7514a71f549`.
Задание прочитано из
`.dev/growth/pr7727-correction-review-scope-2026-10-22.md`.

Проверен снимок `.dev/growth/pr7727-correction-snapshot-2026-10-22.json`,
SHA-256 `70e63f599e81a0d87ae77e411368b124f1f165ffcde4e9bfdd4229b0760a906f`.
Все **11/11** хешей исходников/тестов совпали до и после самостоятельных проб.
Просмотрены весь diff этих файлов и применимые consumers. Чужое изменение
security checklist не редактировалось и не включено в принадлежащий reviewer
срез. Reviewer записал только этот отчёт.

## Capacity: полнота входа, бюджет, защита и итог

Python consumer больше не приписывает `capacity_input_unverified` любому
`capacity_ready=false`. Полнота/свежесть исходного измерения проверяются
отдельно; pending/expired/невалидный бюджет сохраняет собственный blocker,
инцидент — собственный blocker. Если итог закрыт, а известной причины нет,
добавляется `capacity_not_ready`; такой вход не превращается в готовность.

Shell consumer также имеет отдельный `capacity_not_ready` при необъяснённом
закрытом результате. Понятные причины берутся из существующих state/причин
guard; причина неполноты не выводится из самого итога. Правило нового кода
присутствует в alert-rules с владельцем и сроком эскалации. Изменение не
переключает provider или incident latch.

Reviewer самостоятельно вызвал текущий
`test_complete_capacity_input_remains_independent_of_readiness` с временными
каталогами для healthy/budget/protection/input/unexplained. Проверены решения
Python и shell с `--dry-run`: **5/5 PASS**.

Негативный контроль исходного HEAD выполнен без checkout: источник модуля
загружен через `git show aac22c63…:apps/server/src/twobrain_rec_server/product_analytics/provider_readiness.py`
в отдельное имя Python-модуля. При полном входе и pending budget исходный
consumer даёт `(capacity_budget_unverified, capacity_input_unverified)`,
исправленный — только `(capacity_budget_unverified)`. Дефект воспроизведён,
блокировка бюджета сохранена.

## Restore: самодекларация не становится доказательством

В текущем срезе нет доверенного полного verifier T118. Поэтому реальный
Python collector явно возвращает `restore_consistent=False`, а shell
consumer не принимает самодекларированный файл за проверенное
восстановление. Нет нового доверительного флага, ослабления схемы или
привязки к произвольно выбранному последнему ежедневному backup.

Это намеренное закрытое состояние до реализации T118, а не заявление, что
согласованное восстановление реализовано. Настройки восстановления и
разрешения запуска не обходят его. Missing, failed, unknown/future/stale
время по-прежнему имеют самостоятельную диагностику; ошибка proof не
скрывает ошибку времени.

Reviewer самостоятельно проверил два receipt: только postgres/clickhouse и
все восемь разрешённых классов, с синтетическими pass и hex-digest. Взятые
через `git show` исходные Python и shell принимали такой proof без
`restore_verification_failed`; исправленные оба consumer отвергают его.
**2/2 исходных отрицательных контролей и исправленных сценариев PASS**.
Исходный shell исполнялся из временного файла только с `--dry-run` и
тестовым curl, без сети и реальной доставки.

Отдельно выполнены случаи missing receipt / неизвестное время / будущее /
возраст ровно30 суток: Python и shell сохраняют соответствующие
`restore_verification_missing` или `restore_verification_stale`; при
существующем файле дополнительно присутствует `restore_verification_failed`.
**4/4 PASS**. Все временные каталоги проб удалены штатным TemporaryDirectory.

## Тестовые подстановки и реальные consumers

`stub_verified_restore` меняет только поле типизированного evidence через
`dataclasses.replace` в процессе теста. Реальный collector остаётся
закрытым. Найдены ровно три явных вызова: один PostHog transport test,
один Яндекс offline transport test и один Яндекс page-policy test.
Автоматической общей fixture или runtime-импорта этого helper нет.
В page-policy test перед подстановкой дополнительно проверена блокировка
реального context. Это изоляция других правил, а не доказательство restore.

Реальные integration readiness, launch approvals и provider gate assertions
исправлены на ожидаемый отказ `analytics_operations_not_ready` при
самодекларированном proof. Они не используют подстановку. Права согласия,
страничный inventory и запреты результата transport остаются предметом
соответствующих тестов; новых событий, IP или передач срез не добавляет.

## Проверенные журналы исполнителя

- `pr7727-followup-alerts-final.log`: **129 passed**, 2 warnings, 47.90 s;
  SHA-256 `900de2250f03a7267e6cd911bbcf3f1613786e6954e19423710e867cd53a057e`.
- `pr7727-followup-provider.log`: **21 passed**, 2 warnings, 0.32 s;
  SHA-256 `a90c346f3803140ff5631a475bebe8ead2a09c58c59d782186ad07cc4d438ffd`.
- `pr7727-followup-consumers-final.log`: **47 passed**, 2 warnings, 0.95 s;
  SHA-256 `ed818af5b7d068a195d187923ac0fe243a5fe9f0797ead6a710b83a571c853d9`.

Пути выше находятся в `.dev/growth/`. Ранее
`pr7727-followup-focused.log` имел 2 failed/148 passed из-за прежних
положительных ожиданий integration readiness; это не успешное доказательство.
Текущий diff закрывает эти ожидания, а новый отдельный readiness-профиль
завершён21/21. Полный прогон этих наборов reviewer повторно не запускал;
самостоятельные пробы перечислены выше. Предупреждения относятся к fixture
rewrite и устаревающему httpx TestClient, тестовые ошибки финальных профилей
не скрыты.

## Контрольный список и оставшиеся ворота

Заново прочитаны все45 вопросов `privacy-measurement.md`: **45/0**.
Суммы остальных списков: requirements16/0, infra25/0, security25/0;
всего **111 отмечено / 0 не отмечено**. Отметки reviewer не менял:
исправлены нарушения уже действующих требований, а не их смысл.
Качество требований не равно рабочей приёмке.

`git diff --check` прошёл. Будущий commit/CI точного SHA, штатный выпуск,
реальная установка, доверенный полный T118 verifier и его операторские
доказательства остаются открытыми. Реальная аналитика не включена; трафик,
продажи и готовность остальных задач F273 этим PASS не подтверждены.
