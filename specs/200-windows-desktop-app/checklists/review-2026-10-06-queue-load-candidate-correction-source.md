# Round265 — SOURCE: исправление SRC265-1

## Решение и границы

**Scoped SOURCE GO / APPROVE для исправленного queue-load candidate.**
CRITICAL=0, HIGH=0, MEDIUM=0 незакрытых замечаний в этом объёме.
**SRC265-1 CLOSED** на конечных исходниках265g/265j: проверка `npos`
и регрессия соответствуют принятому requirements gate. Это не GO всего
приложения, защищённой очереди, AAC или полного T116.

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserved.
Lane `high-risk-product`, существующий T116/#7444, без нового task/schema.
Requirements gate SHA
`8703c09d254a584a50a706eada5cf9270f3088a5681fd55308736c771007b8fe`.
Старый SOURCE REQUEST_CHANGES/NO-GO SHA
`f182dda24cd4c2821145543f6a40b455fb0c092a1a70156b25b02f5a16fd55f2`
остаётся правильным историческим решением для старого кода и не переписан.

Лично прочитаны `code-reviewer` и `ponytail-review` skills, исправленный
decoder, тестовая матрица, прежний SOURCE report и конечные exports.
Reviewer не исполнял Windows/EXE/тесты и не менял implementation.
Единственная запись — этот новый отчёт; source/tests/старые отчёты,
markers/tasks/spec/plan/GitHub/runtime/profile/commit не изменялись.

## Исправление и причинная проверка

`apps/windows/RecApp/Upload/DesktopUploadQueueService.cpp:307`:

```cpp
if (stampEnd == cursor || stampEnd == std::string_view::npos) return false;
```

Для обрыва сразу после цифр корневого `updated_at_ms` decoder теперь
возвращает false до `substr/stoull`, присваивания cursor и `compare(npos)`.
Следовательно, load использует ветку malformed/quarantine rename, а не
non-renaming execution-exception fence. Старое живое состояние не принимается
частично, required candidate persist и effects не выполняются.

Это ровно один production guard относительно265a2. Удаление только
добавленного условия в памяти даёт прежний CPP SHA
`c3370c1afeb0a000b68eb7df07454108e7c03689c62bf6679e0aab46934d93f9`;
файл при этой проверке не переписывался. H не изменён. Production grammar,
v3/read-v2 compatibility, caps и публичный API не расширены.

`apps/windows/Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp:256`
добавляет badStamp в существующую invalid matrix. Fixture находит именно
корневое `],"updated_at_ms":1000` и обрывает документ после числа. После
failed load проверены прежние непустые items/operations/ACK, quarantine и
запрет effects; writer count не вырос, backup равен повреждённым bytes.
Каждая итерация восстанавливает valid fixture и успешно reload; проверки
не отключены в Release. Это не отдельный новый framework/target/seam.

Genuine portable RED на старом CPP: raw содержит assert264 проверки backup,
0.68s/Test Failed. Main execution session25691/chunkd6999 сообщил build0/
test8 до guard. Отдельная frozen RED map не создавалась: не выдаю этот log
за independently mapped native RED. Последующая native Release/Debug и
portable3 проходят новую регрессию на нынешнем frozen коде.

Ранее проверенные свойства частного decoder, поздних swaps всех трёх vectors
и stamp, ledgerKnown/missing, required recovery persist и quarantine guards
сохраняются; correction их не меняет. Частный candidate остаётся обычным
значением, а не protected owner/authority. Это узкая повторная приёмка
исправления обязательного замечания, не заявление об универсальной строгости
старой JSON grammar или отсутствии всех возможных ошибок очереди.

Ponytail, только сложность: **Lean already. Ship.** Минимальный guard и reuse
существующей матрицы; безопасных удалений или лишних абстракций не найдено.
Эта формулировка не разрешает выпуск приложения.

## Лично сверенные конечные исходники

| Input | SHA-256 |
| --- | --- |
| Upload/DesktopUploadQueueService.cpp | `8d1384c54e6295d141d4ffd6d7902efd386e8b7748c8ea9a6389392e962aa50b` |
| Upload/DesktopUploadQueueService.h | `b3de437363e7e85adb19c649221408dd6f6ff0081932c51e69a46c634399fc6f` |
| Tests/GrafWindowsCoreTests/DesktopUploadQueueV2Tests.cpp | `1c4143cbdecdbd7b1ab7f2adfb14f386cd836eded84e72b6d9c2d01379eab8d7` |

