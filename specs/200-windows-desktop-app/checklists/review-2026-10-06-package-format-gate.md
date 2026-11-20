# Round255 — независимая проверка требований общей границы формата

Дата: 2026-10-06. Feature200, существующая T116/#7444, lane
`high-risk-product`. Рабочая копия:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty.
Это проверка требований до правок, не SOURCE/runtime/installed approval.

## Решение и точная область

**REQUIREMENTS GO — 15/15; CRITICAL0/HIGH0/MEDIUM0/LOW0.**
Блокирующего неразрешённого уточнения для предложенной формулы нет.
Допущено только исправление существующей общей классификации
`LocalRecordingPackage::inspect`: normal/valid требует результата прежнего
`canonicalPlayback` независимо от наличия explicit custody root.
Корень продолжает ограничивать исключительно полномочие UI на playback.
Новый codec/decoder/schema/public API/adapter не вводится.

`plan.md:1586–1588`, dependency5, и T116:568 уже владеют исправлением
существующих format/hash/upload consumers; FR-011:454–458 и desktop §5
задают неизменные WAV/M4A/длительность. Отдельный новый task или смена норм
не нужны. Старый package-assembly gate B254-2 не разрешал consumer adoption;
здесь отдельно принимается узкая format correction, а не его обход.

Принята предложенная main семантика, не её будущая реализация:

```cpp
const bool playbackValid = playbackMatches && canonicalPlayback(playback, durationMs);
// Один вычисленный результат, без повторного MF открытия.
integrity = mediaValid && playbackMatches && (degraded || playbackValid)
    ? (degraded ? PackageIntegrity::degraded : PackageIntegrity::valid)
    : PackageIntegrity::malformed;
playbackAvailable = !custodyRoot.empty() && playbackValid;
```

Формула оставляет текущую degraded/prefix политику неизменной: проверенный
по bytes/hash degraded артефакт не становится normal и не получает playback
без принятого AAC. Она не превращает любое повреждение normal в degraded.
Независимые duration от valid WAV, wall-clock optional/drop-invalid bounds,
capture reason, UUID, exact legacy manifest shape, root/symlink confinement
и исходный размер4096 этой функции не меняются в данном исправлении.
Принятый будущий manifest64KiB/privacySegments остаётся T116/T120, не отменён.

## Подтверждённая причина и все производственные вызовы

| Место текущего исходника | Наблюдаемая граница |
| --- | --- |
| Recording/LocalRecordingPackage.cpp:36–42 | matchesArtifact доказывает confinement, bytes и SHA, но не AAC. |
| Тот же файл:61–95 | canonicalPlayback: portable=false; native COM/MF open, native subtype AAC, 48000Hz, mono, положительная presentation duration и разница<=100ms. |
| Тот же файл:157–169 | Сейчас normal integrity требует только mediaValid/playbackMatches; canonicalPlayback вызывается лишь при explicit root для playbackAvailable. |
| Upload/DesktopHttpTransport.cpp:145–191 | Единственный packageTracks вызывает inspect без root, пропускает только valid, затем строит manifest/media/playback tracks. |
| Тот же файл:547–558 | packageTrackBytes на Windows проходит packageTracks; отрицательный пакет даёт нулевые размеры. |
| Тот же файл:993–1016 | upload(item,send) после прежних cancel/permanent/owner/token/send guards проходит тот же packageTracks; отказ -> invalidPackage до первого send. |
| AppMain.cpp:1941–1972 | updateLocalRecordings: worker inspect с custody root, проекция результата; не второй format validator. |
| AppMain.cpp:2170–2200 | open: worker inspect с root перед существующим UI handoff; root и независимость playback от upload сохраняются. |

Независимый `rg` по всему apps/windows нашёл эти три production inspect
call sites: один transport и два AppMain; остальные вызовы — тесты.
**P255-1 — подтверждённый существующий HIGH дефект продукта**:
исправные SHA/bytes произвольного playback допускают normal upload.
Это цель правки, НЕ открытый дефект предложенных требований.
Нулевой HIGH в verdict относится только к requirements gate, не к текущему коду.

