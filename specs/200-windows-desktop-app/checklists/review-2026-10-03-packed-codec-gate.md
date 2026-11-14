# Независимый допуск T116: typed packed codec — 2026-10-03

## Решение и граница

**PASS — качество требований ближайшего codec-only шага T116. CRITICAL=0,
HIGH=0; блокирующих уточнений в этой области нет. Пять нормативных чеклистов:
112 checked / 0 unchecked.** Предложенный API допустим без расширения области.
Это не проверка ещё не написанного кодека, не выполненные native tests,
не runtime/performance acceptance и не закрытие T116 или всей Feature 200.

Разрешённый предмет следующей реализации: типизированные DATA/NODE/HEAD
оболочки в памяти, exact wire/entropy/context/length/SHA проверки, bounded
DPAPI helper с сохранением v1 и адресные регрессии на искусственных данных.
Никаких файловых операций, публикации heads, создания proof или подключения
представления к рабочим данным этот допуск не принимает.

Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD
`99b00a579c24b50e320465b69d9a296038bc544d`. Значимые документы и предыдущие
исходники уже изменены; результат привязан к их SHA-256, не только к HEAD.
Lane: независимая проверка требований внутри действующего
`high-risk-product` среза хранения. Единственная запись рецензента — этот отчёт.

## Основания допуска

- Прочитаны применимые AGENTS и guidance по рабочим копиям, Spec Kit,
  product gates, validation/evidence safety; конституционные требования
  I/II/IV/VI, текущие storage-разделы spec/plan/tasks/data-model/quickstart,
  весь packed contract и codec-раздел базового v1 contract. Руководства
  `code-reviewer` и `ov-experience-memory` прочитаны самим рецензентом;
  прежний опыт использован только как подсказка процедуры, не как полномочие
  или доказательство текущего состояния.
- Пять нормативных чеклистов перечитаны, их фактические CHK markers
  пересчитаны. Исторические файлы каталога просмотрены как контекст области
  и прежних решений; их аудиты и испытания не выполнялись повторно.
- `review-2026-10-03-packed-custody-amendment.md:178` сохраняет исходный
  REQUEST CHANGES и последующее APPROVED C0/H0/M0. Исправления H1/H2/M1
  независимо сверены с текущими packed §§3/5/6: generation=selected base+1,
  exact protected Ref length/SHA для всех DATA/NODE/root до DPAPI,
  разделение live retention и разрешённого whole-object удаления.
- Round215 в `validation-2026-10-02.md:5038`, особенно решение main по T115
  и scoped analyze, принимается как документированный предыдущий этап.
  T115 теперь `[X]`, T116/T117/T118 остаются `[ ]`; текущий подсчёт:
  119 задач, 93 checked / 26 unchecked. Это не перенос прежнего общего PASS.
- `plan.md:1411` задаёт codec первым шагом, переиспользование
  ProtectedCustodyCodec primitives и отдельные последующие owner/tree/schema
  gates. `quickstart.md:475` определяет отрицательные проверки и не принимает
  sustained capture по одному codec или арифметике размера дерева.
- `.specify/feature.json` и prerequisites указывают именно эту Feature 200
  и канонический путь. В `.specify/extensions.yml` before_implement и
  after_implement hooks отключены. Рецензент hooks не запускал и не менял.
- Issue #7444 независимо прочитан через GitHub connector: **OPEN**, T116,
  весь защищённый поток, включая codec. Отдельный primitive не закрывает
  задачу согласно её явным критериям. Issue/comment/label mutations отсутствуют;
  повторная синхронизация всей фичи не объявляется выполненной.

## Проверенный API и распределение ответственности

