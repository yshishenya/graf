# Feature Specification: Локальные CI и release workflows

**Feature Branch**: `148-local-workflows`

**Created**: 2026-08-13

**Status**: Implemented — local validation complete; release/deploy excluded

**Input**: User description: "Все workflows должны быть локальными, а не GitHub Actions"

## User Scenarios & Testing

### User Story 1 - Локальная проверка изменений (Priority: P1)

Разработчик запускает быструю или полную проверку GRAF на своей рабочей
станции и получает однозначный результат без запуска удалённого CI.

**Why this priority**: Это ежедневная обратная связь для каждого изменения и
замена автоматической проверки pull request.

**Independent Test**: На чистом checkout запускаются быстрая и полная локальные
линии; каждая завершается явным pass/fail и не создаёт GitHub Actions run.

**Acceptance Scenarios**:

1. **Given** подготовленное изменение, **When** разработчик запускает быструю
   линию, **Then** серверные тесты и статические проверки выполняются локально.
2. **Given** release-кандидат, **When** оператор запускает полную линию,
   **Then** локально выполняются macOS, server и deployment-readiness проверки.

---

### User Story 2 - Локальная проверка ключа подписи (Priority: P1)

Release-оператор проверяет активный Sparkle signer непосредственно в macOS
Keychain и получает metadata-only attestation, привязанную к точному тегу и
commit, не экспортируя приватный ключ.

**Why this priority**: После отключения GitHub Actions нельзя потерять
fail-closed проверку custody и соответствие публичному ключу приложения.

**Independent Test**: Проверка с правильным Keychain signer создаёт attestation;
отсутствующий или несовпадающий signer, tag либо commit завершают процесс до
подписи и публикации.

**Acceptance Scenarios**:

1. **Given** активный manifest, опубликованный tag текущего `master` и
   соответствующий Keychain signer, **When** оператор запускает проверку,
   **Then** создаётся только metadata-only attestation без приватного материала.
2. **Given** signer или provenance не совпадает, **When** запускается проверка,
   **Then** процесс останавливается до изменения release-артефактов.

---

### User Story 3 - Локальная подпись draft release (Priority: P1)

Release-оператор одной локальной командой скачивает утверждённые draft assets,
проверяет provenance и Keychain custody, подписывает Sparkle update и загружает
результат обратно в тот же draft GitHub Release.

**Why this priority**: Это локальная замена удалённого workflow, без которой
публичный update-процесс станет неполным.

**Independent Test**: На disposable signer и draft fixture команда создаёт ZIP,
appcast, checksum и metadata-only attestation; любой неверный вход останавливает
процесс до upload.

**Acceptance Scenarios**:

1. **Given** чистый checkout точного tag на текущем `master`, draft release,
   безопасные assets и соответствующий Keychain signer, **When** оператор
   запускает локальную подпись, **Then** подписанные assets загружаются в draft.
2. **Given** release уже опубликован, archive небезопасен, tag не равен
   `origin/master` или signer не совпадает, **When** команда запускается,
   **Then** она завершается без публикации новых assets.

---

### User Story 4 - GitHub без исполняемых workflows (Priority: P2)

Владелец репозитория использует GitHub для кода, pull requests, issues, tags и
releases, но не для выполнения CI, signing или custody-проверок.

**Why this priority**: Это устраняет повторные медленные запуски и зависимость
от GitHub Actions billing.

**Independent Test**: В default branch отсутствуют исполняемые Actions workflow,
а repository-level Actions остаются выключены.

**Acceptance Scenarios**:

1. **Given** merge feature, **When** создаётся или обновляется pull request,
   **Then** GitHub Actions run не создаётся.
2. **Given** release-оператору нужны CI или signing, **When** он читает runbook,
   **Then** все обязательные команды описаны как локальные.

### Edge Cases

- Локальный Keychain signer отсутствует или заблокирован.
- Публичный manifest не соответствует signer либо встроенному ключу приложения.
- Tag отсутствует на origin, не равен текущему `origin/master` или checkout dirty.
- GitHub Release отсутствует, уже опубликован или содержит отсутствующий asset.
- ZIP содержит абсолютный путь, traversal, обратный slash или не содержит
  единственный ожидаемый `GRAF.app` root.
