# GRAF cabinet UX/UI/IA — feature 240

- Упорядочена визуальная иерархия кабинета: рабочая область, toolbar, карточки,
  состояния, настройки и detail используют единые отступы, границы, фокус и
  responsive-правила.
- Добавлена доступная мобильная навигация standalone browser; на ширине до 390
  px она не допускает клиппинга и использует доступные имена у icon-only ссылок.
- Сохранены маршруты, формы, HTMX/data-hooks, accessibility IDs и вся
  функциональная семантика записи, загрузки, обработки, playback, удаления,
  sharing, export, auth и privacy.
- Проверка и screenshots: `specs/240-cabinet-ux-overhaul/design-qa.md`.