Сам helper не вызывает ReadSample до EOF и не проверяет отдельный AAC-LC
profile/каждый stream/payload. Поэтому будущий SOURCE/validation итог этого
шага нельзя назвать полным proof декодирования, stream closure или всей
FR-011. V5LocalRecordingWriter.cpp:290–347 также по-прежнему имеет собственную
raw encoder/finalization модель; normalPackage() в V5LocalRecordingWriter.h
не является новым независимым format proof. Полная защищённая интеграция
и её validator/finalizer остаются следующей работой T116.

## Критерии требований

| ID | Критерий | Основание и решение |
| --- | --- | --- |
| R01 | Реальное общее место отказа, не новый primitive | PASS — inspect и все три callers прослежены выше, T116 dependency5. |
| R02 | Normal требует текущего AAC/type/duration результата без root | PASS — FR-011, desktop §5, явная формула; default-root bypass запрещён. |
| R03 | Один cached результат helper | PASS — reuse прежнего helper; UI root не определяет normal classification. |
| R04 | Bytes/hash/WAV/confinement не заменены AAC результатом | PASS — оба прежних artifact guards обязательны, канонический WAV и regex не ослабляются. |
| R05 | Degraded/prefix не выдан за normal и не уничтожен | PASS — исходный degraded branch сохранён; transport только valid, files/recovery не очищаются. |
| R06 | Playback остаётся независимо ограничен root и AAC | PASS — UI root&&playbackValid; degraded с настоящим AAC может быть playable. |
| R07 | Legacy status/time совместимость доказуема реальным AAC | PASS — исходные accepted shapes/optional bounds сохранены, native positive cases обязательны. |
| R08 | Portable/MF failure не выдаёт новый normal proof | PASS — portable helper false; native open/type/duration failures дают non-normal, без fallback. |
| R09 | Невалидные bytes с новым корректным SHA дают RED | PASS — не старый hash mismatch; default-root inspect и transport sends0 обязательны. |
| R10 | Duration mismatch изолирован от WAV/hash mismatch | PASS — настоящие AAC и независимый канонический WAV правильного SHA/length, разница>100ms. |
| R11 | Native positive upload/hash/state assertions не потеряны | PASS — реальные default V5 AAC fixtures вместо fake, прежние status/ranges/CNG/fences исполняются Windows. |
| R12 | Portable writer/queue assertions сохранены честно | PASS — fake encoder только RAW writer/state; no inspect valid; negative invalidPackage/sends0 отдельно от native wire proof. |
| R13 | IO не переносится в UI/capture callback | PASS — существующие worker callers сохранены, FR-012/021; API и scheduling не меняются. |
| R14 | Нет новых форматов, thresholds, dependencies/knobs | PASS — прежние AAC48mono/100ms, shape/hash/v5; native MF/default encoder reuse. |
| R15 | Scoped review не закрывает full storage/installed goal | PASS — T116/T117/T118, working-profile H250 и независимые аппаратные/release gates остаются открытыми. |

Scoped analyze: FR-011/012/014 и SC-003/006 -> existing T116,
**5/5 covered, executable task1, unmapped0, ambiguity0, duplication0**.
FR-011 исторически также T022/T037, SC-003 T022/T063; нынешний исправляющий
owner — T116, не новая отметка исторически выполненных tasks.
Constitution I/II: честная запись/Stop; III: серверный API и секреты;
IV: retention/deletion; VI: independent requirements/source/evidence —
сохранены. Scope GO не означает полный F200 analyze22FR/10SC/120tasks.

## Обязательные RED/GREEN и сохранение покрытия — ещё NOT RUN

1. V5LocalRecordingWriterTests: текстовая fake M4A с корректными bytes/SHA
   и valid WAV должна стать malformed, с root и без; RAW encoder return/hash/
   frame/duration/idempotent finalize/append-after-finalize asserts сохранить.
   Initial behavioral RED должен падать на сегодняшнем valid classification,
   не на ошибке компиляции, окружения или старой неверной SHA.
2. Native real default V5 encoder: 100frames/1s, valid WAV/M4A, inspect
   без root valid и playback=false; внутри root valid/playback=true;
   outside root отказ. Сохранить native degraded/playback/hash corruption.
3. Заменить M4A не-AAC bytes и пересчитать manifest playback bytes/SHA,
   не ломая exact shape или WAV. Оба inspect пути malformed/playback=false;
   production upload с синтетическим owned config/send -> invalidPackage,
   send counter0; реальные account/network/device данные не нужны.
