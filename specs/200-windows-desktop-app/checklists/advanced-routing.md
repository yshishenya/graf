# Advanced-routing Checklist: Windows desktop-приложение GRAF

**Purpose**: Проверить, что первый Windows-срез не вводит скрытую routing-архитектуру и
что будущий process-isolated capture остаётся отдельной безопасной capability.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md), [research.md](../research.md)

## Явная граница первого Windows-среза

- [X] CHK001 Спецификация прямо отделяет global render loopback от process-isolated loopback и не называет первый «записью только Zoom/Teams/браузера». [Clarity, Spec §Context and goal]
- [X] CHK002 Stereo Mix, hardware loopback, virtual audio driver, kernel component, exclusive mode и elevated service перечислены как out of scope, а не оставлены неявными. [Completeness, Spec §Out of Scope]
- [X] CHK003 Требования не предполагают обход Windows privacy, DRM или endpoint ownership через вспомогательный privileged process. [Safety, Spec §FR-007, §FR-019]
- [X] CHK004 Архитектура не содержит второго audio routing stack или cross-platform abstraction, который владеет capture authorization/clock/local truth. [Consistency, Plan §Source ownership]
- [X] CHK005 Любое ограничение protected audio представлено честным degraded/limited result и не компенсируется скрытым альтернативным источником. [Truthfulness, Spec §FR-017]

## Будущая capability boundary

- [X] CHK006 Process loopback оформлен как отдельная будущая feature с собственными OS/build prerequisites и не попадает в acceptance criteria Feature 200. [Scope, Research §Decision]
- [X] CHK007 Для возможного будущего process loopback требования отдельно задают техническое управление пользователя/ОС и область данных: выбор и проверку identity целевого приложения, область дочерних процессов, применимые разрешения Windows, защищённый звук, минимизацию данных и запасной сценарий. «Техническое разрешение пользователя/ОС» не означает юридическое уведомление или согласие участников и не становится условием старта записи. [Clarity, Future dependency, Research §Пересмотр гипотезы часов и границы будущего routing; Constitution §II]
- [X] CHK008 Любая будущая routing feature требует новой QA matrix, package/installer model, resource gate, rollback evidence и явного product approval. [Governance, Constitution §Advanced routing gate]
- [X] CHK009 В tasks не появляется задача на driver installer, Stereo Mix enablement или system service под видом поддержки Windows audio. [Consistency, Spec §Out of Scope]
- [X] CHK010 В user-facing copy не обещается контроль отдельного процесса, если первый Windows-срез получает общий микс текущего render endpoint. [UX truth, Spec §Context and goal]

## Resource and rollback constraints

- [X] CHK011 Требования к CPU, memory, device ownership, uninstall и rollback не зависят от установки kernel/virtual routing component. [Packaging, Spec §FR-019–FR-020]
- [X] CHK012 Указано, что отказ будущего advanced-routing proof не может блокировать или незаметно менять базовый shared-loopback срез. [Recovery, Plan §Complexity Tracking]
- [X] CHK013 Требования будущего нестандартного источника называют его владельца и явный выбор локального пользователя, применимые технические разрешения Windows и metadata-safe limitation; это не юридическое уведомление или согласие участников. Эвристическое «нашли Stereo Mix» запрещено. [Security, Research §Пересмотр гипотезы часов и границы будущего routing; Spec §FR-008, §FR-021; Constitution §II]
- [X] CHK014 До начала такой будущей работы должен существовать отдельный approved spec; отсутствие его является stop condition, а не задачей для реализации Feature 200. [Governance, Spec §Out of Scope]

### Повторная независимая проверка требований — 2026-09-30, раунд 2

PASS — 14/14; неподтверждённых пунктов нет. Повторно прочитаны все пункты и
сверены с актуальными `spec.md`, `plan.md`, `research.md`, `tasks.md`,
конституцией и `docs/agent-guidance/{spec-kit-flow,product-gates}.md`.
Формулировки CHK007 и CHK013 уточнены: в исследовании будущего process loopback
«privacy» прямо означает технический контроль пользователя/ОС и область данных,
а не юридическое уведомление/согласие участников; Конституция II не допускает
превращать согласие участников в приложение-предусловие записи. Будущий routing
остаётся вне Feature 200 и требует отдельного одобрения.

Это проверка качества требований и их границ, а не проверка реализации,
разрешений Windows, устройства, сборки или записи звука.
