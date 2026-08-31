# Feature Specification: Единый процесс разработки и переносимый harness

**Feature Branch**: `216-development-governance-harness`

**Created**: 2026-08-31

**Status**: Draft

**Input**: Запрос владельца GRAF: перестроить совместную работу с агентами, один полноценный Dev-стенд, безопасные worktree, SHA-привязанный CI, редкие release train, стабильный `AGENTS.md`, changelog fragments, атомарные номера фич, системное удаление legacy и переносимый отдельный репозиторий правил.

## Actors and Goals

- **Владелец продукта** — выдаёт задачу и получает понятный статус: что готово, на каком SHA проверено и что можно выпускать.
- **Агент-разработчик** — работает в своём worktree, видит только нужный контекст и не меняет общие файлы, принадлежащие другим фичам.
- **Reviewer** — проверяет требования, риски, evidence и границы; его решения не подменяются агентом реализации.
- **Dev operator** — продвигает выбранный exact SHA в один локальный стенд и может безопасно вернуть предыдущий.
- **Release operator** — собирает несколько проверенных фич в редкий release candidate, запускает полный gate и публикует релиз.
- **CI/automation** — проверяет неизменность SHA, отменяет устаревшие запуски и сохраняет metadata-only evidence.
- **Потребитель harness** — подключает переносимые правила и команды в другом публичном проекте без данных GRAF.

## User Scenarios & Testing

### User Story 1 — Изолированная работа агента (Priority: P1)

Владелец запускает несколько фич параллельно. Каждый агент получает отдельный worktree, свежий Feature ID, короткий стабильный набор правил и явный task-контекст. Работа одной фичи не меняет активный контекст, changelog или незакоммиченные файлы другой.

**Why this priority**: сейчас параллельная работа создаёт конфликты и засоряет контекст, что замедляет все остальные проверки.

**Independent Test**: создать два disposable worktree и выполнить preflight одновременно; каждый получает разные claims, одинаковые стабильные правила и отдельные fragment-файлы.

**Acceptance Scenarios**:

1. **Given** две открытые фичи, **When** агенты запускают preflight, **Then** каждый видит только свой Feature ID, branch, spec и task, а root `AGENTS.md` остаётся неизменным.
2. **Given** агент завершил задачу, **When** он записывает changelog, **Then** изменяется только fragment его фичи, а общий `CHANGELOG.md` не конфликтует.
3. **Given** активный worktree содержит пользовательские изменения, **When** запускается harness, **Then** он останавливается с понятной диагностикой и ничего не сбрасывает.

### User Story 2 — Полный единый Dev-стенд (Priority: P1)

Dev operator собирает backend, frontend и macOS-клиент из одного exact SHA, продвигает их в один локальный стенд и открывает одну установленную `/Applications/GRAF Dev.app`. Стенд имеет понятный manifest, health/smoke и обратимый rollback.

**Why this priority**: без единого стенда невозможно честно проверить сквозной пользовательский путь.

**Independent Test**: собрать synthetic build, выполнить `build → promote → status → smoke → rollback`, убедившись, что все компоненты ссылаются на один SHA и предыдущий manifest восстанавливается.

**Acceptance Scenarios**:

1. **Given** clean exact SHA, **When** выполняется promote, **Then** backend, frontend, worker/dependencies и Dev app получают один manifest с SHA, image digests, migration head и временем.
2. **Given** promote завершился частично, **When** health/smoke не проходит, **Then** активным остаётся предыдущий manifest, а partial build не выдаётся за Dev.
3. **Given** две фичи одновременно запрашивают promote, **When** действует lock, **Then** только одна становится active, вторая получает отказ с причиной и не перезаписывает стенд.
4. **Given** Dev app обновляется, **When** пользователь уже выдал microphone/screen permissions, **Then** bundle ID, designated requirement и подпись сохраняются, а повторные разрешения не запрашиваются без изменения trust identity.

### User Story 3 — Честный CI для меняющегося SHA (Priority: P1)

Разработчик получает быстрый feedback на текущий коммит. Если появляется новый SHA, старый длительный запуск отменяется или помечается stale; его результат нельзя использовать для merge или release.

**Independent Test**: запустить два CI harness runs на разных synthetic SHAs и доказать, что первый не может стать evidence для второго.

**Acceptance Scenarios**:

