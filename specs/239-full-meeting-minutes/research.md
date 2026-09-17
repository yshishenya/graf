# Решения чистого перезапуска F239

## Документ, а не восемь плоских списков

Decision: единый вложенный протокол с темами и источниками в одном nullable
поле существующего outcome. Rationale: обычная замена промпта оставит плоские
хранение/вывод. Alternative: свободный Markdown без проверяемых ссылок —
не подходит для навигации и повторного использования в разных выгрузках.
Точные проекции нынешнего API не меняют слова и не становятся второй моделью.

## Один существующий жизненный цикл

Decision: изменить нынешний `outcomes/ai_service.py`, не переносить целиком
накопленную реализацию #6787. Rationale: master уже имеет один вызов, durable
ledger, защиту публикации и отдельную доставку наблюдений. Найденный expiry
после ответа сейчас теряет response; новая проверка должна закрыть эту ветку.
Alternative: извлечение + генерация + LLM-verifier — отклонено владельцем.

## Langfuse и источники

Decision: точная версия prompt/config на попытку; dev отдельно от production.
Проверена актуальная документация Langfuse о version/label: явный get по
version или label поддерживается, отсутствие label означает production.
Поэтому значение label передаётся явно; dev не использует production fallback.
Зависимость Langfuse остаётся текущей 4.15.1: обновление SDK не нужно для
документированного get_prompt и увеличило бы несвязанный diff.

Модель ссылается на sequence, сервер добавляет время и ID. Цитата nullable,
при наличии — буквальная. Это проверка адреса/цитаты, не доказательство смысла;
смысл проверяется при приёмке, а не дополнительной production LLM.

## Уроки прошлой работы

Исходные материалы предыдущего исследования: OpenAI speaker-aware cookbook,
QMSum (2021.naacl-main.472), MeetingBank (2023.acl-long.906). Используем
тематическую связность, разнесённые источники и отдельную оценку полноты,
фактичности, связности. Прошлые отрицательные прогоны не становятся PASS.
Никаких дополнительных стадий только ради воспроизведения исследовательской
архитектуры. Первоначальный prompt остаётся редакционной основой.

## References

- https://langfuse.com/docs/prompt-management/features/prompt-version-control
- https://developers.openai.com/cookbook/examples/audio/speaker_aware_meeting_intelligence/speaker_aware_meeting_intelligence
- https://aclanthology.org/2021.naacl-main.472.pdf
- https://aclanthology.org/2023.acl-long.906.pdf
