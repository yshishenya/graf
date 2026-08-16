# Process Requirements Checklist: Процесс от разработки до релиза

**Purpose**: Проверить полноту и непротиворечивость правил рабочего цикла.
**Created**: 2026-08-16
**Feature**: [spec.md](../spec.md)

## Completeness

- [x] CHK001 Определены focused checks для локального edit.
- [x] CHK002 Определён fast lane перед PR/closeout.
- [x] CHK003 Определён full lane для release candidate.
- [x] CHK004 Описан обязательный full gate production execute.
- [x] CHK005 Описаны dry-run, approval, smoke и rollback.

## Clarity and Consistency

- [x] CHK006 Ясно, что fast lane и focused checks не считаются full CI.
- [x] CHK007 Ясно, что новый commit после full CI требует повторной проверки.
- [x] CHK008 Release evidence привязано к exact SHA.
- [x] CHK009 `--skip-local-ci` ограничен incident-исключением.
- [x] CHK010 Новые правила не ослабляют signing, notarization и security gates.
- [x] CHK011 Release metadata готовится до финального full CI.

## Notes

Проверка выполнена против `ci-local.sh`, `cd-remote.sh` и текущего
`release-and-validation.md`; runtime-поведение не меняется.
