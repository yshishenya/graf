# Независимая проверка кода интеграции F096

Дата: 16.10.2026. Задача: T109 / issue #7472, восстановление совместимости draft PR #7477 с текущим master. Режим проверки: active Spec Kit / high-risk-product. Применён навык `code-reviewer`.

**Вердикт: PASS для просмотренного локального кода; подтверждённых замечаний P0–P3 нет.** Первоначальная ошибка подготовки браузерной проверки устранена успешным отдельным запуском с готовыми зависимостями. Этот отчёт не разрешает коммит, выпуск, включение провайдера или запуск кампании.

## Точная область

Проверен итоговый `git diff HEAD`, включая staged/unstaged изменения и новую неотслеживаемую миграцию `0105_merge_analytics_sharing.py`, в `/Users/yshishenya/.codex/worktrees/analytics-recovery/crisp`:

- база / HEAD `d567a7dc51b0c4d99b22660d27950316ae609a66`;
- исходный draft `a2bfee6b5ecb4e855cc96e9cc983195ff34adac8`, общий предок исходного PR `f3ec4dd95c3aa68fc7246338bd7c58908d24aee2`;
- API, explicit funnel, browser context и consent JS/template, PostHog wrapper, readiness/delivery gates, settings/Compose/example, macOS client/reporter/bridge и вызовы, миграции, изменённые server/Swift tests;
- текущие auth/CSRF, user identity/RLS context, account merge и требования FR-030–034a прочитаны как окружающий код и контракт.

Проверено сохранение новых частей master при переносе исходного PR. Из файлов исходного изменения различаются ожидаемые объединённые места: `TwoBrainRecApp.swift`, `EmbeddedCabinetWebView.swift`, cabinet `base.html`, Compose и два теста ожидания вершины миграций. Дополнительное интеграционное изменение — пустая merge-миграция и расширение существующего теста обновления. Удаления новых защитных проверок master в просмотренном diff не обнаружены.

Контрольный SHA-256 28 изменённых файлов под `apps/` и `infra/`, включая новую merge-миграцию: `16e0d1fb9afc8fc65bb143893453d3aca423695c4add9cadcffd98049194034c`. Порядок вычисления: сортированные пути; для каждого UTF-8 path + NUL + текущие bytes + NUL. Это привязка к незакоммиченному снимку, а не замена точного Git SHA/CI. Последующие изменения требуют оценки применимости отчёта.

## Проверенные свойства

- Alembic имеет ровно одну упакованную вершину `0105_merge_analytics_sharing`, её родители — `0102_explicit_analytics_consent` и `0104_summary_share_scope_cascade`. Новая миграция не выполняет операций и не переписывает прежние ревизии. Analytics добавляет только nullable JSON без default/backfill. Переход с каждой существующей ветки применяет недостающую соседнюю ветку, сохраняя sharing.
- Существующий migration test расширен параметрами 0037/0104/0102 и сохраняет прежние проверки схемы, функций/ограничений и новых таблиц. Дополнительно проверяет JSON/nullable/no-default, прежнего синтетического пользователя с NULL consent и наличие sharing-таблиц. Проверки таблиц не подменяют отдельный сквозной пользовательский сценарий sharing.
- API получает действующего пользователя из principal, tenant context и запроса по user/organization/status. Cookie-изменения используют существующий CSRF; UI связывает действие с показанным пользователем и текущей версией. GET не выдаёт принятие согласия; записи согласия не создаются при миграции, загрузке страницы или восстановлении cookies.
- Consent/event сериализуются блокировкой одной строки пользователя. Отзыв сохраняется при выключенной готовности/старой версии; принятие требует текущую готовую версию. Недоступный провайдер не создаёт durable receipt. Неопределённая доставка/откат транзакции могут повторить стабильный UUID; фактическая дедупликация PostHog остаётся отдельным доказательством.
- Explicit events проверяют серверный пользовательский псевдоним, закрытый каталог событий и значений, отвергают вложенную identity и произвольный контент. Account-connected создаётся сервером. Provider acceptance и ingestion отражаются раздельно; HTTP 200 без допустимого provider receipt не засчитывается.
- Native reporter получает identity/consent с собственного сервера, сбрасывает контекст при auth-change и перед изменением согласия. Поздний refresh ограничен generation; сигнал bridge не предоставляет согласие. Native отправка остаётся через GRAF, свободные campaign/bridge поля удаляются, категории помечаются weak/unknown. Ни native-сборка, ни ручная проверка приложения рецензентом не выполнялись.
- Новые settings/Compose сохраняют explicit mode=false, backup policy=required. Узкое `owner_accepted_loss` не включает провайдер и не снимает access/legal/retention/approval gates. Общая готовность кампании остаётся false, исходные отсутствующие backup/restore proofs не превращаются в успешные. Generic capture без корректного server-derived explicit UUID блокируется до чтения ключа/transport в этом режиме.
- Existing public/anonymous measurement, sharing, billing и provider routes не получают нового разрешения из интеграционного переноса. В explicit mode прежний claim-based ingest и broad web/desktop capture закрываются. Доказательств регрессии окружающего master в просмотренном коде не найдено; это ограниченная проверка изменения, а не переаттестация всех подсистем.

