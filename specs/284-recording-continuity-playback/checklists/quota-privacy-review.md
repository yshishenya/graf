# Независимая проверка квоты и приватности F284 — T017/T018

Дата: 2026-10-04. Проверяющий: отдельный агент quota_privacy_requirements_review.
Риск: high-risk-product, действующий срез F284. HEAD при первом проходе:
`af6e73eb395158f22aa1f119c913a3a0f313ccb0`. Проверено текущее рабочее дерево,
документы T017/T018 ещё не зафиксированы.

## Первый проход требований

Результат: **BLOCK, CRITICAL 0 · HIGH 1 · MEDIUM 0** по согласованности
требований. Переоткрыты requirements CHK002 и safety CHK005; остальные
отметки подтверждены в пределах проверки требований. Реализация, тесты,
GRAF Dev, CI, слияние и выпуск этим отчётом не принимаются.

### H001 — прежний shared billing договор противоречит уточнению FR006

FR006 теперь требует обращения к владельцу без ссылки на оплату для общей
встречи. T018 и новый раздел плана повторяют это точно. Однако прежние
абзацы Clarifications в spec, Project Structure в plan и contracts всё ещё
разрешают /billing с shared access. SC004 и сценарий US2.1 требуют переход
к управлению хранилищем без разделения ролей. Первая серверная строка
contracts также обещает billing/storage link без ограничения собственной
встречей. Поэтому согласованная приёмка own/shared пока не определена.

Нужно привести эти описания к одному правилу: объяснение квоты в обоих
случаях; существующий /billing только для собственной встречи; общая встреча
показывает обращение к владельцу без /billing. Исправление документов —
ответственность исполнителя; reviewer их не менял. После этого требуется
повторное чтение, а не автоматическое восстановление отметок.

## Основания остальных пунктов

Прочитаны AGENTS.md; guidance README/spec-kit-flow/product-gates; constitution
7.1.0 (особенно I/II/VI и независимые ворота); применимые разделы PRD/current
status по системному звуку, Pause и диагностике; активные spec/plan/tasks/
quickstart/contracts/analysis и все шесть reviewer-owned списков F284 вместе
с существующими отчётами в checklists. Активный путь подтверждён feature.json
и check-prerequisites --json --paths-only.

| Чеклист / пункты | Конкретное доказательство | Вывод |
|---|---|---|
| requirements CHK001, CHK003–005 | US1/US2; FR004/005/007/009; SC001–005; ограничения тарифов/старого звука; план T011 и quickstart7 | Независимые цели и границы, права/удаление/согласие, ограниченная обработка и обязательный физический контроль заданы. CHK002 открыт по H001. |
| safety CHK001–004 | FR001–005/007; SC001–003; complete/partial контракт и T010; FR013/SC009 | 45min, 15s/600s, источник истины, дочерние процессы, ручные запреты и routeUUID/open-only/access/hash ограничения определены. |
| safety CHK006 | FR005; native button контракт; существующий GRAF player | Русская доступная кнопка и существующий проигрыватель заданы; новых сторонних ресурсов нет. Это оценка требования, не проверка доступности приложения. |
| safety CHK007 | FR008; product-gates Audio/Artifacts/Diagnostics; T017; текущий validation.md; текстовые и JSON-доказательства F284 | В рабочем validation.md домашний путь заменён нейтральным обозначением существующих Playwright modules. Версия, команды, результаты Chromium/WebKit и исторические ограничения сохранены. Скан текущих .md/.json F284 не нашёл домашних/живых временных путей; JSON описывают метаданные и счётчики, не сырое аудио. Старый HEAD этим исправлением не переписан; отсутствие пути относится к предлагаемому текущему содержимому, не к историческому Git. |
| safety CHK008–012 | plan Validation/Release Gate/T011; quickstart1/5/7; FR009/SC005; T011 уточнение | Эмуляция и аппаратный контроль отделены от SHA/CI/выпуска. Ограничения одной порции/128 live work/конечного stop сохраняются; только относительная диагностика; явное разрешение контрольного Telemost в единственном Dev и запрет обхода Apple сохранены. |
| pr-followup CHK001–005 | FR010/011; SC006/007; plan T012/T013; quickstart8–10 | Заглушение очереди, конечная граница или явный отказ resume, неизменность PTS/system/Stop, исходный meetingId и stale success/403/404/network/body, Chromium/WebKit и новые Dev/CI/review ворота заданы. |
| producer-boundary CHK001–005 | FR012/SC008; plan T014; contracts FR012; quickstart11 | Одна атомарная FIFO граница snapshot/state/append/read, forwarding, порядок wrapper→base, конечный callback без reentrancy, отказ при недоказанной границе и обе стороны гонки сформулированы. |
| registry-lifecycle CHK001–004 | FR013/SC009; plan T015; contracts FR013; quickstart12 | Один advance сохраняет ended15s без registry, исключает новые предложения/телеметрию; complete/partial, manual/deferred Stop/600s и актуальная отдельная Dev-проверка заданы. |
| prompt-recovery CHK001–005 | FR014/SC010; plan T016 и observer ordering; contracts/quickstart13 | Retry относится только к ожидающему prompt, accepted/Skip/Stop остаются окончательными; существующие2s/8s и nil registry сохранены. Оба порядка auth observers и generic terminal через authEpoch/presenter.invalidate включены в требования. |

