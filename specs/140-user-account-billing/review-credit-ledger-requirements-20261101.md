# Независимое ревью требований T077/credit-ledger — 01.11.2026

Результат: PASS только по качеству требований C1–C6/O10.
Предметный checklist: 10 отмечены / 0 открыты. Блокирующих замечаний нет.
До кода остаются отдельные scoped analyze и синхронизация исходной issue.
Исполнитель /root/f140_notification_content_review, тот же дочерний диалог
01a1955c-cb77-78e3-8844-ffeabcb2d594. Область — только O10/C1–C6,
исходная T077/#4932, владелец repository-audit, high-risk-product.
Ветка codex/140-observation-credit-ledger, HEAD
458e874ddb40b3eb56dbc6535d84ef2e6bd2f8df.
Разрешена запись только этого отчёта и checklists/credit-ledger.md.

## Собственные полные чтения изменённых оригиналов

Записи относятся к текущему назначению в том же дочернем диалоге.
Усечённые совмещённые выводы не считаются полным чтением; ниже указаны
последующие неусечённые диапазоны оригиналов.

| Оригинал | SHA-256 | Полное собственное чтение |
| --- | --- | --- |
| spec.md | `2cf1269dce138f8aeea8ba3dfd5372df3fdf82f2682bcb335393ae7f143284dd` | Последовательные отдельные выводы sed1–125,126–250,251–350,351–435,436–560,561–710,711–848 из specs/140-user-account-billing/spec.md в текущем назначении; весь файл. |
| contracts/operator-observation.md | `166ad09e28b8fc4ee822f2d3e59b40925cfee1f685e7f86f30bd9b5025cc471b` | Отдельный полный cat1–299 в текущем назначении; O1–O10 полностью. |
| plan.md | `fbe8556b2f80853c10cb86261de035342743bbb8298bf45674af187dccd36469` | Два неусечённых отдельных вывода sed1–260 и261–520 в текущем назначении; весь файл. |
| tasks.md | `659e788fc6dd71d95330d81358a13cd3f07d09af27ee06df576b2bc9040d2535` | Два неусечённых отдельных вывода sed1–215 и216–428 в текущем назначении; весь файл. |
| quickstart.md | `2ee2f913f9640af1a8729d513d93b08f741c0029a42ebf82d5a4fdac8c8d2ee9` | Три неусечённых отдельных вывода sed1–220,221–460,461–732 в текущем назначении; весь файл. |
| research.md | `367ea8f385b7cbb64cc05e99433c832b4e5e8ea2bc96d53a277ac1a1a64d0f51` | Два неусечённых отдельных вывода sed1–210 и211–409 в текущем назначении; весь файл. |
| data-model.md | `386df316da75fdb96c2fa841c213b567cd5fa05bbc0112ae20d1fb1fb28e9e68` | Два неусечённых отдельных вывода sed1–210 и211–403 в текущем назначении; весь файл. |

Новая применимая зависимость: contracts/billing-lifecycle.md полностью прочитана отдельным cat в текущем назначении; SHA-256 `1d3e8fe3a672a34a4bc7a34bb6135800781d840e6e9350e0659bd142c5931ff7`. Применимы Authority hierarchy, Referral service time, External refund boundary и ограничения Subscription behavior/Renewal without grace: наблюдение не меняет authority, зрелость не равна eligibility, Free/hold допускают ожидание, нет баланса/долга. Источник — фактический вывод команды cat этого файла в журнале текущего диалога.

## Происхождение и восстановление контекста

Собственный журнал того же диалога:
`rollout-2026-11-01T07-27-29-01a1955c-cb77-78e3-8844-ffeabcb2d594.jsonl`.
Сверены фактические output-блоки, не только входные команды. Неусечённые
выводы совпали с оригиналами; в последних диапазонах некоторых файлов
следом находился только их SHA-256, поэтому проверялось полное совпадение
префикса до этой служебной строки.