| Поверхность | Достаточный смысл внутри этого допуска |
| --- | --- |
| `PackedRecordAddress(kind, physical offset, selector, version, exact body length)` | Ожидаемый тип/адрес до DPAPI; только DATA, три NODE levels и HEAD, версии >0. EMPTY/ZERO — лишь inline refs, не защищённые records. |
| `sealRecord(context, address, body)` | Проверка адреса и exact body size; header128 и нужный checksum; per-record user DPAPI; exact envelope framing и cap. HEAD возвращается как cell16384 с нулевым padding. |
| `openReferenced(context, selector, exact protected ref, envelope)` | Только non-inline DATA/NODE; exact envelope size/SHA относительно ожидаемого Ref **до** DPAPI. Затем полный typed context/header, exact native plaintext length, internal checksum; результат — body и исходная record version. |
| `openHead(context, slot, cell, expectedGeneration=0)` | Отдельный HEAD-only вход: slot0/1 и соответствующий физический offset, exact cell/framing/zero padding. Неизвестная version разрешена только для cold HEAD; header version >0, при заданной expectedGeneration совпадение обязательно. Whole-plaintext checksum и context проверяются до возврата body/version. |
| `ProtectedCustodyPrimitives.{h,cpp}` | Общие borrowed bounded SHA и DPAPI helper с RAII wipe/LocalFree; packed exact output length проверяется **до** `CustodyBytes` copy. V1 wrapper сохраняет идентичные entropy/domain/version args, limits и публичное поведение. |

Typed address проверяет DATA selector в диапазоне 0..262143 и NODE base
в том же представлении с alignment64/4096/262144 по уровню; NODE_L2 base0.
Append DATA/NODE offset не ниже32896, alignment16, checked offset+length;
HEAD физически только128/16512 для соответствующего slot. Unknown kind/role,
flags/schema/magic, extra/truncated bytes и nonzero reserved/padding отвергаются.
Роли только canonical1/media2/playback3 из ожидаемого object context, не из
неподтверждённого plaintext. Node body4096, HEAD body128, DATA body1..262144.

Packed entropy берётся из ожидаемых context/address/ref/slot: ASCII
`graf.custody.packed.v2` без NUL, LE schema u16/kind u8/role u8, три IDs,
offset u64/selector u64. Header содержит record version, которая затем
сверяется; добавлять её к нормативному packed entropy не требуется.
V1 entropy остаётся `graf.custody.v1` с прежними IDs/role u16/kind u16/
selector u64/version u64. Нативный вызов user-scope с
`CRYPTPROTECT_UI_FORBIDDEN`, без LOCAL_MACHINE, prompt или key cache.

DATA checksum — SHA exact payload. NODE/HEAD checksum — SHA всего typed
plaintext с zero digest field; внешний Ref SHA покрывает exact envelope,
а не plaintext и не alignment gap. DATA полный envelope cap=P+4096,
NODE8192, HEAD cell16384. Native output после unprotect должен иметь ровно
128+body bytes: TRUE не разрешает short/oversized/corrupted output.
Это пределы принятия приложением, не предел внутренних allocations DPAPI.

**Возвращённый record сам по себе никогда не proof.** Проверка NODE/HEAD
checksum не декодирует семантику ссылок или descriptor. Происхождение Ref,
ожидаемый путь, child-before-parent/committed extent, допустимость ZERO/EOF,
tail/generation отношения, HEAD version=descriptor generation, paired-head
authority, birth, checked successor и commit ACK проверяет следующий
семантический owner/tree слой T116. Он обязан принять эти правила до
normal effects; текущий API не делает их необязательными и не создаёт
сериализуемый `verified=true`. Cold HEAD decode не является cold full closure.

## Нормативные чеклисты

