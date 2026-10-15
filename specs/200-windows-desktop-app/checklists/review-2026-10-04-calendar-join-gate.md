# T119: текущая независимая проверка качества требований

**Purpose**: ограниченная переоценка требований календарного подключения, не проверка реализации.
**Created**: 2026-10-04.
**Feature**: `../spec.md`, US2/FR-002/005/006/015, SC-002/006/009; существующая T119.
**Lane**: high-risk-product, reviewer-owned requirements review.
**Ownership**: reviewer меняет только этот новый отчёт. Старые чеклисты/отчёты неизменны. `[x]` означает достаточное качество требований, не выполненные код или испытания.

## Критерии требований

- [x] CHK001 Определены ли общий пользовательский сценарий Mac и граница handoff, без утверждения входа во встречу? [Clarity, Spec US2/FR-002, bridge §10]
- [x] CHK002 Однозначны ли exact envelope/action/event UUID/request UUID, запреты URL/Record/extra/duplicate/replay и разрешённый main document/route/nonce? [Security, Spec FR-005/006, bridge §§3/10]
- [x] CHK003 Заданы ли trusted delegated click/keyboard/HTMX, handshake и конечный ответ busy/not-ready без второго перехода? [Coverage, bridge §10:385–403]
- [x] CHK004 Определены ли authenticated fresh resolver, exact matching response, bounds и различимые HTTP/redirect/malformed отказы? [Completeness, bridge §10:407–418, plan T119]
- [x] CHK005 Однозначны ли один busy owner, общий deadline15s и actual worker lifetime при отмене/истечении, без позднего launch? [Lifetime, bridge §10:419–422, quickstart §13]
- [x] CHK006 Полны ли owner/workspace/session/token/document/operation fences и HTMX same-ID/replacement/removal, без освобождения новой операции старым callback? [Consistency, bridge §10:424–431, Data Model §8]
- [x] CHK007 Определён ли общий URL policy через закреплённый Mac/server corpus, включая normalization/numeric IP/IPv6/query/fragment/port и отсутствие передачи GRAF credentials? [Security, bridge §10:435–441, 462–464]
- [x] CHK008 Однозначно ли provider_family отделён от validated host/path и задан Windows-native/browser выбор с preflight absent/unknown/error? [Clarity, bridge §10:443–461, plan T119, quickstart §13]
- [x] CHK009 Заданы ли явное browser recovery со свежим resolver, terminal reply/pending cleanup и отсутствие автоматического повторного launch? [Recovery, bridge §10:397–403, 466–468]
- [x] CHK010 Определены ли handoff-only закрытие карточки, bounded failed retention и native-only Join-and-record после current/readiness? [State, bridge §10:469–474, Spec FR-015]
- [x] CHK011 Измеримы ли доступность и отдельная installed matrix, включая наблюдаемый запуск именно Телемоста, а не inference из API true? [Measurability, Spec SC-009, quickstart §13:454–474]
- [x] CHK012 Прослеживаются ли требования к existing T119/test-first/reuse и обязательным analyze/issue-sync/source/installed gates без дублирования server/backend/задач? [Traceability, tasks Phase19/T119, plan T119]

## Notes

Создано 12 unchecked критериев до независимой оценки. `$speckit-implement` читает markers, но не меняет их. Результат будет записан после оценки; runtime неизвестности не превращаются в requirements PASS реализации.

## Завершённая независимая оценка — 2026-10-04

**REQUIREMENTS PASS — 12 checked / 0 unchecked; C0/H0/M0.**
Первоначальные 12 unchecked критериев оценены лично и по отдельности.
`[x]` принимает качество написанных требований, не реализацию T119.

Canonical repo / branch / HEAD лично сверены read-only:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Источник — текущие рабочие байты и SHA-256 ниже, не один HEAD и не прежний
112/0. Проверено только воздействие этих 12 критериев; hardware/capture/
storage/whole-feature research не повторялось.

### Основания по всем 12 пунктам

