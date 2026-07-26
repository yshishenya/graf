# Feature Specification: Developer ID как единственный публичный macOS-релиз

**Feature Branch**: `130-developer-id-release`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: «После публикации v2026.07.26.6 проанализировать
все документы и инструкции и закрепить Developer ID как единственный путь,
не возвращаясь к самоподписанному релизу».

## User Scenarios & Testing

### User Story 1 - Выпустить доверенный macOS-релиз (Priority: P1)

Оператор релиза хочет видеть один канонический путь сборки и публикации GRAF,
чтобы пользователи получали приложение с Apple Developer ID, нотарификацией и
проверкой Gatekeeper.

**Why this priority**: Неподписанный или локально подписанный публичный пакет
может быть заблокирован macOS и нарушить доверие к установке.

**Independent Test**: Оператор проходит release checklist с чистого точного тега
и получает только Developer ID app/package, notarization staple, Gatekeeper
acceptance, GitHub Release и проверенный public download.

**Acceptance Scenarios**:

1. **Given** точный release tag, доступные Developer ID identities и свежие
   проверки CI, **When** оператор запускает канонический release workflow,
   **Then** public artifact gate принимает только Developer ID Application и
   Developer ID Installer с Apple notarization/staple.
2. **Given** выбран локальный, ad-hoc или owner-only code-signing identity,
   **When** этот identity передаётся в public release validation,
   **Then** workflow завершается ошибкой до публикации артефакта.

### User Story 2 - Безопасно перейти со старого клиента (Priority: P1)

Пользователь, у которого установлена историческая self-signed сборка, хочет
один раз установить новый notarized `.pkg`, не получив несовместимое Sparkle
обновление и не потеряв ясность о дальнейших обновлениях.

**Why this priority**: Signing lineage является частью идентичности приложения;
автоматическое local → Developer ID обновление может быть отвергнуто macOS или
потребовать повторных разрешений.

**Independent Test**: На паре старого local/self-signed `GRAF.app` и нового
Developer ID `GRAF.app` migration validator принимает только отдельно
обозначенный manual bootstrap, проверяет notarization/Gatekeeper и запрещает
подменять live appcast этим переходом.

**Acceptance Scenarios**:

1. **Given** старый клиент с local/self-signed signing kind и новый Developer ID
   кандидат, **When** оператор проверяет migration bootstrap, **Then** проверка
   требует notarized Developer ID `.pkg` и не разрешает публиковать кандидат как
   обычный Sparkle update.
2. **Given** пользователь установил Developer ID bootstrap, **When** готовится
   следующий обычный релиз, **Then** предыдущий кандидат проверяется как
   Developer ID с той же team identity/designated-requirement совместимостью.

### User Story 3 - Следовать инструкциям без поиска legacy-пути (Priority: P1)

Разработчик или новый оператор хочет найти в README, checklist, AGENTS и
release runbook одинаковую команду и одинаковые ограничения, не выбирая между
несколькими историческими схемами подписи.

**Why this priority**: Противоречивые инструкции возвращают запрещённый путь
даже после успешной настройки Apple Developer account.

**Independent Test**: Полнотекстовый аудит active documentation и release
scripts показывает Developer ID-only wording; каждое оставшееся упоминание
local/self-signed явно помечено как historical receipt или isolated test
fixture.

**Acceptance Scenarios**:

1. **Given** active release docs and scripts, **When** новый оператор ищет
   signing/build/release instructions, **Then** первым и единственным обычным
   вариантом является Developer ID + notarization + stapling.
2. **Given** исторический release receipt, **When** он содержит старую signing
   схему, **Then** документ явно помечает её как архивный факт и не предлагает
   повторить её для нового релиза.

## Edge Cases

- Developer ID certificate, installer identity, notarization profile или Apple
  response отсутствует: публикация останавливается без замены public files.
- Notary Service принимает app, но отклоняет package, или staple/Gatekeeper
  validation не проходит: release остаётся непубличным, старый appcast и
  rollback assets сохраняются.
