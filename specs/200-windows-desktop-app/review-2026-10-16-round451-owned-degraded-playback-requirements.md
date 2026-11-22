# Round451 — owned-degraded local playback requirements preparation

2026-10-16. Independent reviewer, high-risk-product, existing Feature200 T116/#7444.
**Статус: PREPARATION / final requirements-analyze gate PENDING scoped plan.**
Это не implementation/runtime GO. Main ещё не сохранил новый admission/cuts append
на момент проверки; production этого среза reviewer не менял и не принимал.

## Fresh baseline

Authoritative repo /Users/yshishenya/Documents/crisp-worktrees/200-windows-followup,
branch codex/200-windows-followup, HEAD
b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1. Active feature.json и supported
check-prerequisites --json --require-tasks --include-tasks подтверждают Feature200,
owner codex/high-risk-product. Skill требует --require-spec, но local script
ранее установлено не поддерживает его; используется supported check и actual
чтение/hash spec. Before/after checklist/analyze enabled hooks0.

198 checklist files,452 checked/0 unchecked, aggregate
854d7bb9071c38cf7d08f16f2e9651e58a84cd97dcba66cea729de44a19c2e48 — unchanged.
Tasks120=93 checked/27 open, SHA
80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f.
T116 task:568 открыт, local mapping #7444:552; remote state сейчас не читался.
Исторические runtime reports не переинтерпретированы как current acceptance.

Все10/10 SHA совпали с принятым requirements baseline448/450:

| Artifact | SHA256 до draft451 |
|---|---|
| spec.md | 0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 |
| plan.md | cb5d5c9edeea9863ed8bc8354b59cd929ba554c9dcafb9dc20d882d80294ab08 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| quickstart.md | c352f1b9a4970a3468bb66e52638c377aefcf075c60876a9d06bb87364b25e38 |
| data-model.md | 4d03cbc8517403e1bd754dff0dc7aa877a21a03309aec5de1c1b8f5bacb1815f |
| research.md | 6c1b4432fc37af7eb97f7d9202072344b0c8e5ccf7724d26ad3081ec8b79f716 |
| contracts/windows-desktop-contract.md | 8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 |
| contracts/windows-protected-local-custody.md | 38c86bcb8a600dcff0a76098099b1876c4d783238f39c44a8d3712dcce2c7f93 |
| contracts/windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| .specify/memory/constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |

## Scope и требования, которые должен замкнуть draft

Заявленный main scope не требует нового user decision, schema или task.
FR012/013/014/022, T116, custody §§6–7 и immutable Start-owner contract дают
основания для local playback проверенного degraded artifact. Но plan:2411–2413
и cold-prefix CHK013 явно исключают quarantine UI из прежнего B. Это сохранённая
граница прежнего этапа, не противоречие и не готовое разрешение нового доступа.
Main должен связать следующий узкий этап с этой границей, не стирать её историю.

Пункты независимого review будущего append (не новые tasks/checklist markers):

1. **Exact owned-only eligibility.** Quarantined/capture_prepared, original
   nonempty valid user/workspace == current confirmed native account;
   exact session/local/directory/path, no alias/server/deletion/active-reservation
   conflict. Не blanket quarantine, не known no-login claim, не unknown/legacy
   backfill. Current B не получает A даже после успешного decode.
2. **Display не authority.** Только scalar evidence о verified playable
   sealedDegraded, привязанное к actual adopted value/account epoch/package
   context+generation. Duration/decrypt/canOpen alone не доказательство playable.
   Не передавать pair/proof/reader/path в WebView. Если display evidence устаревает
   после B, определить fresh inspection/publication без бесконечного poll/hash
   и без stale cache, привязанного лишь к неизменной queue generation.
3. **Fresh native permission/proof.** UI request не обходит fresh owner queue /
   exact-row/deletion проверку; actual sealedDegraded + full BOTH/hash/session/
   recovery/media/AAC evidence до audio. Тот же player/retained pair/token и
   read-only worker/executor boundary. Normal branch остаётся прежним; общий
   запрет quarantine не удаляется без отдельного узкого предиката/проверки фазы.