Reviewer не запускал тесты, приложение, сборку, GitHub или релизные действия.
Существующая регрессия quota и общий _render_playback прочитаны лишь для
проверки локализации: прежний helper скрывает весь storage_action у shared;
прежний тест проверяет отсутствие ссылки, но не owner guidance у shared.
Это соответствует необходимости T018 и не является приёмкой её будущего кода.

## Счётчики после перечтения

- pr-followup.md: checked 5, unchecked 0.
- producer-boundary.md: checked 5, unchecked 0.
- prompt-recovery.md: checked 5, unchecked 0.
- registry-lifecycle.md: checked 4, unchecked 0.
- requirements.md: checked 4, unchecked 1.
- safety.md: checked 11, unchecked 1.

Итого: **checked 34 / unchecked 2**. Блокер H001 открывает два связанных
пункта. CHK007 имеет подтверждение текущей документационной правки T017,
но завершение этой задачи и публичное состояние исторического Git не заявляются.

## Отпечатки документов первого прохода

- spec.md: `02bec6b3704a8614bc9a6a04dd4d7368b91f4d2629acc93a41b474f6c13f2f5a`.
- plan.md: `7772e352db2093f0fb722af99f967428c50d7d8d9dc0627b2daf9e647bd7515a`.
- tasks.md: `bf3311a3b84c165b1b84258e423fcf66e4687649b977c695f7536ff27639b4a5`.
- quickstart.md: `e55f8adbc386fae80d8108be61b5e1bc7d45fb4caf7245245871c41fa567ad6f`.
- contracts/recording-and-playback.md: `872e84545d74e8a0f1cb15940b903ed211f878dc2b45d9d70c080b373e594d33`.
- validation.md: `9257641e635a5f29f33bc0b3d7c0a2fb0e6864523d04dd4ef040bfb600d0d2ed`.

## Повторное чтение согласованных документов

Spec US2.1/FR006/SC004/Clarifications, plan и обе строки contracts теперь
согласованы: собственная встреча имеет существующий /billing, общая —
owner-contact без оплаты. Общий поиск активных проектных источников выявил
оставшийся прежний абзац research.md:18 с /billing overview (shared access).
Research входит в обязательное чтение перед implementation по spec-kit-flow.
До его согласования H001 и две открытые отметки сохранены; текущий итог
checked34/unchecked2. Остальные чеклисты перечитаны; новых пробелов не найдено.
Скан текущих .md/.json по домашним/живым временным путям снова дал0 файлов.
Продуктовый rendering.py ещё без изменений; реализация не принималась.

## Окончательное повторное ревью требований — PASS

