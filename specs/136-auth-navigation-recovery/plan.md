# Implementation Plan: Безопасное восстановление авторизации и навигации

**Branch**: `codex/136-auth-navigation-recovery` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

## Summary

Исправить macOS WebKit-кабинет так, чтобы только стабильная GET-страница
становилась маршрутом для повторной загрузки и истории. POST-действия,
OAuth-переходы и callback остаются в живом WebView, но не могут быть повторены
SwiftUI, Back/Forward или Reload. Граница сессии очищает историю только после
зафиксированного стабильного результата. Отдельно сохранить безопасный внешний
OAuth-переход для уже авторизованного подключения провайдера.

## Technical Context

**Language/Version**: Swift, Swift Package Manager, macOS 14+
**Primary Dependencies**: SwiftUI, AppKit, WebKit, XCTest; существующие
кабинетные маршруты сервера
**Storage**: N/A — хранилище сессии и серверные контракты не меняются
**Testing**: XCTest в существующем `apps/macos/Shared/Tests`, включая synthetic WKWebView fixture; команды и текущие доказательства — в `quickstart.md` и `validation.md`.
**Risk / Validation Lane**: high-risk feature — меняется auth, граница сессии,
навигация и пользовательский доступ к защищённым страницам
**Release Gate**: no deploy — эта фича готовит проверенный код и changelog; выпуск,
подписание и production deploy требуют отдельного решения пользователя
**Target Platform**: macOS desktop app, встроенный WKWebView
**Project Type**: native desktop app с server-owned HTML кабинетом
**Performance Goals**: после завершения навигации нет самопроизвольной повторной
загрузки; одна явная отправка формы создаёт не более одного исходного действия
**Constraints**: не менять серверные методы входа; не передавать desktop headers
внешнему провайдеру; не логировать коды, cookies, секреты или meeting content;
сохранить native Record/Stop вне WebView
**Scale/Scope**: существующие login/signup, VK ID, Яндекс, provider linking,
настройки и разрешённые страницы кабинета

## Constitution Check

| Gate | Result | Evidence / action |
|---|---|---|
| Auth/session boundary remains fail-closed | PASS by design | Повторный POST, callback и protected history исключаются; 401 сохраняет закрытую границу. |
| Credentials and meeting content stay out of client diagnostics | PASS | Меняется только локальная политика маршрутов и тестовые URL без секретов. |
| Native capture controls remain available and unchanged | PASS | Изменения ограничены cabinet WebKit files и тестами. |
| Clean-room, accessibility and local user control | PASS | Существующие native controls и identifiers сохраняются; поведение кнопок тестируется. |
| Release/deploy integrity | PASS with deferred release | Изменение не развёртывается и не подписывается в этом срезе. |

**Post-design re-check**: PASS. План не вводит серверные обходные GET-маршруты,
новое хранение сессии, внешние зависимости или ослабление origin/header policy.

## Validation Plan

1. Добавить XCTest-матрицу для replay-safe документа, POST, auth start,
callback, provider-link continuation, logout/session boundary и normal history.
2. Запустить focused macOS кабинетные тесты и `swift test --package-path apps/macos`.
3. Выполнить `quickstart.md`; `infra/scripts/ci-local.sh --fast`/`--full` использовать только как диагностический резерв, не как замену GitHub checks.
4. Отдельный T016: manual smoke только в `/Applications/GRAF Dev.app` через штатный dev-harness после чтения `docs/agent-guidance/local-development.md`; с разрешённой тестовой учётной записью:
email start/verify, VK ID, Яндекс, отмена provider flow, Back/Forward/Reload,
provider link и logout/login. В evidence фиксируются только результаты и коды
проверок, не учётные данные, URL с кодами или содержание встреч.

## Project Structure

### Documentation

```text
specs/136-auth-navigation-recovery/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cabinet-navigation-lifecycle.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code

```text
apps/macos/
├── RecApp/Sources/Cabinet/
│   ├── DesktopCabinetRoutePolicy.swift
│   ├── DesktopCabinetWorkspaceView.swift
│   └── EmbeddedCabinetWebView.swift
└── Shared/Tests/
    ├── DesktopCabinetRoutePolicyTests.swift
    └── DesktopCabinetWorkspaceTests.swift

