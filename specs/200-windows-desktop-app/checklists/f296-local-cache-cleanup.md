# F296 parity: качество требований защищённой очистки WAV

Дата: 2026-11-16. Lane: `high-risk-product` (storage/deletion/auth/UX).
Владелец: независимый reviewer Main/Aquinas; автор не отмечает пункты.
Статус: **12 отмечено /0 не отмечено**. Проверяется качество требований,
а не выполнение кода/тестов. **Requirements GO: C0/H0/M0**.
Analyze/issues и отдельный точный wire/codec gate T129 остаются обязательными.

- [X] CHK001 Однозначно ли определено удаление только exact protected media/WAV без изменения manifest/playback/canonical/recovery/queue/server identity и без смешения с purge? [Полнота, F296-R01, Contract §1]
- [X] CHK002 Полон ли свежий proof predicate, включая точные UUID/local namespaces, finalized-vs-active session, owner/device/origin и отказ по missing/unknown/error; разрешено ли явно расхождение contract/Mac по missing finalized local ID? [Безопасность, F296-R02, Contract §2]
- [X] CHK003 Ясно ли заданы включённые границы [-60s,120s],7days/30days, fractional UTC, фактический pre-delete now и запрет продления proof ожиданием? [Измеримость, F296-R02, Contract §2]
- [X] CHK004 Достаточно ли определены durable protected pending/completed, exact media identity/generation/inventory, typed ACK и no-delete при ambiguous/disk-full, без plaintext и обхода bounds? [Данные и ошибки, F296-R03, Contract §3–4]
- [X] CHK005 Покрыты ли все restart cut points, частично удалённый inventory, missing без receipt, replaced media, обе metadata slots/pinned roots и невозможность rollback к full? [Восстановление, F296-R03/R04, Contract §4]
- [X] CHK006 Ограничено ли partial evidence playback-назначением, без generic skip-WAV/full-upload proof и с полным M4A/retained validation/clone drain/account fences? [Совместимость, F296-R04, Contract §5]
- [X] CHK007 Определены ли fresh proof GET без WAV, отсутствие repair/re-encode/новой ревизии и безопасное поведение старого сервера/reader/rollback? [Совместимость, F296-R02/R04, Contract §2/5]
- [X] CHK008 Заданы ли точные manual confirmation/cancel/bytes/reasons/noop и native capability/nonce/epoch, доступность UIA/клавиатуры без угрозы Stop? [UX, F296-R05, Contract §6]
- [X] CHK009 Полон ли auto contract: тот же primitive, default/effective/operator override, single-flight/trigger/debounce/лимиты/oldest-first/pressure stop и приоритет capture? [Полнота, F296-R06, Contract §6]
- [X] CHK010 Отделены ли физически освобождённые bytes от logical WAV, неизвестное место от успеха, quota от permission, T127 от cleanup и неизменные95%/reserve/64MiB gates? [Непротиворечивость, F296-R01/R06/R07, Contract §1/4/6]
- [X] CHK011 Есть ли traceability R01–R08 → draft T128–T133 → deterministic/native/installed validation и независимый точный wire/codec gate до первой записи нового формата? [Проверяемость, Plan F296, Tasks Phase29, Quickstart F296]
- [X] CHK012 Явно ли отделены текущая авторизация parity, авторский draft и будущие review/analyze/issues/source/native/installed/release результаты без переиспользования исторического PASS для новых bytes? [Границы, F296-R08, Contract §7]

Источники: [Spec](../spec.md), [Plan](../plan.md), [Tasks](../tasks.md),
[Quickstart](../quickstart.md), [Contract](../contracts/windows-local-cache-cleanup.md).


## Первая независимая проверка 2026-11-16 — исторический результат

Проверены все 12 пунктов. **HOLD: C0/H1/M1**, открыты CHK002 и CHK011.
Отметки означают достаточность требований, не готовность реализации, native,
installed или release. Lane остаётся `high-risk-product`.

- **CHK002 / H1:** §2 уже безопасно требует оба local revision ID, но spec/plan/
  contract/tasks/quickstart оставляют решение по missing finalized local ID
  открытым. Закрепить wire-authoritative keep: оба local ID присутствуют и равны
  item; missing/null/malformed/mismatch → keep/0 удалений. Это узкое защитное
  отличие от Mac optional guard, основанное на F296 wire §43 и точной серверной
  связи MediaRevision с finalized session (`store.py:236–282`), а не новый вопрос
  владельцу. Явно задать отрицательные missing/null/mismatch и полный положительный
  proof в регрессиях T128; снять статус «открыто» в связанных авторских текстах.
- **CHK011 / M1:** blanket gate contract §7 и quickstart prerequisites требует
  T129 codec GO до любого implementation, но T129 зависит от T128. Развести:
  requirements/checklist + analyze/issues → только неразрушающий T128 fetch/parser/
  predicate/tests; отдельный точный wire/codec/consumer/rollback review → до
  изменения/активации partial format в T129 и destructive T130. Незавершённая
  точная раскладка wire — намеренная задача T129, сама по себе не blocker качества
  требований и не разрешение удаления. Полная frozen/installed приёмка — T133.

Доказательства каждого пункта, точные места и минимальные исправления:
`.dev/f296-local-cache-requirements-independent-20261116.md`.
Авторские файлы reviewer не менял; после правок нужна узкая повторная проверка
CHK002/CHK011 и согласованности затронутых ссылок.


## Узкая повторная проверка H1/M1 — 2026-11-16

**PASS / Requirements GO, C0/H0/M0. Все 12/12 пунктов отмечены.**
Первоначальные H1 и M1 закрыты. Десять ранее принятых отметок сохранены;
полная историческая проверка заново не запускалась.

- **CHK002:** contract §2 теперь обязывает оба local revision ID присутствовать,
  быть корректного типа и совпадать с item; missing/null/malformed/mismatch/
  legacy unknown → keep/0effects manual и auto, без подстановки из playback или
  active session. Явно обосновано узкое защитное отличие от Mac optional guard
  по wire §43 и exact server mapping. T128/quickstart задают missing/null/mismatch
  при прочем корректном proof и полный положительный proof; spec/plan/report
  согласованы с решением.
- **CHK011:** contract §7, plan, Phase29/T128/T129 и quickstart согласованно
  разрешают после общих requirements/checklist/analyze/issues только read-only
  T128 GET/parser/eligibility/tests. T129 сначала exact wire/version/limits/BOTH
  slots/old-reader/rollback review, затем codec/reader/writer code. Partial writes,
  активация consumers и delete не включены в T128; T130 зависит от T129.
  Frozen partial artifacts требуются для соответствующей приёмки, не старта T128.

Шесть фактических SHA256 совпали с
`.dev/f296-rereview-h1-m1-main-pins-20261116.json`; проверены относительные
ссылки и якоря затронутых разделов. Подтверждающие source/contract hashes
первого review неизменны. Полные текущие pins и границы в отдельном отчёте.
Авторские «0/12», «12unchecked», «весь unchecked» отражают этап подготовки,
а не текущий reviewer-owned статус; актуальны настоящие 12/12 и отчёт R2.
Это GO качества требований в lane `high-risk-product`, не product-source,
native/installed/release PASS и не новый допуск удаления. Авторские документы,
исходники, VM и Git reviewer не менял.
