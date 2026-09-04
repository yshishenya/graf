# Data Model: UI surface inventory

Изменений данных, схемы, API или хранения нет. Для проверки используется
мета-модель представления:

| Entity | Meaning | Invariant |
|---|---|---|
| Surface | Список, detail, настройки, billing, shared или auth экран | Сохраняет существующий маршрут и функциональные hooks |
| State | empty/loading/ready/partial/error/unavailable/disabled | Не сообщает состояние только цветом и содержит правдивый следующий шаг |
| Viewport | standalone/embedded × 320/390/768/1024/1440 | Нет горизонтального переполнения обязательного контента |
| UI contract | data-атрибут, id, name, route, HTMX target/trigger, accessible relation | Presentation polish не меняет его без отдельного функционального решения |
| Evidence | metadata-only screenshot, DOM/a11y snapshot, test receipt | Не содержит секретов, аудио, расшифровок или private meeting content |
