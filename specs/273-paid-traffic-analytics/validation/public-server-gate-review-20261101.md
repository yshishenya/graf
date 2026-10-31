# Независимое before-code ревью серверного public gate F273/T106

Дата:01.11.2026. Проверяющий:`/root/public_counter_readiness_review`.
Копия:`/Users/yshishenya/.codex/worktrees/growth-protocol-result/crisp`.
Ветка:`codex/f273-public-gate-20261101`.
Основа:`e8a67a7e21046a641b2bdd0f1caf75aca7895e6f`.
Lane:active Spec Kit slice, privacy/server.

## Решение

**PASS узких требований и минимального плана server context/relay/delivery.
Checklist:5 `[x]` /0 `[ ]`. Blockers/P1/P2/HIGH0.**
Это не PASS кода и не разрешение включить внешний счётчик. Прежний отчёт
public-counter-t106-gate-20261031.md остаётся действительным: external SDK,
старые вкладки, индивидуальный серверный отзыв и весь T106 не приняты.
Изменение рабочих flags/revision, actual provider отправки/readback и T0
не входят. Отдельная feature/таблица/endpoint/кэш не требуется.

## Матрица требований

| Пункт | Итог | Основание |
| --- | --- | --- |
| CHK001 | PASS | Новые spec/plan sections задают старые public flag/env/revision/surface независимо от product provider scope. Существующие public константы и builder определяют этот scope; product yandex_all_pages не подставляется. Context сохраняет прочие прежние настройки, включая counter ID/replay/external surface policy. |
| CHK002 | PASS | Нынешний reader возвращает available=false для missing/OSError/UnicodeError, а file_errors для ошибочного формата. План явно запрещает оба unknown/error случая, принимает только валидный читаемый register без ошибок. Начальное пустое состояние должно быть валидным файлом. Withdrawal только provider_analytics закрывает public уровень3; другой уровень не превращается в общий отказ. Нового хранения/кэша нет. |
| CHK003 | PASS | Одна функция текущего решения в public/analytics.py вызывается для context, после route normalization по page_path и в worker delivery перед созданием прежнего клиента. Существующие flag/revision/same-origin/size/consent/catalog guards сохраняются. PostHog final gate остаётся независимым дополнительным запретом перед transport. |
| CHK004 | PASS | RED/GREEN использует настоящие context/route/delivery и меняющийся temporary register в одном процессе; подмена gate запрещена. Проверяются empty valid/other level/provider withdrawal/missing/malformed/unreadable и false flag/env/revision/private path, изменение register между POST и worker. Подменяется лишь transport/request body. Регрессия включает lifecycle/provider gate и browser harness. |
| CHK005 | PASS | Spec/plan/tasks/quickstart явно оставляют external включение, SDK/старые вкладки/индивидуальный серверный отзыв/T0/полный T106 открытыми. Рабочие flags/revision сохраняются; before-code analyze/sync existing #7696, code review/converge/exact PR checks следуют отдельно. Full только на согласованном готовом кандидате. |

## Почему план достаточен для этого среза

Текущий reader можно использовать без изменения его общей legacy semantics:
public функция должна проверять одновременно available и file_errors перед
withdrawal(provider_analytics). Нельзя использовать лишь отсутствие
withdrawal как разрешение, потому что missing/unreadable возвращают пустой
набор. Нельзя отдавать register.as_dict наружу: он содержит state_path и
записи; достаточно стабильного безопасного кода причины либо None.

Текущее public окружение production/staging или render_only/provider_smoke
должно сохраниться. Shared server decision не отменяет существующую проверку
counter ID в builder и narrower external/replay scope. Категории посетителя
и normalizer остаются отдельным обязательным условием. Другой уровень
реестра не расширяет public scope и не снимает старый product provider gate.

Текущий route проверяет ранние flags/revision, origin/size и normalizer, затем
вызывает delivery через to_thread. Новая самостоятельная проверка после
normalizer защищает именно принятый page_path. Delivery обязан перечитать
реестр в своём потоке, а не получить сохранённое положительное решение из
route. PostHog capture_event уже повторяет resolve_provider_delivery_gate
перед отправкой; это сохраняет дополнительную защиту при изменении основания
после первоначального разрешения. Нельзя заменять её общей public функцией.

Узкий срез не решает все окна runtime settings и прямого внешнего SDK.
Именно поэтому external остаётся закрытым, а callback/storage/BFCache,
индивидуальная серверная фиксация отзыва и настоящий SDK stop не объявляются
выполненными. Разделение соответствует ранее собственному HOLD отчёту,
а не ослабляет его. Для выбранного объёма новая инфраструктура не нужна.

## Прочитанные факты и пределы

Прочитаны новые T106 sections spec/plan/tasks/quickstart и все5 checklist
пунктов; собственный прежний report — решение, установленные public/relay/
reader факты, минимальный объём, критерии и пределы acceptance. Большие
выводы были усечены, поэтому нужные актуальные функции отдельно перечитаны:
build_public_analytics_context, deliver_public_analytics_event,
public_analytics_event, BasisWithdrawalRegister/read_basis_withdrawal_register,
resolve_provider_delivery_gate и capture_event до final gate/secret read.
Они подтверждают необходимость server среза и возможность reuse.

