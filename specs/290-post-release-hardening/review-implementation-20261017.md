# F290: независимое итоговое ревью CI-среза

Дата: 2026-10-17. Reviewer: `review_f290_infra`.
Ветка `290-post-release-hardening`; base
`c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Режим: **high-risk-product**. Implementation пока без commit.
Область: T002–T004, 11 изменённых tracked файлов и `changes/unreleased/F290.yaml`.

## Результат

**PASS. Замечаний P0/P1/P2/P3 к проверенному diff нет.**
Повторно независимо выполнены **275 проверок без пропусков**: governance и
metadata 172 PASS/51.30s, CI/CD contracts 103 PASS/15.08s.
Оба workflow validator и их self-test, actionlint и `git diff --check` — PASS.
T004 этим получает независимое ревью, но разрешение пользователя на
implementation commit/draft остаётся отдельным условием.

Прочитаны текущие diff, F290.yaml, validation.md, task ownership и pointer.
T001–T003 локально отмечены; T004/T005 и US2/US3 остаются открыты.
У pointer корректный enum high-risk-product, пути согласованы с diff; в задачах
13 явных Issue links, а F290.yaml использует штатную схему.

## Проверка правильности и безопасности

1. Независимое чтение GitHub API для всех шести stable tags подтвердило,
   что каждый tag разрешается в указанную full40hex commit identity и
   `action.yml` на этом commit объявляет **node24**. Это не blob SHA.
   checkout7.0.1, cache6.1.0, setup-node7.1.0, setup-python7.0.0,
   upload-artifact7.0.2 и download-artifact8.0.2 совпали с research и YAML.
2. Сравнены разобранные YAML всех шести workflow с HEAD. После исключения
   только заявленных Actions pins, нового native selector, cache namespace,
   archive:true и package-manager-cache:false остальные структуры **совпадают**.
   Сохранены events, conditions, permissions, concurrency, timeouts, env,
   required names, точные checkout refs, сроки/имена/пути receipts и все
   реальные команды build/XCTest/ContractValidation и authoritative checks.
3. Metadata продолжает checkout `github.workflow_sha`, не PR head, и
   выполняет `python3 -I`; credentials не сохраняются. Новый checkout7
   запрет untrusted fork checkout здесь не обходится и не затрагивает
   используемый trusted ref. Граница доверия не расширена.
4. В setup-node новый automatic package-manager cache явно выключен,
   версия Node приложения по-прежнему 22.22.3. Upload явно сохраняет
   `archive:true` и имена; download manifest подтверждает defaults
   `skip-decompress:false` и `digest-mismatch:error`, YAML их не ослабляет.
5. Три native selector побайтно совпали; SHA256 run body:
   `c10d80f1c7b73a16ca65e0c777b50e9e4ed05f8a2845803878f18d7624ade365`.
   Проверяются исполнимость обеих binary, exit status каждой команды,
   строгая semantic version6.0.3, разрешённые executable paths, непустые
   и неизменные SDK/developer значения. set-e не скрывает ошибку assignment.
   Запись GITHUB_PATH происходит последней; принудительных fallback нет.
6. Выполнены настоящие YAML Bash steps в изолированном harness для каждой
   из трёх workflow: success, missing swift/swiftc, wrong version,6.0.31,
   nonzero с valid stdout, xcrun error, SDK drift и developer drift.
   Каждый отказ сохранил исходное содержимое GITHUB_PATH.
   Эти binary являются локальными stubs и **не доказывают Apple Swift build**.
7. Key и restore-prefix обоих Swift caches получили xcode16.2 namespace;
   ни точный cache key, ни prefix не принимают старый Swift.org namespace.
   Cache hit не заменяет build/tests. У diagnostic кэша до изменения не было.
8. Каждый изменённый validator проверяет все вхождения своих Actions,
   поэтому один v4/v99/нулевой pin не принимается при остальных верных.
   Все шесть соответствующих mutation regression прошли в наборе172.
   Не добавлены wildcard pins или ослабляющие workflow условия.
9. Legacy Impact remove соответствует удалению Node20 setup-swift без
   новых aliases, opt-out flags, зависимостей или резервного compiler path.
   В fragment честно выделены смена compiler build, незавершённый hosted
   этап, macos14 retirement и отдельные US2/US3.

## Независимые команды

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/governance/test_governance_workflow.py tests/governance/test_pr_metadata_event.py -q
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider --confcutdir=apps/server/tests/contract apps/server/tests/contract/test_ci_cd_contract.py -q
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate-governance-workflow.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate-governance-workflow.py --self-test
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate-full-ci-workflow.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate-full-ci-workflow.py --self-test
actionlint .github/workflows/*.yml
git diff --check
```

