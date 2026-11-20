# Infrastructure Checklist: F297

**Purpose**: Validate retention/backup operational requirements before implementation
**Created**: 2026-11-17
**Feature**: [spec.md](../spec.md)

- [x] CHK001 Определён ли ежедневный запуск retention и его первый запуск после деплоя?
- [x] CHK002 Ограничен ли batch size и не блокирует ли один workspace остальные?
- [x] CHK003 Идемпотентен ли повторный retention после сбоя?
- [x] CHK004 Определены ли точный root, шаблон имени и возраст backup-каталогов?
- [x] CHK005 Описаны ли dry-run, execute, output и exit codes prune?
- [x] CHK006 Определены ли ежедневный запуск prune через systemd и процедуры установки, включения, отключения и отката?
- [x] CHK007 Допускает ли изменение только аддитивную RLS-миграцию `rec_maintenance_allowed()` без изменения таблиц и данных и не требует ли нового сервиса в API-контейнере?
- [x] CHK008 Отделено ли production-включение prune от кода и требует ли явного действия оператора?
- [x] CHK009 Определены ли rollback/disable и поведение при ошибке prune?
- [x] CHK010 Согласованы ли публичные сроки с фактическим расписанием?