| Пункт | Итог | Лично проверенное основание |
| --- | --- | --- |
| CHK001 | PASS | Spec US2:207–219 и FR-002:397–400 описывают один Mac/Windows сценарий: fresh authorization → передача приложению/браузеру → результат/явный повтор. Bridge §10:370–374,397–403 отделяет handed_off от доказанного входа во встречу. |
| CHK002 | PASS | FR-005/006:410–435; bridge §3:49–77 и §10:378–385: exact envelope/command, ровно action/eventId/requestId, UUID8-4-4-4-12 с нормализацией регистра, request UUID отдельно от message_id. URL/path/Record/extra/duplicates/types/replay запрещены; current attached main origin/RouteKind::meetings/list-inbox/nonce, без detail/auth/payment/frame authority. |
| CHK003 | PASS | Bridge:387–403 задаёт trusted delegated capture-phase click/keyboard после HTMX, отсутствие pending до handshake. Correct trusted busy/not-ready получает terminal cancelled; malformed/untrusted — без ответа. Invalidation снимает старый pending до отзыва nonce; terminal reply снимает aria-disabled и допускает явный повтор. |
| CHK004 | PASS | Bridge:407–419: existing authenticated GET join-target без URL во входе/redirect, matching event_id, provider_family≤64B, https_url≤8192 UTF-8 B, response≤64KiB/depth8, strict duplicate/missing/type rejection. 401 только current auth, 404 единая недоступность, 503/network dependency, malformed/URL/launch failed; ошибка/redirect не handed_off. Plan:1166–1174 сохраняет DesktopApiClient/WinHTTP/JSON reader. |
| CHK005 | PASS | Bridge:390–395,416–428, plan:1181–1184,1202–1207 и quickstart:465–469 задают одного busy owner на resolver/launcher/dialog, общий монотонный resolver deadline15s без продления trickle response. Timeout/cancel терминален для UI; worker lease/busy держится до actual completion, повтор в это время cancelled/busy, старый worker не открывает ссылку. |
| CHK006 | PASS | Bridge:421–428 и data-model §8:315–321 фиксируют origin/owner/workspace/auth generation/session token/operation/document generation/nonce или native action identity/epoch/deadline. Полная сверка до/после await/dialog и перед launch/Record; same UUID HTMX сохраняет действие, removal/replacement/logout/token switch отменяет. Stale callback не освобождает новую операцию. |
| CHK007 | PASS | Bridge:432–438,456–458 и quickstart:446–448 ссылаются на frozen Mac/server corpus на SHA721b5125d799ea798a4af0b3625e18d3c1109039: HTTPS, no userinfo/control/backslash authority, percent/IDNA/numeric IPv4/mapped IPv6/Python3.13 global policy. Query/fragment и порт0..65535 сохраняются. GRAF auth/cookies/headers не передаются, DNS-pinning не обещан. Corpus существует в закреплённом Git object; отсутствие копии в нынешнем рабочем дереве остаётся implementation dependency. |
| CHK008 | PASS | Bridge:440–459 и plan:1186–1196,1202–1207 отделяет provider_family календаря от host/path приложения. calendar/unknown+Zoom и zoom+example.org имеют явные контрпримеры quickstart:449–453. Native conversion только no port/443; browser-only использует IgnoreAppUriHandlers=true. QueryUriSupport available/confirmed absent/unknown/error различены; unknown/error требует явного recovery. Телемост — штатный HTTPS handler, без придуманного EXE/custom scheme. |
| CHK009 | PASS | Bridge:397–403,461–464; US2:211–214; quickstart:445–448: native failure предлагает явные browser recovery/cancel без automatic second launch. Подтверждение и retry заново разрешают тот же event UUID, не используют старый URL; current/nonce/request проверяются, terminal снимает pending, отмена ничего не открывает. |
| CHK010 | PASS | Bridge:464–469 и quickstart:457–461: card закрывается только handed_off; failed retention≤5min после явной попытки без продления background failure, с auth/404/context/replacement/close/expiry/new projection fences. Join-and-record только native: handed_off → current → readiness → Record; active/starting/paused/stopping/finalizing не предлагают вторую запись. FR-015:499–501 сохраняет indicator/Stop. |
| CHK011 | PASS | Spec SC-009:596–598, bridge:401–403 и quickstart:454–474 задают keyboard/focus/accessible status и installed matrix entrypoint×target×client availability, logout/navigation/network/recovery. Для Телемоста отдельно selected/nonselected HTTPS app handler; Available/LaunchUriAsync true не identity proof, требуется наблюдаемый запуск именно клиента. Реальный результат этой матрицы не заявляется. |
| CHK012 | PASS | Tasks Phase19:572–583 даёт existing OPEN T119 с exact paths, scope/requirements/testing/installed owners и reviewer→analyze→issue-sync до кода. Plan:1166–1207 требует tests first и reuse единственного JSON/UUID/transport/dispatcher/opener; backend/standalone UI не дублируется. Quickstart §13 отделяет fake/portable от T119/T097/T063/SC-002 acceptance. Issue #7540 свежо проверена read-only. |