1. **Given** run для SHA-A, **When** branch указывает на SHA-B, **Then** run-A получает статус stale/cancelled и не блокирует SHA-B.
2. **Given** frozen release candidate SHA-C, **When** появляются новые коммиты в branch, **Then** authoritative full run остаётся привязанным к SHA-C и не перезапускается из-за новых изменений.
3. **Given** interrupted или partial run, **When** формируется release evidence, **Then** он явно отмечен неполным и не считается успешным.

### User Story 4 — Атомарная идентификация фичи и GitHub-трекинг (Priority: P1)

Владелец создаёт umbrella GitHub issue до разработки, получает свободный Feature ID, а затем одинаково использует его в spec, branch, tasks, child issues, PR и release evidence. Исторические дубли не переиспользуются.

**Independent Test**: параллельно запросить два claims; они получают разные номера, а validator отклоняет отсутствующий, повторный или несогласованный ID.

**Acceptance Scenarios**:

1. **Given** занятые локальные и удалённые номера, **When** запрашивается новый claim, **Then** выдаётся первый действительно свободный номер после проверки specs, branches, PR и открытых issues.
2. **Given** umbrella issue #6090 и Feature ID 216, **When** создаются task issues, **Then** каждый title/body/label содержит `216`, свой `T###` и ссылку на umbrella.
3. **Given** PR без Feature ID или с другим ID, **When** запускается pre-merge guard, **Then** guard завершается ошибкой до review/merge.

### User Story 5 — Редкий release train (Priority: P1)

Release operator объединяет несколько завершённых и независимо проверенных фич в candidate по расписанию. Полный CI, tag, GitHub Release, русские notes, compatibility impact и rollback относятся к одному immutable SHA.

**Independent Test**: заморозить synthetic candidate, выполнить metadata preparation, full gate и release checklist; попытка изменить candidate после full gate должна сделать evidence недействительным.

**Acceptance Scenarios**:

1. **Given** несколько PR с fast evidence, **When** открывается release window, **Then** создаётся один immutable candidate и один authoritative full run.
2. **Given** полный gate успешен, **When** выпускается продукт, **Then** создаются CalVer tag, GitHub Release и русские notes со ссылками на PR/issues и exact SHA.
3. **Given** smoke/rollback gate не пройден, **When** release operator закрывает candidate, **Then** публикация блокируется, а причина и следующий шаг сохранены.
4. **Given** срочная production-проблема, **When** нужен hotfix, **Then** он проходит отдельный явно отмеченный путь и не превращает каждую фичу в обычный релиз.

### User Story 6 — Нет нового legacy и управляемое retirement (Priority: P1)

Каждая новая фича показывает Legacy Impact: что удалено, что сохранено и почему. Compatibility exception допускается только с владельцем, сроком окончания, trigger удаления и отдельной задачей. Существующий legacy пока остаётся отдельными slices.

**Independent Test**: validator отклоняет feature/PR без Legacy Impact и истёкшее исключение; synthetic exception с owner/expiry/trigger проходит.

**Acceptance Scenarios**:

1. **Given** новый alias, fallback, flag, dependency, fixture, test или documentation path, **When** фича закрывается, **Then** он удалён либо оформлен как временное исключение.
2. **Given** compatibility exception достигла expiry, **When** запускается governance check, **Then** PR/release блокируется до retirement или продления с объяснением.
3. **Given** найден существующий legacy contour, **When** создаётся follow-up, **Then** он имеет отдельный spec/issue и не смешан с harness.

### User Story 7 — Контекст без переполнения (Priority: P2)

Агент на каждом шаге получает минимальный релевантный контекст: стабильные project rules, активный feature pointer, текущий task, risk lane и ссылки на нужные guidance-файлы. Исторические документы и чужие worktree не загружаются автоматически.

**Independent Test**: preflight на активной и неактивной фиче показывает bounded context manifest без mtime-эвристики и без чтения чужих specs.

**Acceptance Scenarios**:

1. **Given** несколько specs с разным временем изменения, **When** запускается preflight, **Then** выбирается только `.specify/feature.json`, а не самый свежий `mtime`.
2. **Given** отсутствует active feature pointer, **When** агент начинает изменение, **Then** harness останавливается и просит создать feature, не выбирая случайную.
3. **Given** длинный historical log, **When** формируется prompt context, **Then** включаются только краткий summary, ссылки и текущие критерии, а не вся история.

### User Story 8 — Переносимый публичный harness (Priority: P2)