## Проверки и их происхождение

Независимо выполнено рецензентом в существующем временном окружении, без cacheprovider и с `PYTHONDONTWRITEBYTECODE=1`:

```text
PYTHONPATH=src /tmp/graf-f096-recovery-venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/unit/test_explicit_product_funnel.py \
  tests/unit/test_product_analytics_provider_delivery_gate.py
55 passed, 2 warnings in 0.46s
```

Предупреждения: существующие PytestAssertRewriteWarning для plugin fixture и StarletteDeprecationWarning о httpx. Сеть к провайдеру, рабочая БД, credentials и native приложение не использовались. Независимо прочитан граф через Alembic ScriptDirectory: одна вершина и точные два родителя подтверждены. `git diff HEAD --check` завершился успешно.

Отдельно прочитан полный журнал запуска исполнителя `/tmp/graf-f096-recovery-tests.log`: **96 passed / 1 error / 2 warnings**. Все три обновления 0037/0104/0102, clean migration path, downgrade, cookie CSRF/render-bound identity и серверные explicit integration tests прошли. Первоначальная ошибка setup `test_real_notice_cookie_auth_consent_and_postgres`: `Browser proof requires npm ci in tests/browser and playwright install chromium`. Это отсутствие обязательной зависимости, а не установленный дефект кода. Исходный неуспешный результат сохранён как факт, не переписан в успешный.

После подключения готовых Playwright/Chromium исполнитель повторил целевую проверку. Рецензент прочитал итоговые журналы:

- `/tmp/graf-f096-recovery-browser.log`: **2 passed, 0 skipped**, включая реальный vendored notice, current FastAPI, cookie auth/CSRF и временный PostgreSQL; успешное удаление изолированного контейнера подтверждено журналом.
- `/tmp/graf-f096-recovery-regressions.log`: **48 passed**, старые PostHog/activation/contract/readiness проверки; изолированный контейнер удалён.
- `/tmp/graf-f096-recovery-swift.log`: **30 ProductActivationAnalyticsContractTests passed, 0 failures**; это целевые Swift tests, а не ручная проверка установленного приложения.

Первоначальный browser blocker этим повторным запуском закрыт. Рецензент не повторял эти наборы и не выдаёт журналы исполнителя за собственное исполнение. Числа наборов не складываются в количество уникальных тестов: между ними есть пересечения.

## Пределы и следующие условия

До принятия реализации требуется выполнить converge/остальные выбранные проверки. Коммит и изменение remote PR требуют отдельного явного разрешения владельца после проверки. Старые CI PR #7477 и прошлые approvals не являются доказательствами этого нового снимка; обязательны checks точного нового SHA и проверенной базы.

Нужны отдельные реальные изолированные PostHog/ClickHouse ingestion/readback/dedupe, подтверждение no-IP и 365 дней, поддерживаемого доступа/MFA/legal и условия одобренного выпуска. Синтетические provider fixtures доказывают только контракт программы. T109 остаётся открытой до полного результата. Производственные флаги, ключи, доступы, история и данные рецензентом не менялись.

Рецензент изменил только этот отчёт; после записи перечитал его. Код, список требований, планы/задачи, управление проектом, GitHub и коммиты не изменены, работа других участников сохранена.