| Оригинал | Проверенные строки журнала с выводами |
| --- | --- |
| spec.md | 5012,5019,5031,5036,5045,5050,5055; весь файл 1–848 |
| contracts/operator-observation.md | 5063, call_ae863b9c22ae484e8609f76de0a87644; полный оригинал 1–299 |
| plan.md | 5071,5076; весь файл 1–520 |
| tasks.md | 5084,5089; весь файл 1–428 |
| quickstart.md | 5097,5102,5109; весь файл 1–732 |
| research.md | 5119,5124; весь файл 1–409 |
| data-model.md | 5130,5154; весь файл 1–403 |

Усечённые выводы 5005/5024 и совмещённый вывод 5182 исключены из доказательства
полного чтения. После сжатия неизменный обязательный корпус сверялся с
собственными исходными receipts в
`review-free-projection-requirements-20261101.md`, разделах «Собственное чтение
оригиналов» и «Восстановление собственных исходных выводов после сжатия».
Это тот же исполнитель/диалог; прежнее O9-решение не используется как O10 PASS.
Все 12 исходных сумм неизменного корпуса совпали с зафиксированными там
значениями. Хеши не заменяют понимание требований: применимые оригиналы
повторно прочитаны по карте ниже.

## Карта применимости и разрешённых зависимостей

| Оригинал и повторно прочитанные целые разделы | Причина применения |
| --- | --- |
| Constitution I/II, III general boundary, IV/VI, Product And Platform Constraints, Development Workflow And Quality Gates, Governance (89–191/300–367/405–530) | Не менять capture/Stop, конфиденциальность, серверные полномочия; независимый reviewer, анализ до кода и отдельная приёмка. |
| PRD 1/1A,5/6,13/14,17,25/26,31,34,39 (1–150/349–374/688–844/1031–1101/1578–1777/2035–2072/2278–2326/2471–2474) | Общие обещания, диагностика без частного содержимого, tenant isolation, полнота наблюдения, отдельная приёмка и приоритет заменяющей спецификации. |
| current-product-status F272/F150/F140/F199 (179–217/451–470/529–622) | Исторические stop/runtime gates не возвращаются; maintenance/source и production acceptance разделены. |
| product-gates; README; document-reading; spec-kit-flow; development-process; tracker-policy — полные повторные чтения | Границы evidence, собственное чтение, независимые отметки, анализ/issue sync до реализации, Refs для частичной работы. |
| release-and-validation Validation Lanes, Development-To-Release Workflow1–2, Closeout/Full decision, Changelog/Legacy, Git/Evidence Safety (171–244/410–443/646–692/758–770) | Профильная проверка и три exact-SHA/base GitHub проверки; новый код не принимает старые результаты; отдельный выпуск, свой fragment. |
| operator-observation O1–O10; spec T077608–669; plan Technical Context83–109; tasks253–284; quickstart87–122; research354–378; data-model Promotions and referrals | Новый источник и временные признаки согласованы с неизменными guard/RLS/RR/пределами и полным остатком O6. Семь оригиналов полностью прочитаны выше; после сжатия восстановлены применимые разделы. |
| operations-reconciliation, registry-operator-import, security-privacy-compliance — полные повторные чтения | Scope магазина не переносится на database inventory; сохраняются owner/deadline, финансовые и приватностные сроки, запрет provider/money mutation и tenant расширения. |
| billing-lifecycle — новое полное чтение | Реальный смысл service credit, Free/security hold, отсутствие cash balance/debt; наблюдение не принимает financial eligibility. |
| F278 spec Requirements/Functional Requirements и единый учёт приёмки (158–203/295–302) | FR009/012/014/041 сохраняют неизвестные/поздние деньги, оплаченный срок после отзыва, три окна и реакцию≤24ч. |

Прямые зависимости разрешены этими чтениями. Исторические ссылки на выпуск,
merchant canary и macOS не требуют новых действий в этом назначении: здесь
нет приложения, сборки, миграции, платежа, почты или production. Исходный
пропуск контекста до PR7884 не исправляется задним числом.

## Решение по каждому пункту

