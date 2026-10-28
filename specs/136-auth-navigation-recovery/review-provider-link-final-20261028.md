# F136: итоговое независимое ревью T004/T011/T012

Дата: 2026-10-28. Решение: **APPROVE ограниченной локальной реализации**.
Открытых замечаний и блокеров к просмотренному коду: **0**.
Ветка: `codex/136-provider-link-continuation`.
HEAD и основа разработки: `888ad9539c8bc21a9fe4c3935d6647e035272aa3`.
Срез: T004/#4731, T011/#4738, T012/#4739; полоса **high-risk-product**, auth/session/history.

Решение относится к незакоммиченным байтам, закреплённым ниже SHA-256.
HEAD сам по себе эти изменения не идентифицирует. Новые проверки GitHub точного
PR SHA и проверенной основы, принятие PR и закрытие issues этим решением
не подтверждаются. Ручная T016/#4743 и вся F136 остаются открытыми.

## Полномочия и независимость

Проверяющий изменил только два назначенных reviewer-owned checklist и этот
отчёт с тождественной внешней копией. Код, тесты, spec/plan/tasks, governance,
Git/GitHub, приложение, аккаунты, сессии, выпуск и развёртывание он не менял.
Тесты и сборки не запускал; независимо читал фактические журналы, пересчитывал
терминальные test-case IDs, сопоставлял diff/методы и SHA-256.
Использован навык `code-reviewer`; необязательный запуск тестов не выполнялся
по назначению основного агента.

После сжатия контекста полностью перечитаны AGENTS, guidance README,
document-reading, codex-worktrees, development-process, spec-kit-flow,
release-and-validation, product-gates, конституция, PRD и current-product-status,
весь активный комплект spec/plan/tasks/quickstart/research/data-model/contract,
оба checklist, validation и changelog fragment. Последняя правка Legacy Impact
в spec, отделяющая прежнюю принятую T017 от текущего среза и T016, проверена
после полного повторного чтения spec. Заголовки и хеши полное чтение не заменяли.

В реализации полностью прочитан текущий продуктовый diff и diff тестов;
проверены применимые целые методы controller/coordinator: action/response,
start/commit/finish/fail/cancel/redirect, attach/detach, auth-cookie dispatch,
создание нового окна и terminal скачивания. Workspace, request/response policy
прочитаны целиком; route policy просмотрена в применимых разделах.
Весь большой EmbeddedCabinetWebView, весь тестовый файл и серверный auth API
целиком не аттестуются. Серверные контракты и их неизменные байты не выдаются
за новый end-to-end результат внешнего провайдера.

## Исправление и проверенные границы

Один Bool заменён enum `none / primarySignIn / providerLink`. Это минимальное
разделение двух уже заданных режимов, без новых зависимостей, серверного
маршрута, отдельной системы авторизации или механизма поколений ответов.

| Переход / граница | Фактическое основание | Вывод |
| --- | --- | --- |
| Доверенный старт providerLink | `allowsProviderLinkStart`: текущий завершённый authenticated Settings, source==document, main source/target, exact same-origin POST; route kind и точная форма пути | GET, чужой источник, неподтверждённый документ, subframe, query/fragment, encoded spelling/separators и двойной/завершающий слеш не регистрируют linking |
| Промежуточный authProvider/callback | Передача preservingProviderLink в controller и `.ready` в coordinator; transient route/identity не фиксируются | Старый sessionBoundaryID и WKWebView сохраняются; POST не превращается в GET |
| Финальный безопасный Settings GET | Сначала маршрут/GET identity/presentation; затем штатное завершение | Продолжение снимается, Reload снова безопасен, нет лишнего POST или remount |
| Первичный вход | Отдельное primarySignIn; прежние root-only и stable/protected условия | Не подменён linking; успешная смена сессии сохраняет собственную отложенную границу |
| Root login/logout | Безопасный auth document прекращает продолжение, общий controller применяет границу | Прежняя protected history закрыта; отдельный настоящий WebKit тест PASS |
| 401 / выбор пространства | Accepted response cancel, reset, markSessionExpired | Linking не маскирует потерю доступа; прежние команды закрыты, оба WebKit сценария PASS |
| Текущая ошибка/отмена/blocked/самостоятельная замена | Сброс enum в уже принятых terminal/dispatch путях; независимая навигация вне цепочки даёт none | Нет постоянного разрешения внешних адресов; cancel и503 проверены настоящим WebKit, остальные пути также сверены чтением |
| Redirect / внутреннее добавление headers | Существующая identity/revision/cookie barrier; continuation учитывается в replacement request | Redirect-only и промежуточная цепочка проходят, POST не повторяется |
| Stale callback / detach / process termination | Сброс после accepted controller terminal; attachment/current navigation guards, detach/termination reset | Старое событие не отменяет новое разрешение; разные URL и завершённый same-URL случай имеют отдельные регрессии |
| Download/resource и новое окно | Enum снимается только после принятого finish; общая проверка nil-navigation сохраняет собственный URL fallback; createWebView использует лишь текущий continuation | Общий cancellation guard не перенесён на resource/download finish; отдельного download-lifecycle RED не заявляется |
| Заголовки и платёжная цепочка | Неизменные same-origin request policy, cookie barrier и отдельная payment policy | Внешний OAuth не получает desktop headers или новое платёжное разрешение; положительные синтетические правила не являются внешней OAuth-приёмкой |

