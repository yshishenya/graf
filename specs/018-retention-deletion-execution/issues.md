# GitHub Issue Sync: Retention And Deletion Execution

**Created**: 2026-06-16
**Feature**: `018-retention-deletion-execution`
**Repository**: `yshishenya/crisp`

## Summary

- Created issues: 66
- Issue range: #889-#954
- Canon validation: `github-issue-canon: OK (192 Spec Kit issue(s) checked)`
- Duplicate search before creation: no existing `feature:018` issues found

## Mapping

| Task | Issue | Title |
|------|-------|-------|
| T001 | #889 | `[018][P0][setup] Создать пакет deletion domain` |
| T002 | #890 | `[018][P0][test] Подготовить фикстуры deletion lifecycle` |
| T003 | #891 | `[018][P0][macos] Подготовить Swift-тест local purge` |
| T004 | #892 | `[018][P0][lifecycle] Добавить lifecycle enums` |
| T005 | #893 | `[018][P0][db] Добавить deletion models` |
| T006 | #894 | `[018][P0][db] Экспортировать deletion models` |
| T007 | #895 | `[018][P0][db] Добавить lifecycle columns к meetings` |
| T008 | #896 | `[018][P0][db] Добавить миграцию retention deletion` |
| T009 | #897 | `[018][P0][db] Обновить RLS inventory` |
| T010 | #898 | `[018][P0][api] Добавить lifecycle schemas` |
| T011 | #899 | `[018][P0][security] Сделать lifecycle audit fail-closed` |
| T012 | #900 | `[018][P0][deletion] Собрать report primitives` |
| T013 | #901 | `[018][P0][test] Покрыть migration и RLS` |
| T014 | #902 | `[018][P0][test] Покрыть no-secret contracts` |
| T015 | #903 | `[018][P0][test] Покрыть audit metadata` |
| T016 | #904 | `[018][P1][test] Покрыть deletion request API` |
| T017 | #905 | `[018][P1][test] Покрыть manual deletion workflow` |
| T018 | #906 | `[018][P1][test] Покрыть access blocking` |
| T019 | #907 | `[018][P1][test] Покрыть report view models` |
| T020 | #908 | `[018][P1][deletion] Реализовать deletion request validation` |
| T021 | #909 | `[018][P1][deletion] Реализовать active server purge accounting` |
| T022 | #910 | `[018][P1][deletion] Собрать verification report` |
| T023 | #911 | `[018][P1][api] Добавить deletion routes` |
| T024 | #912 | `[018][P1][access] Блокировать access для deleting meetings` |
| T025 | #913 | `[018][P1][access] Скрывать deleted rows из list` |
| T026 | #914 | `[018][P1][egress] Блокировать egress после deletion start` |
| T027 | #915 | `[018][P1][lifecycle] Смаппить lifecycle governance` |
| T028 | #916 | `[018][P1][web] Показать delete confirmation и report` |
| T029 | #917 | `[018][P1][test] Покрыть retention run contract` |
| T030 | #918 | `[018][P1][test] Покрыть retention execution` |
| T031 | #919 | `[018][P1][test] Покрыть retention snapshot` |
| T032 | #920 | `[018][P1][retention] Реализовать retention policy snapshot` |
| T033 | #921 | `[018][P1][retention] Реализовать retention eligibility scan` |
| T034 | #922 | `[018][P1][retention] Переиспользовать deletion workflow для retention` |
| T035 | #923 | `[018][P1][api] Добавить internal retention route` |
| T036 | #924 | `[018][P1][retention] Добавить retention activity rows` |
| T037 | #925 | `[018][P1][test] Покрыть local purge contract` |
| T038 | #926 | `[018][P1][test] Покрыть local purge coordination` |
| T039 | #927 | `[018][P1][macos] Покрыть Swift local purge client` |
| T040 | #928 | `[018][P1][deletion] Реализовать local purge task service` |
| T041 | #929 | `[018][P1][api] Добавить local purge API` |
| T042 | #930 | `[018][P1][security] Запретить private payload в purge ack` |
| T043 | #931 | `[018][P1][macos] Добавить local purge models в DesktopUploadClient` |
| T044 | #932 | `[018][P1][macos] Добавить local purge acknowledgement в upload queue` |
| T045 | #933 | `[018][P1][web] Показать local purge states` |
| T046 | #934 | `[018][P1][test] Покрыть dependency и backup contracts` |
| T047 | #935 | `[018][P1][test] Покрыть dependency deletion states` |
| T048 | #936 | `[018][P1][test] Покрыть post-egress и backup report` |
| T049 | #937 | `[018][P1][deletion] Смаппить dependency states` |
| T050 | #938 | `[018][P1][egress] Сохранить post-egress limits` |
| T051 | #939 | `[018][P1][retention] Добавить backup expiry policy` |
| T052 | #940 | `[018][P1][web] Показать backup dependency post-egress rows` |
| T053 | #941 | `[018][P2][test] Покрыть lifecycle activity contracts` |
| T054 | #942 | `[018][P2][test] Покрыть metadata-only activity integration` |
| T055 | #943 | `[018][P2][test] Расширить no-secret audit tests` |
| T056 | #944 | `[018][P2][deletion] Смаппить lifecycle activity response` |
| T057 | #945 | `[018][P2][lifecycle] Добавить lifecycle events в cabinet activity` |
| T058 | #946 | `[018][P2][web] Показать metadata-only lifecycle activity` |
| T059 | #947 | `[018][P2][deletion] Добавить safe retry guidance` |
| T060 | #948 | `[018][P2][docs] Обновить current product status` |
| T061 | #949 | `[018][P2][docs] Добавить changelog entry для 018` |
| T062 | #950 | `[018][P2][evidence] Создать evidence index для 018` |
| T063 | #951 | `[018][P2][evidence] Записать quickstart validation` |
| T064 | #952 | `[018][P2][evidence] Записать browser screenshot validation` |
| T065 | #953 | `[018][P1][evidence] Записать ci-local результат` |
| T066 | #954 | `[018][P1][evidence] Проверить evidence на private content` |

## Required Labels

Every created issue includes:

- `feature:018`
- one `priority:P0`/`priority:P1`/`priority:P2`
- one `area:*`
- one `gate:*`
- one `type:*`
