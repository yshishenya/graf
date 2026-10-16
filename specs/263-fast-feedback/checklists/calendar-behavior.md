# Качество требований: текущая US4 / F263

Purpose: независимое ревью до реализации. Created:2026-10-16.

Состояние пунктов принадлежит независимому рецензенту. [x] означает качество
требований текущей US4, не реализацию или завершение всейF263.

## Полнота и безопасность

- [x] CHK001 Явно ли отделены восстановленный текст и утраченные оригинальные node IDs? [Clarity, Spec §Происхождение]
- [x] CHK002 Ограничена ли текущая реализация независимойUS4 без принятияUS1–US3? [Scope, Spec §Clarifications]
- [x] CHK003 Названы ли всеmatching/API/modelисточники и оба существующих результата? [Completeness, Spec §FR-012, Plan §Phase1]
- [x] CHK004 Описан ли union/covered и единственный владелец целого файла вmixedfast? [Consistency, Spec §US4, Plan §Phase1]
- [x] CHK005 Определено ли отсутствие повторногоcalendarperformance и сохранение обязательного порога? [Measurability, Spec §SC-004, Plan §Phase1]
- [x] CHK006 Разделены ли требования окруженияcabinet/calendar и исключено ли новое выполнениеPostgresдляcabinet? [Isolation, Spec §US4]
- [x] CHK007 Названы ли обязательные отказыmissing/empty/syntax/symlink до исполнения? [Coverage, Spec §US4]
- [x] CHK008 Описаны лиskip/deselect/nonzeroи отсутствие ложногоPASS? [Failures, Spec §US4]
- [x] CHK009 Сохранены лиunknown/shared/rename/base и частичный характер карты? [Completeness, Spec §FR-014]
- [x] CHK010 Предписан ли существующий изолированныйPGсмиграциями/RLSиcleanup без новых зависимостей? [Safety, Plan §Phase1]
- [x] CHK011 Разделены лиstubконтракты и фактический запуск обоихcalendarфайлов? [Evidence, Quickstart §Реальный календарь]
- [x] CHK012 Согласованы лиreview/analyze/sync/converge/exactSHAи отдельное разрешениеcommit? [Governance, Spec §FR-015]
- [x] CHK013 Сохранены лиисходныеissues/задачии критерии старых замеров безsilentcancel? [Traceability, Tasks §Setup]
- [x] CHK014 Предписаны ли metadata-onlyevidenceи отсутствие измененийDev/production? [Privacy, Plan §Constraints]
- [x] CHK015 Нет ли изменения конституционных принципов или ослабленияunit/component/releasegates? [Consistency, Plan §Constitution Check]

## Notes

$ speckit-implement только читает состояние; автор не отмечает пункты.

Независимое ревью 2026-10-16: 15 подтверждено, 0 не подтверждено.
Доказательства по каждому пункту и границы PASS:
[review-calendar-behavior-20261016.md](../review-calendar-behavior-20261016.md).
Это приёмка качества требований US4 перед кодом; analyze, сверка issues,
реализация, проверки и разрешения остаются отдельными обязательными этапами.