External root `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
Все перечисленные JSON лично parsed; UTF-8 BOM убран только в памяти,
исходные exports не нормализованы. SHA считается по исходным bytes.
Обе карты и source_hashes конечных receipts лично сопоставлены с каждым
canonical input:172/179, mismatches0. Release/Debug raw paths и EXE maps
различены; старые a2/b2/d2/e2 не используются как нынешнее доказательство.

| Export basename | SHA-256 |
| --- | --- |
| source-queue-load-candidate-round265g-release.json | `60d49c9ece70d513b10b4557d87eb42e57c60bdb0ea933c563cf020a46e47215` |
| source-sdk-round265j.json | `a42b8b882c0e5517207824c471ec8926aec55feaca78424bbaa4c91003a678b7` |
| graf-f200-queue-load-candidate-round265-stamp-red-test.log | `b634f430a28e44f7b9e176458b9fd7a6c9a393a65307a7fc9f7653d7feee5837` |
| graf-f200-queue-load-candidate-round265g-release.json | `8061256fe92b6190944007aa733a20aba6953d8d5cafd86c2cdd280b760a3e2c` |
| graf-f200-queue-load-candidate-round265g-release-test.log | `87173653b28a94dff3a28a43bd1e1b58fb1d722e8eff007b8f5b8b852a1c3952` |
| graf-f200-queue-load-candidate-round265h-debug.json | `f8c8dc8147e33f6f690a7870d09b8fb104e047c5bbbe2c8138c386c2dd2a3810` |
| graf-f200-queue-load-candidate-round265h-debug-test.log | `065f8f7ae2546d607db7b48c55a4ba9ba708f3bbfe2db25060dc5c903f4cb966` |
| graf-f200-queue-load-candidate-round265-portable3-test.log | `68551635a24daa6a39d7a7c6d484b553dd18a801c473cbc743c6b84690f37cbd` |
| graf-f200-sdk-live-round265j.json | `a867b31403bd537b1ae74bca1521839950c06b5fc7a872734789285999504eb3` |
| graf-f200-queue-load-candidate-round265k-all.json | `83d8e6b18c79a49b3b4e080dccdbe3f64adc4181e18524dd7187eff9a430eee6` |
| graf-f200-queue-load-candidate-round265k-all-test.log | `78e14026b0de6c58b5535af833bd3073cfb7d4140ad0f9cfd3d38237516d615f` |
| read-queue-load-candidate-round265m.ps1 | `b342f9cd781efa68282dfda25812d08d5e09aa6395efb66e53d5dc6082d4107a` |

Release265g и Debug265h: terminal passed, configure/build/test0,6/6 raw
results; фактические Release/Debug commands и6 EXE hashes в каждом receipt.
V2 times0.51s/1.02s. Portable3:46/46, Mac paths, не native-platform proof.
SDK265j: terminal passed restore/build0,179 inputs; приложение EXE SHA
`733a15e15ea7d002d804a0fcb1f19868a620a7d786fb548c4a9b95f24e9d0de8`.
Общие времена14.32s/16.66s/21.83s — execution summaries main;
individual command/results/times лично прочитаны в raw logs.

ALL265k: terminal failed configure0/buildALL0/test8,50 unique tests,
**49 PASS/1 FAIL**, не GREEN. Единственный отказ #47NativeHashFailureTests,
assert395: original_frames48128, corrupt_decode_complete1/corrupt_frames0,
explicit_root_normal1/explicit_root_playback1/default_root_normal1,
invalid_package0/synthetic_sends1. Это прежний AAC_MDAT_COUNTEREXAMPLE,
не новое исправленное поведение и не новая очередь task. Main summary:
250.10s, runner exit1 FULL_NATIVE_TEST_FAILED; skip/disable не заявляется.

Read265m script лично прочитан полностью: сверяет именно Release265g,
Debug265h и SDK265j,172 mirror/NTFS inputs и12 focused EXEs,179 SDK inputs
и SDK EXE. **Actual main execution**, session54936/chunkb376a1 exit0:
обе `MIRROR_NTFS_SOURCE_AND_EXE_MATCH`, SDK
`SDK179_MIRROR_NTFS_SOURCE_AND_EXE_MATCH`, `ROUND265M_READONLY_EXIT=0`.
Это переданный main tool result, не личное reviewer выполнение NTFS и
не standalone exported stdout receipt. Соответствующий correction append
validation-2026-10-02.md:12021–12086 лично прочитан; F200 fragment прочитан.
Build/readback не доказывают install/signature/runtime/пользовательскую приёмку.

## Сохранённые ограничения и неизменность

Short-read/growth/seek race защищены source guards, без deterministic OS-race
injection. Нет exhaustive OOM, protected shared64MiB accounting, полной
проверки private stamp внутри writer callback или отдельного ACK omission
case. Empty ACK replacement покрыт прежней матрицей. Эти ограничения не
скрываются и не требуют новой схемы ради исправления SRC265-1.

Tasks SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`,
120/93/27 неизменно. T116–T120, protected queue owner/BOTH/bootstrap/
migration/admission/async hookup, H250/B1/legacy AAC, installed/hardware и
full application acceptance остаются открытыми. Source GO не закрывает их.

До записи126 checklist files:10 current normative154 checked/0 open,
отдельно116 historical/context256 checked/10 open. Старые historical open
не объявляются новыми нормативными обязательствами. После записи —127,
добавлен только этот report; все126 прежних hashes сохранены. Markers неизменны.
Registry: шесть before/after implement/analyze/checklist, в каждом1registered
git.commit disabled,0enabled/0dispatch. Ни hooks, ни commit/GitHub mutation
reviewer не выполнял. Risk lane и requirements policy не снижены.

**Итог: SRC265-1 закрыт; узкий queue-load SOURCE компонент принят на265g/j.
Полный Windows набор и цель приложения остаются НЕ GREEN.**