Дополнительно stdlib/PyYAML проверкой только чтением выполнено сравнение
разобранных workflow, равенство трёх run bodies и six tag→commit→runtime
проверка через `gh api`. Ни runner, ни GitHub state этим не изменялись.

## Привязка к проверенному содержимому

SHA256 файлов после независимых тестов:

| Путь | SHA256 |
|---|---|
| .github/workflows/backup-restore-rehearsal.yml | d7700b914ab4c6b62b892f77f3469058aff41134a0773d8c31e1cc0af22db44b |
| .github/workflows/governance-fast.yml | b5261aaaf4b375a8eac6e36c16c7a523a969f107d81c58c3e23a1e402d381442 |
| .github/workflows/macos-diagnostic.yml | 03e36534be234812750a4b7a5e72cc8becb664a50335d1e9d265cce791f0ac80 |
| .github/workflows/macos-pr.yml | 5aa2a59ec9d8e5036305e271818ebd0dbb70a587d2c56900f3b6060af228d942 |
| .github/workflows/pr-metadata.yml | 6de748b16a52a0a50a6d2d97467e2f3d186d71862649713be1e38f849c7ea119 |
| .github/workflows/release-full.yml | ca3c546ff5e6237bc9a9cebaeb2c69c07dab240111e62032e5f64c459c4ccff9 |
| apps/server/tests/contract/test_ci_cd_contract.py | c7db85d3e557615ab51cb0cd84836fbcab0d00cbd1371a46e20885aa5d980c18 |
| scripts/validate-full-ci-workflow.py | bbda28fe4d607b29c9a524f5add32407605de346917705deeb14eb9300be90f5 |
| scripts/validate-governance-workflow.py | d67d7f8f8a421aecb567a5a98cb948e526db91fff8b06aeac2aa06cfa67e8e6f |
| tests/governance/test_governance_workflow.py | 6a11fdc5c586681851dd85588c164d2ea50fc32010858835ba4fe3f36643a30e |
| tests/governance/test_pr_metadata_event.py | 7df119a6880e89eb72866e09409de51002aee5e68f9dbb378c0c4006b61a10c1 |
| changes/unreleased/F290.yaml | 7149ab8a7c4a5af1e2ad780ab1f7fa6cc7869efa05caf958eebfffefb94ce13e |

## Границы

Ревью даёт локальный PASS текущему CI diff. Настоящий Apple compiler и
совместимость с прежним SDK обязаны пройти hosted build/XCTest/ContractValidation
в T005 после разрешённого commit; local stubs их не заменяют. Macos14 retirement
2026-11-02 остаётся ограничением с отдельной миграцией image. Выпуск требует
своего нового frozen Full; старый Full не запускался.

US2/US3, stash, сервер, production, установленный GRAF Dev, merge и release
в этом review не проверялись и не изменялись. Требования infra checklist
не переоценивались, его 13/0 остаются requirements-quality результатом.
Исправлено только нормализованное название lane в собственном предыдущем
отчёте и добавлен этот независимый отчёт; код и чужие документы не менялись.
