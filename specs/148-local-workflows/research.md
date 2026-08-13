# Research: Локальные CI и release workflows

## Decision 1: Отключение GitHub Actions

**Decision**: Сохранить repository-level `enabled=false` и удалить tracked
workflow YAML после появления локальных эквивалентов.

**Rationale**: Setting предотвращает запуск даже при случайном появлении YAML;
удаление YAML делает source of truth однозначным и убирает ложные инструкции.

**Alternatives considered**: Оставить YAML как документацию — отвергнуто,
поскольку это исполняемые файлы и дублирующий контур. Переименовать extension —
не даёт гарантию repository-level disable.

## Decision 2: CI и CD

**Decision**: Использовать существующие `infra/scripts/ci-local.sh --fast|--full`
и `infra/scripts/cd-remote.sh`; новый CI wrapper не создавать.

**Rationale**: GitHub validation workflow уже только вызывал эти проверки либо
дублировал команды, которые входят в full lane. Existing scripts являются
canonical и уже проверены release evidence.

**Alternatives considered**: Перенести YAML шаги в новый `workflow-local.sh` —
отвергнуто как лишний слой и новый источник расхождений.

## Decision 3: Custody и signer

**Decision**: Сделать named macOS Keychain единственным active signing channel;
не экспортировать signer и не сохранять его в GitHub environment.

**Rationale**: Keychain уже содержит recovery generation, public identity
совпадает с manifest. Прямое использование уменьшает число копий private key и
исключает transient secret files/environment.

**Alternatives considered**: Скачать GitHub secret локально — GitHub не позволяет
читать secret и это ухудшило бы custody. Хранить encrypted key file — добавляет
новый key-management контур без необходимости. Ротация — не нужна и повышает
риск несовместимости установленных клиентов.

## Decision 4: Локальная attestation

**Decision**: Использовать существующий формат Keychain attestation с exact tag,
origin commit, timestamp и UUID; расширить active manifest до local-only channel.

**Rationale**: Формат уже валидируется и не содержит private material. Один
local attestation достаточно подтверждает и custody, и signer, потому что
подпись выполняется тем же named Keychain account на той же машине.

**Alternatives considered**: Эмулировать `github-environment` attestation —
ложное доказательство. Требовать две локальные attestation — дублирование без
независимого trust boundary.

## Decision 5: Draft release orchestration

**Decision**: Новый локальный script сохраняет прежние input/provenance/archive
checks, использует `prepare-app-update.sh` в `keychain` mode и загружает outputs
через authenticated `gh` только после полного staging success.

**Rationale**: Это минимальная миграция уже проверенного workflow без изменения
public update contract.

**Alternatives considered**: Работать только с локальными input paths — теряется
проверка immutable draft assets. Автоматически публиковать release/feed —
нарушает текущую разделённую publication gate.