Active .specify/feature.json подтверждает F273/T106, branch/source/owned paths.
Scoped исключение владельца F273 применено к повторному чтению неизменных
базовых документов: constitution/PRD/status/product-gates hashes совпали с
собственным прежним чтением. Operations, activation-milestones и прежний
public analytics contract также сверены: hashes совпадают с собственным
отчётом31.10. Это не новое полное чтение неизменных документов. Реальный
код public analytics/web и lifecycle/provider_gate тоже совпал по hashes
с прежним собственным review, а затронутые функции перечитаны непосредственно.

Тесты/сеть/Git/GitHub/CI/runtime/release не запускались. До review уже
изменены четыре документа, присутствуют новый checklist и старый untracked
report; они сохранены. Изменены только новый checklist и этот отчёт.
Проверяющий не отмечал существующий общий T106 выполненным и не менял
четыре общих checklist F273. После записи новый checklist перечитан:5/0.
Analyze и sync existing issue#7696 следуют перед кодом; GitHub не проверялся.

## Контрольные суммы before-code состояния

- spec:`8b57f28a03b7fafedcf35eafa1ebf40303a33cfd92bf47c2764d2e6b78614236`.
- plan:`f62f5d3fc5e2f38ea66430f849996e9a87401945a2490a59a2bf76c64242b4f2`.
- tasks:`bbaefe5658b612147d76879fd23a046c6d9f9377b58598e1dce2853bf0d0f9cb`.
- quickstart:`3d0007c4e45f543f8213a79ce5a3698882ed53fddf13fb624b8aad0f3206d435`.
- public analytics:`862c8163bf06545536ff8493f817c7feb7be2e286e63dea708b1d87494a7e480`.
- public web:`33f7a2b294f60c5e2f77079295880a1e1511c5a183f7373fb328d437f64844e2`.
- lifecycle:`ac4eb465afb0c647b0d3501bdbeaca2a8a4b1d9c6cad59d4c9a9953cae5f81f9`.
- provider gate:`fbb2616e62802ee0050b0dd2bf220583bd6f4c9772c2a1d88a261c0bcdc04f9e`.
- constitution:`7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- PRD:`0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- status:`25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- product-gates:`9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.


## Независимое implementation review / scoped converge — 01.11.2026

**PASS узкого server среза; открытых P1/P2/HIGH0.** Checklist повторно
целиком прочитан: **5 `[x]` /0 `[ ]`**. Точный исходный HEAD остаётся
e8a67a7e21046a641b2bdd0f1caf75aca7895e6f плюс проверенные рабочие изменения.
Это локальная приёмка нового кода, не exact-SHA PR/release/runtime приёмка.

### Фактический код и границы решения

Прочитаны весь фактический diff public analytics/web, opt-in fixture,
CLI synthetic config и всех затронутых тестов. public_analytics_blocker
проверяет прежние public flag, exact revision, env/validation и surface;
затем заново вызывает existing reader без кэша. !available/file_errors
возвращают безопасный public_basis_unavailable; withdrawal ровно
provider_analytics — public_basis_withdrawn. Raw register/state_path/IP/
visitor данные не возвращаются. Валидный пустой файл и отзыв другого
уровня не блокируют эту функцию при пригодной прежней public настройке.

Builder сохраняет counter_id условие и прежние narrower external/replay
scope, а общий blocker теперь сужает configured/enabled/consent_ui.
Route сохранил flag/revision/origin/size/consent/catalog/normalizer guards;
новый blocker использует normalized event.page_path после normalizer.
Delivery заново вычисляет blocker перед созданием клиента и при отказе
возвращает delivered=false. Положительного сохранённого разрешения,
endpoint/хранилища/таблицы/нового транспорта нет.

PostHogClientWrapper и provider_delivery_gate не изменены; hashes совпали
с before-code состоянием. Их собственный final provider gate сохранён
в capture_event. Новый public blocker не назначает другой product scope
и не отменяет approvals/readiness/согласия конечного получателя. Изменение
runtime flags, consent revision, browser SDK/JS в diff отсутствует.

### Настоящая route→worker гонка и профиль

Новый contract test исполняет настоящий FastAPI route, normalizer и
настоящую deliver_public_analytics_event. Он меняет реальный temporary
register перед вызовами и внутри обёртки asyncio.to_thread перед запуском
настоящего worker function. После route admission отзыв даёт HTTP202 с
delivered=false, счётчик capture вызовов не растёт. Это доказывает повторное
server решение в worker; подмены самого blocker/reader/delivery нет.

Граница провайдера в этом test изолирована через замену from_settings на
учебный Client. Поэтому race test сам по себе не доказывает исполнение
настоящего PostHog final gate или настоящую внешнюю доставку. Он доказывает,
что реальная public delivery откажет ещё до создания/использования такого
клиента. Сохранность настоящего final gate подтверждена чтением неизменного
кода и отдельными прежними lifecycle/provider/PostHog контрактами в профиле.
Это достаточная изоляция для принятого server среза; actual receiver/SDK
приёмкой она не объявляется.