changes/unreleased/F136.yaml
```

**Structure Decision**: Реализовать в существующем macOS cabinet модуле;
server routes остаются неизменными. Тесты дополняют текущую policy/workspace
матрицу без новой инфраструктуры.

## Complexity Tracking

Нет нарушений constitution. Небольшой enum состояния продолжения OAuth
оправдан двумя различающимися безопасностными режимами: первичный вход меняет
сессию, а подключение провайдера из Settings не должно её сбрасывать.

## Возобновлённый срез T005/T006/T010 — 2026-10-17

1. Исторические документы восстановлены из защищённого Git ref; старые отметки
   не являются текущим доказательством. Идентичность F136 и старые task IDs сохранены.
2. Причина T005 подтверждена на базовом SHA: protected POST устанавливает
   `historyFencePending`; finish/fail/cancel очищают историю и меняют
   `sessionBoundaryID`. `.id` в workspace пересоздаёт WebView до route commit.
3. Минимальное исправление в существующем controller/coordinator: исключить
   границу только из-за POST, отложить успешную границу до стабильных route и
   request identity. `markSessionExpired` при 401/выборе пространства остаётся
   немедленной защитой. Не переносить старый архивный Swift-файл целиком.
4. Сохранить текущие billing chain, download, navigation identity, отмену и
   отклонение устаревших callbacks. Все callers finish/fail/cancel и attach/detach
   входят в анализ. Повторную отправку POST не использовать для восстановления.
5. До кода — независимое ревью обоих checklists, анализ spec/plan/tasks и sync
   существующих issues. Затем RED на текущем коде, GREEN после исправления;
   ordinary GET/POST, ошибка/отмена, вход/выход, 401/выбор пространства, кнопки,
   устаревшие callbacks и billing проверяются существующим набором XCTest.
6. T004/T011/T012 и T016 остаются отдельными открытыми воротами всей F136.
   Если дальнейшая проверка выявит связь OAuth/303 с этим исправлением, добавить
   обязательную работу через converge; не менять её по предположению.
7. Перед реализационным коммитом — converge, независимое итоговое ревью
   и текущие проверки. Перед принятием PR —
   governance-fast, macos-pr, pr-metadata на точном SHA/основании через общий
   `scripts/validate-pr-checks.py`. Выпуск и развёртывание остаются вне среза.

**Constitution re-check**: проект не меняет серверный auth contract, доступы,
системный захват, хранение и секреты. Требования к metadata-only evidence,
независимому reviewer и единственному GRAF Dev применяются без исключений.


## Текущее замечание истории — 2026-10-19

До исправления — повторное независимое ревью обоих списков требований.
Причина подтверждена: ledger по URL навсегда блокирует U после POST, а
синтетический URLRequest в finish не отличает следующий настоящий GET.
Нужно различать настоящую навигацию/запись истории от синтетической сверки;
сохранить запрет старых POST, включая повторяющиеся URL, кнопки и жесты.
Предпочесть существующие WebKit identity и controller/policy, без новой
абстракции, зависимости или автоматического повторного открытия POST.

Регрессия сначала должна показать отказ последующего GET на текущем коде,
затем подтвердить его Reload/Back/Forward и отсутствие повтора старого POST.
Отдельно сохранить текущие POST/error/cancel/303/stale/session сценарии.
Точные method/history callbacks необходимо подтвердить настоящим WebKit,
а не предполагать метод исторической навигации. Не снимать консервативный
запрет, пока проверка этого не подтверждает. Незавершённый nil unwrap
в GitHub — отдельный обязательный блокер с диагностическими фазами;
локальный полный PASS его не снимает. Исправление относится к текущим
T005/T006/T010/T018; отдельные OAuth и установленная T016 остаются открыты.


### Результат исследования и выбранное исправление

Настоящий WebKit воспроизвёл блокировку нового GET после POST того жеURL.
Одно снятие запрета поURL и проверка метода не решают выбор native history:
кнопка может выбрать старыйPOST и остановиться вместо перехода к безопасной
записи. Поэтому используется уже принятый NSHashTable weak-pattern для
опасных WKBackForwardListItem; native Back/Forward пропускают именно эти
записи. Успешный настоящий didFinish закрепляет метод нового документа;
синтетический finishGET и завершение ресурса ничего не реабилитируют.
Флаг запроса очищается на всех путях отмены/отсоединения и исключения ресурса.

WKNavigationAction сообщаетURL и метод, но не WKBackForwardListItem.
Если жест нельзя однозначно связать с безопасной записью и существует
опасная запись того жеURL, жест отклоняется; нативные кнопки выбирают
конкретную безопасную запись и продолжают работать. Это консервативное
ограничение сохраняет FR-005 и не допускает старыйPOST из page cache.
Безопасная история без такой неоднозначности не ограничивается.

В тесте последний history policy наблюдается через передачу реального
WKNavigationAction настоящему Coordinator, без выбора policy в тесте;
ожидается реальный cancel и фактический откат currentItem. Дополнительно
проверяется supersededGET с удержанным серверным ответом и artifact404:
прежнийPOST-документ остаётся прежним и не становится доступным для Reload.
Дополнительный риск resource terminal выявлен чтением общих callers;
этот сценарий на промежуточном коде не дал отдельного продуктового RED,
поэтому доказательство его воспроизведения не заявляется.


## Неудачный POST к текущему GET — замечание4312424786, 21.10.2026

Текущие T005/T006/T010/T018 охватывают этот остаток; OAuth и установленная
T016 не меняются. До кода требуется независимое ревью требований.
observeNavigationRequest не должен необратимо помечать прежний GET опасным
до замены документа: сохраняется только pendingHistoryRequestIsSafe=false.
При настоящем WKNavigation didCommit контроллер, проверив текущую identity,
помечает новую POST history item/URL опасными; didFinish сохраняет прежнюю
сертификацию только настоящего GET. Provisional failure/cancel/response refusal
без нового commit оставляют прежнюю безопасную запись пригодной для Reload
и истории. Если новый POST документ уже committed, даже ошибка до didFinish
не разрешает его повторение. Старые unsafe POST entries и неоднозначные
WebKit gestures остаются закрытыми. Нужны настоящие WebKit отрицательные
сценарии same-URL provisional error и response cancellation, положительное
восстановление Reload/Back и отдельная защита committed-but-failed POST;
затем весь DesktopCabinetWorkspaceTests и обязательный hosted exact SHA.
Один общий lifecycle, без отдельного URL rollback ledger или обхода guards.


### Исправление синтетического ответа после hosted отказа — 21.10.2026

На adb345c42a55ea5a5acf7777fa4e13b7eacef7fc run39607758091 не дождался
настоящего didCommit в committed-cancellation тесте. Остальные пять assertions
этого теста зависели от отсутствующего события; продуктовый код этим отказом
не признан неверным. Короткий HTML с намеренно завышенным Content-Length
не гарантирует начало нового документа во всех версиях WebKit; точный
внутренний порог буферизации неизвестен.

В рамках T006/T017 заменить только этот synthetic response: полный основной
POST HTML с правильным Content-Length содержит img на отдельный loopback
ресурс; ресурс сервер принимает и удерживает без ответа. Тест ждёт настоящий
didCommit и фактический запрос ресурса, подтверждает смену history item,
webView.isLoading и отсутствие didFinish, затем вызывает прежний stopLoading.
Проверки запрета Reload старого POST, нового безопасного GET и пропуска POST
в Back остаются. Точки ожидания не заменять ручным callback/таймером или skip;
запреты продукта, timeout и остальные fixture-сценарии не ослабляются.
До изменения — независимый допуск обоих checklists, после — отдельный тест,
весь кабинетный/полный набор quickstart, независимое ревью и новые три
hosted checks на точном SHA/основе. События и счётчики остаются синтетическими.
