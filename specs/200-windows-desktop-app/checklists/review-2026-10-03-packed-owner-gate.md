# Независимый requirements-quality gate: packed owner и physical IO

Дата: 2026-10-03. Риск существующего среза: `high-risk-product`.

## Решение

**PASS качества требований ограниченного prerequisite: C0 / H0.**
Блокирующего уточнения spec по Windows sharing/writable mapping или данным
предложенного physical API не выявлено. Можно начинать синтетические RED-тесты
и последующую ограниченную реализацию шага 2 внутри существующей T116 при
сохранении остальных обязательных gates. Это не их повторное подтверждение.

Принимается только continuous native GuardOwner и positioned typed ciphertext
IO с переиспользованием confinement существующего ProtectedCustodyFiles.
Произвольный публичный `writeAt` исключён. Limited empty-g1 preparation и
публикация полной HEAD-cell не дают logical ACK, cold closure или tree proof.
Полная T116 не сокращена и остаётся открытой; T117/T118 также не принимаются.

Рабочее дерево: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Это грязное совместное дерево: HEAD не представляет все прочитанные bytes.
Нормативный снимок отдельно связан SHA-256 ниже. Чужие изменения сохранены.

## Область и основания

Рецензент лично прочитал навык `code-reviewer` и применил его критерии
корректности, безопасности, обработки отказов и проверяемости к требованиям,
не к ещё отсутствующим исходникам owner. Учтены прочитанные AGENTS/guidance.
После уточнения пользователя проверка завершена в узкой области:

- Пять нормативных checklists: requirements, audio-capture,
  advanced-routing, security, ux; все 112 существующих пунктов.
- Текущие spec/plan/tasks/constitution; packed contract §§2/5/6/7 и
  quickstart §14. Прочитанные ранее материалы не заменяют эти требования.
- Последние уточнения main: один private synchronous RW HANDLE,
  FILE_SHARE_READ, non-inheritable; OVERLAPPED offsets с mutex;
  validate+append immutable typed envelopes после actual EOF;
  отдельная full HEAD-cell publication; shared owner у jobs/read results;
  reuse State/inspect/security/retained ancestor handles через friend в том же CPP.

Plan:1440–1461 прямо задаёт порядок в существующей T116: codec → native
continuous owner/positioned append/flush/readback/heads → persistent tree и
pinned Reader/Clone → measurements → strict metadata/consumer integration →
T117 → T118. Поэтому отдельный физический prerequisite допустим: последующие
семантические обязанности не вычеркнуты и не объявлены выполненными.
Tasks:566–568 сохраняет design-only T115 и полный открытый T116. Его метка
CRITICAL означает незавершённую реализацию обязательного потока, а не новый
нормативный C finding, запрещающий начать согласованный prerequisite.

Spec FR-012/013/014/022, constitution II/III/IV/VI сохраняют отсутствие
plaintext fallback, полную metadata authority/no rollback, доступ и delete
intent, видимость/Stop, независимое ревью и раздельную приёмку. Шаг не вводит
другую криптографию, dispatcher, очередь, сервер или второй storage lifecycle.

## Нормативные C/H и уточнения

| Вопрос | Основание и решение |
| --- | --- |
| Continuous same-file ownership | §2 требует actual native identity/confinement и непрерывный HANDLE, а не pathname или reopen. Предложенные private RW/share-read HANDLE и shared ownership соответствуют этой границе. C/H нет. |
| Writable handle/mapping | §2 и quickstart §14 уже требуют отказ при существующем внешнем writable handle/mapping либо неизвестном результате проверки. Нельзя ослабить это до «не нашли открытый FileStream». Отдельное product/spec решение или private inventory для старта не требуется; native отказ и синтетические проверки относятся к следующему source/test gate. |
| Positioned synchronous IO | Worker-only serialized offsets и chunks≤256KiB сохраняют §2, без общего caller file pointer, async dispatcher и раннего release по cancel. OVERLAPPED здесь задаёт адрес, не обещает асинхронное завершение. Нормативного требования перейти на async нет. |
| Данные API | Входы ограничены sealed prefix, immutable typed records и full HEAD cells принятого wire. Нет generic arbitrary writeAt, plaintext producer, новой persistent схемы или caller-выданного proof. Exact enum/методы относятся к реализации, не требуют нового spec. |
| Empty g1 | §5 допускает CREATE_NEW prefix + две independently protected heads с exact empty descriptor. В prerequisite допустима только физическая подготовка/flush/readback; результат не устанавливает логическое доказательство. Existing-open prefix-only не является cold proof. |
| Non-atomic HEAD | §5 уже определяет ambiguous с первой попытки head write, sticky fault и запрет next commit/GC/normal effects до reconciliation. Physical publication не подменяет paired logical commit. C/H нет. |
| Ресурсы и lifetime | §2/§6 и quickstart §14 задают pins32/process, jobs4, owned64MiB до allocation, actual completion и удержание results. Новый общий native-job counter в существующем memory слое допустим; dirty4 не заменяет jobs4. |
| Полная T116 | Tree diff, paired ACK, full cold closure, retained roots, versioned metadata, adapters/consumers и measurements остаются последующими обязанностями. Их отсутствие в prerequisite не размывает полную задачу. |

