# Validation summary

Дата: 2026-07-27

Risk / validation lane: high-risk test-infrastructure and artifact-egress change.
Production deploy
не выполнялся.

## Aggregate results

| Lane | Result | Evidence |
|---|---|---|
| Fast | pass | 554 passed, 691 deselected, 4.78 s |
| Owner audio focused | pass | 33 passed, 54.77 s |
| Governance | pass | 210 passed, 1 035 deselected, 9.34 s |
| Full ordinary | pass | 1 031 passed, 81.89 s; 8 xdist workers |
| Full governance | pass | 210 passed, 7.76 s; 8 xdist workers |
| Full strict RLS | pass | 4 passed, 0.73 s; serial phase |

Full baseline и phase union совпали: 1 245 tests, collection digest
`e91a9c89e132a84d116c85f59564fdf479c833c4c7737b4254a2fc913515bc41`.
Runner подтвердил удаление disposable PostgreSQL container после каждой фазы.

## Additional checks

- `ruff check .` — pass.
- Python compile check — pass.
- `uv lock --check` — pass.
- `docker compose config` — pass.
- deployment evidence scan — pass.
- RLS hardening boundary — ожидаемо сообщает `blocked` в `postgres_test`, потому
  что production database не передавалась и live probe не запускался.
Единственное предупреждение — существующее предупреждение Starlette о будущем
переходе с текущего httpx TestClient; оно не связано с этим diff.
