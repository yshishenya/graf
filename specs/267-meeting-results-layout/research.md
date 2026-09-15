# Research: F267

## Provenance without a new stored field

Decision: новый descriptor graf_meeting_protocol_about_v1 в существующем response_format.json_schema.name; при сохранении exact pinned snapshot определяет существующий generator_version meeting-protocol-v1-about-v1.
Rationale: _validate_protocol_config проверяет синтаксис descriptor отдельно от точного JSON Schema; _stored_prompt_snapshot восстанавливает снимок без нового запроса; provenance уже доставляет generator_version в detail.
Rejected: текстовые эвристики по длине/словам, первый executive_summary, глобальный bump версии попыток, новый столбец или параметр продукта.
Evidence: исследование Cicero, функции resolve_candidate_prompt, _store_candidate_protocol, _stored_prompt_snapshot в outcomes/ai_service.py; stored_outcome_truth_state в cabinet/view_models.py.
Rollout: generation-side классификация должна быть установлена до активации нового prompt/config. Старые закреплённые попытки и recovery классифицируются по собственному снимку.
Synchronization: sync_prompts переносит response_format из desired_prompts вместе с новым текстом; модель и разрешённые параметры берутся из текущей конфигурации. Синтетический тест перехватывает create_prompt для всех встроенных форматов и custom и проверяет descriptor, текст и сохранение параметров без реальной публикации.
Editorial core: meeting_minutes.md сохраняется побайтно (существующий hash-контракт). Два уточнения добавляются в уже существующий GRAF transport adapter: nature + concrete subject для meeting_type и компактное самодостаточное executive_summary.

## Shared surfaces and export

Decision: derived flag передаётся аргументом через render_shared_meeting_summary_page из уже загруженного outcome. Изменить browser._render_shared_summary_for_grant и три API HTML caller. narrow_summary_projection не получает новое поле; закрытые источники не возвращаются.
Rationale: сам projection намеренно удаляет provenance и ссылки; новое поле не нужно.
Decision: protocol_blocks/protocol_lines и XLSX сохраняют текущий полный документ/порядок, интерактивный renderer отделён.
Rejected: изменение общего списка блоков с неявной сменой экспорта.

## Presentation and validation

Decision: native details, существующая таблица, источник и user_time_element; один актуальный h1 с описанием/датой/участниками.
Rationale: готовые компоненты уже решают доступность и локальное время. Caption таблицы не дублирует видимый заголовок.
Decision: автоматизированная проверка реального серверного HTML с синтетическими данными в worktree и последующее чтение снимков; установленная ручная проверка только через GRAF Dev harness после отдельного commit/promotion.
Rejected: отдельный GRAF Preview/Test, подмена runtime SHA, изменение занятого стенда.
