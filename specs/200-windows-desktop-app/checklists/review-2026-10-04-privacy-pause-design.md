# Независимая проверка требований приватной паузы T120

Дата: 2026-10-04. Объём: качество12 требований `privacy-pause.md`, устранение
H1–H4 и согласованность уточнения T120 с FR-002/009/010, SC-002/004,
защищённым хранением T116 и выбранным Mac F284. Lane: high-risk-product,
этап независимой проверки требований, не реализации.

## Привязка и границы

- Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
- Фактически прочитанные Git HEAD/branch:
  `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, `codex/200-windows-followup`.
- Уточнения находятся в незакоммиченном снимке; один HEAD не описывает их
  содержимое. SHA-256 прочитанных файлов приведены ниже.
- Mac-образец прочитан лично через локальный `git show` на
  `c8d67ccefe7848f731798b23d72d37757ad812f5`, не из старой рабочей копии Mac.
- Прочитаны полностью SKILL.md speckit-checklist, speckit-analyze,
  code-reviewer, корневой AGENTS, guidance index, codex-worktrees,
  spec-kit-flow, product-gates, release-and-validation и конституция.
  В product baseline/status прочитаны относящиеся к предмету части;
  полного нового прочтения всей истории F200 не заявляю.
- В активных документах лично прочитаны Session2026-10-04, FR/SC выше,
  desktop §3, local-custody §3 и существующая граница commit §4,
  plan T120, data-model §1, research T120, quickstart §15, T116/T120.
  Неизменённый packed contract используется из ранее прочитанного контекста
  после повторного подтверждения SHA `7ff9a1a0…331eed`.
- `.specify/feature.json` и `check-prerequisites.sh --json --paths-only`
  подтвердили путь F200. Этот режим не сохраняет feature.json. Выдаваемое
  скриптом имя feature `200-windows-desktop-app` не заменяет фактическую
  Git-ветку выше. Обычный режим с возможной записью feature.json не запускался;
  литерал `--require-spec` не поддерживается установленным скриптом.
- YAML hooks для before/after checklist/analyze разобран: enabled0 для всех
  четырёх точек. Commit/issue hooks не запускались.
- Разрешённые изменения reviewer: только `privacy-pause.md` и этот отчёт.
  Нет продуктовых, нормативных, VM, аудио, GitHub, issue, commit или release
  изменений. Обзор существующего кода служит только проверке зависимостей.

## Доказательства по каждому пункту

| Пункт | Основание достаточности требований | Итог |
| --- | --- | --- |
| CHK001 | spec Session2026-10-04 фиксирует полный Mac SHA и связь FR-002/009; desktop §3 и plan T120 прямо отвергают bool-only drain как готовую паузу. Mac recording-and-playback контракт прочитан целиком. | checked |
| CHK002 | desktop §3 пункты1/4, spec и quickstart §15 разделяют mandatory OPEN с rollback/отказом Pause и best-effort CLOSE после успешного Resume с retained durable OPEN. Подтверждено Mac V5LocalRecordingWriter.pausePrivacyOnQueue/resumePrivacyOnQueue. | checked |
| CHK003 | desktop §3 пункт2, plan шаг1 и quickstart задают queued/in-flight/prefetched/timeline/partial suppression без изменения уже записанного prefix; pre-Pause pending выделен отдельно. Это не только будущий кадр после переключения bool. | checked |
| CHK004 | desktop пункт3 и plan требуют синхронную producer/read FIFO границу, replacement count, отсутствие двойного учёта и ожидания пустой очереди. Mac wrapper держит lock на read/update, snapshot меняет state под FIFO lock, остаток заменяется; partial prefix обнуляется при сохранении формата/PTS. | checked |
| CHK005 | desktop пункт3/4 и quickstart boundary-unavailable сохраняют paused/OPEN/Stop; некорректная граница не даёт Resume. Mac update возвращает Bool; writer бросает resumeBoundaryUnavailable до закрытия сегмента. | checked |
| CHK006 | FR-009/010, desktop пункт5 и quickstart требуют исходную валидацию и неизменные system/PTS/count/channels/format/route/AEC/Stop/EOS; NaN/Inf и faults не скрываются подавлением, raw fallback/padding запрещены. | checked |
| CHK007 | spec, desktop пункт6, plan шаг3 и T116/T120 требуют protected metadata до durable integration; plaintext journal и текущий открытый writer не являются разрешённым обходом. | checked |
| CHK008 | data-model §1 перечисляет все11 полей ProductPrivacySegment, control/treatment/initiator, optional endedAt/endMonotonicMs, OPEN duration0 и закрытую duration; лично сопоставлено с pinned Mac model/enums. ManifestService использует JSONEncoder/Decoder .iso8601, nil поля сегмента опускаются синтезированным Codable. Известное отсутствие privacySegments и строгие известные формы сохраняются; whitespace/key order не новая authority. | checked |
| CHK009 | local-custody §3, plan и quickstart задают весь serialized manifest≤65536B и отказ65537B до publication; 1/4096/4097/65536 — codec roundtrip, не признание произвольного JSON валидным пакетом. Один блок256KiB, physical envelope/index bounds и общий owned64MiB/job2MiB/root4096/cache/pins/jobs/queue/audio budgets не увеличиваются. | checked |
| CHK010 | desktop пункты1/6, local-custody §3 и quickstart явно запрещают принятый Pause при отказе OPEN, усечение истории, произвольный segment-count cap и substring validation. Plan шаг3 требует exact Mac fixtures/известный validator до durable consumer; quickstart отдельно требует unknown/duplicate-key отказ, hash/format/ownership и legacy/new consumer acceptance. | checked |
| CHK011 | desktop пункт7, plan шаг5, data-model и quickstart задают единственного owner/writer, session/generation ordering, запрет file I/O на UI/WASAPI callback, доступность Stop и запрет позднему результату возобновлять stopped/new session. | checked |
| CHK012 | plan/T120 и quickstart §15 отделяют codec prerequisite T116/#7444 от capture T120 и protected consumer adoption. RED, synthetic/native/source и exact installed acceptance самостоятельны; hardware/physical x64/60min/AEC/accessibility/signature/update/release не принимаются этим документом. | checked |

## H1–H4 и ограниченный analyze

- H1 устранена: OPEN и CLOSE имеют различные условия принятия; отсутствие
  FIFO boundary не смешано с best-effort CLOSE failure.
- H2 устранена: область подавления и непереписываемый trusted prefix названы;
  точная граница/replacement/частичный prefix/continuous producer проверяемы.
- H3 устранена: защищённое сохранение зависит от T116, без временного
  plaintext journal; single-owner ordering/UI/Stop/late completion определены.
- H4 устранена как проектная норма: manifest64KiB — явная новая вместимость,
  взятая из существующего metadata bound, а не незаявленное увеличение4096.
  Проверяется полный сериализованный manifest; OPEN failure не принимает
  Pause и не стирает историю. Это не обещание неограниченного числа пауз.

Ограниченная cross-artifact проверка: CRITICAL0/HIGH0/MEDIUM0.
Основные FR-002/009 и SC-002/004 имеют явное покрытие T120; FR-010 сохраняет
fault/no-raw границу, FR-012/013/014/022 и защищённые consumers остаются T116.
Противоречий конституции I/II/IV/VI/VII в прочитанном срезе не найдено;
credential/server/egress границы III не меняются. Нет новой задачи или
переотметки исторического source acceptance. Это не полный analyze всех120
задач и не новое подтверждение старой общей матрицы.

## Незавершённые реализации, не неоднозначности требований

Лично прочитанный текущий `ProtectedCustodyCodec.cpp:116` всё ещё возвращает
manifest4096, а `LocalRecordingPackage.cpp:117/127` имеет4096 и старую exact
regex форму. Их изменение НЕ принято. План явно требует согласовать codec,
decoder/reader/writer/legacy и строгий consumer validator до adoption.
Увеличение logicalLimit само по себе не принимает новый v5 JSON или пакет.

Минимальный codec prerequisite остаётся в существующей T116/#7444:
отдельный RED/new-limit/native/failure/source review; без protected writer/
consumer adoption T116 и полная T120 остаются открытыми. Issue authorization
T120 по сообщению main запрошена/ожидается; GitHub в этом review не опрашивался.
Этот PASS не разрешает main обходить analyze/issue sync перед capture edits.
Тесты, сборки, VM, устройства, установленное приложение и public release здесь
не выполнялись и не принимались. Старый воспроизведённый privacy defect
остаётся реализационной работой T120, не скрывается нулём требований C/H.

## SHA-256 прочитанного снимка Windows

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | f59f95b967cf1b2bbf18b44e3a8ee99467418f46d4da2e956361527155132a7d |
| plan.md | 91f6b4c5e2bfd29a795a21ce79650395bbfe811ec49d6faf9c462fcd87069828 |
| tasks.md | 80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f |
| quickstart.md | c6619ad9ad5fe5e27cced14dd9cbc3d1a708315884559cfb1508d33753804cee |
| data-model.md | 90427dcfb14aaea27de331728ecae324ba600bc92927ebde2a637a55a4b1ea20 |
| research.md | f24b604558d3eaacdbb09d97e980752bede714524c9d9e1cbdfb17231c47ac00 |
| contracts/windows-desktop-contract.md | 79a5b1870748f50f857e082d6ec5b2f99ba6a9149d846718865ef1de71cf5d2d |
| contracts/windows-protected-local-custody.md | 090f4511fb9f3e1aa9fc27caf8ba922f39fc1a5d1d778e7b29a3ae946ec65402 |
| contracts/windows-protected-packed-custody.md, unchanged | 7ff9a1a0b67f05fd1872358dcd33455331cdadb721e890f9f68295a3dc331eed |
| constitution.md, unchanged/full read | d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859 |
| privacy-pause.md before reviewer marks,12 unchecked | 39b62d56942c98bf2ce3c0fb057a3abe39375d3de25ce7304b59cdf9571e6c98 |
| ProtectedCustodyCodec.cpp, dependency observation only | 5372538eb3055c2b9a89786ef15089eb090e574025a3c0c030f87730873506c9 |
| LocalRecordingPackage.cpp, dependency observation only | 7cfc575282ae03714b52adc219d798121dcbf6d6c4af8a3398f7760de8c30a40 |

Исторические Reader отчёты неизменны: gate
`3a5a79e248accd100b23348c68a2fb14e11f35346b773ffd0bb549048a2063e9`, source
`c08c8d563fa4641c6668d93586270ae26b69576e43e30ead1e1d274dda967c18`.
Их принятие не распространяется на T120.

## SHA-256 точного Mac образца

Все объекты ниже прочитаны из commit
`c8d67ccefe7848f731798b23d72d37757ad812f5`; SHA — полного содержимого файла,
не утверждение о полном прочтении несвязанных частей больших Swift файлов.

| Артефакт | SHA-256 |
| --- | --- |
| F284 contracts/recording-and-playback.md, full read | b1b234fac88839b40bb359b6c2155b2d7722f73607e42bae957be8fee41f1d50 |
| MeetingMuteTruthModels.swift, enums/ProductPrivacySegment | a01b4f1799379c4abea9715354f2327fafc3dd706cad4fe93c30f3f296415767 |
| LocalRecordingManifestService.swift, encoder/write/read portions | 36fec91280c57d6d8e30b3ae07969d7994520edb3de38c488d6c83ca2259558a |
| PrivacySuppressingSampleSource.swift, full read | ca8d3b86defb99d1945d18cc81795c0f528cfdbcc9add3ddea591caea920cd32 |
| V5LocalRecordingWriter.swift, pause/resume/checkpoint portions | 044061b32fea07979229474337c934f7c4620ab42ffe5da910b5b944294a5b23 |

## Конечный вердикт

**PASS только качества требований данного среза:12 checked/0 unchecked,
CRITICAL0/HIGH0/MEDIUM0. H1–H4 устранены.** Все12 отметок reviewer опираются
на перечисленные артефакты, не на обещание будущего прохождения тестов.
Source acceptance, готовность T116/T120, приложения, установленного пакета,
hardware и выпуска НЕ выданы. Main обязан пройти оставшиеся собственные
analyze/issue/source/runtime gates. Итоговый readback и hashes двух reviewer
файлов сообщаются отдельно; собственный SHA не включается в этот файл.