| Пункт | Решение и основание |
| --- | --- |
| CHK001 | PASS. O10 C1/C2 задают точный time_credit_ledger_entries, database_inventory/current_state и все строки снимка независимо от report_date. Count не назван днями/наградами/пользователями/заданиями. Spec652–668, plan83–109, model Promotions and referrals и research354–378 согласованы. |
| CHK002 | PASS. C2 перечисляет pending/available/applied/expired/rejected/reversed, одну безопасную unrecognized для иных/NULL, непустые группы с сортировкой state и count=sum(groups.count). matured исключён по реальному helper, отрицательная reversal считается строкой. |
| CHK003 | PASS. C3 классифицирует только pending/available, сначала NULL/expiry≤maturity; затем валидные expiry≤as_of, maturity≤as_of<expiry и as_of<maturity. Эти условия попарно несовместимы и покрывают все валидные строки; задано равенство суммы четырёх количеств count. Quickstart2–3 требует равенства и ±1µs. |
| CHK004 | PASS. C3 явно разрешает будущие maturity/expiry и отделяет сохранённую дату от eligibility/сбоя/SLA. Billing-lifecycle Referral service time, FR067/101 и writers подтверждают законные security hold, Free/отсутствие пригодной оплаченной подписки. Специальное правило C3 уточняет общий future-invalid шаблон O3 только для нового семейства. |
| CHK005 | PASS. C3 задаёт floor неотрицательного max(as_of−maturity_at) только maturity_reached_unexpired и null при отсутствии; plan требует MIN допустимой maturity, не сумму возрастов. Терминальные/unknown/invalid/expired/waiting исключены. |
| CHK006 | PASS. C1/C4 всегда partial, четыре add-on/job поля null, приоритет unrecognized→invalid_schedule→jobs_uninstrumented. Успешная пустота явно count0/groups[]/четыре0/возрастnull; последнее reason сохраняется. Специальное C4 уточняет общий empty шаблон O3; ошибка доступа/БД/схемы отвергает весь отчёт. |
| CHK007 | PASS. C5 разрешает только state/maturity/expiry и агрегаты. Запрещены days/source_ref/IDs/связи/capacity/applied interval и финансовые функции. O1/O2/O5 сохраняют реальный maintenance guard, forced RLS, один UTC as_of/READ ONLY RR, 15s/5s/2s/500 gaps/64KiB и cleanup. Новых schema/полномочий/служб/зависимостей нет. |
| CHK008 | PASS как качество плана, не как выполненные тесты. C6 и quickstart87–122 требуют RED, настоящий CLI/guard/PostgreSQL/forced RLS, пустоту/шесть state/unknown/недействительные/будущие даты/reversal, exact boundary±1µs, два снимка/новый процесс, no-write/privacy/schema failure. Реальную NOT NULL схему запрещено ослаблять: INSERT NULL должен быть отвергнут, защитная SQL NULL-ветвь проверяется отдельно формой запроса. |
| CHK009 | PASS. Все семь документов согласованы с прочитанными моделью, migration0044, referral_rewards/referrals и maintenance: сохраняется rejected, matured только dataclass helper; reversal добавляет отрицательные days и меняет state исходной строки; matured_credits — применённые дни за проход. Мониторинг не вызывает эти writers и не выдаёт append-only требование за неизменность всех полей. 87 полных исходных task lines побайтно равны HEAD. |
| CHK010 | PASS. O6/O8/C6, spec608–668, plan и исходная T077 сохраняют O6/FR089, [ ]/#4932 и Refs; новый источник не принимает add-on/job metrics, тревоги, сроки или весь продукт. Все восемь старых checklist побайтно равны HEAD, 162 отмечены/58 открыты. F272/F199 gates не возвращаются, F278FR041 не отменяется. |

## Независимая сверка фактических предпосылок

Читались исходники, тесты/продуктовые команды не запускались.

- `apps/server/src/twobrain_rec_server/billing/referral_rewards.py`28–38:
  TimeCredit/mature_credit возвращает только вспомогательный matured.
  create_pending_credit59–135 пишет pending; mature_pending_credits138–233
  пишет expired/rejected/available/applied, сохраняет hold и ожидание собственной
  оплаты; total_applied складывает дни. Reverse238–337 меняет исходный state,
  для применённого credit создаёт days=-row.days и отдельную reversed строку.