Владелец публикует reusable harness в отдельном публичном репозитории с pinned version, self-test, документацией и безопасным upgrade path. GRAF-specific product gates остаются в GRAF и не утекают в общий пакет.

**Independent Test**: установить harness в чистый примерный репозиторий, пройти self-test и secret/path scan, затем обновить pinned version без drift.

**Acceptance Scenarios**:

1. **Given** чистый публичный проект, **When** подключается pinned harness release, **Then** применяются правила worktree, Feature ID, CI, release и legacy без абсолютных путей GRAF.
2. **Given** в package случайно попадает секрет, private meeting data или machine-specific path, **When** запускается publish guard, **Then** публикация блокируется.
3. **Given** новая версия harness, **When** проект обновляет lock, **Then** change log и migration notes объясняют совместимость и rollback.

## Edge Cases and Failure States

- GitHub недоступен: claim не выдаётся повторно и не заменяется локальным максимумом; работа может продолжиться только в явно offline draft mode без merge/release claim.
- Два агента создают umbrella issue почти одновременно: один номер/claim считается действительным, duplicate issue помечается ссылкой на source of truth.
- Worktree detached, грязный или основан не на `origin/master`: preflight сообщает точный SHA и блокирует promote до явного исправления.
- Dev lock потерян во время promote: новый процесс проверяет manifest и либо безопасно продолжает идемпотентную операцию, либо оставляет предыдущий active manifest.
- Backend/frontend/app имеют разные SHA или digest: status — degraded, smoke и release блокируются.
- Миграция БД несовместима с rollback: promotion запрещён без reversible/expand-contract плана; reset/reseed разрешён только для Dev.
- macOS keychain, signing identity или permission trust изменились: Dev app не заменяется молча, старый app остаётся активным.
- CI runner упал после фактического завершения тестов: evidence имеет `ambiguous`, повторный полный запуск разрешён только с новым run identity.
- Feature branch переименована: claim сохраняет историческую связь, validator требует обновить branch metadata, а не создавать новый Feature ID.
- Legacy path нужен для production compatibility: exception содержит owner, expiry, trigger, migration/cutover и отдельную задачу; «оставить на всякий случай» запрещено.
- Отдельный harness не может знать GRAF product privacy/capture rules: он применяет generic safety hooks и требует project adapter, не копируя закрытые данные.

## Requirements

### Functional Requirements

