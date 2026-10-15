# Round410 — независимая проверка требований privacy history

Дата: 2026-10-15. Lane: high-risk-product, ограниченный REQUIREMENTS gate
внутри speckit-implement.

**Итог: GO требований для предложенного ограниченного следующего среза;
CRITICAL 0 / HIGH 0 / MEDIUM 0.**
Не найдены непокрытые противоречия или неоднозначности требований,
мешающие начать этот срез. Это не SOURCE GO, не runtime PASS и не приёмка
приватной Pause/Resume либо всего защищённого потока. T116/T120 остаются OPEN.

## Идентичность и предел проверки

Авторитетная рабочая копия:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`,
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Активный указатель .specify/feature.json и read-only prerequisites разрешают
specs/200-windows-desktop-app. Нормативный незакоммиченный снимок привязан
к SHA-256 ниже, а не только к HEAD.

Проверено предложение: V5LocalRecordingWriter хранит логическую историю
privacySegments по настоящему Mac ProductPrivacySegment; OPEN durable до Pause
ACK; CLOSE после принятой границы Resume best-effort и консервативен при отказе.
Никакого нового формата, schema, зависимости, plaintext journal или открытия
глобального допуска записи.

Применены speckit-implement и ограничения независимого reviewer:
прочитаны root AGENTS/применимые правила, guidance index, worktrees,
spec-kit-flow, product-gates, tracker-policy, относящиеся к проверке разделы
release-and-validation, constitution и продуктовых baseline/status.
Прочитаны активные spec/plan/tasks/quickstart/data-model/research и контракты
в относящемся к privacy/T116/T120 объёме. Полные SHA не означают повторного
аудита всей исторической хронологии этих файлов или всех исходников.
Packed contract сверён как неизменённая зависимость.

Перечитаны критерии всех 10 текущих чеклистов и все 266 checkbox-строк
исторических отчётов. Исторические source/runtime утверждения не
переквалифицированы в текущие и не проверялись заново. Поток Windows
writer/controller и production ProtectedCustodyMetadata не исследовался:
это отдельная параллельная работа основного агента.

## Независимая сверка Mac-образца

Нормативный Mac F284: `c8d67ccefe7848f731798b23d72d37757ad812f5`.
Использован локальный git show, без сети. Прочитаны ProductPrivacySegment,
связанные enum, настройки Codable дат в LocalRecordingManifestService и
F284 recording-and-playback contract; не writer/controller flow.

Сегмент имеет ровно 11 полей:
segmentId, sessionId, control, startedAt, endedAt, startMonotonicMs,
endMonotonicMs, durationMs, localMicTreatment, initiator, diagnosticSafe.
OPEN опускает nil endedAt/endMonotonicMs, durationMs=0; даты ISO8601 UTC;
закрытие сохраняет идентичность, исходный control и начало.
userPause имеет control=pause, localMicTreatment=silenced, initiator=user.
Числа неотрицательны, end>=start, duration без overflow.
Модель не разрешает замену отсутствующих optional на произвольный null,
новый journal или приблизительные substring-проверки JSON.
Whitespace/key order не дают authority; известное legacy отсутствие
privacySegments остаётся допустимым. Data-model:51–79 согласован с образцом.

## Повторная оценка privacy-pause.md

Все 12 отметок сохраняются: это качество требований, не готовность кода.

| Критерий | Доказательство в текущих требованиях | Вывод |
| --- | --- | --- |
| CHK001 | spec Session2026-10-04:651–675; desktop:75–79; точный Mac F284 выше, FR-002/009 | PASS |
| CHK002 | desktop:81–84 и 96–99; plan:1621–1629: обязательный OPEN и best-effort CLOSE различены | PASS |
| CHK003 | desktop:85–89: queued/in-flight/prefetched/timeline/partial, сохранение уже записанного prefix | PASS |
| CHK004 | desktop:90–95: один FIFO ownership, exact boundary, замена остатка, без ожидания пустоты | PASS |
| CHK005 | desktop:94–95 и data-model:75–79: отказ Resume сохраняет paused/OPEN/Stop | PASS |
| CHK006 | desktop:100–104; FR-009/010: system/PTS/count/format/AEC и исходная валидация не ослаблены | PASS |
| CHK007 | desktop:105–109; plan:1621–1624; tasks T116/T120: только защищённый metadata путь | PASS |
| CHK008 | data-model:51–73; Mac модель/Codable: exact fields, ISO8601 и omission optional, known legacy | PASS |
| CHK009 | desktop:105–113; local-custody §3; plan:1631–1640: cap всего manifest 65536 bytes и прежние budgets | PASS |
| CHK010 | desktop:81–84,105–109; data-model:72–73: OPEN refusal, без потери истории и ослабления validator | PASS |
| CHK011 | desktop:110–113; plan:1627–1629: один writer, session/generation, async I/O, stale completion | PASS |
| CHK012 | desktop:115–117; plan:1614–1629; quickstart §15; tasks T116/T120: отдельные source/native/installed gates | PASS |

### Границы, которые нельзя потерять при реализации

1. Перед durable integration нужны exact logical-v5 fixtures по Mac и строгий
   existing consumer validator (plan:1621–1624). Storage codec roundtrip,
   generated metadata или прежний live-metadata native PASS не заменяют их.
2. OPEN должен иметь настоящий durable ACK до опубликованного paused/подавления.
   Capacity/serialization/storage failure не даёт успешный Pause. Не обрезать
   старую историю и не вводить отдельный произвольный лимит числа сегментов.
   Проверяется весь сериализованный manifest: 65536 допустимо, 65537 — отказ.
3. CLOSE следует только за принятой exact FIFO границей. Его отказ не отменяет
   принятый Resume задним числом; это не гарантия, что после неоднозначного
   post-publish отказа физически не записались новые bytes.
   Desktop:99 прямо сохраняет обычные storage failure gates, а local-custody:
   139–154 требует sticky ambiguous, retained artifacts/last checkpoint и
   запрет слепого retry/следующей generation до reconciliation.
   Консервативный прежний OPEN не разрешает rollback authority к старому ledger,
   объявление normal/saved или сокрытие фактического неопределённого результата.
4. Writer-only prerequisite не принимает FIFO/in-flight suppression и UI ACK.
   Session/generation/order и Stop/Quit late completions остаются обязательными.
   UI/WASAPI не выполняют I/O; очереди/owner/pin/job/memory caps не расширяются.
5. Plan:1970 сохраняет global admission=false до всех consumers, включая T120.
   Этот отчёт не открывает storageWritable/localQueueComplete/Record и не
   меняет продуктовые, аппаратные, installed или release gates.

Это существующие обязательства, не новые нормы и не найденные пробелы.
Отдельная проверка реализации должна показать их исполнение; здесь оно
не утверждается.

## Текущесть analyze

Последняя относящаяся к этому срезу проверка:
review-2026-10-12-privacy-pause-requirements-refresh.md,
SHA-256 `55d2808cf7287baae809b182f34d64d8b0a66d2ff3ffeec8636ba72d51f0c0de`.
Все 10 её нормативных SHA в таблице ниже совпадают с текущими файлами;
privacy-pause.md также неизменён:
`5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec`.

Поэтому её scoped cross-artifact вывод остаётся текущим для тех же требований;
Round410 независимо перепроверяет его для предложенного writer-history среза.
Изменения тестовых/production исходников сами по себе не меняют эти нормы,
но требуют нового source/runtime доказательства и не наследуют старый PASS.

Это не новый полный feature-wide speckit-analyze. Старый privacy design
2026-10-04 с другими spec/plan/model SHA — исторический, не текущий анализ.
Cold-inspection gate 2026-10-11 имеет иной предмет и не заменяет privacy review.
Исторический Oct12 implementation STOP по authorization/issue sync не является
свежей проверкой GitHub: сеть здесь запрещена. Текущий внешний issue/ownership
не подтверждался и не опровергался. Requirements GO не является разрешением
публикации или обходом обязательного tracker-порядка.

## Полный пересчёт отметок

До добавления отчёта: 194 Markdown-файла в checklists, 29 с checkbox-строками.
Новый отчёт не добавляет checkbox-строк; существующие отметки не меняются.
В 10 текущих чеклистах: **154 checked / 0 unchecked**.
В 19 исторических отчётах: **266 checked / 0 unchecked**.
Итого: **420 checked / 0 unchecked**. Это 420 вхождений отметок, включая
повторные исторические секции, а не 420 заново принятых требований реализации.

| Файл | Всего | Checked | Unchecked |
| --- | ---: | ---: | ---: |
| advanced-routing.md | 14 | 14 | 0 |
| audio-capture.md | 24 | 24 | 0 |
| calendar-launcher.md | 5 | 5 | 0 |
| calendar-operation.md | 8 | 8 | 0 |
| calendar-wire.md | 5 | 5 | 0 |
| packed-writer.md | 12 | 12 | 0 |
| privacy-pause.md | 12 | 12 | 0 |
| requirements.md | 22 | 22 | 0 |
| review-2026-10-03-packed-tree-source.md | 38 | 38 | 0 |
| review-2026-10-04-calendar-join-gate.md | 12 | 12 | 0 |
| review-2026-10-04-calendar-resolver-gate.md | 12 | 12 | 0 |
| review-2026-10-04-calendar-url-gate.md | 12 | 12 | 0 |
| review-2026-10-04-manifest-cap-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-cadence-gate.md | 12 | 12 | 0 |
| review-2026-10-04-packed-cadence-source.md | 18 | 18 | 0 |
| review-2026-10-04-packed-live-writer-gate.md | 14 | 14 | 0 |
| review-2026-10-04-packed-live-writer-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-package-gate.md | 12 | 12 | 0 |
| review-2026-10-04-packed-reader-gate.md | 20 | 20 | 0 |
| review-2026-10-04-packed-reader-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-resize-gate.md | 14 | 14 | 0 |
| review-2026-10-04-packed-resize-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-rewrite-gate.md | 16 | 16 | 0 |
| review-2026-10-04-packed-rewrite-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-tail-gate.md | 14 | 14 | 0 |
| review-2026-10-04-packed-tail-source.md | 9 | 9 | 0 |
| review-2026-10-04-packed-writer-source.md | 18 | 18 | 0 |
| security.md | 27 | 27 | 0 |
| ux.md | 25 | 25 | 0 |
| **Итого** | **420** | **420** | **0** |

Tasks отдельно: 120, из них 93 checked / 27 open.
T116 (tasks:568) и T120 (tasks:602) остаются unchecked.
Менять reviewer markers оснований нет.

## SHA-256 нормативного снимка

| Файл от корня repo | SHA-256 |
| --- | --- |
| specs/200-windows-desktop-app/spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| specs/200-windows-desktop-app/plan.md | `40443131fdafc41aa13ef98058e2fa95608dfdc1f60ae03d2ea6ab3acadb4868` |
| specs/200-windows-desktop-app/tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| specs/200-windows-desktop-app/quickstart.md | `6a070377de42113eea427d376f6b39beac5e222ca1dab31a69a85587b68f6dc3` |
| specs/200-windows-desktop-app/data-model.md | `c24b9d10bf5b935bcf51bb12034a0bb9ccef4a0b3719a138b48a26cbaa0d3bc7` |
| specs/200-windows-desktop-app/research.md | `901de067501da665dc3d28710c7691665a3d584f7bdcdb8f4f3c1a1ebbf8a774` |
| specs/200-windows-desktop-app/contracts/windows-desktop-contract.md | `79a5b1870748f50f857e082d6ec5b2f99ba6a9149d846718865ef1de71cf5d2d` |
| specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md | `598223854ea7e614694167c4019ef199e30c82b3ac1c44b33fcefa94fbe27fee` |
| specs/200-windows-desktop-app/contracts/windows-protected-packed-custody.md | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

## Контроль границы записи

Разрешён единственный новый файл: этот отчёт.
Reviewer не менял исходники, spec/plan/tasks, constitution или существующие
чеклисты. Повторная сверка после создания отчёта подтвердила: все 10
нормативных SHA и hashes прежних 194 checklist-файлов неизменны; повторный
пересчёт — 420/0, tasks 93/27. Всего стало 195 Markdown-файлов в checklists.
Digest прежних 194 checklist-файлов:
`98854ab3c8b80bd76dd87e003b726c85bc3f6415e0d6c53dd99b6dcbccd2053f`.
Алгоритм: SHA-256 UTF-8 конкатенации basename + space + sha256 + newline
для отсортированных прежних путей; новый отчёт исключён.

Сборки, тесты, VM, сеть/GitHub, commits и installs reviewer не выполнял.
Старые native green receipts не перенесены на логическую privacy acceptance.

