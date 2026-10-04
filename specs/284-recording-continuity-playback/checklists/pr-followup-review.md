# Независимая проверка требований T012–T013

Дата: 2026-10-03. Область: reviewer-owned `pr-followup.md` перед реализацией. Риск: high-risk-product, продолжение F284. Итог повторной проверки: **PASS, checked5 / unchecked0**. Это проверка требований и проекта решения; тесты нового кода, аппаратная приёмка и выпуск не заявляются.

Прочитаны AGENTS.md, guidance index, spec-kit-flow.md, product-gates.md, constitution §I/II/VI и quality gates, продуктовый договор Pause из PRD/current-product-status Feature022, активные spec/plan/tasks/quickstart/analysis. Проверены реальные очереди RecordingSampleSources, PrivacySuppressingSampleSource, privacy pause/resume writer, производственная factory, UI catch и функции playback recovery. Изменены только этот отчёт и список проверки.

| Пункт | Итог | Доказательство |
| --- | --- | --- |
| CHK001 | PASS | Уточнённый FR-010 охватывает исходную очередь и предварительно прочитанную порцию; сохраняет PTS/формат/число кадров/system audio, запрещает двойной учёт, требует новые кадры после успешного resume. Без точной границы resume явно отказывает с сохранением паузы. |
| CHK002 | PASS | T012/SC-006, plan и quickstart задают несколько порций, частичные чтения, повторные паузы, red/green и настоящий writer. SC-006 теперь явно проверяет непрерывное пополнение nil-diagnostics источника, отказ resume, сохранение заглушения и ограниченный stop. Plan сохраняет открытый durable checkpoint, исключает ожидание пустого чтения и требует проверить производственные factories. |
| CHK003 | PASS | FR-011 и plan сохраняют исходный meetingId до fetch; требуют проверки до recovery, после асинхронных чтений и в catch. Действующий отказ своей встречи сохраняется. |
| CHK004 | PASS | SC-007, plan и quickstart различают задержку fetch и чтения тела, reused main, success/403/404/network-error, действующий403; plan требует Chromium/WebKit. |
| CHK005 | PASS | spec/plan/analysis отдельно ограничивают прежний45min40s SHA6f1b441; требуют новый SHA, independent review, Dev и обязательные GitHub/release gates. Apple403 не разрешает обход проверки Apple или публикацию неподтверждённого приложения. |

## Закрытый пробел первого прохода

Первый проход имел BLOCK4/1: fallback «подавлять до первого пустого чтения» мог заглушать новые кадры бесконечно при непрерывном пополнении. До реализации исполнитель уточнил spec FR010/SC006, plan, quickstart и analysis. Теперь без точной конечной FIFO-границы resume обязан явно отказать; writer не завершает privacy segment, обёртка остаётся paused. Неподтверждённый успешный resume и ожидание пустой очереди запрещены. Противоречие с возобновлением новых кадров устранено: оно требуется после успешного resume поддержанного источника.

## Проверенные предпосылки проекта

Счётчик ожидающих паузных кадров совместим с прежним согласием: заглушение следует долговечной отметке Pause, системный звук продолжает прежний путь. Счётчик O(1) не вводит очередь аудио или журнал интервалов. Plan требует сериализовать чтение и переходы одной блокировкой обёртки; точный FIFO snapshot задаёт конечную границу. Частичное чтение уменьшает число кадров, повторная пауза не складывает повторно учтённое; предварительно прочитанная порция учитывается отдельно.

Производственная factory найдена в `TwoBrainRecApp.swift:2091`: она передаёт AppOwnedMicrophoneSampleSource. В `MicrophoneCaptureService.swift:92` источник делегирует diagnostics BufferedLocalRecordingSampleSource; тот снимает queuedFrameCount под NSLock (`RecordingSampleSources.swift:175`) и читает FIFO под тем же lock. Дополнительный runtime proof в Shared/Tools/MeetingMuteTruthRuntimeProof также использует Buffered источник; иные production factories в RecApp/Shared Tools не обнаружены. Optional diagnostics остаются допустимыми для обычной записи; отсутствие snapshot запрещает только неподтверждённое возобновление после Pause.

Существующий `resumeManualRecording` (`TwoBrainRecApp.swift:2443`) сначала ожидает writer.resumePrivacyAsync и лишь затем переводит captureController/captureSession в capturing. Его catch сохраняет paused и показывает: «Не удалось включить микрофон в записи. Системный звук продолжает записываться; попробуйте еще раз или остановите запись». Проект отказа writer использует этот путь без новой продуктовой опции или нового согласия.

## Обязательные доказательства после реализации

PASS допускает следующий шаг Spec Kit после issue-sync. Реализация всё ещё обязана доказать red/green, несколько/частичные порции, повторные паузы, сохранение кадров/PTS/discontinuity, отсутствие двойного учёта, ошибку resume без изменения paused/open checkpoint и bounded stop у непрерывного nil-diagnostics источника. Производственный поддержанный источник должен восстанавливать новые кадры без зависимости от прочих необязательных diagnostic полей. Отдельно нужны браузерные T013, независимое ревью реализации, новый SHA/CI, Dev и действующие release gates. Сырые аудио/тексты/личные пути в git не допускаются.

Итоговый список перечитан после правки: **5 отмеченных, 0 открытых**. Код, spec/plan/tasks, git, GitHub и релиз не изменены reviewer.