- `billing/referrals.py`1–90: будущая maturity+14дней и expiry допустимы;
  risk review не самостоятельное автоматическое отрицание награды.
- `billing/maintenance.py`186–201/381–397 действительно вызывает
  mature_pending_credits и возвращает его значение matured_credits.
- `db/models/billing.py`318–338 и migration0044 строки289–300 подтверждают
  state/maturity/expiry и NOT NULL; ledger не имеет created_at.
  Поиск последующих миграций не нашёл ослабления этих дат.
- `billing/monitoring.py`44–49/197–236: generic _groups предполагает timestamp
  и считает будущее invalid; addon_and_time_credit пока not_connected.
  План правильно требует отдельную ограниченную агрегацию и новое RED,
  не повторное применение чуждой модели времени.

Суммы фактических входов совпали с source-research: referral_rewards
`11815fe057e520f8c298c6f9daf16b725b517e77757fd0c0cfcf38e135c8dfa1`,
referrals `d9033802d89c54b45d57e5cea85651449799912981e4901db80e31fb07d15a03`,
maintenance `342912bc2cf2d1aaad3f751c137ab21db31b2f023549c8082ce4d36242d12328`,
model `146c5c83debc274027de8e6630c7389a6a16c6ba018b48e446fd78b4f07f24bb`,
migration0044 `9e6f237ecb0d6ebd787014dc3b533b535a40fec94a9d49aee5a829ab9cc9cf1b`,
monitoring `b8caa43321df419cb63a3d2e065e6491caf677812f82a282b5ec0b35086afa6e`.

## Сохранённые открытые границы

Старые checklist не редактировались. Текущие результаты:
requirements17/8, operations10/8, security11/6, payments14/6,
launch-readiness32/8, post-plan-readiness25/15, product-market36/4, ux17/3
(отмечены/открыты). Просмотрены все 58 открытых исходных пунктов.
Для этого нового чтения применимы их authority/RLS/metadata-only требования,
реакция/owner/deadlines и отсутствие money/access mutation — они отдельно
заданы O1–O8/C5/C6. Их широкая продуктовая/финансовая/запускная приёмка
не выполнена; старые X4/X5/X6 требования с заменёнными stop/no-retry/Free
или тарифными решениями не восстанавливаются. Новый PASS не проставляет
ни одну из 58 старых отметок и не разрешает весь F140.

O6 сохраняет: transient15мин/24ч; fair-use≤24ч; receipt canceled немедленно,
pending escalation3дня; registry/F278FR041 реакция≤24ч. Неизмеренные
job attempts/errors/retries, остальные семейства, регулярность/heartbeat,
доставка тревог и сохраняемая реакция остаются в исходной T077 и у прежнего
владельца repository-audit. Сроки не перенесены.

## Граница допуска

CRITICAL0/HIGH0/MEDIUM0 содержательных замечаний в C1–C6; это независимое
ревью качества требований, не формальный scoped analyze и не кодовое ревью.
Основной исполнитель должен отдельно выполнить scoped analyze и issue sync,
затем RED/реализацию и реальные профильные проверки; после кода — независимое
review/converge и три точных SHA/base GitHub gates. Только Refs #4932.
T077 [ ], #4932 OPEN, O6/FR089 HIGH/partial и отдельные обязательные приёмки
сохраняются. GitHub live state здесь не запрашивался и не менялся.

Запись ограничена двумя разрешёнными документами этого назначения. pytest,
PostgreSQL/Docker/продуктовый CLI, приложение, commit/PR/merge, выпуск и
развёртывание не выполнялись.

Итоговое собственное перечитывание: полный checklist и отчёт1–105/106–конец
в отдельных неусечённых выводах текущего диалога. Прямой подсчёт: 10 отмечены,
0 открыты. Финальная сверка семи входных SHA-256: 7/7 совпали; 87 полных task
lines и восемь старых checklist повторно побайтно равны HEAD. `git diff
--check` и отдельная whitespace-проверка обоих новых документов через
`git diff --no-index --check /dev/null <file>` прошли: допустимы только0/1
при пустом stdout/stderr, код1 означает различие с пустым файлом, не ошибку
пробелов. Продуктовые тесты не запускались.
