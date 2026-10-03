# Requirements Review: Capture, access and UX
Reviewer-owned requirements quality gate, not implementation acceptance. Feature ../spec.md; plan ../plan.md.
- [x] CHK001 Long-call evidence and log-delay/reset causes have measurable requirements and concrete validation scenarios (FR001–002, SC001).
- [x] CHK002 True inactivity15s, unknown600s, known-empty vs unavailable, child attribution and observer failure are unambiguous (FR003, contracts).
- [x] CHK003 Manual Stop, Never, visible control, consent and target policy remain explicit (FR004).
- [x] CHK004 Detail native action is matched to current meeting and permits only open; lifecycle, deletion, owner and file integrity fences are specified (FR005/007).
- [x] CHK005 Capacity policy is unchanged, quota copy/action honest, browser local-file absence defined; no automatic recovery promised (FR006).
- [x] CHK006 Native button uses normal keyboard accessible control and Russian wording, existing GRAF player; no third-party assets (FR005, plan).
- [x] CHK007 Private audio/text/paths/secrets absent from committed evidence; detection metadata probe does not capture or request new permission. The separate T011 physical capture has explicit user authorization and metadata-only evidence (FR008; spec T011).
- [x] CHK008 Emulation, hardware, PR SHA/CI and release gates are separate and required checks are named (quickstart/plan).

## Уточнение T011 — независимое ревью 2026-10-03
- [x] CHK009 Проект чтения по PTS ограничивает ожидание одной порцией каждого источника между live-проходами и работу128 порциями; stop имеет конечный отдельный предел. Буферы не увеличиваются, несовместимые часы и настоящая потеря остаются отказами (FR009; plan, кандидат исправления).
- [x] CHK010 Диагностика различает принятую/обработанную границу, ожидающие кадры, размер/частоту последней порции; необязательный снимок имеет nil по умолчанию. В журнале разрешены только относительные значения, без исходных PTS, аудио, текста и личных путей (spec T011; plan, кандидат исправления).
- [x] CHK011 Повторный контрольный Telemost с микрофоном и системным звуком разрешён пользователем2026-10-03 только в единственном GRAF Dev; видимый индикатор/Stop, ручные запреты, приватность и запрет остановки чужих процессов сохраняются (FR004/008; spec T011; quickstart7).
- [x] CHK012 Реальная45min приёмка, проверка длительности/проигрывания, независимое ревью, CI для нового SHA и релизные ворота обязательны по отдельности. Первый контроль имеет FAIL; Apple403 не допускает обхода нотариализации (tasks Phase6; plan T011; quickstart7).
