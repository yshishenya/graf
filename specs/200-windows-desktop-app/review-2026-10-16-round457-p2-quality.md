# Round457 — независимый requirements/checklist/analyze gate P2

Дата: 2026-10-16. **Нормативный GO для узкого completed-layout continuation.**
Scoped analyze: **CRITICAL=0 / HIGH=0**. Это допуск качества требований к RED и
последующей реализации, не source/runtime acceptance и не закрытие P2/T116.

## Проверенный снимок и границы

Authoritative repository: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Независимо прочитаны branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, feature200/high-risk-product pointer.
Paths-only prerequisite указывает тот же каталог feature; его synthetic BRANCH
не подменяет фактический branch. Обычный режим prerequisite с записью state
не запускался. Checklist/analyze hooks disabled; state-changing hooks не вызывались.

Использованы speckit-checklist и speckit-analyze: проверка качества требований,
трассировки и противоречий. Прочитаны свежие plan:2505–end, research:3098–end,
quickstart:1099 и связанный контекст; constitution, применимые guidance,
spec FR-012/013/022 и Start-owner clarification, SC-005/006, tasks T116–T118/T120,
local custody §§2/4–7 и packed §§1–2/5–6. Прежняя construction B сопоставлена
с новой узкой веткой; research457 использован как техническое основание, не GO.

Все198 checklist-файлов включены в свежую инвентаризацию, подсчёт markers и
побайтовую сверку baseline. Полностью перечитаны применимые cold-prefix28,
start-owner10, packed-writer12, requirements22; дополнительно сопоставлены
security/privacy/package trust-boundary критерии. Не проводился повторный аудит
сотен исторических runtime narratives и не переносились их PASS на новый код.

Единственная запись reviewer — этот новый отчёт. Code/spec/plan/tasks,
checklist markers, Git/index, GitHub, VM, frozen456 и cleanup не изменялись;
сборки/тесты не запускались. Read-only shell checks включали hashes, чтение
артефактов, Git identity и prerequisite только `--json --paths-only`.

## Checklist / task gate

- **198 Markdown-файлов / 458 checked / 0 unchecked** по actual checkbox lines.
- Полный checklist198 digest: `6068a3186e5d261c4c5eef4dd10a11b86730f478273bfa3c10633b62ef7953ae`.
- Baseline197 без cold-prefix-recovery: `59bc24759fca8106f71173c1b12f19dade015ca887b0471249eaf58c5391d692`, совпадает с принятым446.
- Baseline194: `98854ab3c8b80bd76dd87e003b726c85bc3f6415e0d6c53dd99b6dcbccd2053f`, совпадает с report445. Исключения baseline194 — cold-prefix-recovery и три позднейших файла, перечисленные в report445.
- Digest — SHA256 конкатенации sorted basename + пробел + SHA256 bytes + LF.
- Tasks: **120 / 93 checked / 27 open**; T116 не отмечена и связана с существующей #7444. Live GitHub state здесь не проверялся и не изменялся.

Нового checklist или изменения markers не требуется: quality obligations уже
покрыты cold-prefix CHK002/005–012, CHK014–020 и start-owner CHK005/007/009/010,
а также packed-writer CHK007–012 и package gate CHK007/009–011.
Unused-only формулировки cold-prefix CHK001/003/020 описывают прежний этап B;
они не принимают произвольные started outputs. Новый plan457 задаёт отдельное
исключение только для полностью доказанного terminal layout. Старые отказы
partial/orphan/invalid peers не снимаются, полный P2 остаётся открытым.
Маркеры означают качество требований, не выполненную реализацию.

## Конструкция и scoped analyze

| Обязательство | Основание / результат проверки |
|---|---|
| Private existing-only acquisition | Plan457 п.1: отдельный internal mode, package-state writeExisting, пять ролей readExisting, непрерывные root/package/role leases. Общие identity/BOTH checks переиспользуются, unused guard не ослабляется. После effect-free отказа — новая полная acquisition без переноса старого proof через разрыв. |
| Prefix не authority | П.2 и research: store/object/role из genuine native identity; container ID только candidate из того же held handle. Prefix + authenticated closures обоих heads до refs/adoption. Нет write upgrade, replacement IDs или release/reopen внутри проверки. |
| Preflight не sealed proof | П.3: common value-only semantic validation с genuine readonly streams/metadata; public phase guards и private ProtectedInspection constructor не ослабляются. Нет synthetic Pair/ProtectedInspection или caller-supplied verified boolean. |
| Exact terminal/history binding | Только selected finalizing с live canonical, действующим bound degraded/artifact manifest, согласованными media/playback BOTH и recovery birth BOTH generation1. Closed parse связанных manifest snapshots, exact original session/privacy/time и recovery tuple. Unknown/newer-unbound/partial/invalid/unknown children сохраняются с отказом. |
| Один эффект | П.4: actual descriptors/hashes/metadata indices, полная проверка содержимого и повтор current package generation/BOTH refs под retained leases; затем только package generation+1 → sealedDegraded. Canonical/WAV/AAC/manifest/recovery bytes, indices и IDs не переписываются. Нет повторного retainPrefix/encoding/checkpoint/нового журнала. |
| Истина после публикации | Actual commit/readback, release временных readers, затем настоящий sealed inspectProtected. Только его результат допускает semanticVerified/prefix. Cancel/error/ambiguous не разрешают normal claim, blind retry на failed lease, cleanup или изменение queue/original owner. |
| Existing native lifecycle | П.5: acquisition на storage worker, hashes/AAC/final seal на прежнем executor, private mode в existing prepare/finish. Start/Stop, independent finalizer, cancellation/actual drain и quotas сохраняются; новой authority/pool/dispatcher нет. |

