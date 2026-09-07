# Implementation Plan: Полноценные итоги встреч

**Branch**: `239-full-meeting-minutes` | **Date**: 2026-09-04 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/239-full-meeting-minutes/spec.md`

## Summary

Заменить активный плоский договор `category_states + items` одним вложенным
протоколом встречи. Первый модельный проход извлекает факты из полной
закреплённой канонической расшифровки в хронологическом порядке. Второй
получает полный источник и извлечённые факты, возвращает тематическую
структуру и ссылки на сегменты. Сервер
проверяет ссылки; отдельный закреплённый вызов-проверка сопоставляет документ
с полной расшифровкой. Только прошедший обе проверки документ обогащается
каноническими таймкодами. Один принятый `protocol_json` используется интерфейсом,
summary-only, совместным доступом и Markdown/JSON-выгрузкой. Старый локальный
генератор и плоские рендереры удаляются из активного тракта; если у старой
встречи нет нового протокола, система честно предлагает сформировать его и не
показывает прежний формат.

## Technical Context

**Language/Version**: Python 3.13, vanilla JavaScript, CSS,
Jinja/server-rendered HTML

**Primary Dependencies**: FastAPI, Pydantic, SQLAlchemy async, PostgreSQL,
Temporal, Langfuse Prompt Config, LiteLLM, существующие cabinet renderer/player

**Storage**: PostgreSQL `MeetingOutcomeSet` с новым `protocol_json`,
`protocol_state` и `protocol_schema_version`; существующие slot/candidate,
Generation Call, transcript и source-revision сущности сохраняются

**Testing**: pytest unit/contract/integration, PostgreSQL/RLS, synthetic
prompt fixtures, закрытая проверка выборки по FR-028, HTML/Markdown parity,
`infra/scripts/ci-local.sh --fast` и `--full`

**Risk / Validation Lane**: `high-risk-feature`; меняются AI-договор,
PostgreSQL-хранение, доказательность, пользовательский интерфейс, совместный
доступ и выгрузки частных встреч

**Release Gate**: актуальное указание владельца — только готовый проверенный
PR, без merge в master, релиза, deploy и production promotion. Общий выпуск
готовых фич выполняется отдельной задачей владельца. Прежняя трактовка
разрешения на отдельный технический выпуск отменена; уже выполненное слияние
PR #6661 не считается выпуском протоколов или приёмкой качества.
Сравнение моделей уже выполнено отдельными опытами; до готовности PR обязателен
финальный exact run трёх реальных встреч (одна ≥3600 секунд) и семи controls.
Полный корпус не блокирует PR по указанию владельца от 2026-09-07.
Дополнительное прямое разрешение владельца от 2026-09-06 позволяет сейчас
удалить только специальный pre-call ограничитель ГРАФ в LiteLLM. Старому
production ГРАФ сохраняются только ответные метаданные без запрета запросов;
в новый код совместимость не добавляется. Ключи, маршруты и общие guardrails
не меняются; другой ключ для обхода ограничений не используется. Для отдельной
задачи выпуска подготовить согласованный порядок активации GRAF/root/LiteLLM,
exact-SHA release-gates и smoke; в этой задаче его не исполнять.

**Target Platform**: Linux server, web и macOS embedded cabinet; запись и
macOS capture не меняются

**Project Type**: monorepo web service с существующей macOS shell

**Performance Goals**: три стадии (извлечение, синтез и независимая проверка), каждая с
отдельной Generation Call; полная расшифровка без
скрытого усечения; не более 100 тем и 500 доказательных тезисов по закрытому
контракту; текущие Temporal payload limits и 5-second dispatch reconciliation
сохраняются

HTTP-прогон 2026-09-06 выявил недостаточность прежнего 120-second ожидания
подробного ответа. Транспортное ожидание по умолчанию — 900 секунд на вызов;
Temporal получает бюджет трёх последовательных стадий плюс 120 секунд на
проверки/хранение из результата resolve activity. Исторический записанный
результат этой activity воспроизводит прежний бюджет, не старый генератор.
Настройка транспорта не отправляется модели и не заменяет Langfuse config.
Неоднозначный вызов не повторяется; сравнительный опыт получает новую identity.

**Constraints**: модель не создаёт таймкоды; никакого рабочего v1/fallback;
смысловые поля создаются только LLM и не редактируются кодом (FR-035);
accepted truth остаётся единственным источником share/export; никакого нового
сервиса, UI framework или зависимости; частное содержание не попадает в Git,
GitHub и обычные журналы

**Scale/Scope**: все доступные пригодные встречи разрешённой базы без верхнего
лимита выборки; все существующие типы итогов получают одну полную структуру с
разным акцентом; один backend/cabinet/export тракт

## Constitution Check

**D239-P01: исправление включено владельцем в текущий PR.** Дополнение
FR-038/039 и договор допуска ниже заменяют прежнее ошибочное предположение,
что root-only integrity уже является полным разрешением на исполнение.
До reviewer/analyze исправленного design gate остаётся открытым; это не
обход требования и не разрешение выполнять promotion. Runtime третьей стадии
и новый допуск ещё не реализованы.

*Design assessment; окончательный gate фиксируется reviewer после проверки.
Пункты ниже описывают обязательства, не пройденные runtime tests.*

- PASS — capture, видимый индикатор и one-action Stop не затрагиваются.
- PASS — content-bearing вызов остаётся серверным и проходит только через
  закреплённый Langfuse root bundle и разрешённый LiteLLM gateway. Модель и
  параметры принадлежат Langfuse; отдельного ограничения на одну модель нет.
- PASS — один завершённый model call остаётся связан с одной Generation Call,
  полным transcript snapshot, raw response и validated result; retry не
  повторяет двусмысленный provider egress.
- PASS — Temporal, source/deletion fences, candidate immutability, accepted
  pointer, RLS и атомарная публикация переиспользуются.
- PASS — сервер канонизирует source IDs/times и отклоняет неподтверждённые
  ссылки; transcript остаётся недоверенными данными.
- PASS — share/export читают только принятый результат и не раскрывают
  owner-only candidate.
- DESIGN GATE — закрытая проверка реальных встреч выполняется в отдельном
  контуре оценки по процедуре quickstart; проверены read-only доступ к базе и
  настроенные адреса зависимостей. Запуск и качество ещё не подтверждены.
- PASS — старый формат не остаётся рабочим fallback. Исторические строки могут
  физически жить до обычного lifecycle cleanup, но активный код их не читает и
  не рендерит.
- PASS — Ponytail: добавляется один JSON-договор в существующий outcome set;
  новые сервисы, очереди и зависимости не требуются.

Post-Phase-1 requirements re-check 2026-09-06: reviewer подтвердил 38/38
критериев; см. requirements-review.md, финальная повторная проверка. Анализ
34 FR, 13 SC и 52 tasks не выявил незакрытых CRITICAL/HIGH; issue-sync полный.
Это gate требований, не runtime/quality PASS. Разрешённая оценка не является
production promotion или заменой пользовательских результатов.

## Design and Implementation

1. `outcomes/prompts.py` определяет один strict nested protocol schema и
   рекурсивный validator. Общий доказательный тезис содержит текст и 1–8
   ссылок `{sequence, quote}`; решение дополнительно имеет ссылку на принятие, задача — раздельные
   ссылки на действие, исполнителя и срок. Любой неверный ref отклоняет весь
   документ; частичного удаления доказательств или угадывания id нет.
2. `cli/langfuse_prompts.py` компилирует подробный adaptive meeting-minutes
   prompt для каждого существующего профиля. Все профили используют одну
   вложенную схему, личные разделы сохраняются по явному mapping в contracts.
   Root bundle закрепляет exact children `graf/meeting-outcome/extract` и
   `graf/meeting-outcome/verify`. Извлечение — общий для всех профилей закрытый
   список фактов и действий с отдельной модальностью обязательства и срока
   (см. data-model.md). Синтез получает полный transcript и exact extraction;
   verifier не получает extraction, чтобы не наследовать его пропуски. Он
   проверяет весь документ, финальные решения/обязательства и полноту
   по исходному тексту. `fail`, неверный ответ или неоднозначный вызов блокируют
   candidate. Проверяющая модель не объявляется безошибочным доказательством.
   В модельном представлении полные реплики остаются в исходном порядке,
   а повторяющиеся поля атрибуции выносятся в таблицу с точным индексом каждой
   реплики. Преобразование обратимо до всех полей canonical snapshot;
   ledger сохраняет исходный snapshot и точный фактический запрос. UUID/sequence,
   текст, времена и признаки неопределённости не сокращаются. Порядок полей
   схемы восстанавливается из закреплённого `required` перед отправкой, включая
   загрузку после канонической сериализации. Обе трансформации входят в
   runtime hash нового root, не изменяя маршрут модели.
3. `outcomes/ai_service.py` сохраняет проверенный документ непосредственно в
   `MeetingOutcomeSet.protocol_json`, после server-side canonical enrichment
   всех source refs по exact unique sequence, включая canonical UUID. Модельные
   ответы и validated тела extraction/draft/verification не содержат UUID
   в refs; protocol внутри envelope call 3 обогащён каноническими UUID/временами,
   а hash call 3 покрывает весь envelope. Преобразования старых ответов нет.
   Existing Generation Call, prompt snapshot, stale/deletion
   fences и публикация не меняют смысл. Извлечение, синтез и проверка имеют
   call_sequence 1, 2 и 3. Соответствие sequence/role/prompt задаётся в одном
   месте; универсальный граф стадий не добавляется. Повтор Temporal не вызывает
   модель заново. Синтез связан с exact extraction id/hash, проверка — с exact
   draft id/hash; publication proof требует всю цепочку, transcript/header/root,
   reparsing raw responses и реконструкцию каждого фактического запроса.
   Метаданные стадий сохраняются для observation-only доставки после удаления.
   Заголовочные сведения и имена замораживаются до первого вызова в снимке
   кандидата и входят в content_hash, не перечитываются при рендеринге.
4. Автоматический путь больше не формирует deterministic extractive baseline.
   До AI результата отображается честное processing/blocked состояние. Старые
   outcome sets без `protocol_json` не проецируются в пользовательский документ
   и не запускают прежний генератор.
5. Cabinet строит `MeetingProtocolView` из одного accepted/candidate document.
   Темы отображаются как `Контекст → Обсуждение → Предложения и альтернативы
   → Итог`; таймкоды находятся рядом с тезисом и используют существующий
   `data-seek-seconds` переход.
6. Markdown и JSON используют тот же protocol document. Markdown экранирует
   только контекстно опасные конструкции, а не обычную пунктуацию; служебная
   provenance не занимает основной документ.
7. Миграция добавляет новые protocol-поля без переименования template keys,
   default или slot/share привязок. Суффикс существующего идентификатора не
   выбирает старый runtime; новая schema_version определяет договор.
   Исторические плоские строки не преобразуются в выдуманный протокол; для них
   состояние — «нужно сформировать новую версию».
8. Закрытый run сохраняет полную инвентаризацию и закрепляет выборку по FR-028
   до первого вызова. Создаёт новые протоколы, проверяет ссылки и позволяет
   Codex сопоставить каждый выбранный результат с полной расшифровкой.
   Повторяющаяся существенная ошибка исправляется в общем тракте; после неё
   весь выбранный объём запускается заново. Непроверенные строки не PASS.
9. FR-036/037 заменяют ограниченный опыт config 4/high: единый config contract 5
   для generation/verifier/judges/reflection, без модельных defaults; root v3
   без route descriptor. Модельные параметры берутся только из Langfuse.
   Синхронизация текста/схемы требует exact source versions из Langfuse и
   сохраняет их модельные настройки; неизвестный параметр не теряется молча.
   Точный закрытый договор и порядок безопасного переключения описаны в
   contracts/meeting-protocol.md. Никаких новых зависимостей или routing layer.
10. FR-038/039: одна новая операторская строка-журнал `PromptRootPromotion`
    хранит полный root export, activation, qualification и успешное событие
    переключения с закрытыми схемами и хешами. Это F239-договор, не сокращённая
    реализация будущего F183/194/195/200. Таблица также владеет указателем
    текущего допуска; старый изменяемый MinIO LKG pointer удаляется из активного
    пути. Worker читает журнал, но не изменяет его. Типизированные ссылки
    адресуют точные поля строки; повторное чтение и проверка их полных тел
    обязательны перед каждой production-стадией и публикацией. Qualification
    создаётся только после вызова finalize_run и проверки закреплённой выборки и
    controls, не импортируется как произвольный JSON с PASS. Детали, первое включение,
    сериализация писателей и восстановление — contracts/meeting-protocol.md.
    Отдельный универсальный registry, сервис, подпись собственного формата
    и новая модельная политика не добавляются.
11. `dev` разрешается в точную версию один раз на весь evaluation run. Общий
    исполнитель проверяет отдельную EvaluationAuthority и изоляцию, а не
    считает callback разрешением. Она никогда не подходит production-пути.
    Полный export/Activation закрепляется в run-owned снимке до первого вызова;
    evaluation loader читает этот снимок без operator journal/Qualification.
    Поздняя Qualification сверяет exact identities/hashes, не будущий row ID.
    Старое продвижение/откат отдельных child prompts оптимизатором удаляется;
    его результат — только непомеченный кандидат для следующего root.

## Validation Plan

1. Unit: strict schema, nested normalization, multi-segment support,
   decision/action boundaries, owner/due restraint, quote/ref validation,
   prompt injection and Markdown punctuation; сохранность слов модели через
   validation/enrichment/render/export, без содержательной постобработки.
2. Contract/integration: migration, one ledger identity per stage, candidate
   publication, stale/deletion races, accepted-only share/export, RLS and
   historical-flat unavailable state.
3. UI: complete Russian section hierarchy, responsive layout, keyboard source
   links, seek/focus, task table, empty states, candidate/accepted/summary-only
   parity.
4. Synthetic quality corpus: multi-topic, revisited topic, rejected proposal,
   late correction, reassignment, unknown owner/due, multilingual and no-speech.
5. Private representative run: три разные реальные встречи, одна ≥3600 секунд,
   и семь controls; полное чтение выбранных источников по FR-029, безопасные
   агрегаты, отдельный счёт непроверенных строк; повтор после общей правки.
6. Closeout: focused tests throughout, `speckit-converge`,
   focused server/PG checks и exact-SHA `governance-fast` для PR. Полный CI
   не повторяется локально ради подготовки PR. Release-full, CD dry-run, deploy и production
   smoke принадлежат отдельной задаче общего выпуска и здесь не выполняются.

## Project Structure

### Documentation (this feature)

```text
specs/239-full-meeting-minutes/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/meeting-protocol.md
├── checklists/
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── db/{models/outcomes.py,migrations/versions/}
├── outcomes/{models.py,prompts.py,templates.py,service.py,store.py,ai_service.py}
├── cli/langfuse_prompts.py
├── api/{schemas.py,cabinet.py}
└── cabinet/{view_models.py,rendering.py,exports.py,egress.py,web_routes/browser.py}