Применимые принципы конституции сохранены: capture и ручные Record/Stop не
затронуты; secret/egress границы не расширены; storage/deletion не меняются;
публичный выпуск не выполняется; независимый reviewer gate и текущий Spec Kit
сохранены; доступные имена нативной навигации и самостоятельная реализация
сохранены, новых сторонних assets нет. Legacy Impact `untouched` соответствует
отсутствию новых aliases/fallback/flags/dependencies и путей совместимости.

## Причинные результаты и исправленные замечания

1. На исходном коде два WebKit сценария: intermediate получил expiredSession
   вместо ready — 1 assertion failure в одном тесте; redirect-only уже PASS.
   Исходный PASS не называется RED. После enum/presentation исправления оба PASS.
2. Дополнительная pure-policy матрица обнаружила принятие двойного слеша:
   4 теста,1 FAIL. Предикат ограничен точной формой пути; policy7 PASS и
   focused100 PASS подтверждены отдельными журналами.
3. Ревью выявило мутацию состояния до проверки принадлежности старого response.
   После сохранённого настоящего503 другого URL и нового завершённого linking
   его явная повторная доставка дала offline и снятие внешнего разрешения:
   1 тест,2 assertions,0 unexpected. Теперь cancel сначала должен быть принят
   controller; pending URL имеет приоритет при проверке response.
4. Остаток для того же URL воспроизведён отдельно: первый явный POST503,
   восстановление Settings GET, второй явный POST200, затем повторно переданный
   сохранённый response первого POST. RED:1 тест,2 assertions,0 unexpected.
   Минимальная дополнительная строка в navigationDidCancel требует текущий
   pending/active target, поэтому idle response не меняет новое завершённое
   продолжение. Общий resource/download finish этим условием не ограничен.
5. При сверке validation обнаружены неверные ссылки на промежуточные результаты:
   green2 ошибочно был записан как97, expanded4/1FAIL как100PASS. Автор исправил
   таблицу: green2, focused97, expanded4/1FAIL, policy7, focused-latest100.
   Исправление независимо сверено с фактическими summaries. Ошибки fixture,
   compile и expectation overflow сохранены отдельно и не являются продуктовым RED.

Настоящий WKNavigationResponse сохранён из WebKit, но повторно доставлен
Coordinator тестом намеренно. Это проверяет заданный порядок событий после
завершения новой навигации; естественная сетевая гонка WebKit этим не доказана.
Публичный response не предоставляет WKNavigation identity для одновременных
активных переходов к одному URL; универсальное решение этой отдельной
недоказанной гонки не заявляется и дополнительная архитектура не требуется.

## Независимая сверка журналов