Новых нормативных C/H: **0/0**. Отсутствие этих findings не утверждает
безошибочность будущего кода и не переносит результаты codec/VM на owner.

## Точные границы ограниченной приёмки

1. **Confinement до effects и после readback.** Переиспользовать private State,
   inspect/security и удерживаемые ancestor handles. Проверять actual paths/ACL,
   store/object handles и IDs, исходный FILE_ID_INFO, reparse/hard-link и
   default-only streams. Enumeration bounded; неизвестная/неполная проверка
   отказывает, не считается отсутствием ADS. Strict share-read store-ID guard
   для packed acquire должен существовать до content effects. Поведение v1 не
   ослабляется ради reuse directory metadata.
2. **Один HANDLE и один lifetime.** Не выдавать HANDLE/file pointer, не
   наследовать/дублировать write capability и не создавать writable mapping.
   Jobs и возвращённые ciphertext results сильно удерживают тот же owner.
   Монотонный epoch отказывает при exhaustion; release/reacquire даже той же
   file identity не переносит RAM proof/cache. Writer revoke и observed fault
   не сбрасываются; revoke не закрывает owner под живым reader/result/job.
   Последнее закрытие — после actual IO, затем уничтожение proof и release pin.
3. **Bounded positioned IO.** Только worker; mutex сериализует физические
   chunks≤262144B. Проверить offset+length, native conversions и границы до IO
   и allocation; учитывать short/zero/error results. DATA envelope cap266240B
   не уменьшается до chunk cap: допустимая запись разбивается на chunks.
   Read result владеет ciphertext budget и shared guard; partial failure не
   выдаётся за verified logical bytes. Cancel/timeout не освобождает занятые
   buffers/owner, и нет обещания wall-time completion.
4. **Неизменяемый append.** Валидировать expected context/type/address/length
   принятого codec до записи. Append только после actual EOF с checked
   alignment; не truncate, не overwrite/reuse orphan tail. Prefix не становится
   изменяемой пользовательской областью. Наличие tail/EOF не означает
   committed extent или допустимость ссылки из tree.
5. **Отдельная HEAD операция.** Только полный cell фиксированного slot, с
   проверкой sealed wire, flush и same-HANDLE independent readback.
   С первой попытки записи outcome ambiguous; short write/flush/readback
   failure оставляет sticky failure и артефакты. Даже physical success не
   называется logical committed ACK. Совпадение одной cell не принимает пару.
6. **Ограниченный create.** CREATE_NEW, sealed prefix и две independently
   protected empty-g1 bodies: length0/root EMPTY/extent32896; exact descriptor
   comparison и полный flush/readback обеих. Сбой сохраняет orphan/partial
   birth; restart не достраивает его до normal authority. Результат — физическая
   подготовка, не sealed package/empty queue/tree proof. Existing-open проверяет
   prefix/native context, но не даёт cold closure.
7. **Общие ограничения до работы.** Pins≤32/process и admitted native IO
   jobs≤4, не квоты на каждого owner; резервировать до работы/выделения.
   Existing allocator учитывает живые ciphertext copies/results в owned64MiB.
   Completed job и retained result — разные сроки жизни: освобождение job
   slot не освобождает guard/budget живого результата. Disk reserve/physical
   orphan/temp peaks также не отменяются. Эти guards не доказывают полный
   process resource PASS до consumer integration.