apps/server/tests/{unit,contract,integration}/
changes/unreleased/
```

**Structure Decision**: изменить существующий outcomes/cabinet/export тракт и
переиспользовать его lifecycle и source controls. Новый пользовательский
артефакт — вложенный protocol document в существующем outcome set.
Операторский журнал допуска общий для всех стадий и не содержит частных текстов встреч.

## Complexity Tracking

Не добавляются отдельный summarization service, vector store, UI framework или
параллельный v2 renderer. Три стадии используют существующий durable call
тракт. 2026-09-06 read-only инвентаризация обнаружила 61 неудалённую встречу
с available transcript (max 110915 символов, 8298.768 секунд); это ещё не
semantic eligibility. После отрицательных двухстадийных опытов выбран один
полнотекстовый extraction перед синтезом и независимой проверкой. Все три
вызова получают полный источник; размер синтеза включает ещё и extraction,
размер verifier — draft. Текст не усекается. Если трёхстадийная проверка
выявит потерю дальнего контекста или нехватку входного/выходного бюджета,
до PR требуется явный пересмотр разбиения и полной проверки длинного источника,
новый root и полный повтор корпуса. Части по темам не отбираются эвристикой.
Скрытое усечение и исключение длинной пригодной встречи ради PASS запрещены.

Обновление design 2026-09-06 после root22: отдельный extraction — минимальное
изменение существующего тракта, не новый сервис. Новый root включает extractor
и обновлённый runtime hash; старый двухстадийный root не исполняется как новый.
Точное перенесение promotion/qualification/event binding проверяется в T065:
пока оно не доказано на runtime/publication, готовность к выпуску не заявляется.

D239-R01, 2026-09-07: два реальных опыта с разными моделями воспроизвели
ошибки копирования UUID и согласования UUID/sequence, несмотря на exact-copy
инструкцию. Убирается избыточный UUID только из модельного ответа. Источник,
валидация, evidence semantics, публичные UUID и source fences не сокращаются;
выбор фрагмента остаётся полностью за LLM. Изменяются существующие schema,
ref-validator и enrichment, без нового слоя сопоставления. Требуются новый
exact root/runtime, отрицательные проверки всех трёх стадий и publisher tamper,
затем новый полный corpus-run. До отдельного review/analyze этого уточнения
runtime-изменение не выполняется.