- **FR-001**: Система MUST создавать ровно один активный Feature ID claim на одну feature-инициативу до создания branch/spec.
- **FR-002**: Claim MUST проверять локальные specs, все видимые remote branches, открытые GitHub issues/PR и существующие claims.
- **FR-003**: Feature ID MUST быть стабильным, не переиспользоваться после закрытия и присутствовать в spec directory, branch, tasks, issue labels, PR title/body и evidence.
- **FR-004**: Root `AGENTS.md` MUST содержать только стабильные project rules и ссылки; он MUST NOT меняться из-за активной feature или текущего task.
- **FR-005**: Активный feature/task context MUST храниться в ignored per-worktree state и читаться только явно выбранным preflight.
- **FR-006**: Context resolver MUST fail closed при отсутствии или повреждении active pointer и MUST NOT выбирать feature по `mtime`.
- **FR-007**: Один agent worktree MUST иметь одного владельца, одну feature и один branch; disposable worktree не является общей Dev-средой.
- **FR-008**: Feature agent MUST изменять только собственные spec/task/fragment/evidence файлы и согласованные source files.
- **FR-009**: Changelog fragment MUST иметь уникальное имя Feature ID, schema/version и безопасные русские entries; общий `CHANGELOG.md` изменяет только release operator.
- **FR-010**: PR guard MUST проверять Feature ID, umbrella issue, task IDs, risk lane, validation evidence, Legacy Impact и корректные `Fixes`/`Refs` keywords.
- **FR-011**: Dev harness MUST предоставлять операции `build`, `promote`, `status`, `rollback`, `reset-data` и `smoke` с dry-run режимом.
- **FR-012**: Dev promotion MUST быть lock-protected, идемпотентным и атомарным на уровне active manifest.
- **FR-013**: Dev manifest MUST содержать feature ID, exact source SHA, component digests/versions, migration head, app identity, operator, timestamps, parent manifest и health result.
- **FR-014**: В active Dev-среде MUST находиться ровно один backend/frontend bundle и одна `/Applications/GRAF Dev.app`; параллельные кандидаты не устанавливаются рядом.
- **FR-015**: Dev app MUST сохранять bundle ID, signing identity, designated requirement, entitlements и Sparkle/update trust; обновление MUST быть атомарным.
- **FR-016**: Dev smoke MUST проверять backend health, frontend reachability, auth/session bootstrap, one representative API flow, processing dependency health и app-to-backend connection.
- **FR-017**: Dev reset MUST работать только с локальной Dev data boundary и MUST требовать явного подтверждения/флага; production data недоступна этой операции.
- **FR-018**: CI run MUST сохранять exact SHA при старте и перед публикацией результата.
- **FR-019**: Run для SHA, который больше не является target SHA, MUST быть cancelled/stale и MUST NOT считаться merge/release evidence.
- **FR-020**: Release candidate MUST быть immutable после metadata freeze; изменение source, lock, changelog или manifest инвалидирует candidate.
- **FR-021**: На один frozen candidate допускается ровно один authoritative Full CI; retries получают отдельный identity и явно объясненную причину.
- **FR-022**: Fast CI MUST быть обычным PR feedback, Full CI MUST запускаться только на frozen candidate или для диагностического broad baseline.
- **FR-023**: Release train MUST иметь schedule/window, owner, candidate manifest, go/no-go checklist, rollback plan и metadata-only evidence.
- **FR-024**: Product release MUST использовать CalVer `vYYYY.MM.DD.N`; tag, GitHub Release и русские notes MUST ссылаться на один SHA.
- **FR-025**: Hotfix MUST быть явно помечен и документировать, почему обычное окно пропущено.
- **FR-026**: Every feature spec MUST contain Legacy Impact section and classify changed legacy surfaces as remove, retain-with-exception or untouched.
- **FR-027**: Compatibility exception MUST contain owner, expiry date, removal trigger, affected surface, risk and linked retirement task; expired exceptions block merge/release.
- **FR-028**: Definition of Done MUST запрещать новый legacy alias, fallback, flag, dependency, fixture, test, docs path or compatibility branch без exception.
- **FR-029**: Existing legacy cleanup MUST be decomposed into separately testable retirement slices with evidence and migration/cutover safety.
- **FR-030**: Harness package MUST separate generic rules from GRAF-specific adapters and MUST publish pinned immutable versions with SemVer.
- **FR-031**: Harness publish guard MUST reject secrets, raw audio, transcript text, private meeting data, credentials, signed URLs and machine-specific absolute paths.
- **FR-032**: All issue/PR/release text generated by the process MUST follow Russian issue canon, include task IDs and use labels `feature`, `priority`, `area`, `type`, `gate` where applicable.
- **FR-033**: Optional auto-commit hooks MUST be disabled by default; commits after implementation require explicit owner approval following validation and convergence.
- **FR-034**: Reviewer-owned checklist states MUST NOT be changed by implementation agents; unresolved required items block convergence.
- **FR-035**: Every gate result MUST include command, exact SHA, start/end time, status, scope, skipped gates and safe failure reason.
- **FR-036**: The process MUST provide a short operator runbook with next action for each blocked state and a rollback command for each mutable operation.

### Key Entities

- **Feature Claim** — immutable Feature ID, umbrella issue, owner, branch/spec, creation time and status (`reserved`, `active`, `closed`, `retired`).
- **Agent Context Manifest** — active Feature ID, task, risk lane, relevant guidance links, source SHA and worktree identity.
- **Changelog Fragment** — Feature ID, category, Russian entry, issue/task links, compatibility and release-note metadata.
- **Dev Manifest** — exact source SHA, backend/frontend/app artifacts, digests, migration head, app identity, health result, parent manifest and promotion timestamps.
- **CI Run Evidence** — run ID, target SHA, observed SHA, lane (`focused`, `fast`, `full`), result, cancellation/stale reason and artifact hashes.
- **Release Candidate** — frozen SHA, included Feature IDs, changelog snapshot, full-CI identity, go/no-go decision, tag/release and rollback target.
- **Legacy Exception** — affected path, reason, owner, expiry, removal trigger, linked retirement task and validation boundary.
- **Harness Release** — immutable SemVer, portable rules/scripts/templates, adapters, self-test result, provenance and migration notes.

## Clarifications

### Session 2026-08-31

