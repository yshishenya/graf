# Feature Specification: Universal macOS Installer

**Feature Branch**: `147-macos-arch-builds`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Зафиксировать поддержку Intel и собирать один универсальный установщик для Apple Silicon и Intel, обновив документацию и страницу скачивания"

## User Scenarios & Testing

### User Story 1 - One installer for supported Macs (Priority: P1)

As a GRAF user on Apple Silicon or Intel Mac, I want to download one installer
that works natively on my computer so that I do not need to understand CPU
architectures or choose a package manually.

**Why this priority**: One reliable download is the simplest user experience
and the central product decision for Intel support.

**Independent Test**: Build one release installer, inspect that its application
contains both required native slices, and install it on matching Apple Silicon
and Intel macOS runtimes.

**Acceptance Scenarios**:

1. **Given** a release version is prepared, **When** the release build runs,
   **Then** it produces one installer containing both `arm64` and `x86_64`
   application code with one product version and bundle identity.
2. **Given** an Apple Silicon Mac, **When** the universal installer is installed
   and the application is launched, **Then** macOS runs the `arm64` slice
   natively without Rosetta.
3. **Given** an Intel Mac that meets the supported macOS minimum, **When** the
   same universal installer is installed and the application is launched,
   **Then** macOS runs the `x86_64` slice natively and the application reaches
   the same supported capture and cabinet behavior.
4. **Given** the built application is inspected before publication, **When** one
   architecture slice is missing or invalid, **Then** release validation fails
   before the installer can be published.

---

### User Story 2 - Simple public download flow (Priority: P1)

As a person visiting the GRAF download page, I want one clear download action
that works from either supported Mac architecture so that I do not have to
identify my processor or rely on browser detection.

**Why this priority**: The universal installer removes the need for an
architecture choice; the website should communicate that simplicity.

**Independent Test**: Render the public download page and verify that its main
download action points to the universal installer, is accessible, and does not
present obsolete architecture-specific packages.

**Acceptance Scenarios**:

1. **Given** the public download page loads, **When** the user views the main
   action, **Then** the page presents one labelled GRAF download link.
2. **Given** the user is on either Apple Silicon or Intel Mac, **When** they
   follow the link, **Then** the same universal installer is downloaded.
3. **Given** the browser does not expose architecture information, **When**
   the page renders, **Then** the download action remains fully usable without
   JavaScript or a browser-specific hint.
4. **Given** the universal installer is not available, **When** the page is
   rendered, **Then** the page does not claim that a downloadable installer is
   ready and shows a truthful recovery state.

---

### User Story 3 - Repeatable documented release process (Priority: P2)

As a maintainer, I want the universal build, publication, and support rules
documented in one consistent place so that every future release keeps both
architectures, one download URL, and the same compatibility promise.

**Why this priority**: Without a repeatable release contract, a later change
could silently publish an ARM-only installer or reintroduce confusing package
choices.

**Independent Test**: Follow the documented release checklist from a release
input and verify that it requires the universal artifact, validates both
architectures, checks the public link, and records the Intel support boundary.

**Acceptance Scenarios**:

1. **Given** a maintainer follows the release procedure, **When** they prepare a
   version, **Then** the procedure requires both native slices in one installer
   before publication.
2. **Given** a contributor reads the product and status documentation, **When**
   they look up macOS support, **Then** it states native Apple Silicon and
   Intel support with the declared macOS minimum and no obsolete ARM-only
   promise.
3. **Given** a release is rolled back, **When** the previous public artifact is
   restored, **Then** the single download URL resolves to that previous
   universal installer.

### Edge Cases

- A build host can compile only one architecture; the release process must
  fail closed instead of publishing a partial installer.
- The universal application and every executable nested inside it must be
  checked for the required architecture coverage where applicable.
- An Intel Mac that cannot run the supported macOS minimum is outside the
  supported promise and must receive a clear compatibility message.
- A stale architecture-specific artifact or link must not remain presented as
  the current public download.
- The installer must retain one stable product identity and version across both
  architecture slices.

## Requirements

### Functional Requirements

- **FR-001**: The release process MUST produce one universal macOS installer for
  every supported GRAF release.
- **FR-002**: The installed GRAF application MUST contain native `arm64` and
  native `x86_64` slices in the same executable bundle.
- **FR-003**: The universal installer MUST use one product version, bundle
  identifier, minimum macOS version, product name, signing policy, and release
  notes.
- **FR-004**: Release validation MUST inspect the final application and reject
  a missing, invalid, or incorrectly assembled architecture slice before
  publication.
- **FR-005**: The public download page MUST expose one primary download choice
  for the universal installer.
- **FR-006**: The public download link MUST use one stable filename and resolve
  to the universal installer shown by the page.
- **FR-007**: The download page MUST NOT require JavaScript, browser
  architecture detection, or manual CPU selection to download the installer.
- **FR-008**: The published installer MUST pass the repository's required
  signing, notarization, packaging, and metadata checks before release.
- **FR-009**: Product, installer, download-page, release, and current-status
  documentation MUST use one canonical vocabulary for universal support and
  the included `arm64`/`x86_64` slices.
- **FR-010**: The supported Intel promise MUST be limited to Intel Macs that
  can run the declared minimum macOS version; older systems MUST be described
  as unsupported rather than silently receiving an incompatible installer.
- **FR-011**: ARM and Intel execution MUST provide the same product behavior
  and server boundary; architecture slices MUST NOT become separate feature
  variants without a separately approved product decision.
- **FR-012**: Release rollback documentation MUST restore the matched universal
  installer for the selected rollback version.

### Key Entities

- **Universal installer**: The single release installer containing the GRAF
  application with both native macOS architecture slices.
- **Architecture slice**: The native `arm64` or `x86_64` executable selected by
  macOS on the current machine.
- **Release artifact**: The versioned installer, its checksum, signing and
  notarization result, and architecture validation evidence.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every release candidate produces and validates one installer with
  both required architecture slices before any public download link is updated.
- **SC-002**: The public download page has exactly one primary installer link,
  and 100% of rendered-page and HTTP checks resolve it to the current universal
  artifact.
- **SC-003**: A reviewer can start the correct download in one page view without
  knowing the Mac's processor architecture.
- **SC-004**: The ARM and Intel slices report the same product version, bundle
  identifier, minimum macOS version, signing status, and release metadata.
- **SC-005**: The release checklist, installer documentation, product baseline,
  and current product status contain no remaining statement that Intel is
  unsupported for the declared macOS minimum.
- **SC-006**: A missing architecture slice causes release validation to fail
  before publication.

## Assumptions

- The current macOS minimum remains macOS 14.5 unless a separate compatibility
  decision changes it.
- GRAF continues to use the existing native macOS app and server-mediated
  cabinet boundary for both architectures.
- The universal build is produced from one source revision and one release
  version; no permanent code fork is introduced.
- The current installer container and install location remain in scope for
  this feature; a future migration to another container format is a separate
  release architecture slice.
- The public download page remains usable without authentication, JavaScript,
  or browser architecture hints.
