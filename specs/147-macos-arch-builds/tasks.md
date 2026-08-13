# Tasks

- [X] T003 Обновить installer до `graf.pkg` и единого app-only component.
- [X] T004 Собрать arm64 и x86_64 SwiftPM binaries в отдельных scratch paths.
- [X] T005 Объединить binaries через `lipo` и проверить exact architecture set.
- [X] T006 Разрешить Intel в `PlatformSupport` при сохранении macOS 14.5 floor.
- [X] T007 Добавить unit coverage для Apple Silicon, Intel, unknown и старой ОС.
- [X] T008 Усилить installer validation проверкой universal staged executable.
- [X] T009 Переключить public template, asset и contract tests на `graf.pkg`.
- [X] T010 Исправить PRD, current status, READMEs, feature index и changelog.
- [X] T021 Проверить SwiftPM и cross-architecture release build.
- [X] T022 Пройти полный local CI для Feature 147.

## Phase 7: Convergence

- [X] T023 Синхронизировать канонический `graf.pkg` из checkout в read-only runtime mount при остановленном `rec-api` непосредственно перед первым candidate Compose up в `infra/scripts/cd-remote-runtime.sh` (partial: public download requirement).
- [X] T024 Добавить regression contract для синхронизации и внешнего smoke страницы `/download` и fingerprinted `graf.pkg` в `apps/server/tests/integration/test_deployment_readiness_gates.py` (partial: public download requirement).
- [X] T025 Подтвердить live `/download` и подписанный нотарифицированный `graf.pkg`, записать evidence в `specs/147-macos-arch-builds/evidence/validation-summary.md` и закрыть release checklist (partial: public download requirement).
