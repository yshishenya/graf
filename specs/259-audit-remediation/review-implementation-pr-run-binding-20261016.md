# Независимое ревью реализации F259: точная связь PR и CI

Дата: 2026-10-16. Проверяющий: отдельный агент `review_f259_binding`.
Ветка: `codex/259-ci-proof-binding`; основа
`c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Полоса: high-risk-product / significant governance, существующая US3.
Владелец текущего объёма: #7644 / T027–T029.

**PASS локальной реализации; actionable findings 0; CRITICAL 0, HIGH 0.**
Это не разрешение на коммит/слияние, не точный SHA GitHub CI и не закрытие
#7644, #7020, F267 либо общего бэклога F259.

## Проверка реализации

- Прочитан полный diff кода и тестов, все callers verify_feature_runs и
_github_pr_checks, общий validate-pr-checks.py и его набор тестов.
Удалён единственный helper _github_commit_pull_requests и единственные его
caller/cache; поиск по scripts/tests не нашёл оставшихся Python-ссылок.
Новых зависимостей, форматов, флагов или исключений для F267 нет.
- Единственное новое разрешение в проверке запуска: пустой нормализованный
массив run.pull_requests не запускает commit fallback. Полное доказательство
по-прежнему обязательно вызывается ниже для точных PR/head/run. Непустой
массив допускается только при точном [expected_pr_number]; чужой номер,
несколько номеров и явное противоречие продолжают давать ошибку.
- До и после изменения сохранены repository URL, conclusion, workflow name,
event, path, SHA, merged PR и явная связь PR с issue. Внешний общий валидатор
по-прежнему получает --expected-sha и --code-run-id; проверяет base, PR,
run/attempt, артефакты, весь требуемый набор и свежесть попытки/метаданных.
Ошибка subprocess/JSON/артефакта не превращается в успех.
- checked_prs сохраняет ключ (PR, head, governance-run). В кэш попадает
только успешный полный вызов. Две issues с тем же ключом используют один
успех; иной PR/head/run не может использовать этот ключ.
- Feature/live single CLI по-прежнему вызывают один общий verify_feature_runs,
структурный режим без --verify-live остаётся только структурной проверкой.
Release-full сохраняет отдельные candidate/event/path/SHA и не получает
исключения для PR. Код этих режимов не менялся.
- Старый отрицательный сценарий commit_prs.append(9999) заменён ровно по
уточнённому контракту: PASS с проверкой точного полного вызова и запретом
неожиданного subprocess. Остальные прежние assertions сохранены, включая
прямую чужую run-связь, release SHA/path и явную PR→issue связь.
Проверка ошибки полного proof теперь выполняется при пустом run API-массиве
для missing/expired, identity mismatch и stale metadata; добавлена проверка
единственного вызова при двух issues.

## Независимое выполнение

Рецензент самостоятельно выполнил изолированно, без записи в GitHub:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/yshishenya/Documents/crisp/apps/server/.venv/bin/python -m pytest -p no:cacheprovider tests/governance/test_validator_safety.py tests/governance/test_pr_checks.py -q
python3 -B scripts/validate-issue-closeout.py --self-test
```

Результаты: **189 passed in 19.99s, 0 skipped, 0 failed**;
`issue-closeout self-test: OK`.
Общий набор проверяет, в частности, неправильные head/base/run/attempt,
workflow/event/path, missing/expired/duplicate артефакт, более позднюю
неуспешную попытку, политику, изменения PR и состояние обязательных jobs.

Прочитаны внешние журналы исполнителя: исходный целевой RED 1 failed,
последующий GREEN 1 passed, полный набор 189 passed in 20.23s. Живой
исходный #7020/PR7123 отвергался из-за неоднозначного commit fallback;
последующий read-only single/live replay проходит. Общий валидатор для
старого #7059 возвращает `code receipt identity mismatch`, а не успех
по тому же SHA. Сам рецензент этот live replay не повторял; прочитанные
журналы и сообщение исполнителя отделены от его собственного прогона.

