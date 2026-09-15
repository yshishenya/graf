# Data Model: F267

Схема graf-meeting-protocol-v1 и таблицы не меняются.

| Existing field | Use |
|---|---|
| Meeting.title | Единственный актуальный заголовок страницы |
| Meeting.started_at / existing upload time basis | Каноническое время через user_time_element; неизвестное начало не берётся из текста модели |
| MeetingProtocol.meeting_type | Сохранённая категория для истории; характер и предмет для новой инструкции |
| executive_summary | Главное без пересказа/обрезания интерфейсом |
| decisions / action_items | Точные договорённости и задачи; неизвестные owner/due остаются null |
| open_questions / next_steps | Оставшиеся вопросы и шаги в исходном порядке |
| topics.{title,outcome,context,discussion,proposals} | Название раскрытия и непустые подразделы |
| notes | Свёрнутые примечания |
| prompt_config.response_format.json_schema.name | Existing descriptor identifies exact generating contract |
| MeetingOutcomeSet.generator_version | Existing persisted legacy/new semantic discriminator |
| notes_action_truth.provenance.generator_version | Existing delivery of discriminator to detail; derived flag is not a new API field |

Новые lifecycle states не вводятся. Сохранение и replay берут семантику только из точного исходного снимка. Unknown/legacy version → «Тип встречи». Просмотр, изменение названия и смена labels не меняют сохранённый результат. Access/source/deletion fences сохраняются. Shared HTML передаёт только derived flag, не полный снимок/внутренние данные.
