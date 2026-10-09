# Implementation Plan: Надёжная подготовка аудио при платном хранении

**Branch**: `287-audio-storage-permissions` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

## Summary

Согласовать минимальное чтение финансовых фактов с существующим расчётом хранения. Выбрать только снимок объёма бонуса и снимок тарифа счёта вместо целых ORM-объектов; выдать службе SELECT конкретных столбцов четырёх таблиц. Сохранить все предикаты, порядок, NULL-семантику и ветки расчёта. Использовать существующие настройку/проверку ролей и испытания PostgreSQL.

## Technical Context

**Language/Version**: Python 3.13, PostgreSQL 17.
**Primary Dependencies**: существующие SQLAlchemy, asyncpg, pytest, Alembic; новых зависимостей нет.
**Storage**: существующие финансовые таблицы и RLS; схема данных не меняется.
**Testing**: причинный PostgreSQL-тест под `twobrain_rec_media`, матрица вычисления объёма, отрицательные права и действующие наборы хранения/подготовки.
**Risk / Validation Lane**: high-risk-product: права PostgreSQL и общий расчёт хранения.
**Release Gate**: no deploy в текущем запросе разработки; commit/merge/production после отдельного разрешения по AGENTS.md. Затем exact-SHA/base governance-fast, macos-pr, pr-metadata; frozen release-full и cd-remote.sh --dry-run до исполнения выпуска.
**Target Platform**: Linux Docker server; локальная проверка PostgreSQL на Mac.
**Project Type**: внутреннее исправление серверной службы.
**Performance Goals**: тот же порядок/число запросов и отсутствие загрузки ненужных финансовых столбцов.
**Constraints**: финансовая запись, лишние поля, BYPASSRLS и членство в ролях запрещены; реальные встречи не используются в тестах.
**Scale/Scope**: четыре группы столбцов; один общий расчёт; существующие production/test пути настройки ролей.

## Constitution Check

До исследования: PASS. Существующие capture/consent/deletion/source/egress/квоты сохраняются. Исходный инцидент подтверждён метаданными, не помещаем реальные записи в артефакты. Соблюдаем полный Spec Kit; правила выпуска и reviewer ownership не обходятся.
После проектирования: PASS. Разрешено только чтение необходимых полей своей рабочей области; нет новых таблиц, SECURITY DEFINER, денежных операций, сторонней передачи или новых механизмов восстановления.

## Validation Plan

1. До исправления: новый тест действующей `personal`-подписки воспроизводит `database_unavailable` при `run_normalization_job` под настоящей ограниченной ролью.
2. После исправления: тот же тест публикует результат, резервирование завершается, квота не превышается.
3. Все разрешённые поля доступны только внутри рабочего контекста; лишние финансовые поля, таблицы целиком и запись отклоняются.
4. Все варианты квоты (включая NULL бонуса и старые снимки) сохраняют значения в действующих unit/integration наборах. Проверяем повторную настройку и отзыв/лишнее разрешение.
5. Изолированный PostgreSQL удаляется штатным runner; сохраняются только журналы и результаты. Проверяем governance, lint, diff; независимое ревью и convergence до запроса разрешения на commit.

## Project Structure

Документы: `specs/287-audio-storage-permissions/{spec,plan,research,data-model,quickstart,tasks}.md`, `contracts/media-storage-read.md`, reviewer-owned `checklists/{security,infra}.md`.
Код: `apps/server/src/twobrain_rec_server/billing/purchases.py`, `apps/server/scripts/bootstrap_runtime_database_roles.py`.
Проверки: `apps/server/tests/fixtures/postgres_test_database.py`, `apps/server/tests/integration/test_playback_normalization_postgres.py`, `apps/server/tests/integration/test_rls_postgres_policies.py`, `apps/server/tests/unit/test_storage_packages.py`, `apps/server/tests/unit/test_billing_entitlements.py`, `apps/server/tests/unit/test_renewal_charge.py`.
Фрагмент изменений: `changes/unreleased/F287.yaml`.

**Structure Decision**: Продолжить существующий путь настройки ролей и тестов; без нового приложения, подсистемы прав или восстановителя.

## Complexity Tracking

Нарушений конституции нет.