После исправления research.md выполнено повторное чтение всех шести
reviewer-owned чеклистов и изменённых проектных источников. H001 устранён:
US2.1/FR006/SC004/Clarifications в spec, plan, contracts и research имеют
один договор own/shared. Существующий /billing доступен в собственной
встрече; получатель общей встречи видит обращение к владельцу без ссылки
на оплату. Новые права, покупка, квота или восстановление не вводятся.
Quickstart14 и T018 требуют red/green в существующем контракте для embedded/
web и own/shared, проверку производственных callers, Dev и независимое ревью.
T017/T018 имеют локальные ссылки на issues7522/7523; внешнее состояние
GitHub reviewer не проверял и не менял.

Текущий результат качества требований: **PASS, CRITICAL 0 · HIGH 0 ·
MEDIUM 0**. Восстановлены только requirements CHK002 и safety CHK005.
CHK007 подтверждён текущим нейтральным validation и повторным сканом
доказательств; исторический HEAD и прежние результаты остаются историей.
Предыдущие BLOCK разделы отчёта сохранены как последовательность проверки,
они не являются текущим результатом.

После изменений чеклисты перечитаны целиком и пересчитаны:

- pr-followup.md: checked5 / unchecked0.
- producer-boundary.md: checked5 / unchecked0.
- prompt-recovery.md: checked5 / unchecked0.
- registry-lifecycle.md: checked4 / unchecked0.
- requirements.md: checked5 / unchecked0.
- safety.md: checked12 / unchecked0.

Итого **checked36 / unchecked0**. Неподтверждённых пунктов качества
требований нет. Код ещё не изменён; тесты/приложение не запускались.
Реализация T018, её red/green и независимое ревью, актуальные Dev/CI и выпуск
остаются отдельными воротами.

Отпечатки текущих проверенных документов:

- spec.md: `7f292d40220d0dd83077909c00edf8fc6e25f58ecec8a004e8ffab182a458408`.
- plan.md: `085258deaf72ee301a7aa9f7129426361766b4a989a203a4ed3dc7ed2c7edcbd`.
- tasks.md: `fbb1479a7f156ab3a046bd0c169d1a72f75a4bd553262823662ec1d99d508f9e`.
- quickstart.md: `e55f8adbc386fae80d8108be61b5e1bc7d45fb4caf7245245871c41fa567ad6f`.
- research.md: `f0a19d65772c70a4b262dd4a6d6e9421b597d8d1e4ef92a7df8fbb12ad26d234`.
- contracts/recording-and-playback.md: `b1b234fac88839b40bb359b6c2155b2d7722f73607e42bae957be8fee41f1d50`.
- validation.md: `9257641e635a5f29f33bc0b3d7c0a2fb0e6864523d04dd4ef040bfb600d0d2ed`.

## Независимое ревью реализации T017/T018

Проверено рабочее изменение поверх af6e73eb395158f22aa1f119c913a3a0f313ccb0.
Результат чтения кода и представленных исполняемых доказательств:
**CRITICAL 0 · HIGH 0 · MEDIUM 0**. Замечаний к реализации T017/T018 не
найдено. Это ревью данного изменения, не готовность слияния или выпуска.

### T018 — общий helper и все вызывающие пути

Весь _render_playback перечитан. Единственное продуктовое изменение — две
добавленные строки в storage_action. Ветка storage_capacity_exceeded с
shared_workspace_id=None сохраняет прежнее сообщение и /billing. При
shared_workspace_id заданном та же причина получает текст «Обратитесь к
владельцу пространства, чтобы освободить место для аудио.» без ссылки.
Другие причины возвращают пустой storage_action: условие второй ветви
повторно требует точный storage_capacity_exceeded. Это вывод из прочитанного
условия, отдельный исполняемый отрицательный HTML-тест не заявляется.
Доступное аудио возвращается из прежней can_play/playback_path ветви до
storage_action; разметка доступности, escape, status/focus и плеер не меняются.

Найден один производственный caller _render_playback — общий
_render_meeting_detail_content. Полная страница и fragment передают
embedded/shared_workspace_id в него явно, а тот передаёт их helper.
Общий shared-meetings route в browser.py проверяет recipient proof и
can_view/can_view_full_meeting, затем передаёт owner workspace_id как
shared_workspace_id и вычисляет embedded по X-GRAF-Client. Собственные
browser/desktop routes, owner-only title-error и calendar fragment используют
тот же renderer с прежним значением по умолчанию. Эти callers и передача
признака shared не изменялись. Новых прав, endpoints, действий оплаты,
выдачи аудио, квотной admission либо изменений локального доступа нет.