- Параллельно запущены две локальные попытки подписи одного update feed.
- Upload частично не завершён; production feed при этом не должен изменяться.
- GitHub Actions случайно включены повторно на уровне repository settings.

## Requirements

### Functional Requirements

- **FR-001**: Все CI, custody, signing и release-validation сценарии MUST иметь
  локально запускаемый canonical entrypoint.
- **FR-002**: Репозиторий MUST NOT содержать исполняемые GitHub Actions workflow,
  а Actions MUST оставаться выключенными на уровне repository settings.
- **FR-003**: Быстрая локальная линия MUST выполнять серверные unit-тесты, lint и
  compile checks; полная линия MUST сохранять macOS, server, RLS, Compose и
  deployment-evidence gates.
- **FR-004**: Production deploy MUST продолжать запускать полную локальную линию
  на точном pinned SHA до remote mutation.
- **FR-005**: Sparkle private key MUST оставаться в named macOS Keychain и MUST
  NOT экспортироваться в файл, environment, repository, logs или GitHub secret
  как часть нового локального пути.
- **FR-006**: Локальная custody-проверка MUST сверять signer с активным public
  manifest и `SUPublicEDKey`, а attestation MUST быть metadata-only и привязана
  к точным release tag и commit.
- **FR-007**: Локальная подпись MUST требовать чистый checkout, точное совпадение
  HEAD, опубликованного tag и текущего `origin/master`, а также draft state
  целевого GitHub Release.
- **FR-008**: Все скачанные archives MUST проходить integrity и path-safety
  проверки до extraction; signer mismatch MUST останавливать процесс до upload.
- **FR-009**: Подпись MUST использовать pinned и checksum-verified Sparkle tools
  либо уже установленный artifact, доказанно соответствующий той же версии.
- **FR-010**: Upload MUST ограничиваться versioned ZIP, appcast, checksum и
  metadata-only signing attestation целевого draft release; production feed
  MUST оставаться отдельной последующей операцией.
- **FR-011**: Локальная staging/signing операция MUST быть сериализована и MUST
  очищать временные assets при success, failure и interruption.
- **FR-012**: Документация MUST называть локальные команды единственным активным
  workflow и не предлагать GitHub Actions как fallback.
- **FR-013**: Исторические release receipts MAY сохранять упоминания фактически
  использованных GitHub Actions; active guidance, tests и manifests MUST быть
  переведены на локальную модель.
- **FR-014**: Миграция MUST сохранить текущую Sparkle trust generation, key ID и
  public key; ротация ключа и production deployment не входят в feature.

### Key Entities

- **Public signing manifest**: публичная trust generation, key ID, public key и
  имя единственного разрешённого локального Keychain account.
- **Local signing attestation**: metadata-only доказательство времени, tag,
  commit, trust generation, key ID и уникального evidence ID.
- **Draft release inputs**: candidate app ZIP, predecessor app ZIP и русские
  release notes, загруженные из конкретных immutable tags.
- **Staged update outputs**: подписанный ZIP, appcast, SHA-256 checksum и
  metadata-only attestation, ещё не опубликованные в production feed.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% трёх существующих GitHub Actions workflows заменены
  документированными локальными entrypoints до удаления workflow-файлов.
- **SC-002**: Создание pull request и release не создаёт ни одного нового
  GitHub Actions run при выключенной repository setting.
- **SC-003**: Полная локальная CI-линия и release-signing custody fixture suite
  завершаются успешно на final feature diff.
- **SC-004**: Во всех негативных signing-сценариях upload count равен нулю и
  production appcast не изменяется.
- **SC-005**: В tracked diff и validation output отсутствует приватный signing
  material; key ID и trust generation после миграции совпадают с baseline.

## Assumptions

- Release signing выполняется только на доверенном macOS operator workstation.
- Активный Sparkle signer уже существует в named Keychain account и соответствует
  текущему public manifest.
- GitHub остаётся местом хранения draft/final release assets, но не исполняет
  workflows.
- Удаление существующей копии secret из GitHub environment выполняется отдельным
  явно подтверждённым security-cleanup после проверки локального signer.
- Production deploy и публикация live appcast не выполняются в этой feature.
