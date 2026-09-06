# Анализ согласованности Feature 254

Дата: 2026-09-06. Объект: spec, normative UI/telemetry/acceptance, plan/research/data-model/contracts/tasks. База исследования приложения: `a389657e607ef8389fcf947b26b158cee6928884`. Анализ требований и технического плана, не аудит развёрнутой системы и не исполнение тестов.

## Метод и результат

Авторская проверка + два независимых исследовательских направления: `admin_access` — auth/RLS/egress/worker/UX; `diagnostics` — billing/promo/telemetry. Первый проход выявил 1 CRITICAL, 10 HIGH; все исправлены в документах. Повторное чтение обоих направлений не нашло новых CRITICAL/HIGH. Дополнительные неточности модели, метрик и согласованности полного UI также исправлены до передачи реализации.

| ID | Уровень первого прохода | Найденная проблема | Исправление |
|---|---|---|---|
| A01 | CRITICAL | Старая permissive PUBLIC RLS обходит новую system policy | Обязательная restrictive policy для system role на каждой доступной relation; fake request/worker/bootstrap context negative tests |
| A02 | HIGH | Worker должен читать запрещённые ему system tables | Узкие SECURITY DEFINER claim/continue/result helpers, restricted owner/EXECUTE, без credentials |
| A03 | HIGH | Нет основания продолжения после revoke | Durable effect-start/fence/allowed continuation на каждый target; principal lock сериализует revoke/start |
| A04 | HIGH | Recovery напрямую выдаёт полную session | Только version-bound enrolment challenge, полный вход после нового TOTP; последний assignment сохраняется |
| A05 | HIGH | Старые preauth переживают reset/revoke | auth/credential versions, invalidation всех challenges, consume под lock, key rotation/backup contract |
| A06 | HIGH | Нет отдельного content export / audio-only context | content.export endpoint и отдельные permissions, revision binding, context не даёт прав |
| A07 | HIGH | Cookie на общем origin доступна product backend/JS | Отдельный console origin/host-only cookie, no credentialed CORS, exact Origin/CSRF |
| B01 | HIGH | Release DB lock до network оставляет окно gift/send | Durable dispatching claim до unlock, same provider key, crash означает possible send, reconcile first |
| B02 | HIGH | Backfill проверен до остановки old writers | Writer barrier + final watermark catch-up, lag=0/counter/snapshot equality до включения |
| B03 | HIGH | Plan code 64 больше String(32) | Ограничение 3–32 без обрезания, новая ветка по имени не нужна |
| B04 | HIGH | Нет обязательной fair-use resolve команды | Superadmin-only non-grantable fair_use.manage, typed cleared/confirmed, version/idempotency, AC/T020/T022 |
| C01 | MEDIUM | Recovery поля не отражены в schema | recovery_pending и credential_version добавлены |
| C02 | MEDIUM | Helper owner не мог взять principal lock | Узкие column permissions на id/status/auth_version, без password hash |
| C03 | LOW | Второй bootstrap противоречил одноразовому init | Первый bootstrap, второй invite+activation |
| D01 | MEDIUM | Семидневный пересчёт пропускает W4/30-day cohort | Все открытые когорты до своего окна+7 дней, late correction на нужный bucket, тест 35/42 день |
| D02 | MEDIUM | M27 payments/unique payer может давать >100% | В обеих частях уникальный payer той же invoice cohort; число оплат отдельно, сохранены 72h/created-at anchor и gifts |
| E01 | MEDIUM | UI plan code дефис против regex underscore | Единые 3–32, первая строчная буква, затем буквы/цифры/underscore |
| E02 | HIGH | Полный UI settings шире security/API allowlist | Единый key-level набор; configured contacts/recipients, export ceilings, prospective diagnostics retention, bounded queue pause/resume |
| E03 | MEDIUM | Future schedule зависит от 12h browser session | Exact scheduled approval, актуальная роль/условия на запуске, revoke/security reset отменяет, natural expiry не отменяет |
| B05 | HIGH | Scheduled approval не закреплял временный grant | authorizing permission/grant ID/version/expiry; execute_at внутри срока, expiry/revoke/replacement отменяет, AC-022 |

Каждое исправление связано с задачами и проверками приёмки. Прежние статусы автономного пакета («нет фичи/плана») заменены регистрацией Feature 254 и ссылками на технические артефакты.

## Покрытие