Расширен один существующий test_quota_playback_copy_offers_existing_billing_overview.
Две вложенные итерации проверяют все четыре own/shared × web/embedded
комбинации. В каждой требуется честное объяснение квоты, owner guidance,
отсутствие сообщения о кодеке и audio; /billing присутствует ровно для own.
Fixture _review имеет unavailable playback без готового player; native
или реальная браузерная приёмка этим контрактом не подменяются.

### Прочитанные red/green доказательства

Reviewer сам тесты не запускал. Прочитаны предоставленные журналы:

- Red:1 failed,9 deselected,0.45s; падает assertion owner guidance на
  прежнем shared HTML. Подтверждён конкретный дефект после запуска
  существующей расширенной регрессии, не только отсутствие API.
- Green: полный test_playback_status_contract.py,10 passed,2 warnings,
  34.06s; isolated PostgreSQL helper сообщает focused status=pass,
  cleanup=isolated_container_removed. Предупреждения относятся к уже
  импортированному pytest module и deprecated httpx/TestClient. Они
  не являются ошибкой проверки и не скрыты.

Предварительная ошибка setup, о которой сообщил исполнитель, не считается
поведенческим red. Восстановление venv через uv sync --frozen --reinstall
описано исполнителем; reviewer не запускал установку и не приписывает
себе независимую проверку этого шага. Governance/changelog/ruff/diff-check
сообщены исполнителем; данный reviewer их не запускал и не принимает
отдельно как собственные результаты.

### T017 — приватность постоянных доказательств

В validation.md заменено только значение домашнего NODE_PATH на нейтральное
обозначение существующих pinned Playwright modules. Playwright1.63.0,
команды, Chromium/WebKit, результаты и ограничения прежних прогонов
сохранены. Повторный скан текущих .md/.json всей F284 по домашним/живым
временным путям дал0 файлов. Сырые red/green журналы остаются локальными: их
полные строки, временные каталоги и предупреждения в отчёт не копировались.
Исторический HEAD не переписан, удаление из старой Git-истории не заявляется.

### Повторное перечтение чеклистов и границы

Все шесть reviewer-owned списков после ревью реализации перечитаны.
Отметки требований остаются без изменений:

- pr-followup.md: checked5 / unchecked0.
- producer-boundary.md: checked5 / unchecked0.
- prompt-recovery.md: checked5 / unchecked0.
- registry-lifecycle.md: checked4 / unchecked0.
- requirements.md: checked5 / unchecked0.
- safety.md: checked12 / unchecked0.

Итого **checked36 / unchecked0**. Предыдущие требования PASS сохраняются;
новых противоречий с FR006/SC004/FR008 не найдено. Dev с обновлённым
кабинетом, текущие GitHub проверки окончательного SHA, merge, release-full,
Apple/public/Sparkle/installed ворота остаются отдельными.

В apps изменены только rendering.py и существующий contract test;
capture/native/T015/T016 код неизменён. Reviewer изменил только этот отчёт,
не менял код/spec/plan/tasks/git/GitHub/runtime и не запускал приложения.

SHA-256 проверенных файлов и локальных журналов:

- apps/server/src/twobrain_rec_server/cabinet/rendering.py: `284caf64714e20655c425677cd56e09446a599b79476913166db7dd6aecd80b2`.
- apps/server/tests/contract/test_playback_status_contract.py: `6676737564abccf41ae2c753419beb1e6b8b348903bbb882c7a6d6cf2301f027`.
- specs/284-recording-continuity-playback/validation.md: `1e37a6506d69c2133ecf65dad6853aa81dc432d050d6da2205a804da450ea2a2`.
- Локальный журнал red: `35188e7ee4ee26d3b359fa72d58c0d927f5e9670794f31dfec413cddb419fe7d`.
- Локальный журнал green: `24dc9fc7b218a3307bd7006f7a588bb8d719efd79c786f1a711ee485cbc23736`.