4. **Current commands и invalidation.** Actual current document/nonce/Source,
   auth epoch и current owner проверяются до/после ожиданий и при play/resume/
   seek; current auth/document invalidation отменяет, stale callback не портит
   более новое состояние. Не менять auth/network readiness всей записи.
5. **Delete/drain/concurrency.** Deletion intent/row change/exit/update/shutdown
   закрывают новые действия и отменяют старые; actual engine/readers/pins drain
   предшествует purge. Отдельно display→open, open→ready, ready→seek cuts;
   no timeout-as-success, no forceclose/no changed admission для живого Record/Stop.
6. **No new effect/status.** Queue/owner/status/reason/generation и protected
   bytes unchanged от inspection/open/play/seek. NoSend/HTTP0/no normal/Saved/
   uploadComplete и без repair/re-encode/new UUID. Existing local delete authority
   не расширяется. Prefix duration truthful, unknown original times не синтезируются,
   «X из Y» только при actual known Y; keyboard/accessible UI semantics сохраняются.
7. **Measurable evidence.** Genuine cold B sealedDegraded ownedA/currentB denial
   → actual A resolution/display/open/muted progression/pause/seek; unsealed,
   degraded nonplayable, wrong owner/unknown/no-login, integrity/IO/quota/cancel
   refusals и реальные stale/delete/drain cuts. Actual source/PE receipts, existing
   normal playback/revalidation/resource regressions; no inherited450 runtime GO.

Специальный риск для draft: B может изменить package phase/generation без queue
mutation. Старый display result для того же queue snapshot не должен навсегда
скрыть новый playable result либо авторизовать другой package. Нужна явная
invalidation/refresh привязка существующего value flow, не новый cache service.
Это пункт проверки draft, а не найденный defect ещё ненаписанного кода451.

## Checklist / analyze решение на этом этапе

Existing cold-prefix CHK013/014/017–022, start-owner CHK004–007/009–010,
security bridge/custody и UX truth/accessibility покрывают сохраняемые границы.
Новый самостоятельный checklist пока не создан. После actual append оценить
нужность лишь небольшого дополнения existing checklist для нового разрешения;
старые checked markers не дают ему GO и не будут молча переосмыслены.
CRITICAL/HIGH противоречия заявленного scope с существующими требованиями не
обнаружены; final scoped analyze и coverage verdict не завершены без draft.

Constitution прочитана; unchanged normative hashes/inventory подтверждены,
нужные Start-owner/B/custody/account/bridge/UX критерии перечитаны выборочно,
не повторялся аудит всех исторических runtime narratives. speckit-checklist
применён к качеству требований; speckit-analyze read-only до сохранения этого
отдельно разрешённого reviewer report. Никаких других writes, tests/build/VM,
GitHub/commits или checklist/task completion не было.

## Final scoped requirements / checklist / analyze gate — current append451

2026-10-16. **Нормативный GO только для указанного owned-degraded local playback
среза existing T116. CRITICAL0/HIGH0, constitution conflicts0, unresolved user
choices0.** Preparation pending выше — историческое состояние до сохранения
append; теперь прочитаны целиком plan:2417–2458, data-model:671–678,
custody:641–652 и quickstart:1073–1085. Этот gate не source/runtime GO.

После генерации шести unchecked requirements criteria reviewer независимо
оценил их по этим append и существующим auth/deletion/custody правилам:

