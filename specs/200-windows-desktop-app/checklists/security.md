# Security Checklist: Windows desktop-приложение GRAF

**Purpose**: Проверить требования к WebView2 trust boundary, локальной custody,
секретам, диагностике, удалению и стандартному пользовательскому контексту.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md), [windows-native-web-bridge.md](../contracts/windows-native-web-bridge.md)

## WebView2 и навигация

- [ ] CHK001 Trusted origin нормализуется по scheme/host/port и не разрешает broad substring-проверки вроде `contains("desktop")` или `contains("meeting")`. [Clarity, Bridge §Trusted origin]
- [ ] CHK002 Approved route kinds перечислены для meetings, detail, settings, auth recovery, share и deletion report; native-only и неизвестные пути имеют отдельный результат. [Completeness, Bridge §Trusted origin]
- [ ] CHK003 Redirect, cross-frame navigation, `file:`, `data:`, `javascript:`, local filesystem, loopback development и external browser handoff имеют явную policy. [Coverage, Bridge §Navigation lifecycle]
- [ ] CHK004 WebView2 Evergreen availability, runtime repair и failure state не превращаются в permission error и не блокируют native capture/local custody. [Consistency, Spec §FR-020, §Edge Cases]
- [ ] CHK005 AreHostObjectsAllowed, COM host object policy, script dialogs, capability scope и standard-user execution явно ограничены. [Completeness, Bridge §WebView2 settings]

## Bridge protocol

- [ ] CHK006 Каждое сообщение имеет protocol, version, direction, message id, ephemeral session nonce, typed payload и monotonic send time. [Traceability, Bridge §Envelope]
- [ ] CHK007 Origin/source, document/session boundary, direction, schema, payload size/depth, message replay и nonce rotation имеют измеримые правила отказа. [Measurability, Spec §FR-006]
- [ ] CHK008 Allowlist web-to-native ограничен native settings/diagnostics, runtime repair и display acknowledgement; start/stop/pause/resume, file, process, token и cookie commands запрещены. [Least privilege, Bridge §Web-to-native intents]
- [ ] CHK009 Native-to-web events не передают file paths, device handles, cookies, tokens, raw samples, transcript text, signed URLs или приватный meeting content. [Data boundary, Bridge §Native-to-web events]
- [ ] CHK010 WebView acknowledgement не считается proof сохранения, upload или server acceptance; source of truth указан в custody contract. [Truthfulness, Contract §Local custody and upload]
- [ ] CHK011 Ошибка/закрытие/recreate WebView инвалидирует nonce и bridge state, но не изменяет native session state. [Recovery, Bridge §Navigation lifecycle]

## Локальная custody и egress

- [ ] CHK012 Local recordings ограничены user-scoped app-data directory, имеют user-only ACL, temp-plus-atomic-rename и bounded flush/error semantics. [Completeness, Spec §FR-012]
- [ ] CHK013 Queue ledger имеет atomic write, malformed-document quarantine и recoverable backup; пустая очередь не может молча заменить повреждённую. [Durability, Spec §FR-013]
- [ ] CHK014 Upload egress ограничен существующими GRAF desktop APIs; MediaScribe/MinIO/provider credentials и direct traffic отсутствуют в Windows boundary. [Secret discipline, Spec §FR-014]
- [ ] CHK015 Local purge признаётся только после deletion/tombstone/cryptographic unrecoverability proof, а server deletion truth не подменяется локальным флагом. [Deletion, Spec §FR-022]
- [ ] CHK016 Update/uninstall/rollback сохраняют или явно обрабатывают local packages, queue, auth profile policy и не удаляют данные неявным clean-up. [Recovery, Spec §SC-008]

## Diagnostics и supply chain

- [ ] CHK017 Metadata-only diagnostics перечисляют разрешённые поля и запретные поля на уровне contract, включая local absolute paths и process command lines. [Completeness, Spec §FR-021]
- [ ] CHK018 Audio buffers, transcripts, private meeting ids, credentials, cookies, signed URLs и raw response bodies исключены из committed evidence, logs, screenshots и support bundles. [Privacy, Spec §Repository Hygiene]
- [ ] CHK019 Pinned AEC3 source revision, license notices, hash/identity и reproducible build inputs имеют owner и evidence path. [Supply chain, Plan §Phase 0]
- [ ] CHK020 Package signature, architecture, Windows App SDK dependency, WebView2 runtime channel и rollback proof входят в release-readiness criteria до распространения. [Packaging, Spec §FR-020]
- [ ] CHK021 Native host, WebView2 and audio capture run without elevation, driver, system service or privileged audio component. [Privilege, Spec §FR-019]
- [ ] CHK022 Threat scenarios include hostile origin, stale nonce, replay, malformed/deep/oversized payload, untrusted redirect, WebView close during capture and missing runtime. [Coverage, Bridge §Security tests]
