# T116 — независимая проверка конструкции защищённой HTTP-интеграции

**SCOPED REQUIREMENTS / ANALYZE GO — C0/H0/M0/L0.**
Принята только конструкция plan.md:1995–2105 с обязательным prepare commit
для непустого flight. Это допуск к RED/реализации существующей T116/#7444,
не SOURCE/runtime/installed/release PASS и не закрытие T116/T117/T118/T120.

## Снимок и метод

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Оценены текущие dirty bytes, не только HEAD. Применён scoped `speckit-analyze`:
согласованность требований, модели, контракта, задач и RED; реализация не принята.
Конституция II/III/IV/VI, guidance spec-kit-flow/product-gates/release-and-validation,
FR-012/013/014/022 и local custody §5–7 сохраняют прежние границы.
before_analyze/after_analyze: по одному registered disabled hook, enabled0;
hooks не исполнялись. Governance/bootstrap/diff PASS сообщены main, здесь не повторялись.

| Проверенный файл | SHA-256 |
| --- | --- |
| spec.md | b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658 |
| plan.md | 9cdc5200419b6264d8e0c6a8c01aca5956b225661e674bba49acecbc4b90cf21 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| research.md | 4a7a1f9d8f7606a106b68e5b6194a0de8d75243508232c191f945f0fc0faa90e |
| data-model.md | c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7 |
| quickstart.md | 44c93c6558e8564aefe15a2180fd22d117f6368307d865b02253f9e0dffdf0b9 |
| contracts/windows-protected-local-custody.md | 598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee |
| contracts/windows-protected-packed-custody.md | a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5 |
| .specify/memory/constitution.md (от корня репозитория) | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |

## H1/H2 и ограниченный analyze

| Область | Основание и решение |
| --- | --- |
| H1 prepare | plan:2016–2032, model:605–608, research:3008–3011. Непустой выбор всегда публикует full candidate следующим поколением и ждёт обычный committed/adoption ACK, включая неизменный logical payload. false domain helper не является persistence failure. Пустой выбор не создаёт flight/commit/HTTP. No-change оптимизация и отдельный протокол исключены. Дополнительная metadata стоимость явно принята; SC-003 не ослаблен. |
| H1 feasibility | Storage/ProtectedCustodyMetadata.cpp:1546–1585 принимает полный bounded payload, проверяет overflow и задаёт target=base+1 без требования изменения строк. Это чтение совместимого primitive, не доказательство подключения caller или native PASS. |
| Владение/потоки | plan:2007–2014,2026–2037. Proof готовится и executor запускается storage worker; network выполняется отдельно. Native last release, включая launch failure, не передаётся UI. Сеть не удерживает единственный storage worker на время HTTP. |
| Result/adoption | plan:2038–2058; local custody:204–241,293–305. Один свежий candidate текущего принятого поколения объединяет server truth/status. До publication stale row/epoch отвергает результат с revalidation; после начала publish cancellation не отменяет readback/physical adoption. Pending/lost poll удерживает flight/result/busy/lease; ambiguous закрывает продолжение. Stop predicate учитывает flight и фактическое завершение, не timeout/закрытие handle. |
| H2 bytes/body | plan:2062–2089. Retained inspectProtected и те же production upload decisions; exact logical length/hash/ranges без plaintext reopen/re-encode. Parts default4MiB/clamp64KiB–16MiB собираются reads≤256KiB. shared<const CustodyBytes> и control block charged; request copy удерживает того же owner, обычный body пуст, оба body запрещены. |
| H2 lifetime/budget | plan:2078–2089, research:3004–3007. Body удерживается через SendRequest до ReceiveResponse либо закрытия request handle при ошибке; cancel не стирает память внутри native call. Тот же worker закрывает handle до release body. Request/response/hash/serialization и retained results учитываются до allocation, включая capacity/control/Debug. Owned64MiB/cache2MiB/pins32/jobs4 не увеличены. |
| Покрытие | FR-012/013/014/022 → tasks:568 T116; plan:1995–2105 → model:597–617 → contract:605–614 → quickstart:902–934. Новые endpoint/server/auth-policy/schema/UUID/idempotency/partSize не вводятся. Пробелов или противоречий C/H в этой конструкции не осталось. |

## RED и приёмка реализации — ещё не выполнены

- Actual NativeCapture ≥3000 generated кадров → protected insertion/adoption →
  release прежних owners → cold discovery → actual transport с подменой только
  send → single protected result commit/adoption → restart. Без READY setters,
  caller-created context/generation, реального аккаунта/сети/аудио.
- Непустой prepare без domain changes: никакого HTTP до full commit/adoption,
  generation продвигается ровно один раз; пустой выбор без commit/HTTP.
  Проверить отказ prepare, stale/cancel, pending/lost poll и repeated ACK.
- Exact bodies/hash/ranges/part indices на64KiB/4MiB/16MiB, tail/невыравненном
  диапазоне и resumed accepted ranges; wrong binding/degraded/discard,
  corruption/short read/hash failure без некорректного PUT/finalize/fallback.
- Result not_committed/ambiguous, fresh candidate при конкурирующей mutation,
  stale до/после publish, shutdown/update/network drain и actual worker last release.
- Body lifetime через delayed ReceiveResponse/cancel/error/handle-close,
  request copy без data copy; response/retained result/control/Debug allocations
  под общей квотой. Длительный send не блокирует EOS/finalizer.

Existing NativeCaptureStorageIntegrationTests, DesktopUploadRecoveryTests и
DesktopUploadCustodySmokeTests владеют этими проверками. Helpers/direct transport
PASS без scheduler/worker continuation не принимают срез. Native Release/Debug,
SDK caller/source map и SC-003 остаются будущими доказательствами.

## Сохранность и предел допуска

До отчёта:166 checklist Markdown, из них10 нормативных154 checked/0 open;
156 historical/context файлов отдельно256 checked/10 historical open.
Это текущий подсчёт, не повторное принятие всех старых критериев или SOURCE.
Tasks120/93/27; markers и задачи не менялись. Этот отчёт содержит0checkbox.
Единственная запись reviewer — этот файл. Код/tests/spec/plan/model/contracts/
quickstart/research не изменялись reviewer; сборки/VM/CUA/GitHub/network/hooks
не запускались, native301/304 не затронуты. Global storageWritable/localQueueComplete
остаётся false до всех HTTP/playback/delete/T120 consumers. T117 migration,
T118 whole-pipeline/100cycles, installed/hardware/macOS parity/release OPEN.