### Ограниченный analyze и трассировка

Применены лично прочитанные project-local `speckit-checklist` и
`speckit-analyze`: current artifact consistency, coverage, security/failure
clarity и constitution alignment. Scope — эти 12 пунктов, не новый полный
анализ программы и не разрешение реализации остальных работ.

| Требование | Покрытие | Обязательная граница |
| --- | --- | --- |
| FR-002 | T119; plan §T119; US2 | Same user-visible scenario; handoff не вход |
| FR-005 | T119; bridge §§3/10 | Exact source/main document/route policy |
| FR-006 | T119; bridge §§3/10 | Typed intent/reply, no web URL/Record authority |
| FR-015 | T119; bridge:467–469 | Native readiness/current перед Record, indicator/Stop |
| SC-002 | T119 → T097/T063 | Both-platform installed parity после source checks |
| SC-006 | T119; quickstart §13 | Strict trust boundaries, no private reply/log content |
| SC-009 | T119 → installed matrix | Keyboard/status/accessibility; portable не full acceptance |

Покрытие 7/7 в этом срезе; непокрытых требований/дублирующих tasks нет.
Constitution II/III/VI/VII сохраняет native visible control, credential
isolation, независимый review и truthful platform/accessibility acceptance.
Итог: CRITICAL=0, HIGH=0, MEDIUM=0, blocking clarification=0.
Полный Feature 200 analyze этим не заменяется.

### Пять исходных чек-листов: свежая сверка границы воздействия

Фактические markers перечитаны: requirements22/0, audio-capture24/0,
advanced-routing14/0, security27/0, ux25/0 — всего112/0.
Это статистика существующего reviewer state, не новая полная переоценка112
требований. Лично перечитаны затронутые ownership/bridge/controls/recovery/
accessibility формулировки, включая security CHK008/009.

Четыре hashes совпадают с финальным T119 review 2026-10-02; security hash
изменился. Текущие CHK008/009 остаются согласованы с bridge §10;
перечитаны также package-related CHK012/015. Они сохраняют exact protected
readback/retained-root/whole-object-delete границы и не дают Join новых
полномочий. Прежние C1/C2 не возвращаются. Пять файлов не редактировались,
их исторический PASS не используется как самостоятельное доказательство
нынешних 12 критериев. T120/clock/whole-capture за рамками этой проверки.

| Артефакт | SHA-256 |
| --- | --- |
| checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| checklists/security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

### Tracker и внешние блокеры

