# Round434 — независимая проверка Start-owner requirements и scoped analyze

Дата: 2026-10-16. Финальный снимок нормативных SHA: 2026-10-16T02:17:38.436Z.
Lane: existing high-risk-product T116/#7444; reviewer-owned requirements gate.

**Текущий итог: bounded normative GO — CRITICAL 0 / HIGH 0.**
Все новые CHK001–CHK010 подтверждены. H2 закрыт после узкого перечитывания
исправленного quickstart п.4; полный исторический аудит не повторялся.
Это не source/runtime GO, не закрытие T116/T117/T118 и не разрешение commit/push.

## Идентичность и предел

Авторитетная рабочая копия:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Active feature — `specs/200-windows-desktop-app`, risk_lane high-risk-product.

Применён speckit-analyze для текущей ограниченной конструкции.
До/после analyze hooks отключены. Инструкция skill передаёт отсутствующий
в установленном prerequisite script флаг --require-spec: после read-only --help
использован поддерживаемый --json --require-tasks --include-tasks;
FEATURE_DIR и наличие tasks подтверждены. Это не запуск тестов/сборки.

Прочитаны актуальные scoped spec/plan/tasks/quickstart/research/data-model,
desktop/local-custody contracts, конституция и применимые guidance:
root router, guidance index, spec-kit-flow и product-gates.
Packed contract проверен как неизменённая нормативная зависимость;
логический v5, девять package-state keys и resource bounds не меняются.
Для auth boundary дополнительно прочитаны реальные WebView2Host/AppMain/
NativeCapture callers. Их нынешняя реализация не объявляется реализацией Round434.

## Findings

| ID | Severity | Место | Проблема | Минимальное исправление |
| --- | --- | --- | --- | --- |
| H2 (CLOSED) | бывший HIGH | quickstart.md, §Start-owner, п.4 | Прежняя фраза «остальные отзывают прежнюю authority» включала stale callback, способный ошибочно отозвать более новую authority. | Исправление независимо прочитано: valid current empty cookie read доказывает signed-out; только актуальные unreconciled/expired/reselection/calendar-authRequired дают unknown; stale document/nonce/Source игнорируется без изменения более нового auth/ownership state. Оба исхода проверяются раздельно. |

CRITICAL отсутствуют; конституционных конфликтов в scoped construction не выявлено.
Открытых HIGH/MEDIUM в этом срезе не найдено. Нового человеческого
продуктового решения не требуется; stale fence согласован.

Закрытое замечание H1: прежнего «native observation с пустым token» было
недостаточно. Реальный WebView2Host::reconcileAuthSessionForDocument вызывает
string-handler до проверки reconciled; expiredSession/workspaceReselection и
AppMain Calendar authRequired тоже выдают пустую строку. Добавленные plan п.2
и quickstart п.4 теперь требуют различать источник наблюдения на существующем
WebView2Host → AppMain → NativeCapture boundary. Не всякий setter(empty)
доказывает signed-out. Не требуется новая сеть/окно/дисковое поле.

## Доказательства новых десяти критериев

Ссылки на пункты — текущий plan §T116: исходный владелец до audio admission;
quickstart §T116: Start-owner и аварийное восстановление.

| Критерий | Текущее evidence | Итог |
| --- | --- | --- |
| CHK001 | spec FR-012/013/014 и Session2026-10-16; plan п.2 и source-boundary addition: confirmed owner / proven signed-out / unknown; failed/default/expired/reselection не signed-out | PASS |
| CHK002 | plan п.1–2: sole genuine StoreOwner, непереиспользуемые UUID, confined path, conflict при row/alias/directory; запрет backfill обоих markers | PASS |
| CHK003 | plan п.1,3,6; custody Start-owner; data-model durable Start-owner: full protected queue BOTH/readback/adoption до factory/audio; не новый формат и не durable FileId | PASS |
| CHK004 | plan п.4; custody Start-owner: preparing/active/finalizing/partial worker fences до actual drain, независимо от UI | PASS |
| CHK005 | plan п.5–6,8: exact reservation update, immutable owner, no duplicate enqueue; server/deletion/alias conflict не перезаписывается | PASS |
| CHK006 | plan п.7–8; desktop ownership contract: только proven no-login marker допускает narrow native claim после full sealed-normal inspection и fresh commit/adoption; unknown/legacy не назначаются, HTTP0, current-auth display | PASS |
| CHK007 | plan п.6,8; custody §4–7: complete480 prefix отдельно от normal; zero/partial/key/IO/quota/ambiguous сохраняются без empty ledger/fallback/автодостройки | PASS |
| CHK008 | plan п.9–10; custody Start-owner: genuine BOTH positive short intent, exact-row retirement → commit/adoption → unchanged no-queue-alias physical discard; deletion operations/ack сохраняются | PASS |
| CHK009 | plan п.3,5–10; quickstart п.1–6 покрывают publication/adoption/birth/seal/claim/short cuts; исправленный п.4 раздельно задаёт current invalidation → unknown и stale callback → ignore без изменения нового состояния | PASS |
| CHK010 | spec offline Record/FR-015, plan intro/п.4/8/final evidence section; custody §5: Stop/resource limits/global admission=false, отдельные synthetic/native/installed/hardware/release | PASS |

## Scoped cross-artifact analyze — только T116 Start-owner construction