| Журнал | Подтверждённый результат |
| --- | --- |
| f136-provider-link-baseline-tests-20261028.log |93 PASS, исходный кабинетный профиль |
| f136-provider-link-red-20261028.log |2 выбранных,1 PASS/1 FAIL,0 unexpected; intermediate expiredSession |
| f136-provider-link-green-20261028.log |2 PASS |
| f136-provider-link-focused-20261028.log |97 PASS |
| f136-provider-link-expanded-20261028.log |4 выбранных,1 FAIL по двойному слешу |
| f136-provider-link-policy-20261028.log |7 PASS |
| f136-provider-link-focused-latest-20261028.log |100 PASS |
| f136-provider-link-stale-response-red-runtime-20261028.log |1 тест,2 assertion failures,0 unexpected |
| f136-provider-link-stale-response-green-20261028.log |104 PASS |
| f136-provider-link-full-20261028.log |1295 различных,1286 PASS/9 SKIP/0 FAIL; до последнего same-URL guard |
| f136-provider-link-stale-same-url-red-20261028.log |1 тест,2 assertion failures,0 unexpected |
| f136-provider-link-stale-same-url-green-20261028.log |106 различных PASS,0 SKIP/FAIL:83 Workspace+23 RoutePolicy |
| f136-provider-link-full-final-20261028.log |1296 различных:1287 PASS/9 SKIP/0 FAIL,169.782 секунды |
| f136-provider-link-contracts-final-20261028.log |Сборка ContractValidation завершена, ContractValidation: PASS |

Финальные терминальные test-case IDs пересчитаны скриптом независимо:
1296 физических и1296 уникальных, повторов0; все106 профильных присутствуют
в полном наборе. В focused baseline93 → final106 удалённых IDs0, добавленных13;
все13 providerLink tests PASS в окончательном полном журнале. Повторные и
пересекающиеся запуски к числу разных тестов не прибавляются. Exit0 полного
запуска и ContractValidation сообщён исполнителем; сами журналы независимо
подтверждают успешные terminal summaries и результат ContractValidation.

Девять SKIP не считаются PASS: пять DesktopNotificationAccessibility и два
DesktopNotificationPromptLifecycle не получили фокус обычного контрольного
AppKit-окна; два image-export не имели каталогов назначения. Это не новая
приёмка доступности карточек и не ручной результат установленного GRAF Dev.
Финальные106 кабинетных тестов не имеют SKIP.

ProviderPolicyProbe передаёт настоящий WKNavigationAction координатору и
сохраняет его решение, но WebKit всегда получает cancel для provider.invalid.
Внешний провайдер не вызывается. Настоящий DesktopCabinetWorkspaceView в
NSHostingView/NSWindow отдельно подтверждает один и тот же WebView и DOM
после SwiftUI reconciliation, route/identity до/после результата и счётчики
POST/callback/final GET без повтора начального действия.

Полные CI журналы не загружались в контекст целиком: прочитаны summaries,
причины SKIP, профильные случаи и ошибки; исходный файл целиком обработан
для контрольной суммы и пересчёта IDs. Это не запуск тестов проверяющим.
Governance/process/changelog PASS сообщил основной агент; эти команды
проверяющий не запускал. `git diff --check` выполнен независимо: PASS.

## Повторная проверка всех пунктов требований

R01–R16 — исходный порядок requirements.md; смысл checklist не менялся.

| Пункт | Текущее основание качества требований |
| --- | --- |
| R01 | FR описывают поведение; enum и API находятся в design artifacts |
| R02 | US1–3: доступ к кабинету, безопасная навигация, однократные настройки |
| R03 | Пользовательские причины и результаты отделены от технического плана |
| R04 | Scenarios, FR, entities, SC, assumptions и Legacy Impact присутствуют |
| R05 | Блокирующих уточнений нет; сессия28.10 фиксирует границы linking |
| R06 | FR001–009 и contract задают trusted start, state/reset и приоритет expiry |
| R07 | SC001:10 секунд; SC002:однократность; SC003/004:проверяемая навигация |
| R08 | SC описывают исходы и измерения, не внутренний алгоритм |
| R09 | US/AC, edge cases, contract и quickstart содержат текущую матрицу |
| R10 | Отмена/ошибка/restart/stale/detach/root auth/401/reselection учтены |
| R11 | Текущие T004/T011/T012 отделены от принятой T017, T016 и выпуска |
| R12 | Серверные маршруты, session storage/provider set неизменны; данные синтетические |
| R13 | FR связаны с US/SC, contract и quickstart; доказательства ограничены своей областью |
| R14 | Первичный вход, linking и обычные формы/навигация покрыты сценариями |
| R15 | План измеряет boundary/view/route/identity/method counts; это качество требований |
| R16 | Продуктовый spec не заменён описанием реализации |