4. Настоящий1s AAC при valid canonical WAV/manifest другой длительности,
   отличающейся более100ms: WAV bytes/header/hash полностью согласованы с
   manifest, M4A bytes/hash правильны. Отказ обусловлен AAC duration,
   а не прежним WAV guard. Проверить default-root upload sends0.
5. Legacy forms без capture_status и без wall-clock fields, current time fields,
   impossible stopped/start и invalid timezone bounds: на Windows тот же
   реальный AAC сохраняет positive valid semantics и drop-invalid-time.
   Фиктивный файл сохраняет parsing/time/raw-byte checks, но не valid assertion.
6. NativeHashFailureTests.cpp:268–300 — настоящий default encoder/100frames;
   прежние success retryableFailure/sends1/creates3/destroys3 и CNG create3
   fault invalidPackage/sends0/creates3/destroys2 сохранить буквально.
   MF guard не разрешает пропустить ни одну CNG failure assertion.
7. DesktopUploadRecoveryTests.cpp testUploadProblemResponses:479 и
   testSyncNotRetryableRecovery:645 — native real encoder/1s. Все прежние
   create/part/finalize/sync, supported reason/status/retryClass, accepted ranges,
   restart/no-requeue, immutable bytes/owner assertions должны исполняться
   на Windows; нельзя превратить матрицу в один invalidPackage test или skip.
   Portable: явно отдельный non-normal package/invalidPackage/sends0;
   portable не выдаёт имитацию за пройденные server stages.
8. CaptureFaultStateTests.cpp:235–325 — scenario0/30s keep threshold на Windows
   остаётся real encoder valid, остальные scenarios без accepted writer frames.
   Policy/currentness/finalizer/queue/restart assertions не ослаблять.
   Portable synthetic writer остаётся state proof, inspect non-valid;
   не менять 3000frames/30s policy ради более удобного AAC.
9. Interrupted/error/degraded fake artifacts сохраняют нынешний non-normal
   статус, trusted-prefix файлы и причины; независимый valid WAV duration
   остаётся доступен даже при invalid playback. Нет нормального upload.
10. Current Release/Debug/native/portable результаты фиксируются отдельно,
    включая все затронутые 4 suites, до SOURCE approval. Actual source input
    и EXE hashes обязательны; прошлые50/50 и46/46 не новые проверки.
    MF unavailable/Windows N non-normal — контракт качества требований;
    без конкретного выполнения не записывать tested PASS этой редакции ОС.

Реальные fixtures генерируются прежним default Windows V5 encoder, без новой
библиотеки, knobs, публичного helper или committed audio/container.
Изменённое portable positive покрытие заменяется Windows execution, а не
исчезает молча. В source report перечислить реально сохранённые assertions
и отдельно перенесённые native-only ветки.

## Существующие checklist markers и границы независимости

Перечислены и SHA-256 сверены все **103** прежних checklist Markdown files.
Действующие десять normative criteria: requirements22/0, audio24/0, routing14/0,
security27/0, ux25/0, launcher5/0, operation8/0, wire5/0, writer12/0,
privacy12/0: **154 checked /0 unchecked**. Критерии прочитаны; отметки
не переустановлены и не становятся runtime approval.

Физические markers всех103: **410 checked /10 unchecked**;
остальные отчёты256/10 — исторические повторные execution cohorts,
не дополнительные420 текущих требований. Unchecked — packed tree-source3,
packed writer-source4, cadence-source3; этим шагом не закрываются.
Исторические отчёты инвентаризированы/hashed, но не заявляется полный новый
audit каждого исторического execution. Personally прочитаны актуальные
consumer source/caller/test участки, применимые FR/SC/plan dependency5,
task definitions/traceability и T116–T120 boundaries, quickstart gates,
constitution/guides/PRD local buffer/current status. Это scoped requirements,
не переаудит всех прежних implementation rounds.

Sorted baseline (basename + space + SHA256 + LF):
`955821f0655d758ad2deed676f90c91f93e2861ed08cbd2d0140ff0fe60e6db8`.
Tasks: **120 =93checked +27open**, SHA ниже. Новых checkbox markers здесь0.
Extensions YAML parsed: before/after_analyze enabled hooks0.
Read-only analysis выполнен отдельно; сохранение этого reviewer report —
единственная явно разрешённая запись, не правка spec/plan/tasks/checklists.

