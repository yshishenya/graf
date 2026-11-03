# T106 — локальный выбор открытой вкладки

Полоса active Spec Kit slice, privacy/browser. Основа b18f1a485a4b500c4b6a2c92667b4464b205016d.
До кода scoped analyze пяти групп: актуальная сохранённая запись и все
canUseAnalytics callers; cross-tab/resume без автоматического старта;
устаревший callback против свежего решения; отключение собственной очереди
и destruct; причинные проверки и явные пределы среза.
Coverage 5/5, C/H/M 0, unmapped 0, все группы относятся к существующей
T106/#7696. Constitution II/III/IV/VI не меняются; новые получатели, данные,
постоянное состояние и инфраструктура отсутствуют.

Базовые constitution/PRD/status/product-gates и три затронутых contracts
сверены по прежним SHA256, все совпали; использовано разрешённое владельцем
исключение повторного чтения F273. Непосредственно перечитаны новые T106
разделы, FR-001/003/006/059, SC-004, review public-counter T106 и затронутые
потоки analytics.js и существующий Node harness.

Следующий gate — независимый reviewer-owned checklist. До его PASS
продуктовый JS и тесты не меняются. Полный T106, server individual revoke,
active-tab global permission, настоящий SDK/network и T0 остаются открытыми.

Независимое before-code review: checklist5/0,P1/P2/HIGH0. Canon ensure/
validate253issues PASS; #7696 подтверждает владение T106, status comment
6549465691 записан до product code. RED Node: прежний код отправил
public_download_viewed после смены localStorage на revoked до storage event.
После минимального JS изменения этот причинный сценарий закрыт.
Первый GREEN дошёл до новой проверки повторных listeners и выявил
неполную тестовую предпосылку: productConfig отсутствовал, поэтому click
listener не должен был существовать. Добавлен прежний product config
с учебным псевдонимом; assertion не ослаблен.

Повторный Node GREEN: все18 именованных сценариев,0skips. Считаются
реальные synthetic relay/ym commands; проверены revoked/missing/damaged/
unreadable storage,5 lifecycle вариантов, stale callback, явный regrant,
очистка только собственной queue и provider destruct exception. Это VM
на настоящем JS, а не реальный SDK или рабочая передача.
Focused с настоящим CookieConsent modal:53passed,0skips,12,05с; consent,
public contracts/unit и PostHog autocapture. Учебная PostgreSQL удалена
штатным runner; данные/контейнеры не сохранены. JS syntax/process/
Spec Kit governance, fragment checker и diff PASS; тесты узкие и не заменяют
точные GitHub checks/Full/CD. Независимое implementation review/converge
следует отдельно. Global permission/individual server revoke/actual SDK
и T0/полная T106 не принимаются.

Независимое implementation review/converge PASS: checklist5/0,
P1/P2/HIGH0; фактический JS hash
c04612cb03eee01b893c4b8cc2b680e6d8e052854c2cfba10bffa004c51eee14
подтверждён. Коммит и exact PR checks следуют отдельно.