| Пункт | Текущее основание качества требований |
| --- | --- |
| CHK001 | FR002/003, entities, data-model, contract invariants1–3 |
| CHK002 | primarySignIn/providerLink разделены в contract/data-model |
| CHK003 | FR004 и contract: success/logout/expiry/reselection |
| CHK004 | Assumptions/FR007 и contract Boundary исключают смену сервера/хранения |
| CHK005 | FR001/003/007, SC002: нет повтора или замены метода |
| CHK006 | FR002–005: native controls, gestures, recovery и restart |
| CHK007 | FR004: stable route/identity до успешной границы,401 сразу |
| CHK008 | FR006/SC004 сохраняют обычные встречи/Settings |
| CHK009 | US1/SC001/002 и отдельная настоящая матрица T016 |
| CHK010 | US2 и contract запрещают transient Reload/Forward, сохраняют полезный Back |
| CHK011 | Edge Cases/FR008/contract: отмена, ошибка, limit, restart и сброс |
| CHK012 | FR007, assumptions и quickstart исключают secrets/content в evidence |
| CHK013 | FR009 сохраняет доступность и имена нативных кнопок |
| CHK014 | Existing server-owned routes, contract Boundary/plan; обход не нужен |
| CHK015 | Quickstart T016 ограничен разрешённым тестом и metadata-only evidence |
| CHK016 | Датированные срезы и текущий Status отделяют историю и остаток T016 |
| CHK017 | FR006 сохраняет ordinary POST при200/error/cancel без remount |
| CHK018 | FR004/contract: stable success, немедленная утрата доступа, stale guards |
| CHK019 | Настоящий исходный RED отделён от policy, callback replay и ручной приёмки |
| CHK020 | Root-only login/signup остаются safe, start/callback transient |

После добавления итоговых notes оба checklist полностью перечитаны,
отметки пересчитаны: **requirements16 checked/0 unchecked;
auth-navigation20 checked/0 unchecked**. Checkbox state не менялся.
Отметки качества требований не заменяют реализацию, CI или T016.

## Документы и оставшиеся этапы

Итоговые spec/plan/tasks/quickstart/contract, validation и F136.yaml согласованы
с текущим кодом и границами доказательств. Прошлые датированные исходные отказы
сохранены. Analyze и convergence прочитаны;9FR/4SC/7AC и8 переходов contract
сопоставлены с реализацией. Новых обязательных пробелов/дублирующих задач
не выявлено. Convergence оставила tasks.md побайтно неизменным; на момент
среза T004/T011/T012 ещё[ ], их отметки после решения меняет основной агент.

Открыты отдельно: новые governance-fast/macos-pr/pr-metadata на точном PR SHA
и проверенной основе через общий validate-pr-checks.py; обычное принятие PR
после согласованного выпускного окна; подробные комментарии и live closeout
каждой issue. Реальные email/VK/Яндекс, успешный внешний OAuth и вся матрица
установленного GRAF Dev принадлежат T016/#4743. Release-full, подпись,
notarization, выпуск, CD и production данным ревью не выполняются и не принимаются.

## SHA-256 проверенных входов

Полные нормативные документы и feature artifacts прочитаны, большие source
файлы — в указанной выше области. Хеш закрепляет байты, не заменяет прочтение
или приёмку продукта. Хеш этого отчёта фиксируется отдельно, чтобы не создавать
самоссылочную контрольную сумму.