## SHA-256 снимка до реализации

| Артефакт относительно canonical repo | SHA-256 |
| --- | --- |
| `specs/200-windows-desktop-app/spec.md` | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| `specs/200-windows-desktop-app/plan.md` | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| `specs/200-windows-desktop-app/tasks.md` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| `specs/200-windows-desktop-app/quickstart.md` | `565fd909cf3a79a6adfc21f7ab0e8ea146f850f2ddc146e115778e42ba29014c` |
| `.specify/memory/constitution.md` | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| `apps/windows/RecApp/Recording/LocalRecordingPackage.cpp` | `7cfc575282ae03714b52adc219d798121dcbf6d6c4af8a3398f7760de8c30a40` |
| `apps/windows/RecApp/Recording/LocalRecordingPackage.h` | `bd54424e3e9b826c3233d5a1158247ecec0ef5aff9cef34887097192c87dc698` |
| `apps/windows/RecApp/Recording/V5LocalRecordingWriter.cpp` | `b890339cfc0b21d1ef3d6c2840e01e2eb5ecabbdf5444593682279f780c6c453` |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.cpp` | `5b64cfb025268b40419404f0db3effe947669dae95363f678fa1193dcfe547e3` |
| `apps/windows/RecApp/AppMain.cpp` | `2b7fb97f1a64853b78146cb715bfe3f752a11908727ed4fb2d0babade63194dc` |
| `apps/windows/Tests/GrafWindowsPackageTests/V5LocalRecordingWriterTests.cpp` | `b2fe6c046aaa97a94555cc2286de6277776d609256f4f15a146a6d031c8a9e27` |
| `apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp` | `1e7cf8102a89373cc884749063dba8dea6c795deb9a8c8a7c5b9a31d242e3478` |
| `apps/windows/Tests/GrafWindowsCoreTests/CaptureFaultStateTests.cpp` | `9b957d67a9d660623aa5e695489f5915c6862fc29676c99eeba790134270ca0c` |
| `apps/windows/Tests/GrafWindowsContractTests/DesktopUploadRecoveryTests.cpp` | `1be1e357412d0dc96551496e16767691aa7cc8af25ca2865bdd25e3c3cd4d75c` |

## Следующее действие и терминальная граница

Main лично читает этот GO, затем реализует сначала behavioral RED,
минимальную правку общего classifier и честные fixtures, после frozen diff —
отдельный SOURCE/validation review. До этого никакие тесты не объявляются
пройденными. Новые продуктовые предпочтения, schema или численный порог
не требуются; выявленной clarification gap для этой формулы0.

Полная BOTH package authority/live recovery/manifest/privacySegments/admission,
защищённый V5/MF/upload/playback, T117 migration и T118 acceptance остаются
незавершёнными; их отсутствие не скрыто scoped GO. H250 working-profile
install/launch NO-GO не снимается. Physical x64/60min/AEC/accessibility/trusted
signing/clean install/update/rollback/auth-upload E2E и release не приняты.
Не создавать plaintext export/fallback и не запускать новый пакет на рабочем
inventory. Reviewer не запускал builds/tests/VM/devices и не менял
code/spec/plan/tasks/GitHub/commit/server/Mac. Единственный новый файл —
этот отчёт. Итоговая перечитка и контроль сохранности фиксируются ниже.

### Итоговый контроль reviewer

Отчёт перечитан целиком; R-критериев15, PASS15, новых checkbox markers0.
Все103 исходных checklist/report hashes совпали103/103; добавлен только этот
отчёт. Tasks SHA и120/93/27 совпали; classifier и четыре будущих изменяемых
test files совпали с исходным снимком. Branch/HEAD повторно подтверждены.
`git diff --check` завершился без ошибок. Отдельный контроль line references
уточнил plan dependency5 до1586–1588; прежнее содержимое других файлов не менялось.
**Терминальный verdict: requirements GO15/15 C0/H0/M0/L0;
SOURCE/runtime NOT RUN; full T116/installed/release NO-GO.**