Личный fresh read-only `gh issue view` в репозитории из origin подтвердил
[#7540](https://github.com/yshishenya/graf/issues/7540) OPEN:
`[200][P1][ux] T119: Подключать календарную встречу через единый нативный путь Windows`.
Есть `Spec tasks: T119`, девять canon body sections в требуемом порядке и
`feature:200/priority:P1/area:ux/gate:pr-blocker/type:bug`.

Человек подтвердил schema и issue-canon/labels sync; main сообщил
canonensure/canonvalidate300PASS. Эти ранее исполненные команды reviewer
не повторял; свежий read issue подтверждает текущее tracker состояние,
но не приложение. GitHub/labels/tasks reviewer не менял.

Техническая неизвестность native запуска Телемоста остаётся OPEN.
Нужно наблюдаемое installed evidence при selected/nonselected HTTPS handler;
browser success и API true не принимают native parity. Source tests,
worker/URL implementation, exact installed MSIX и одинаковый сценарий Mac,
T097/T063/SC-002/006/009, hardware/release — отдельные будущие gates.
T119 остаётся незавершённой и OPEN; requirements PASS её не закрывает.

### Источники и SHA-256 текущего снимка

Лично прочитаны applicable parent/root AGENTS, guidance index, codex-worktrees,
spec-kit-flow, product-gates, tracker/canon, constitution, scoped PRD/status/
release sections и project-local skills checklist/analyze. Closer repo AGENTS
отменяет parent Linear rule. Hooks before/after checklist/analyze commit disabled;
issue-sync hooks не запускались. Supported prerequisite checks прошли;
неподдерживаемый `--require-spec` заменён прямым чтением существующего spec.
Записи ограничены этим отчётом и разрешённым package gate.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `0073b6f2ff8e3e9f07389473cf7fc0f5c2eaf146961f08426d140163dd5d4fe2` |
| plan.md | `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `3045f730bc59bbc3abdeaf736a7e7e347825bdf6e8878bdaa10a34d293113acc` |
| data-model.md | `dc91ac60f180e6221e85917c9a91e510e34008430dfb457e7a7cbeb97162e0a7` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| contracts/windows-native-web-bridge.md | `127356a14df140364ce619554bcc42cab03286262065afa40c1fcdb73ac51ff4` |
| AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| .specify/extensions.yml | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| .agents/skills/speckit-checklist/SKILL.md | `890ef64b5527a69a9661f1c100f15b066ec368b67f771d44c05fcc091fe1bbed` |
| .agents/skills/speckit-analyze/SKILL.md | `07ead5c0db569e93b75c4cada8139ef799d5721d6037c3ed15b7482d114d22d1` |

Frozen F279 contract лично прочитан через `git show` из того же canonical
репозитория; schema/opener/worker runtime от этого не принят.
Pinned corpus SHA-256:
`7c6731fe293226eb1033acb2c5acc930897134395e8d67ebc29cca7ba17757d1`.
В текущем дереве файла corpus нет; закреплённый объект существует.

SHA-256 calendar gate до оценки:
`502a4ff2c5f3c5e1b990cfe90101a6e6c06feead96901d9db5eafef76079a747`.
Прежние формулировки сохранены; изменены только 12 markers и добавлен этот
отчёт. Итоговый файл и counts перечитаны после записи; final hash сообщается
отдельно, без self-hash.

**Терминальный вывод: REQUIREMENTS PASS 12/0, C0/H0/M0; блокеров качества
этих требований нет.** Технический/installed Telemost proof, source/runtime
приёмка T119 и общий выпуск остаются открытыми. Reviewer не менял код,
spec/plan/tasks, GitHub, commit/install/build/VM/device state.

### Уточнение границы минимального response decoder — 2026-10-04

Перечитано bridge §10:378–385 и407–415 в том же нормативном снимке.
**Закрытый exact field set с запретом extra относится к входному payload,
не к ответу resolver.** Ответ сервера имеет известные scalar-string поля
`event_id`, `provider_family`, `https_url`; текст §10 не задаёт отказ
из-за дополнительных неизвестных response fields. Фраза quickstart §13
«exact payload/response» не вводит такой запрет поверх точного контракта.

Заявленный минимальный decoder совместим с требованиями: reuse существующего
JsonReader с maxDepth8, whole response≤64KiB, полная проверка корректности JSON/
Unicode, обязательные известные строки через существующий calendarString,
decoded provider_family≤64bytes, decoded https_url≤8192 UTF-8 bytes,
UUID с нормализацией регистра и совпадением с запрошенным событием.
Missing/duplicate/malformed/type/depth/size/UUID mismatch не принимаются.
Неизвестные поля игнорируются семантически только после проверки корректного
JSON и общих bounds; невалидный JSON в них не разрешается этим исключением.
Новый запрет неизвестных ключей reviewer не требует.

URL launch/host/provider policy не является работой этого decoder-only шага;
она остаётся обязательной перед реальным открытием ссылки по §10:430–469.
Отдельный source review должен подтвердить путь existing DesktopApiClient +
ContractFixtures и фактическую проверку JSON/Unicode/границ, не объявлять
готовыми resolver/worker/opener/current fences по одному decoder PASS.

Main сообщил исходный ContractFixtures build/1PASS в новой временной сборке.
Reviewer его не воспроизводил, не принимал как source/runtime evidence и
не изменял сборку. Новых требований/критериев или C/H/M findings не добавлено.
**Конечный requirements verdict сохранён: 12 checked / 0 unchecked,
C0/H0/M0; decoder clarification не блокирует этот ограниченный следующий шаг.**
