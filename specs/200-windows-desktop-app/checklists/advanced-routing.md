# Advanced-routing Checklist: Windows desktop-приложение GRAF

**Purpose**: Проверить, что первый Windows-срез не вводит скрытую routing-архитектуру и
что будущий process-isolated capture остаётся отдельной безопасной capability.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md), [research.md](../research.md)

## Явная граница первого Windows-среза

- [ ] CHK001 Спецификация прямо отделяет global render loopback от process-isolated loopback и не называет первый «записью только Zoom/Teams/браузера». [Clarity, Spec §Context and goal]
- [ ] CHK002 Stereo Mix, hardware loopback, virtual audio driver, kernel component, exclusive mode и elevated service перечислены как out of scope, а не оставлены неявными. [Completeness, Spec §Out of Scope]
- [ ] CHK003 Требования не предполагают обход Windows privacy, DRM или endpoint ownership через вспомогательный privileged process. [Safety, Spec §FR-007, §FR-019]
- [ ] CHK004 Архитектура не содержит второго audio routing stack или cross-platform abstraction, который владеет capture authorization/clock/local truth. [Consistency, Plan §Source ownership]
- [ ] CHK005 Любое ограничение protected audio представлено честным degraded/limited result и не компенсируется скрытым альтернативным источником. [Truthfulness, Spec §FR-017]

## Будущая capability boundary

- [ ] CHK006 Process loopback оформлен как отдельная будущая feature с собственными OS/build prerequisites и не попадает в acceptance criteria Feature 200. [Scope, Research §Decision]
- [ ] CHK007 Для возможного будущего process loopback заранее указаны отдельные вопросы privacy consent, app identity, child-process scope, protected audio и fallback policy. [Gap, Future dependency]
- [ ] CHK008 Любая будущая routing feature требует новой QA matrix, package/installer model, resource gate, rollback evidence и явного product approval. [Governance, Constitution §Advanced routing gate]
- [ ] CHK009 В tasks не появляется задача на driver installer, Stereo Mix enablement или system service под видом поддержки Windows audio. [Consistency, Spec §Out of Scope]
- [ ] CHK010 В user-facing copy не обещается контроль отдельного процесса, если первый Windows-срез получает общий микс текущего render endpoint. [UX truth, Spec §Context and goal]

## Resource and rollback constraints

- [ ] CHK011 Требования к CPU, memory, device ownership, uninstall и rollback не зависят от установки kernel/virtual routing component. [Packaging, Spec §FR-019–FR-020]
- [ ] CHK012 Указано, что отказ будущего advanced-routing proof не может блокировать или незаметно менять базовый shared-loopback срез. [Recovery, Plan §Complexity Tracking]
- [ ] CHK013 Любая запись через нестандартный endpoint имеет явное owner, selected device, user consent и metadata-safe limitation, а не эвристическое «нашли Stereo Mix». [Security, Spec §FR-008, §FR-021]
- [ ] CHK014 До начала такой будущей работы должен существовать отдельный approved spec; отсутствие его является stop condition, а не задачей для реализации Feature 200. [Governance, Spec §Out of Scope]
