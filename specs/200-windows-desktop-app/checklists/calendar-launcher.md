# Calendar launcher requirements: T119

**Purpose**: ограниченная проверка требований к нативному запуску и завершению.
**Created**: 2026-10-05.
**Feature**: [spec.md](../spec.md), T119, FR-002/005/006/015, SC-002/006/009.
**Review Ownership**: reviewer-owned; основной агент не отмечает пункты.
**Marker Semantics**: `[x]` означает качество требований, не выполненный код.

## Полнота и границы

- [x] CHK001 Однозначно ли разделены native target, browser-only, источник календаря и подтверждение получателя, сохраняя текущий Mac сценарий? [Consistency, bridge §10, plan T119 launcher]
- [x] CHK002 Различены ли отмена действия, natural completion и недоказанный Status/Canceled без ложного drain, с понятным восстановлением? [Completeness, bridge §10, data-model §8, quickstart §13]
- [x] CHK003 Ясны ли основания completion при rejected до вызова, startFailed без полученного handle и сохранение полученного handle после отмены, без обещания отсутствия OS effect? [Clarity, plan T119 launcher, bridge §10]
- [x] CHK004 Согласованы ли guard/current, отсутствие автоматического launch/recovery/Record и отдельные operation/work identities с общим owner? [Consistency, bridge §10, plan T119 launcher]
- [x] CHK005 Отделены ли проверяемые SDK/target outcomes от реального installed/auth/dialog/Record/receiver acceptance без изменения capture/release gates? [Traceability, quickstart §13, T119, SC-002/006/009]

## Notes

Все пять пунктов требуют независимой проверки перед adapter code. Исходные
checklists/reports сохранены; этот gate не закрывает T119 или installed сценарии.

Независимая проверка 2026-10-05 завершена: **5 checked / 0 unchecked;
C0 / H0 / M0**, блокирующих дефектов требований в этих пяти пунктах нет.
Основания, точные хеши и границы решения:
[review-2026-10-05-calendar-launcher-gate.md](review-2026-10-05-calendar-launcher-gate.md).
Это допуск требований к ограниченной реализации adapter, не source approval
и не доказательство OS completion, launcher/owner/bridge/Record acceptance.
