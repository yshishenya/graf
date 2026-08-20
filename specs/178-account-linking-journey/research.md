# Research: Подключение email без тупиков

## Decision 1: отдельный `linked`-тип для сохранённого пространства

**Decision**: До переноса `owner_user_id` изменить личное пространство source
профиля на `kind="linked"`. Сохранить его ID, slug, содержимое, membership и
пользовательское имя; стандартное «Моё пространство» заменить на
«Пространство из другого профиля».

**Rationale**: Два `personal` пространства одного владельца запрещены partial
unique index. `corporate` дало бы пространству приглашения и team-admin
семантику. Новый закрытый тип остаётся доступным только через активное
membership и не получает personal-only billing, trial, referral или onboarding
привилегии либо corporate administration.

**Alternatives considered**:

- Снять unique index — отвергнуто: создаёт две личные entitlement-границы.
- Перенести встречи в текущее пространство — отвергнуто: меняет tenant boundary и stable IDs.
- Сделать пространство `corporate` — отвергнуто: обещает командные функции, которых пользователь не выбирал.
- Оставить владельцем merged source — отвергнуто: пространство нельзя безопасно активировать текущему пользователю.

## Decision 2: преобразование входит в существующую merge transaction

**Decision**: Под row lock повторно найти ровно одно source personal workspace,
проверить отсутствие его активной оплаты/календарного конфликта, изменить kind и
имя, затем выполнить существующие identity/membership/owner/session writes в
той же транзакции.

**Rationale**: Один root-cause write перед общим owner update устраняет unique
violation и сохраняет all-or-nothing/replay semantics без нового workflow.

**Alternatives considered**:

- Отдельная миграционная job — отвергнуто: создаёт промежуточное состояние и retry coordination.
- Catch `IntegrityError` после owner update — отвергнуто: чинит симптом после частичной работы.

## Decision 3: bounded preview показывает фактические provider IDs

**Decision**: Расширить `MergePreview` двумя упорядоченными tuples активных,
verified provider IDs и количеством доступных пространств. User-facing labels
строятся существующим provider registry/view-model mapping; неизвестный provider
получает нейтральное «Способ входа».

**Rationale**: Экран объясняет изменение профиля без email, subjects, tokens и
внутренних IDs. Он не рисует способы входа из mockup, которых нет в реестре.

**Alternatives considered**:

- Показать email/subject — отвергнуто: лишние персональные данные на recovery surface.
- Захардкодить Email/Яндекс/VK в template — отвергнуто: изображение не является источником auth truth.

## Decision 4: один экран, один компактный поток решения

**Decision**: Сохранить один существующий confirm route и template. Порядок:
итог и причина → «сейчас / после подключения» → два результата о пространствах
и данных → предупреждение о повторном входе → native `<details>` → primary и
safe secondary actions. Нумерованные секции исключены: это одно решение, а не
wizard из трёх шагов.

**Rationale**: Пользователь сначала понимает решение, затем сохранность данных,
затем последствие для входа. Дополнительный wizard увеличил бы тревогу и replay
поверхность без новой пользовательской развилки.

## Decision 5: blocker actions используют существующие маршруты

**Decision**: Map billing к `/billing`, calendar к `/settings/calendar`,
deletion/temporary state к account settings и повторному запуску. Для
самостоятельно неразрешимых role/meeting conflicts показать «Получить помощь»
только при настроенном безопасном support email, добавив metadata-only reference
из hash intent ID; иначе честно предложить возврат к настройкам.

**Rationale**: Каждая доступная кнопка реально существует. Не создаётся новая
ticketing система и не передаются email, raw IDs или meeting content.

## Decision 6: текущие trust boundaries не расширяются

**Decision**: Не менять proof states, CSRF, nonce, callback context, intent TTL,
idempotency, forced RLS или audit payload. Fresh preview остаётся обязательным
непосредственно перед mutation.

**Rationale**: Feature 157/175 уже доказали эти границы. Текущий дефект —
неподдержанная workspace classification и тупиковая presentation, а не
недостаток полномочий.

## Decision 7: intent хранит ссылки на точные proof records

**Decision**: Добавить nullable migration fields для initiating auth session,
verified source external identity, consumed callback state и optional provider
link state. Каждый новый intent заполняет их; confirm повторно проверяет точные
records. Legacy intent без bindings безопасно отклоняется как `proof_required`.

**Rationale**: Строки `email_proof_state/oauth_proof_state` описывают результат,
но не доказывают, какие одноразовые записи его породили. Точные foreign keys
сохраняют fail-closed behavior без токенов, кодов или нового proof workflow.

Одновременно settings provider callback обязан передавать существующий
browser-state cookie в общий verifier, а desktop provider start — включать уже
существующий external-auth continuation. Новые nonce или allowlist механизмы не
создаются.

## Decision 8: explicit disposition вместо общего переноса user references

**Decision**: Каждому FK на `user_identities` назначить одну из пяти политик:
active access переносится/deduplicate; eligibility следует merged lineage;
mutable external authority блокирует merge; sessions/devices отзываются;
исторические actor/audit references остаются source. Contract test сравнивает
полный model inventory с явной policy map.

**Rationale**: Общий `UPDATE ... user_id=survivor` разрушил бы audit lineage и
уникальные ограничения. Текущий неполный allowlist, наоборот, может потерять
доступ или дать второй trial. Явная map — минимальный fail-closed способ увидеть
новые доменные ссылки при будущих migrations.

Billing blocker проверяет capability, а не одно поле `state`: recurring,
entitlement, payment method, nonterminal operation/webhook и future paid/trial
state. Trial/referral/fair-use eligibility учитывает source rows через
`merged_into_user_id`. Pending join offers и active user share grants
переносятся/deduplicate; audit actors остаются неизменными. Whole-account close
доступен только из primary personal workspace.

Billing notification preferences объединяются privacy-safe: каждый optional
канал (`optional_email_enabled` и `optional_in_app_enabled`) остаётся включённым
только если он был включён в обоих профилях (logical AND). Нормативное правило
закреплено в FR-034 и account-linking contract. Calendar preferences и active
personal summary templates переносятся/deduplicate;
collision одинакового template key/version блокирует операцию. Незавершённые
uploads и requested exports блокируют merge, terminal upload/export rows и
неактивные sessions/devices сохраняют исторического actor.
