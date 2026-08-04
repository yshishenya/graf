# Research: meeting-outcome-value

Дата: 2026-08-04. Исследование clean-room: продукты используются как ориентиры
задач и доверия, но не как источник layout, copy, assets или визуального языка.

## Какую ценность действительно покупает пользователь

После встречи человек не хочет «AI summary» как объект. Он хочет быстро ответить
на четыре вопроса: что произошло, что решено, кто что делает и где это было
сказано. Поэтому основная метрика — не количество секций, а время до правильного
действия при возможности проверить вывод.

## Референсы продуктов

- [Krisp Meetings](https://help.krisp.ai/hc/en-us/articles/10291109632412-Meetings-page-in-account-dashboard)
  держит Notes компактными: key points и action items видны сразу, outline не
  вытесняет главный результат. [Centralized Action Items](https://help.krisp.ai/hc/en-us/articles/18809437531420-Centralized-Action-Items-in-account-dashboard)
  подтверждают ценность task objects, но отдельный cross-meeting hub сейчас не
  нужен GRAF.
- [Krisp sharing](https://help.krisp.ai/hc/en-us/articles/10386573495196-Sharing-your-meetings-with-Krisp)
  и [templates](https://help.krisp.ai/hc/en-us/articles/26708055686044-Meeting-Notes-Templates)
  показывают два полезных принципа: sharing — отдельное осознанное действие, а
  формат меняет приоритеты результата, не сам контракт доверия.
- [Granola AI-enhanced notes](https://docs.granola.ai/help-center/taking-notes/ai-enhanced-notes)
  хорошо разделяет human и AI provenance; [sharing](https://docs.granola.ai/help-center/sharing/sharing-notes)
  сохраняет явную границу распространения.
- [Otter conversation page](https://help.otter.ai/hc/en-us/articles/5093228433687-Conversation-Page-Overview)
  и [action items](https://help.otter.ai/hc/en-us/articles/25983095114519-Action-Items-Overview)
  связывают summary/action с conversation context. При этом destructive
  [summary regeneration](https://help.otter.ai/hc/en-us/articles/25846455610263-Regenerate-the-summary)
  — антипаттерн для GRAF; текущая candidate/accept модель безопаснее.
- [tl;dv AI notes](https://intercom.help/tldv/en/articles/7198123-ai-meeting-notes)
  подтверждает полезность timestamp evidence. GRAF делает эту связь системной
  для каждого доступного outcome item.
- [Microsoft Teams recap](https://support.microsoft.com/en-us/teams/meetings/recap-in-microsoft-teams)
  объединяет recording, transcript, notes и follow-up в одном контексте и
  напоминает проверять AI content. GRAF сохраняет тот же путь проверки без
  тяжёлого workspace.
- [Fathom overview](https://www.fathom.ai/overview) оптимизирует time-to-value:
  результат появляется без отдельной настройки после каждой встречи. Для GRAF
  это означает automatic candidate, но не automatic acceptance/share.

## Исследования качества summary

- [QMSum](https://aclanthology.org/2021.naacl-main.472/) и
  [MeetingBank](https://aclanthology.org/2023.acl-long.906/) показывают, что
  meeting summarization требует отдельного внимания к структуре, длинному
  контексту и разным типам результата.
- [FActScore](https://aclanthology.org/2023.emnlp-main.741/) поддерживает
  атомарную проверку фактов вместо одного общего quality score.
- [RoSE/ACU](https://arxiv.org/abs/2212.07981) поддерживает оценку покрытия
  атомарных content units, а не только similarity текста.
- [ALCE](https://aclanthology.org/2023.emnlp-main.398/) поддерживает отдельную
  оценку корректности attribution/citation.
- [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/) требует
  проверять важный факт в начале, середине и конце длинного входа.
- [BIPIA](https://arxiv.org/abs/2312.14197) подтверждает отдельный adversarial
  gate для indirect prompt injection в untrusted transcript.
- [OpenAI evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
  поддерживают task-specific, multidimensional evals и непрерывную регрессию.

## Решения

### 1. Automatic, но недеструктивный путь

После первой пригодной расшифровки GRAF сохраняет быстрый accepted baseline и
локально создаёт один durable quality candidate/dispatch intent. Model/network
работа остаётся асинхронной. Candidate не меняет accepted pointer и не попадает
viewer/share/export до явного «Использовать».

Альтернативы отклонены: ручной запуск замедляет первую ценность; automatic
overwrite/share создаёт риск незаметной ошибки и утечки.

### 2. Доказательство — часть item, а не декоративный disclaimer

Каждый доступный item обязан иметь минимум один canonical segment ref. Runtime
reject проверяет существование, точную sequence, уникальность и разрешённые
поля; prompt и held-out eval проверяют semantic support. Stored refs обогащаются
canonical timestamps, чтобы accepted и candidate UI использовали один seek
contract.

### 3. Консервативная семантика действий и решений

Decision — только финально принятая позиция. Action — только обязательство или
явное назначение. Предложение, пожелание, вопрос и обсуждение не превращаются в
action/decision. Owner/due разрешены только у action и только при прямом
подтверждении; generic speaker label не является именем.

### 4. Компактная IA сохраняется

Feature 138 остаётся визуальной основой: «Кратко → Действия → Решения →
дополнительные разделы». Исправляется candidate/shared projection, aggregate
state и evidence interaction. Не добавляются dashboard, task hub, chat, badges
на каждый пункт или ещё одна постоянная панель.

### 5. Eval — hard gates плюс полезность

Нельзя усреднять критическую hallucination. Неподтверждённый decision/action/
owner/due, неверный attribution или успешная injection делают пример failed.
Отдельно оцениваются precision, recall/coverage, restraint, states и long-context
position. Held-out gate использует worst example; среднее остаётся только
диагностикой. Judge version change требует human calibration и operator approval.

### 6. Prompt release не равен prompt sync

Изменённый outcome prompt создаётся candidate version без `production` label.
Promotion возможен только после versioned synthetic/held-out evidence,
expected-source serialization, operator approval и rollback target. Это
приводит hand-authored prompt updates к уже существующей governance модели
Feature 121.

## Не включаем сейчас

Cross-meeting task hub, CRM/project integrations, AI chat, transcript editor,
notification center, новый UI framework, отдельный AI service и скрытый
map/reduce. Эти элементы не нужны, чтобы закрыть текущий путь до ценности.
