# Checklist: Качество требований к границе native/WebView

**Purpose**: Review полноты, ясности и согласованности требований до реализации.
**Created**: 2026-09-06
**Feature**: [spec.md](../spec.md)

**Review Ownership**: рецензент владеет отметками. `[x]` означает проверенное качество требования, а не готовность кода. Генерация оставляет все пункты открытыми.

## Требования

- [ ] CHK001 Определены ли доверенные main frame/origin/route, поколение документа и session boundary как отдельные условия допуска? [Полнота, Spec FR-008/FR-015, contracts/interface.md]
- [ ] CHK002 Ограничены ли версия, размер, типы и допустимые значения payload, без передачи секретов и содержимого встреч? [Полнота, Spec FR-008, contracts/interface.md, data-model.md]
- [ ] CHK003 Запрещены ли произвольные URL/JavaScript и обход действующей route policy через команды меню? [Ясность, Spec FR-008, contracts/interface.md]
- [ ] CHK004 Сохраняют ли требования к theme/logout существующие формы, CSRF, ошибки и подтверждённое состояние без второго сетевого клиента? [Согласованность, Spec FR-005/FR-007, contracts/interface.md]
- [ ] CHK005 Определён ли отказ при stale/iframe/foreign сообщениях, смене пользователя, прекращении WebContent и неуспехе передачи управления? [Покрытие, Spec FR-008, contracts/interface.md]
- [ ] CHK006 Согласованы ли смешанные версии и откат с одним владельцем навигации и очисткой прежнего профиля? [Восстановление, Spec FR-008/FR-011, contracts/interface.md]
- [ ] CHK007 Сохранены ли видимое управление записью, quit guards и правила хранения/удаления без расширения полномочий bridge? [Согласованность, Spec FR-009, plan.md Constitution Check]
- [ ] CHK008 Определены ли обезличенное evidence и обязательные exact-SHA/notarization/release gates? [Покрытие, Spec FR-016, quickstart.md]

## Notes

`speckit-implement` читает эти отметки как gate и не меняет их. Замечания рецензента и evidence добавляются рядом с пунктами.