| Путь относительно репозитория | SHA-256 |
| --- | --- |
| `AGENTS.md` | `24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958` |
| `docs/agent-guidance/README.md` | `2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb` |
| `docs/agent-guidance/document-reading.md` | `5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411` |
| `docs/agent-guidance/codex-worktrees.md` | `d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d` |
| `docs/agent-guidance/development-process.md` | `41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864` |
| `docs/agent-guidance/spec-kit-flow.md` | `afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e` |
| `docs/agent-guidance/release-and-validation.md` | `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| `.specify/feature.json` | `dbbe75c83f916471d95d3a3b62366fe001711c10cbcbf847392768757fe7ca56` |
| `specs/136-auth-navigation-recovery/spec.md` | `69234779eb8f5a0daa792972e0851aeeda1911dae7a8fc507883fed93a2436e7` |
| `specs/136-auth-navigation-recovery/plan.md` | `7fe61c98ce2538681b1bc3a40cd35d256894fe2d69d54aa06138635a3a109cf6` |
| `specs/136-auth-navigation-recovery/tasks.md` | `c76f64200a2fdc82557ef73d86625c46580d6d8f9c055c440d6141664c52f4c1` |
| `specs/136-auth-navigation-recovery/quickstart.md` | `cf4e6d9f0e507b26a112e9560079c5cdf3db30dde5f026cfaa577bffdf896be9` |
| `specs/136-auth-navigation-recovery/research.md` | `e49a028936a317a75e21afc6b4f554b04bab19f8175bb0635f3eb377fb2603a8` |
| `specs/136-auth-navigation-recovery/data-model.md` | `ea2683c1e7838b9d154508fac52f37e2b9f5098b4a443f3f793e164c257136ac` |
| `specs/136-auth-navigation-recovery/contracts/cabinet-navigation-lifecycle.md` | `3321cf9d068ae6bd2cc995f1523c9034addbdcbe61ed49b03017d19d3e9d1a29` |
| `specs/136-auth-navigation-recovery/validation.md` | `d7588a430af619eb6003124518392d38ada44676fd1df7ead9acd94134d566de` |
| `specs/136-auth-navigation-recovery/checklists/requirements.md` | `8f699db1eece911255ce4722b89cda5c192be63d7ad9782aa66889f3621c251b` |
| `specs/136-auth-navigation-recovery/checklists/auth-navigation.md` | `dc28283df729d2a978ee7e36b8b03d532c098516592891c67e5f161d17896e11` |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `4d1d05138a4a29d1bcc01353f33e2fb36d7c00dcaf7cd3a6b5d669920005dd2e` |
| `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift` | `e29ed6945c71cd4ee88d481ec1c8ebee5266865e7320f91e4a23e1b931b27fed` |
| `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift` | `a0688ae25b0d25ddc2329bf50ed58069eb1148f5c20e28930082ed4a3cd5c1ea` |
| `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetNavigationRequestPolicy.swift` | `762433c2c84138963dc206d64a5d5a2fb50742077c6535db465a98b1c0e89af0` |
| `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetNavigationResponsePolicy.swift` | `43739cd36236e479216d9cc52c595730d8a9384923f48c1518107d4d5f40f685` |
| `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` | `ea878feea392f0bdc3c24174c9cef2d1641b9338c943af731f19170194699df2` |
| `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift` | `719dbbb0d0dbc63bd1752a1a6b3455cce2dc6e35bb11c0ab2da7b6d60221e7f9` |
| `changes/unreleased/F136.yaml` | `ccc0596b010dd392353206e6d6ba0c671759036dbff28641ac122b8a0872cb5f` |

## SHA-256 ключевых внешних доказательств

Реестр: `graf-repository-audit` за27–28.10.2026. Исходные файлы остаются
во внешнем реестре; полного содержимого журналов или данных в git не добавлено.

| Файл | SHA-256 |
| --- | --- |
| `f136-provider-link-requirements-review-20261028.md` | `1450d48c6bff76df39a9839c70c50ea0fbb6d14659fd6dcb8a9e834515b80647` |
| `f136-provider-link-analyze-20261028.md` | `1b15a88d4e989bf887e171f1901d3c00f9dbc0fccf02a34ddf48579adb20dd84` |
| `f136-provider-link-converge-20261028.md` | `34c36ba1a712c8dad308bdcda71f54a2012371e935c334d3b7fc934c4a026708` |
| `f136-provider-link-red-20261028.log` | `f145a94315050d303e7d3d52f3d53bded1a9dab028f392ece1a4898a31a96a14` |
| `f136-provider-link-expanded-20261028.log` | `963f009a435d2e7da48d0589f46431c1ed4248b1f683b85bdcecaca74b6626e4` |
| `f136-provider-link-stale-response-red-runtime-20261028.log` | `a78c827cd85898bae36785543e2007386fca912fdde9d8dd6c9309b08a446361` |
| `f136-provider-link-stale-same-url-red-20261028.log` | `a576a34eeaeea84b910a6e3ee0202231495b16fc3f2087f35c17d0a80d835e20` |
| `f136-provider-link-stale-same-url-green-20261028.log` | `4b1023ede56bf53d583855fe56fd69b79bea96f2482f8704e23aa3de85b63ab9` |
| `f136-provider-link-full-final-20261028.log` | `1dee5139e4124ce4c6cd90f9d536a0bc3f49d9e326cbbdaebbcbe3111acdedef` |
| `f136-provider-link-contracts-final-20261028.log` | `bc69e1641f38e10609428c35735f2c263f406eb923bf7ea2934072c36a736dd5` |