| Item | Evidence / решение |
|---|---|
| CHK023 | Plan:2425–2430 exact owned marker/IDs/no alias/server/deletion/active; current owner в п.3 и custody append. Supported. |
| CHK024 | Plan:2431–2436 full content/AAC, context/generation adoption, scalar not proof и no duration-only; data-model runtime-only bool. Supported. |
| CHK025 | Plan:2437–2442 exact fresh queue/row including time/status/reason, phase sealedDegraded, retained proof/revalidation, unchanged normal branch. Supported. |
| CHK026 | Plan:2443–2446 и custody append/§7 сохраняют current auth/document/serial, cancellation и actual retirement; не заменяют drain flag/timeout. Supported. |
| CHK027 | Plan:2421–2422/2441–2446 и Constitution check исключают new authority/effects/pools/schema, preserve queue and noSend/HTTP/normal. Supported. |
| CHK028 | Plan:2447–2453 и quickstart451 задают genuine positive/negative/invalidation cases и existing regressions, без наследования прежнего runtime PASS. Supported. |

Изменён только существующий cold-prefix-recovery checklist: добавлены и после
оценки отмечены CHK023–028. В нём28 checked/0 unchecked; прежние22 markers и
граница CHK013 сохранены. Новый файл checklist/task/issue не создавался.
Fresh aggregate: **198 files /458 checked /0 unchecked**,
SHA6068a3186e5d261c4c5eef4dd10a11b86730f478273bfa3c10633b62ef7953ae.
Tasks по-прежнему120=93/27, T116 open/#7444 local mapping. Requirements coverage
этого admission среза6/6 критериев → existing T116; это не coverage всей фичи.
Необеспеченных задач/duplicate tasks/новых ambiguity этого scope не найдено.

### Current10 normative SHA

Четыре изменённых main artifact и шесть unchanged baseline проверены actualhash:

| Artifact | Current SHA256 |
|---|---|
| spec.md | 0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11 |
| plan.md | 52ab9f58a277757c9c3f2eb44076eed7b9a876fb01d5441dd03d700e8b111ba7 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| quickstart.md | 4e43e6b6d187afe3b7ff2af099abf67cab4e04e9f32deea5f220723331d7d067 |
| data-model.md | 6023a5095e3c6726fd5a885c4cf46c573dd8acc31235e0eb2d914460c33f8214 |
| research.md | 6c1b4432fc37af7eb97f7d9202072344b0c8e5ccf7724d26ad3081ec8b79f716 |
| contracts/windows-desktop-contract.md | 8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4 |
| contracts/windows-protected-local-custody.md | a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490 |
| contracts/windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| .specify/memory/constitution.md | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |

### Source follow-up, не дополнительный нормативный blocker

Fresh-result требование исключает использование одной queue generation как
доказательства package phase. Existing worker уже отдаёт startup recovery
приоритет перед display и не запускает display в занятом network slot
(NativeCapture.h:2033–2047/2118–2130); UI creation также ждёт сброса
recoveryCancellation (:2794–2808). Plan вправе переиспользовать этот порядок
вместо нового invalidation/cache subsystem. Это не source GO: в actual diff
проверить, что новые admission predicates не обходят порядок и что прежний
display result не может пережить изменение actual package. Named acceptance
должен наблюдать usable display после настоящего B при неизменной queue;
смена account сама не должна быть единственным механизмом refresh.

Одного bool недостаточно: production open/seek должен независимо повторить
owner/row/deletion/package checks и получить actual sealedDegraded proof.
Отдельно проверить blocked deletion операций, незавершённый active package,
неplayable prefix, aliases и stale document/auth без назначения нового owner.
Требования already exclude эти случаи; настоящее выполнение остаётся будущим.

Skills: speckit-checklist (template/prerequisites/hooks прочитаны, criteria
созданы unchecked, затем оценены reviewer) и read-only speckit-analyze.
Supported prerequisites успешны; --require-spec не запускался повторно, его
несовместимость известна, обязательные файлы явно прочитаны/hashed. Enabled
before/after checklist/analyze hooks0. Optional after_plan agent-context update
относится к main plan stage, здесь не выполнялся. Ни auto-commit, ни source/
spec/plan/tasks/GitHub/VM/build/tests не выполнялись. Записи только в этом
report и reviewer-owned checklist. T116/T117/T118/installed/hardware/release open.