- Старый клиент имеет неполную Sparkle-конфигурацию или другой bundle identity:
  migration validator блокирует автоматический переход и требует manual pkg.
- В public host уже существует versioned asset: workflow не перезаписывает его
  молча и требует проверки целевого SHA.
- В документации найдено историческое self-signed упоминание без archive/test
  маркировки: оно считается active-path defect и исправляется до closeout.

## Requirements

### Functional Requirements

- **FR-001**: Канонический public macOS release workflow MUST требовать Apple
  Developer ID Application для app и Developer ID Installer для package, когда
  package публикуется.
- **FR-002**: Public release validation MUST требовать успешную Apple
  notarization, stapler validation и Gatekeeper acceptance для app/package.
- **FR-003**: Public release validation MUST отклонять ad-hoc, local/self-signed
  и owner-only code-signing identities до публикации.
- **FR-004**: Система MUST иметь отдельно обозначенный Developer ID migration
  bootstrap режим, который принимает исторический local/self-signed predecessor
  только для manual `.pkg` и не создаёт обычный Sparkle appcast entry.
- **FR-005**: Обычный Sparkle update MUST требовать предыдущий Developer ID app
  с совместимыми bundle identifier, team identity, designated requirement,
  feed URL и Sparkle trust generation.
- **FR-006**: Active README, runbook, AGENTS guidance, release checklist и
  Spec Kit release artifacts MUST описывать Developer ID как единственный
  публичный путь и ручной notarized `.pkg` как единственный migration bootstrap.
- **FR-007**: Исторические receipts MAY сохранять точные сведения о старых
  релизах, но MUST быть помечены как historical и не содержать команды,
  предлагающие повторить self-signed public release.
- **FR-008**: Release workflow MUST сохранять предыдущий public appcast и
  versioned rollback assets до проверки нового кандидата и MUST заменять feed
  последним.
- **FR-009**: Все release evidence и docs MUST исключать private keys,
  passwords, notarization secrets, raw audio, transcript text и signed URLs.

### Key Entities

- **Public release candidate**: Developer ID app/package, notarization and
  Gatekeeper evidence, exact tag/commit, checksums and release notes.
- **Migration bootstrap**: One-time notarized `.pkg` transition from a legacy
  local/self-signed app to Developer ID; it is not an in-app update.
- **Ordinary Sparkle update**: A versioned appcast entry whose predecessor and
  candidate have compatible Developer ID signing lineage.
- **Historical receipt**: Immutable documentation of a prior release that is
  not an active instruction.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of active macOS release instructions point to Developer ID,
  notarization, stapling and Gatekeeper; no active instruction points to
  `GRAF Local Code Signing` or owner-only public release.
- **SC-002**: Public validation rejects a local/self-signed candidate before any
  public file or appcast mutation in every covered negative test.
- **SC-003**: The migration bootstrap validator passes the v2026.07.26.6
  transition using metadata-only evidence and explicitly reports that appcast
  publication is not allowed for that transition.
- **SC-004**: A subsequent Developer ID-to-Developer ID candidate passes ordinary
  update continuity validation without weakening bundle, team, feed or trust
  checks.
- **SC-005**: A clean release-operator walkthrough reaches the correct build,
  notarization, artifact, rollback and publication commands without consulting
  historical receipts.

## Assumptions

- `v2026.07.26.6` is the published manual bootstrap from the historical
  self-signed channel to Developer ID.
- The Apple Developer team, Developer ID certificates and local notary profile
  remain in the operator-controlled keychain and are never committed.
- The existing Sparkle Ed25519 trust generation is retained for ordinary
  updates; rotating it is a separate migration.
- Historical release notes and receipts remain immutable facts and are not
  rewritten to claim that earlier artifacts were notarized.
- App Store distribution is out of scope; this slice covers direct notarized
  `.pkg`, public ZIP/update artifacts and production download hosting.

## Out of Scope

- Rewriting old release facts or deleting historical owner-only receipts.
- Adding Mac App Store / App Store Connect publication.
- Rotating the Sparkle Ed25519 key generation.
- Changing capture, storage, transcription, auth or meeting-data semantics.