Синтетический `_github_pr_checks → {}` проверяет обязательный вызов и
распространение ошибок, **не аутентифицирует реальные артефакты**. Ни один
новый тест не выдаётся за живую приёмку. Подлинность проверяемого примера
подкреплена общим валидатором и отдельными live-журналами; содержательная
приёмка F267 остаётся самостоятельной.

Рецензент изменил только этот отдельный отчёт. Контрольные списки, код,
задачи, spec/plan, Git/GitHub, приложение, Docker и production не менял.
Исполнитель параллельно оформляет validation/tasks/changelog; их итоговое
состояние этим отчётом заранее не принимается.

## Повторное чтение контрольных списков

```json
{
  "numbering.md": {
    "checked": 6,
    "unchecked": 0
  },
  "pr-run-binding.md": {
    "checked": 8,
    "unchecked": 0
  },
  "requirements.md": {
    "checked": 13,
    "unchecked": 0
  },
  "three-digit-numbering.md": {
    "checked": 9,
    "unchecked": 0
  },
  "umbrella-ownership.md": {
    "checked": 7,
    "unchecked": 0
  }
}
```

Всего: **43 отмечено / 0 не отмечено**. Это качество требований; отметки
не подменяют приёмку пользовательских сценариев общего бэклога.

## SHA-256 прочитанных исходников

```json
{
  "scripts/validate-issue-closeout.py": "9bf3aa266b323903fdc1147bce7a472dbfc537a3b20166fbae38a370989c57dd",
  "tests/governance/test_validator_safety.py": "58b1dcc1de06d95f6f9b8b91114120a6d53ef26e06c0a59b53f51f8f0bd9749c",
  "scripts/validate-pr-checks.py": "3dadb1b84cfe45bbf4f06939981042ad2d1a0ff6aeb45928cf9e4a9ce0e3380e",
  "tests/governance/test_pr_checks.py": "e19800ce9b901ba81eaa837da9aaf109b620ab56073e460322d8d7699580f1e6",
  "specs/259-audit-remediation/checklists/pr-run-binding.md": "c530dede5b7aa6590e302b9e6d15df4274c5a44034557ac92f678e551b095a1d",
  "specs/259-audit-remediation/spec.md": "67f657a2a4e61640c64a9f597bf77d84ab4c623f1d72b56fa3a821c651cf08c6",
  "specs/259-audit-remediation/plan.md": "a47596213a67a9117149be041eae737d251a044c2364261536a28578243c26d8",
  "specs/259-audit-remediation/quickstart.md": "fd31832270ca3062d26aad50b02e8b96cbaa53a7de34bf428d1bab7029a9e5cb"
}
```

## SHA-256 прочитанных внешних журналов

Каталог: `/Users/yshishenya/Documents/Codex/2026-10-16/graf-issue-by-issue/checks`.

```json
{
  "F259-pr-binding-red.log": "f15a5b8efd8560bf80ac88f266282c3df3508b8c2b112052cfd4907cf928df14",
  "F259-pr-binding-green.log": "a07e89e11cd9c3f5d0db4397434b840807ef52c12d3d4e5267efa97269c2246d",
  "F259-pr-binding-live-before.log": "dc883d976ee3630b03e0ee7aad81a4c15f3f88bd06b50a9dbff4e65507ddfa4a",
  "F259-pr-binding-live-after.log": "6b7968a87faa0941446e7d2df5ecb356a327ce8c62fe06f6ec143d7d8862bdaa",
  "F259-pr-binding-wrong-pr-after.err": "4c7fbdf812af5f5eea7542eca66ec86a1c3cdcb7679246c2080d16f156ba100a",
  "F259-pr-binding-full-tests.log": "7daabe1ee4bf36296d6730a836e2b311b6e35b08e9c61963e5e8ceec9af4cf69"
}
```