Дополнение main о wrapper acquisition(mode), optional discovery candidate,
readonly completedMetadata и bounded eachChild является согласованным способом
реализации этих пунктов, а не новым нормативным выбором. В source review нужно
проверить, что candidate не становится authority до полной проверки и что
неизвестные children действительно отвергаются, а не игнорируются.

Сравнение связанных manifest snapshots относится к неизменным исходным
privacy/time fields, не к равенству всего live и terminal JSON: terminal duration
и artifact descriptors могут отличаться по существующей construction B.
Такое уточнение не требует изменения плана; нельзя синтезировать время/паузы
или принимать историю из unbound metadata.

Обнаруженных CRITICAL/HIGH нормативных противоречий, нового пользовательского
решения или uncovered quality requirement нет. Конституционные encryption,
native ownership, truthful degraded outcome, bounded resources и deletion fences
сохранены. T116/#7444 покрывает этот участок; новых tasks/issues не нужно.

## Threshold и требуемое evidence следующего этапа

1. **Порог начала:** C0/H0, checklist458/0 и точный нормативный снимок ниже.
   Разрешён tests-first RED на реальном named before-final-seal fault456,
   освобождении failed writer/proofs и fresh cold acquisition. Никакой старый
   prefix parsed value сам по себе не разрешает commit.
2. **Узкий GREEN:** fresh completed layout → ровно package generation+1
   sealedDegraded; реальные BOTH/full content/WAV/full AAC проверки; exact
   original session/history/optional times, пять members/IDs и queue неизменны.
   Повтор sealed cold recovery без записи. Guard unused/refusals сохраняется;
   ожидание меняется только для доказанного completed layout.
3. **Ошибка и публикация:** actual hit/exit/source/PE/log; отказ до эффекта и
   possible-publication outcome различены. Никакого semantic success при
   failed final inspection, нормализации capture fault или повторной операции
   по failed lease. Физический readback не заменяется callback/value copy.
4. **Границы:** source correctness, resource/drain и затронутые регрессии ещё
   предстоит квалифицировать на окончательном source. Этот gate не принимает
   произвольные partial outputs, весь P2/T116, public admission, T117/T118/T120,
   installed/hardware/power-loss/release или выполнение Native integration.

## Точные нормативные SHA256

| Артефакт | SHA256 |
|---|---|
| spec.md | `0065a781efbfb52ef59f06ebe40b48e1cecd2f70d5c7e27f62a8570b43bc4e11` |
| plan.md | `2dc804d0304a15ac1eb60ea3e5c1db5f4963c86e822bd8549cf74a411188321d` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `e095b90218b9a92abeccd215547267b197cd59caa336ed5a4d6d8c85dae8cdc1` |
| research.md | `2ee67a0f130a5c30e3064ce960a312c54fab42eaf3c2debb500a826746502297` |
| data-model.md | `6023a5095e3c6726fd5a885c4cf46c573dd8acc31235e0eb2d914460c33f8214` |
| contracts/windows-desktop-contract.md | `8bdafda168ea3f23407bbf70ea73ddf9bca1e27f1c38a1cfcbb6407a625cbba4` |
| contracts/windows-protected-local-custody.md | `a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490` |
| contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Удаление только нового append plan/research и вставки quickstart **в памяти**
восстанавливает их предыдущие принятые SHA соответственно
`2d1f170a0345ef0201848f6d0a934f973db596f001fa7c431e2b973c702bdd1e`,
`6c1b4432fc37af7eb97f7d9202072344b0c8e5ccf7724d26ad3081ec8b79f716`,
`3eb4f3a05a4295025a149ecbb91b4cce71d4caacbf94f19f24d9631f16e25c12`.
Остальные семь нормативных hashes неизменны.

Current Windows **216/216 exact** по frozen456 GREEN3 manifest
`a6774514da8a14b6ef5726970194537a5402ee8e6c17bf6fa37a4500ef87af94`,
несовпадений0. Это подтверждает отсутствие source edits перед этим gate,
но не runtime новой конструкции. Frozen456 не изменён.

**Итог: bounded requirements/checklist/analyze GO к RED457.**
Полный P2, T116, public/installed readiness остаются OPEN.