- Q: Нужно ли удалять существующий legacy в этой фиче? → A: Нет; только запрет нового legacy, Legacy Impact и отдельные retirement slices.
- Q: Должна ли Dev-среда поддерживать параллельные активные SHA? → A: Нет; разработка параллельна, ручная проверка и active promotion последовательны в одном стенде.
- Q: Где должен жить reusable harness? → A: В отдельном публичном репозитории с pinned SemVer; GRAF-specific gates остаются адаптером проекта.
- Coverage decision: вопросы, меняющие архитектуру и validation, закрыты безопасными defaults; оставшиеся детали относятся к Phase 0/Phase 1 plan и не блокируют specification.

## Scope

### In Scope

- Governance, agent/worktree protocol, Feature ID reservation, PR/issue guards and context boundaries.
- One complete Dev harness for backend/frontend/macOS app, manifest, promotion, rollback, reset and smoke.
- SHA-bound focused/fast/full CI and release-train rules.
- Changelog fragments and stable root guidance.
- Legacy Impact/exception policy and a follow-up retirement backlog plan.
- Extraction contract and initial package layout for a separate reusable public harness repository.

### Out of Scope

- Mass deletion of existing product legacy, historical migrations, Temporal compatibility or Sparkle/client compatibility.
- Product behavior changes in capture, auth, billing, transcription or deletion.
- Production deployment, public product release and changing end-user permissions in this feature.
- Moving or rewriting every existing worktree without owner review.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of new feature preflights either receive a unique claim or fail with an actionable collision/availability reason; no duplicate claim is accepted in a concurrency test.
- **SC-002**: Two simultaneous feature worktrees complete preflight with zero changes to root `AGENTS.md` and zero writes outside their owned spec/task/fragment/evidence paths.
- **SC-003**: A Dev promotion/status/smoke sequence proves one active manifest whose backend, frontend and app all report the same exact SHA; rollback restores the prior manifest in under 60 seconds in a local fixture.
- **SC-004**: Stale-SHA tests detect 100% of changed-target, interrupted and mismatched-component cases; stale evidence cannot pass the release validator.
- **SC-005**: A frozen candidate permits one authoritative Full CI identity and produces a complete metadata-only release record with tag, GitHub Release and Russian notes.
- **SC-006**: 100% of feature specs/PRs in the new process contain Legacy Impact; zero new unowned legacy paths and zero expired exceptions pass the governance guard.
- **SC-007**: A clean external sample repository installs the harness from an immutable SemVer, passes self-test and contains no GRAF secrets, private data or machine-specific paths.
- **SC-008**: Agent preflight context stays bounded to the active feature manifest and linked guidance; it never selects a feature by `mtime` or loads unrelated specs automatically.
- **SC-009**: The complete declared feature quickstart and `infra/scripts/ci-local.sh --fast` pass on the PR-ready SHA; Full CI is not run before candidate freeze except for explicitly recorded diagnosis.
- **SC-010**: A separately tracked legacy-cleanup follow-up exists with prioritized contours, owners and safe migration boundaries before this governance feature closes.

## Assumptions and Dependencies

- `origin/master` is the integration base; the current repository is public and GitHub account has permission to create issues, labels, branches and PRs.
- Spec Kit `216` is reserved after checking remote branch `215-summary-auto-recovery` and all visible refs; GitHub issue #6090 is the umbrella reservation record.
- Existing GRAF constitution, product gates, issue canon and CalVer policy remain authoritative; this feature extends them without weakening safety rules.
- GitHub Actions may remain disabled; the harness must provide equivalent local/remote evidence and explicit status.
- A macOS developer keychain is available for local Dev app signing; public Developer ID/notarization remains a separate release gate.
- Dev reset/reseed may recreate local data; production data and migrations require separate approved changes.
- The reusable repository name is provisional (`graf-development-harness`) and must be checked for availability before creation.
- No secrets, private meeting content, raw audio, transcript text or live credentials are committed or published.

## Legacy Impact

- **New legacy**: forbidden by FR-028; every exception must be explicit and time-bounded.
- **Existing contours**: aliases, fallback environment names, old states, compatibility migrations, Temporal patch markers, historical specs and internal names remain untouched in this feature and will be retired in separate slices.
- **Protected compatibility**: database migrations, Temporal history, Sparkle/client updates and production data cutovers require their own spec, owner, migration evidence and rollback plan.
- **Follow-up**: create `217-legacy-retirement-program` (or the next available collision-free Feature ID) after this feature's process artifacts are accepted; it will own inventory, prioritization and deletion slices.