Проверены context loops: valid empty → другой уровень → provider withdrawal
→ malformed → missing → восстановленный valid empty; значения четырёх
context flags и отсутствие state path. PermissionError создаётся на boundary
builtin open, не подменяет gate, и закрывает context. Route/direct delivery
проверяют withdrawal/malformed/missing, false public flag, stale revision,
неподходящее окружение и private path. Existing same-origin/consent/revision/
catalog checks остаются в тех же тестах с прежними assertions.

public_basis_register — обычная opt-in pytest fixture в существующем
conftest, не autouse; она пишет version1 header в tmp_path и monkeypatch
восстанавливает env. Module usefixtures добавлен только выбранным public
тестам; единичные тесты других public контрактов запрашивают её явно.
Первоначальный broad UTM отказ исправлен только добавлением этой
предпосылки, assertions не ослаблены. CLI public_analytics_config использует
TemporaryDirectory и patch.dict вокруг synthetic context, после вывода
очищает файл и восстанавливает окружение. Runtime register не создаётся.

### Прочитанные результаты и пределы

- RED:2failed/27deselected, прежний context enabled и relay202 после revoke.
- GREEN:2passed/27deselected.
- Первый broad focused:112passed/1failed/1skipped; причина UTM prerequisite
  и пропуск настоящего modal сохранены как исторические факты.
- Исправленный focused:30passed/0skips,13.19s; включает весь measurement
  contract, consent enforcement с actual modal и PostHog autocapture contract.
- Отдельный actual modal:1passed,3.23s. Node harness:PASS,0skips.
- Broad журнал подтверждает прежние public unit/landing/legal basis lifecycle/
  provider delivery/public contracts; repeated focused после fixture правки
  покрывает единственный прежний failure и целый обновлённый consent module.
- Оба PostgreSQL runner журнала показывают isolated_container_removed.
  Ruff/process/governance/diff PASS явно сообщены владельцем и записаны
  в validation; отдельных журналов этих команд здесь не было.

Журналы прочитаны; тесты/сеть/Git/GitHub/CI/server операции проверяющим
не запускались. Большие source/test diff выведены без усечения; RED summary
и broad header/failure/summary прочитаны адресно, а не утверждается полное
чтение каждого повторного traceback. Изменены только собственный отчёт
и checklist; прочие изменения сохранены.

### Converge

Все5 групп требований соответствуют выбранному коду/профилю; новых
непокрытых P1/P2/HIGH работ внутри этого server среза не найдено.
Узкий PASS позволяет двигаться к commit и exact PR gates после остальных
обязательных проверок. Общая T106/#7696 не закрывается. SDK/старые вкладки,
индивидуальный серверный отзыв, внешнее включение, runtime/T0 и коммерческие
критерии остаются прежними открытыми пунктами/HOLD. Этот review не разрешает
рабочие отправки и не объявляет HTTP202 подтверждённым внешним визитом.

Хеши принятого рабочего состояния:

- public analytics:`c789fa7ab77ee5090c0542fd422fadab175e50a618c8d7229e10c34416d3694d`.
- public web:`d61c93bb74ae6b0f1bd193844a093985b9d85f25b11e9b4e78e01d3cf9ec19a3`.
- unit test:`f5ea45b147432732f4e11c74c64ab07d444aa401c5b353b406fcb78f2b723b4b`.
- consent contract:`9bae7bab78dfa7d3b3b0fafc4d27948105dc96d5110c2b43872fc192e9efb102`.
- conftest:`0a8a2cb767b2f74e777fcb0c79616e68c65b0bf5a9ad5418838a4a0693389793`.
- CLI fixture:`07253a6f7dba5d917f837ee05c4e4467eacf0676b3df0191f8205465cdf4eb19`.
- provider gate unchanged:`fbb2616e62802ee0050b0dd2bf220583bd6f4c9772c2a1d88a261c0bcdc04f9e`.
- PostHog unchanged:`12b49bb9d0eda5731091faf50dcc8ef770d6e1c90bc1a542353d0e7174ca4e5f`.
- RED:`124caf68f25a299711a67e8440afcb8edb1dd18e6d0a8a6453b627f53e8a018e`.
- GREEN:`d49046edf2b07acfeca0022e8eb4c74f5d7014c2bab0547e90bfcbab4b4db5c1`.
- broad:`6dca5c1c7a0acf8e45c5bd71a6cf76a230a57a5110b4855a40073982b5702b44`.
- fixed:`ea16431328fb4c6144c61d673088a913195c70c03273fa109be4f0c13a4cd81e`.
- modal:`a87c05e04ea5d3ff9bbc8ac1d74a572f38081e0a9e7bd1f9cf979763c15874a6`.
- browser:`714796f7abd23dd1ae177de02253658f6692d7b99aa12821ec9976da026d2c4e`.
