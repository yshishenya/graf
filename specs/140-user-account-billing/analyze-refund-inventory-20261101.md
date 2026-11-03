# Scoped analyze F140/T077 O11 — 01.11.2026

Полоса high-risk-product/active Spec Kit slice, owner repository-audit.
Анализ только нового R1–R6, не повторная приёмка общего F140.
Пререквизиты: штатный --json --require-tasks --include-tasks, spec существует.
Hooks before/after_analyze отключены; обязательного commit нет.

| Требование | Задача | План/проверка |
| --- | --- | --- |
| R1 источник/inventory/строки | T077/#4932 | Technical Context refund, реальные частичные строки |
| R2 совместная пара/unknown/NULL/sort | T077/#4932 | CASE status/source, unit SQL и PG |
| R3 partial/null/reason/ноль/error | T077/#4932 | пустой PG и безопасная schema failure |
| R4 observed_at не provider time | T077/#4932 | разные дни/окружения/NULL/future, без чтения времени |
| R5 один SQL/приватность/no-write | T077/#4932 | SQL projection/fingerprint/guard/READONLYRR |
| R6 порядок/реальные доказательства | T077/#4932 | RED/PG/CLI/review/converge/exact gates |

6 требований,1 исходная задача,100% покрытие; новых ambiguity/duplication/
CRITICAL/HIGH/MEDIUM/LOW=0. Не связанных новых задач0. Конституционные
I–VII сохранены: нет capture/деньги/права/egress/deletion mutations;
metadata-only и обязательный процесс/независимый допуск.
Полный O6/FR089 остаётся HIGH partial в исходной T077; все87полных task
lines,58старых checklist gaps, сроки/внешняя приёмка сохранены. Не выдавать
этот scoped PASS за полную F140 или O8: исторический пропуск PR7884 остаётся.
Далее после проверяемого reviewer PASS10/0 — issue sync и implement.

## Входы анализа

- `spec.md` SHA256 `cadfdaf843487512a774f79eef89e2e3b3c2290904e44045fc9041e832f75818`
- `plan.md` SHA256 `f711fe18badb22d0f73553e22921222eabc49323b2710ee39c6d5b6d40b93fd1`
- `tasks.md` SHA256 `aa7b983a096370377d2b2d036acf5338b4bf49e106480080444e10c9f8466911`
- `quickstart.md` SHA256 `704e31e671bbff92546bf34708012ce9363bc18f2a7f7193f8fcca66f194d6a7`
- `research.md` SHA256 `f13dc79b559299a4a8d3dc1b88c09a72ce651861e5e63bdbb6dab4bd88c55521`
- `data-model.md` SHA256 `41c0c0341a5199cefd1027aff0586b0fe829a92b075191403490374313ae577d`
- `contracts/operator-observation.md` SHA256 `1e950b5f60a6b13cdf9eb25994a55118d6f4400b001b7c96651fb1d25f94540f`
