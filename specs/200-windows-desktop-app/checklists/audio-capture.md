# Audio-capture Checklist: Windows desktop-приложение GRAF

**Purpose**: Проверить полноту и проверяемость требований к WASAPI, clock/PTS,
AEC3, артефактам и отказоустойчивости записи.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md), [windows-desktop-contract.md](../contracts/windows-desktop-contract.md)

## Источники и разрешения

- [ ] CHK001 Явно указано, что system track — shared-mode WASAPI render loopback выбранного/default endpoint, а microphone track — отдельный физический capture endpoint. [Completeness, Spec §FR-007–FR-008]
- [ ] CHK002 Требования отдельно описывают microphone privacy, endpoint availability, format support и storage readiness как prerequisites Record. [Coverage, Spec §FR-004, §FR-008]
- [ ] CHK003 Зафиксировано, что первый релиз не обещает process-isolated app audio, Stereo Mix, virtual driver, kernel routing или exclusive capture. [Scope, Spec §FR-007, §Out of Scope]
- [ ] CHK004 Для default-device change, unplug, disabled endpoint, exclusive-mode consumer и Audio Service restart определён наблюдаемый переход состояния. [Recovery, Spec §FR-017, §Edge Cases]

## Clock, buffering и framing

- [ ] CHK005 Требование использует один monotonic QPC/WASAPI mapping и запрещает выравнивание независимых потоков по wall-clock arrival. [Clarity, Spec §FR-018]
- [ ] CHK006 Для каждого batch определены source, actual format, frame count, PTS, clock domain, route generation и discontinuity reason. [Completeness, data-model §RecordingAudioBatch]
- [ ] CHK007 Максимальная ёмкость queue, reorder window, допустимый gap, drift threshold и overflow result заданы численно или вынесены в versioned contract; стартовые timeline bounds должны совпадать с действующим macOS contract. [Measurability, Spec §FR-009, §FR-018]
- [ ] CHK008 Требование отделяет callback обязанности от worker/timeline обязанностей и запрещает callback I/O, WebView calls, unbounded allocation и blocking waits. [Performance, plan §Performance Goals]
- [ ] CHK009 Описано поведение при неполных 10 ms batches, jitter, out-of-order PTS, backward timestamp и смене clock domain. [Edge Case, Spec §Edge Cases]
- [ ] CHK010 Canonical format 48 kHz mono float и точное 480-sample/10 ms framing определены до AEC3, а не только на стороне writer. [Clarity, Spec §FR-009]

## AEC3 и canonical output

- [ ] CHK011 В требованиях явно указан pinned GRAF WebRTC AEC3 C ABI и порядок render/reference frame перед microphone/near-end frame. [Traceability, Spec §FR-009–FR-010]
- [ ] CHK012 Для AEC3 creation/process error, missing reference, invalid sample, untrusted timestamp, route change и overflow задан единый fail-closed результат. [Safety, Spec §FR-010]
- [ ] CHK013 Запрещён raw-microphone fallback, а правило сохранения очищенного trusted prefix отделено от правила выдачи normal package. [Consistency, Contract §Failure and degraded policy]
- [ ] CHK014 Определено, что system component после AEC3 остаётся неизменённым, а cleaned microphone входит в canonical mix перед двумя writers. [Clarity, Contract §Timeline and artifact contract]
- [ ] CHK015 WAV и M4A имеют отдельные роли, форматы, duration/hash/integrity gates и допустимую разницу длительности не более 100 ms. [Measurability, Spec §FR-011, §SC-003]
- [ ] CHK016 Для Windows N без AAC encoder определено readiness/degraded решение без заявления normal записи с отсутствующим playback artifact. [Dependency, Spec §Edge Cases]

## Power, fault и performance coverage

- [ ] CHK017 Sleep, modern standby, resume и application suspend/termination имеют требования к trusted prefix, отсутствующим frames и повторному Stop. [Recovery, Spec §Edge Cases]
- [ ] CHK018 Protected/DRM render limitation отражается как ограничение evidence/manifest и не объявляется полным system capture. [Truthfulness, Spec §FR-017]
- [ ] CHK019 Для 60-minute reference run определены критерии dropped/duplicated frames, ±100 ppm clock condition, duration error и system-level tolerance. [Measurability, Spec §SC-003]
- [ ] CHK020 Требование no-overheat/resource gate имеет наблюдаемый критерий CPU/memory/queue growth и не подменяется только отсутствием crash. [Performance, Constitution §Capture gates]
- [ ] CHK021 Hardware matrix охватывает Windows 10 22H2 и supported Windows 11, built-in/USB/Bluetooth mic, HDMI/DisplayPort/dock render и явно отмечает RDP limitations. [Coverage, Plan §Validation Plan]
- [ ] CHK022 Диагностика содержит только safe reason codes, counters, durations, format/source classes и redacted fingerprint; raw samples и device paths исключены. [Privacy, Spec §FR-021]
- [ ] CHK023 Pause описан как privacy pause с живым reference/timeline и timestamped zero microphone contribution, без скрытого raw path или wall-clock padding. [Clarity, Contract §Session transitions]
- [ ] CHK024 Stop из любого start/record/pause/degraded/stopping состояния idempotent и связывает writer finalization, manifest status и queue handoff. [Consistency, Contract §Session transitions]