| Файл | Всего | Checked | Unchecked | Результат в области codec |
| --- | ---: | ---: | ---: | --- |
| requirements.md | 22 | 22 | 0 | CHK009/012/019/020/021/022: exact bounds, traceability и прежний logical/ownership scope сохранены |
| audio-capture.md | 24 | 24 | 0 | CHK008/020/022: worker-only crypto, bounded resources и metadata-only evidence; нет новых audio claims |
| advanced-routing.md | 14 | 14 | 0 | Второй routing/privileged stack не вводится; область не меняется |
| security.md | 27 | 27 | 0 | CHK012: typed/ref/checksum contract; CHK015: deletion authority не в codec; CHK016/017/018/021: совместимость, данные и standard-user границы сохранены |
| ux.md | 25 | 25 | 0 | Индикатор/Stop, permissions и UI ownership не меняются; visual/accessibility acceptance не заявлена |
| **Итого** | **112** | **112** | **0** | **PASS только качества требований этого шага** |

Все прежние markers сохранены. Числа отражают текущие нормативные пункты,
не количество выполненных тестов и не переоценку всей реализации Feature 200.

## Обязательные проверки будущей разницы исходников

1. RED → реализация → GREEN для typed header/entropy и exact length;
   независимые LE fixtures с high-u64/version bytes, не только round-trip.
2. DATA, все NODE levels, HEAD: kind/role/ID/container/offset/selector/version
   substitution; bad magic/schema/flags/reserved/body size/truncation/extra;
   selector/range/alignment overflow; EMPTY/ZERO не принимаются как records.
3. Exact protected Ref size/SHA mismatch отвергается до native call,
   включая NODE/root с самосогласованным внутренним checksum. Valid external
   Ref SHA при испорченном internal checksum также не принимает record.
4. HEAD: оба физических slots, padded cell, nonzero padding, unknown cold
   generation только HEAD, version0 и expectedGeneration mismatch отказ.
   Один decoded HEAD не разрешает работу с singleton/broken pair.
5. DPAPI FALSE и TRUE+short/oversized/corrupt output, hash/allocation failure;
   exact packed length отказ до owned copy, native output очищается и
   освобождается на всех путях. Ошибка не выдаёт body/default ZERO/fallback.
6. После извлечения helper — адресные v1 block/index regressions, прежние
   entropy/caps/unsupportedPlatform/error semantics, отсутствие изменения
   decoder downgrade или full/no-rollback metadata правил. Fresh portable
   и Windows native evidence main относится к точным новым source/test hashes.

Это критерии следующей проверки, не незакрытые C/H требования. Рецензент
не выполнял сборок, unit/native/runtime tests, VM/audio/private inventory,
benchmark, install или release. Сведения о прежних GREEN в Round215 являются
предыдущими receipts main и не переносятся на будущий кодек.

## SHA-256 проверенного снимка

Пути относительно корня рабочей копии; для краткости `F` обозначает
`specs/200-windows-desktop-app/`.

| Файл | SHA-256 |
| --- | --- |
| F/tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| F/contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| F/contracts/windows-protected-local-custody.md | `5c2aad2bbcdee3b47c19df1a80574f9ab03a023f1d7ab59aef6948c1518f2509` |
| F/spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| F/plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| F/data-model.md | `ed7da763ddaa281f7cca2d05b9f4349eca9c9af5293d807008371e6e9a42c16d` |
| F/quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| F/checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| F/checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| F/checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| F/checklists/security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| F/checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

## Следующий шаг и сохранение работы

Main может продолжить именно codec-only шаг в существующей T116/#7444,
сначала регрессии, затем отдельный независимый source review новой разницы.
Рецензент доступен для этого review; task markers не редактируются.
Owner/tree/descriptor/birth/commit и полная интеграция остаются T116;
migration T117, полная матрица T118, physical x64/audio/install/accessibility/
signing/release имеют собственные незакрытые проверки.

Код, spec/plan/tasks/constitution, другие отчёты и markers не изменены этим
рецензентом. GitHub, hooks, Git index/branch/commits и установленное приложение
не менялись. Новые параллельные изменения main не откатывались и не присваиваются
этому review. Допуск действителен для указанных требований и этой области;
изменение normative bytes или границ API требует адресной повторной проверки.