8. **Вся logical authority позже.** Caller/tree layer обязан отдельно
   проверять selected proven base, checked base+1/target **до append/head**,
   structural diff, expected Ref envelope SHA, reachable closure/tail/extent,
   обе paired heads и exact selected peer перед ACK. Нет serialized verified
   flag, lazy cold admission, normal effects или GC по physical success.
   Возврат physical result не принимает descriptor/tree semantics.

Разрешённые ближайшие синтетические проверки: writable-handle/mapping
acquisition refusal; external write/delete refusal под guard; independent
offsets и chunk bounds; identity/path/ACL/ADS/reparse faults; short IO и cuts
на write/flush/readback; partial birth; overflow; sticky revoke/fault;
retained result/active job lifetime; pin/job/budget exhaustion и отсутствие
ослабления v1. Tree/forged-proof/cold-closure проверки §7 остаются следующему
слою; standalone owner не может вернуть положительный proof для них.

## 112 нормативных отметок

| Checklist | Checked | Unchecked | Проверенная граница |
| --- | ---: | ---: | --- |
| requirements.md | 22 | 0 | Полный scope, traceability, измеримость, отказы и отсутствие подмены задачи primitive |
| audio-capture.md | 24 | 0 | Worker-only IO, прежние cadence/Stop/budgets; нет новой audio acceptance |
| advanced-routing.md | 14 | 0 | Нет driver/service/второго routing stack; область не меняется |
| security.md | 27 | 0 | Confinement, data/authority, ambiguous failure, no rollback и deletion truth сохранены |
| ux.md | 25 | 0 | Indicator/Stop, permissions, offline/recovery и честность статусов не меняются |
| **Итого** | **112** | **0** | **Requirements-only PASS; не 114 и не implementation PASS** |

Все пункты прочитаны; затронутые storage/resource/authority требования
перепроверены по текущим основаниям. Прочие нормативные области сохранены,
а их реализация/аппаратная приёмка заново не объявляются проверенными.
Markers не изменены: для снятия/добавления отметок нового основания нет.

## Диагностика main и непроверенные результаты

Учтено только сообщение main о metadata-only synthetic .NET/Windows VM:
kept writable MemoryMappedFile после закрытия исходного RW FileStream →
RW/shareRead acquisition denied; после map dispose owner acquired → external
write denied. Сообщены `EXTERNAL_WRITE_DENIED=True`,
`WRITABLE_MAPPING_DENIED=True`, `DIAGNOSTIC_EXIT0`; первый null map name
отвергнут .NET, повтор с unique named map успешен, cleanup обоих synthetic
temp files выполнен main через finally. Reviewer запуск/лог не проверял.
Это один platform diagnostic, не тест отсутствующей owner implementation
и не exhaustive mapping/OS/filesystem matrix. Его отсутствие не меняет
нормативного требования fail-closed в §2.

Тесты/сборки/VM/устройства/реальное аудио/private inventory этим reviewer
не запускались. Source audit будущего owner не выполнялся. GitHub и commits
не изменялись. T116/T117/T118, full cold verify/tree proof/ACK, versioned
metadata/migration, весь generated pipeline/100cycles, measurements,
installed MSIX/physical x64/audio/accessibility/signing/release остаются
отдельными незакрытыми проверками. Другие analyze/issue-sync gates не
объявляются выполненными на основании этого отчёта.

## SHA-256 нормативного снимка

Пути относительно `specs/200-windows-desktop-app/`, кроме constitution.

| Файл | SHA-256 |
| --- | --- |
| spec.md | `7c212bf764b15961944d6ed67bb5fd36a6437c04d397ecd52b91eb28ff44bc90` |
| plan.md | `876bf76283c3d6d5c0586455d663a47b90ed5f4ec1510093c4d6a14e12731b84` |
| tasks.md | `ce8aaf949514d62c19e6b92e9c820e06b39f66dfcfe30b33b68124a59c6fff98` |
| .specify/memory/constitution.md (repo root) | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| contracts/windows-protected-packed-custody.md | `7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed` |
| quickstart.md | `2a1c494eafe087b46470de527b4af024970054adcd75bb5df2e1032312bac2f3` |
| checklists/requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| checklists/audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| checklists/advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| checklists/security.md | `0a321d6d52a4f56d8c2888bd3fa639c85a7c9dc82b5a6acdc2bc3f1bb7a40273` |
| checklists/ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

Рецензент создал только этот отчёт. Исходники, normative text/markers,
plan/tasks/constitution, пользовательские файлы и чужие изменения не менял.
