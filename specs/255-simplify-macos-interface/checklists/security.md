# Checklist: Качество требований к границе native/WebView

**Purpose**: Review полноты, ясности и согласованности требований до реализации.
**Created**: 2026-09-06
**Feature**: [spec.md](../spec.md)

**Review Ownership**: рецензент владеет отметками. `[x]` означает проверенное качество требования, а не готовность кода. Генерация оставляет все пункты открытыми.

## Требования

- [x] CHK001 Определены ли доверенные main frame/origin/route, поколение документа и session boundary как отдельные условия допуска? [Полнота, Spec FR-008/FR-015, contracts/interface.md]
  Evidence reviewer, 2026-09-06: Раздел «Формат и границы» контракта задаёт одновременные main-frame, доверенный origin, route policy, поколение и sessionBoundaryID; lifecycle назначает поколение при commit и очищает его на границах.
- [x] CHK002 Ограничены ли версия, размер, типы и допустимые значения payload, без передачи секретов и содержимого встреч? [Полнота, Spec FR-008, contracts/interface.md, data-model.md]
  Evidence reviewer, 2026-09-06: Контракт задаёт v1, 32 KiB, 32 пункта, размеры ID/label/name/route, допустимые группы и тему; неверные типы, версия, дубли и неоднозначный выбор отклоняют snapshot целиком. Data-model исключает содержимое встреч и секреты.
- [x] CHK003 Запрещены ли произвольные URL/JavaScript и обход действующей route policy через команды меню? [Ясность, Spec FR-008, contracts/interface.md]
  Evidence reviewer, 2026-09-06: Контракт сохраняет DesktopCabinetRoutePolicy и запрет произвольной схемы/host/userinfo/query обхода; команды — фиксированный набор. JavaScript из payload не исполняется. Нынешние обработчики в EmbeddedCabinetWebView уже требуют main frame и route allow.
- [x] CHK004 Сохраняют ли требования к theme/logout существующие формы, CSRF, ошибки и подтверждённое состояние без второго сетевого клиента? [Согласованность, Spec FR-005/FR-007, contracts/interface.md]
  Evidence reviewer, 2026-09-06: Раздел команд требует существующие формы/requestSubmit и CSRF для theme/logout, текущий feedback и подтверждённое состояние/откат; отдельный HTTP preferences client и UserDefaults запрещены.
- [x] CHK005 Определён ли отказ при stale/iframe/foreign сообщениях, смене пользователя, прекращении WebContent и неуспехе передачи управления? [Покрытие, Spec FR-008, contracts/interface.md]
  Evidence reviewer, 2026-09-06: Раздел передачи управления описывает привязку подтверждения к поколению, отказ stale/foreign/iframe через условия допуска, очистку snapshot на session/logout/ошибке/WebContent и восстановление HTML при неудаче передачи.
- [x] CHK006 Согласованы ли смешанные версии и откат с одним владельцем навигации и очисткой прежнего профиля? [Восстановление, Spec FR-008/FR-011, contracts/interface.md]
  Evidence reviewer, 2026-09-06: Таблица mixed versions и раздел восстановления определяют один навигационный набор, HTML по умолчанию и очистку старого профиля; откат не требует миграции. Новое оформление не становится источником прав.
- [x] CHK007 Сохранены ли видимое управление записью, quit guards и правила хранения/удаления без расширения полномочий bridge? [Согласованность, Spec FR-009, plan.md Constitution Check]
  Evidence reviewer, 2026-09-06: FR-009, Constitution Check и контракт фиксируют независимые capture controls, one-action Stop, существующие quit callbacks/guards, три состояния/таймер и отсутствие изменений хранения/удаления. Новый bridge ограничен меню/темой.
- [x] CHK008 Определены ли обезличенное evidence и обязательные exact-SHA/notarization/release gates? [Покрытие, Spec FR-016, quickstart.md]
  Evidence reviewer, 2026-09-06: FR-016 и quickstart запрещают личное содержимое/секреты в evidence; задают проверяемый SHA, governance-fast, frozen Full CI, CD dry-run и Developer ID/notarization/stapling/Gatekeeper/Sparkle до выпуска.

## Notes

`speckit-implement` читает эти отметки как gate и не меняет их. Замечания рецензента и evidence добавляются рядом с пунктами.

Review выполнен отдельным агентом-рецензентом по поручению владельца; основание и пределы — [validation/readiness.md](../validation/readiness.md). Отметки оценивают требования, не готовность реализации.
