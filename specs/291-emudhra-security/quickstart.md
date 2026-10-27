# Validation F291

1. From `apps/server`: `uv lock --upgrade-package certifi`; `uv lock --check`; `uv export --no-dev --extra evaluation --no-emit-project --format requirements-txt --no-hashes -o constraints.txt`. Repeat export to temporary file and compare bytes. Review lock diff: only certifi changes. Record `uv tree --outdated` separately.
2. Run `python3 -m pytest tests/governance/test_governance_workflow.py` from root using prepared project environment. Check every modified Node 22 pin >=22.23.4. Build both server Docker runtime targets through existing CI; inspect installed certifi/system CA versions.
3. Open draft PR. Before merge require `python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr NUMBER` PASS at exact final SHA, independent checklist PASS and convergence.
4. Use `docs/agent-guidance/release-and-validation.md`: latest published stable, fresh release prep, immutable train/candidate, one exact authoritative release-full, decision, dry-run. Do not reuse draft .22.2 as published evidence. No execute without all mandatory backup/restore evidence and applicable permission.
5. After guarded production rollout inspect API, processing-worker, media-worker and maintenance image/source/package versions and state. Use each applicable application HTTP client against `https://dv-g3b-emudhra.we-have-a-problem.com/` and `https://dv-g3b-aaa-emudhra.we-have-a-problem.com/`; both must fail specifically with certificate verification failure. Test `https://pypi.org/` as ordinary HTTPS control. Per-request timeout 15 seconds, no redirects and no secrets. DNS/timeouts are inconclusive. Check default system SSL paths separately for non-certifi consumers.
6. Existing CD health/smoke and repeated Temporal/worker readiness must pass. Keep money, third-party SMTP, analytics, routes, data, mounts and settings unchanged; report limits and rollback outcome. New macOS publication is excluded; preserve existing assets/appcast.

## Сверка выпущенного сервера — 28.10.2026

См. [validation-runtime-20261028.md](validation-runtime-20261028.md): проверены
точные PR/Full/tag/decision/publication, исходная неудачная попытка CD и
последующий успех, фактические версии и здоровье четырёх служб. Внешний HTTPS
изолированного media-worker неприменим к текущей конфигурации; исходные
неопределённые пробы и `all_pass=false` сохранены, 9 проверок образа не выданы
за live TLS. Применимость пересматривается при изменении сети/клиентов.
T007/T008 и #7734 остаются открытыми до принятого подтверждения разрешения
резервирования, восстановления и итогового live closeout. Новые release,
backup/restore, сетевые изменения или запуск Dev в этой сверке не выполнялись.
