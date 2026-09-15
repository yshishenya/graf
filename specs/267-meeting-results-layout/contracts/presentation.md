# Presentation Contract: F267

## Identity

Один h1 из актуальной встречи. Содержательный тип под подписью «О чём встреча» только для meeting-protocol-v1-about-v1; остальные версии → «Тип встречи». Нет анализа длины/содержания текста. Затем существующее локальное время без секунд и участники. Upload-only time retains truthful «Загружено». Нет времени → «Без даты», нет участников → «Не определено».

## Results

1. Главное (executive_summary).
2. Принятые решения.
3. Задачи (task/owner/due; неизвестные значения «Не назначен»/«Не указан»).
4. Открытые вопросы и следующие шаги (open_questions + next_steps).
5. Ключевые обсуждения: закрытые details с названиями; при раскрытии outcome, context, discussion, proposals.
6. Примечания: закрытые details только при наличии.

Цели/input_type скрыты только на странице. Пустые решения/задачи/вопросы — одна строка. Пустое главное/темы — краткое честное состояние. Непустой сохранённый текст не обрезается/не переписывается. System banners remain outside disclosures.

## Sources and accessibility

Одна видимая доступная ссылка на тезис, остальные в details «Ещё N» вертикально. Источники продолжают текст текущей мысли без принудительного переноса, перед дополнительными сведениями; перенос допускается только по доступной ширине. Новая мысль начинается отдельным абзацем. Ноль/один источник не создаёт пустого details. Все existing data-seek-seconds/data-source-segment сохраняются; source revision checks and return navigation unchanged. Тема не переключается от выбора источника.
Native summary доступен с Enter/Space, видимым focus ring и accessible open state. 24px targets, text contrast ≥4.5, line height ≥1.45, no horizontal page overflow at 320–1440 and 200% text.

## Compatibility

Полный browser и embedded имеют одинаковую иерархию. Shared summary имеет свой заголовок, разрешённые сведения и ни одного source control, если source destination отсутствует. Старые category results сохраняют прежний layout; общий источник использует тот же compact overflow.
Exports/clipboard keep canonical complete document and order, unaffected by disclosure state.
