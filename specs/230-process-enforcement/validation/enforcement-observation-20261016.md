# F230: независимое наблюдение GitHub (GET-only)

Источник: независимое исследование f230_enforcement_research, 2026-10-16 около
20:29 UTC; никаких файлов, запусков или GitHub settings исследователь не менял.
Это реальное чтение состояния, не полный rehearsal и не разрешение cutover.

## Master и защиты

- `GET /repos/yshishenya/graf/commits/master`: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
- `GET /repos/yshishenya/graf/branches/master/protection`: strict=true;
  contexts governance-fast/pr-metadata/macos-pr, app_id15368; linear=true;
  conversations=true; approvals0; dismiss_stale=true; admins=false;
  force push/delete запрещены.
- `GET /repos/yshishenya/graf/rulesets?includes_parents=true`: [].
- `GET /repos/yshishenya/graf/rules/branches/master`: [].
- `GET /repos/yshishenya/graf/actions/runs?event=merge_group&per_page=5`: total_count=0.

Правила очереди слияния не обнаружены; это не доказывает невозможность её настройки.
В текущем master governance-fast обрабатывает merge_group, macos-pr — только PR,
pr-metadata — pull_request_target. Полная готовность трёх обязательных checks к
merge queue не доказана; автоматически включать её нельзя.

## Реальный PR source-run

PR #7639, head `121d98d002c64c3faa9afbbd172b716711f0eb46`, checked base
`f4b38141af2fad64bae219e8c012b0a54f237491`, merge 2026-10-16T17:35:33Z.

| Run / attempt1 | Событие | Conclusion | Предел |
|---|---|---|---|
| [38939201760](https://github.com/yshishenya/graf/actions/runs/38939201760) | governance-fast / pull_request | success | реальный bounded fast, partial coverage |
| [38939268951](https://github.com/yshishenya/graf/actions/runs/38939268951) | governance-fast / pull_request | success | повторное использование; bounded fast skipped |
| [38939268691](https://github.com/yshishenya/graf/actions/runs/38939268691) | macos-pr / pull_request | success | native context данного PR |
| [38939269673](https://github.com/yshishenya/graf/actions/runs/38939269673) | pr-metadata / pull_request_target | success | metadata данного PR |
| [38939200257](https://github.com/yshishenya/graf/actions/runs/38939200257) | pr-metadata / pull_request_target | failure | причина по logs не исследована; не объявляется negative test F230 |

Исследователь прочитал в памяти artifact12062258844 через run/jobs/artifacts API
и `/actions/artifacts/12062258844/zip`. Artifact unexpired. Receipt:
requested=target=observed_start=observed_end=`121d98d002c64c3faa9afbbd172b716711f0eb46`;
base=`f4b38141af2fad64bae219e8c012b0a54f237491`; PR[7639]; event pull_request;
merge_group_id=null; passed; final_cleanliness=pass; cancellation/supersession=none.
Local lane fast, coverage partial, components infra/docs, skipped_gates[].
Время реального bounded fast 17:24:10–17:34:07Z.

## Ручной запуск и отсутствие merge_group

Последний governance workflow_dispatch: [34287616840](https://github.com/yshishenya/graf/actions/runs/34287616840),
head `f5cf0785dc79aefa6bcbb57bd6db11d6f55ab171`, success, 2026-09-08.
Jobs показывают execution/receipt success, но artifacts=[]: исторический факт
запуска подтверждён, точный receipt/current workflow rehearsal — нет.

Release-full [38933940635](https://github.com/yshishenya/graf/actions/runs/38933940635)
на `834bdc87e3c83ebd86e1afd2c6e7760229b7297d` success; это другой workflow/SHA,
он не заменяет governance PR/manual/merge_group.

## Остаток

T013/#6327 открыта: нет реального merge_group rehearsal, свежего manual receipt и
полного before/after/operator acceptance. Контракт rollback описан в contracts,
но не исполнен; защита не менялась. Перед применением нужны отдельное решение,
совместимость всех required contexts, новый before snapshot и user approval.