| Группа обязательств | Spec/contract | Покрытие tasks | Вывод |
| --- | --- | --- | --- |
| Durable Start classification, storage ACK до audio, offline при unknown | FR-012/013/014; desktop ownership; plan п.1–4 | существующая открытая T116 | Покрыто; stale acceptance согласован |
| Exact-row finalizer/cold recovery, прежний account immutable | FR-012/013; plan п.5–8 | T116 | Покрыто |
| Read-only package inspection не выдаёт writable/effect authority | custody §4–5; plan: readonly proof не становится writable и п.6 | T116 | Покрыто; capturing/finalizing не sealed-normal и не разрешение нового resume-writer |
| Narrow no-login manual claim/current-auth display; unknown/legacy no assign/no HTTP | FR-013/014; desktop ownership; plan п.7–8 | T116, существующие consumers | Покрыто; H2 закрыт |
| Short-row retirement, actual absence и отдельный deletion intent | FR-022; custody §7/Start-owner; plan п.9–10 | T116 | Покрыто |
| Отдельные validation/release и downstream migration | Constitution VI; quickstart; T117/T118 | T116 → T117 → T118 | Порядок не обойдён |

Проверено соответствие всех 10 новых quality groups существующей T116:
10/10 имеют task coverage; качество 10/10 PASS. Это не feature-wide coverage
22 FR/10 SC и не пересчёт готовности 120 задач.
В scoped construction после узкой повторной проверки: ambiguity/inconsistency 0,
duplication 0, CRITICAL 0, unresolved HIGH 0; blocking human clarification 0.
Unmapped scoped tasks нет; новая задача/issue не нужна.
T116/T117/T118 остаются open; GitHub не читался и не менялся.

Ранее post-seal insertion формулировки plan около1868/1896 перечитаны после
правки Main: Start-owner commit/adoption до audio, exact-row update после seal.
Нового противоречия с п.1–10 там не установлено.

## Весь каталог checklist и сохранённый baseline

До reviewer edits: 196 Markdown-файлов, 30 файлов с checkbox-строками,
420 checked / 10 unchecked.
Инвентаризированы и SHA-256 прочитаны для всех 196 файлов. Перечитаны все
154 пункта прежних 10 действующих checklist, 266 checkbox-вхождений 19
исторических reports и 10 новых пунктов. Исторические runtime narratives
целиком заново не читались и их старые PASS не переоценивались как current.

Прежние 194 файла (без Round410 report и нового checklist) совпадают с
сохранённым baseline byte-for-byte по aggregate SHA:
`98854ab3c8b80bd76dd87e003b726c85bc3f6415e0d6c53dd99b6dcbccd2053f`.
Алгоритм: SHA256 от конкатенации отсортированных basename + пробел +
SHA256(file bytes) + LF. Round410 report также сохранён без изменений.
Его старые нормативные SHA не выдаются за нынешние.

По текущим требованиям не обнаружено основания снимать прежние 420 отметок.
Они сохраняют свою исходную область: historical source/runtime пункты — только
история, не принятие нынешнего кода. requirements.md:22/0 сохранён без изменения;
исправленный acceptance cut подтверждён в новом CHK009.

После финальной reviewer правки: новый checklist 10 checked / 0 unchecked;
действующие checklist 164 checked / 0 unchecked;
исторические 266 checked / 0 unchecked;
**всего 430 checked / 0 unchecked**.
Отчёт не содержит новых checkbox-строк. После добавления отчёта файлов197.

## Текущие десять нормативных SHA-256

| Файл от корня repo | SHA-256 |
| --- | --- |
| specs/200-windows-desktop-app/spec.md | `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11` |
| specs/200-windows-desktop-app/plan.md | `cc214346492856b066a366f72e9a7ecd9c9916a729457e2c90fb2ff8cf778d0b` |
| specs/200-windows-desktop-app/tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| specs/200-windows-desktop-app/quickstart.md | `ff1814ed953048a7bc50d4a58c804e30a8b41c3b85ab7950daccc583906b69fe` |
| specs/200-windows-desktop-app/data-model.md | `bfc33ce67f61e4c389ac635a5707f719631f874a89b0e5b490a0eb81e6441ee8` |
| specs/200-windows-desktop-app/research.md | `d793491bd62d842a1a0f6dd5ad5c4d826da31b29b5c581a1bf83a909093d9ee2` |
| specs/200-windows-desktop-app/contracts/windows-desktop-contract.md | `8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4` |
| specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md | `38c86bcb8a600dcff0a76098099b1876c4d783238f39c44a8d3712dcce2c7f93` |
| specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

## Следующее действие и границы

Финальный узкий reread quickstart п.4 и всех десяти нормативных SHA завершён.
Из десяти нормативных файлов изменился только quickstart; остальные девять
совпадают с предыдущим снимком. Прежний baseline194 повторно совпал;
requirements.md сохранён: SHA256
`91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55`.
CHK009 независимо отмечен; повторный scoped analyze CRITICAL0/HIGH0.
Requirements gate пройден в указанном минимальном scope, не как приёмка кода.

После этого чистого requirements gate допустим только описанный existing T116 scope:
Start reservation/ACK, exact-row continuation, narrow unbound claim/display,
short retirement с прежним physical guard. Marker не новая authority.
На source review отдельно проверить actual callback provenance, включая случай,
когда token string не изменился, но valid empty observation/invalidation
должны различаться; поздний auth result не меняет записанный Start classification.
Нельзя выводить known-no-login из marker с отсутствующими/невалидными owner
fields или автоматически «чинить» такую строку: это следует из запрета backfill.

Reviewer изменил только start-owner-recovery.md и этот собственный report.
Код, нормы, tasks, constitution, GitHub, commits и cleanup не менялись.
Сборки/тесты/SDK/VM commands не запускались. Прежний Round430 runtime не
переиспользован как реализация Round434. Публичные admission/release gates закрыты.