90 уникальных FR, 12 SC, 12 US, 42 AC, 30 метрик, 39 implementation tasks. Каждое FR имеет AC и конкретные задачи помимо общей финальной T039; полная таблица — tasks.md. Каждая US имеет независимую проверку/ответственную тестовую задачу. Все задачи открыты. Ссылки GitHub — issues.md, T000 только umbrella.

Денежные и авторизационные проверки не заменены UI-тестами. PostgreSQL необходим для locking/RLS; старый пользовательский reprocess и grandfathеring обязательны. Нагрузка/настоящая доступность/macOS/offline остаются измеряемыми будущими проверками, не принятыми на словах.

## Конституция и границы

Нарушений конституции в итоговом дизайне не выявлено. Сохранены system-audio-first, локальные предпочтения записи/видимый Stop, серверные MediaScribe credentials, LiteLLM/Langfuse authority, retained GenerationCall/Langfuse/Temporal после удаления, metadata-only обычные события и evidence. Новых внешних получателей/обучения на встречах/произвольных команд нет.

Порядок declare effect/dispatch и обработка неизвестного платежа требуют реальных тестов при реализации: положительный вывод об описанном алгоритме не подтверждает будущий код.

## Процесс и проверки подготовки

Feature ID/umbrella зарезервированы штатным allocator до ветки/specs после устранения отсутствующей feature:254 метки. `setup-plan.sh`, `setup-tasks.sh`, prerequisites, обязательный clarify и сформированные checklist пройдены на уровне документов. Hooks YAML прочитан и корректно разобран. Автокоммиты отключены. Необязательный agent-context update не запускался: активный pointer установлен, корневой AGENTS остаётся стабильным.

`speckit-analyze` проведён чтением с выдачей находок; исправления выполнены отдельными изменениями артефактов в рамках поручения подготовить реализацию. Этот файл сохраняет отчёт после исправлений. Обязательный before_taskstoissues `speckit.github-issue-canon.ensure` выполнен без изменения правил репозитория. Результат after_taskstoissues validate и итоговые команды фиксируются ниже после завершения синхронизации.

Reviewer-owned checklist отмечается только отдельным ревьюером требований, не автором реализации; такой знак не закрывает будущую задачу или тест. Положительный анализ относится к текущим документам и не переносится на будущий diff без повторного review.

## Фактические результаты завершающих проверок

- `python3 specs/254-system-admin-console/validate_artifacts.py` — OK: 90 FR, 12 SC, 42 AC, 39 tasks; ссылки, отсутствие шаблонных пробелов, ацикличность зависимостей, покрытие требований и уникальная связь GitHub.
- `python3 scripts/check_spec_kit_governance.py` — OK: bootstrap integrity + GRAF invariants.
- `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` — правильный каталог `specs/254-system-admin-console`, все требуемые документы найдены. Скрипт отображает короткое имя, фактическая Git-ветка содержит префикс codex/.
- Обязательный `validate_issue_canon.py` — OK, проверены 300 открытых Spec Kit issues в пределах штатной выборки. Дополнительная точная проверка Feature 254: 40 open issues, T000–T039 без дублей, все обязательные секции в правильном порядке и метки соответствуют title.
- Таблицы Markdown — согласованное число колонок; локальные ссылки существуют. Все 39 задач реализации оставлены открытыми.
- Во время проверки штатной umbrella исправлены созданные allocator недочёты: area label и контекст T000. Другие фичи не изменялись. Однократно импорт проверяющего helper создал Python cache в каталоге extension; этот созданный текущей подготовкой cache удалён, frozen governance снова прошёл. Bootstrap/lock/AGENTS не менялись.

Выполнено независимое ревью требований с свидетельствами в пяти профильных checklist и acceptance §5; маркировка относится к документам. Тесты приложения, SQL migrations, нагрузка, браузер, macOS build/notarization и production-проверки в этой подготовке не запускались. Это следующий этап по tasks/quickstart, а не скрытые пропуски реализации.

Итог reviewer-owned состояния: security 6/6, billing 6/6, diagnostics 5/5, UX 5/5, infra 5/5 — 27/27; общий список acceptance §5 — 14/14. Все отметки и свидетельства внесены отдельными ревьюерами после повторного чтения исправлений. Открытых CRITICAL/HIGH/MEDIUM в проверенных разделах не осталось. Дополнительно выполнен whitespace check каждого нового файла через `git diff --no-index --check /dev/null <file>` — OK.
