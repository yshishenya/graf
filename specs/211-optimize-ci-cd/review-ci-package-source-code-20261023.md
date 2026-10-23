# Независимое code review F211 T099

Дата: 2026-10-23. Ветка `codex/211-ci-package-source`, исходный HEAD
`d6243efb782d889e3b9b10da0b750c7a90f0707f`; повторно проверены текущие
незакоммиченные изменения после первого Request Changes.
Lane реализации: active Spec Kit slice, shared CI/infrastructure.
Применён skill `code-reviewer`.

**Итог повторного review: PASS / Approved. Открытых замечаний0.**
Checklist требований перечитан и подтверждён: **7 checked / 0 open**.
Этот итог относится к локальному коду и требованиям; T100 hosted приёмка
остаётся открытой, issue #7738 закрывать по нему нельзя.

## Прежние замечания и проверенное исправление

**F1 / P2 — устранён.** Первая версия проверяла наличие одной строки URIs
и принимала неизвестный дополнительный источник/продолжение/disabled source.
Теперь `infra/scripts/prepare-ci-apt.sh:17–34` разбирает каждый раздел
известного плоского deb822 формата. Строки-продолжения и строки без поля
отклоняются; ключи учитываются без регистра, повторный ключ вызывает отказ.
Каждый непустой раздел должен иметь ровно ожидаемый URI и Enabled=yes либо
не иметь Enabled. Неизвестный URI, несколько URI в значении, disabled section
не проходят. Несколько отдельных корректных разделов разрешены. Все эти
проверки выполняются до чтения/изменения mirror-list.

`test_actual_media_resource_preparation` дополнен четырьмя отрицательными
случаями `second-source`, `continued-source`, `disabled-source`,
`duplicate-source` для каждого из трёх настоящих YAML caller. Проверяются
ненулевой итог, только событие mirror, отсутствие npm/Playwright/установок,
побайтная сохранность source/mirror/чужого репозитория. Положительный
`multiple-stanzas` добавляет отдельный security stanza с тем же ожидаемым URI,
проходит обычную приёмку и повторный no-op. Рецензент перечитал сами ветви
fixture и assertions, не только список названий.

**F2 / P3 — устранён.** `plan.md:533–540` теперь описывает существующий
системный Python/stdlib под sudo, плоские deb822 поля, проверку каждого раздела,
отказ при продолжении/дубликате/disabled и допустимый multi-stanza. Это
соответствует коду, стандартная библиотека не требует установки зависимости.
Уточнение не ослабляет исходный strict-format договор. Изменения качества
требований затрагивают CHK002/005/006; они перечитаны и остаются подтверждены.

## Локальные доказательства, прочитанные рецензентом

- `.dev/ci-package-source/deb822-before.log`: **12 failed /130 deselected,
  3.89s**. Прочитаны начало, соответствующие assertion failures и итог:
  старая проверка возвращала0 в случаях, где требовался отказ. Это4 новых
  отрицательных состояния ×3 caller, а не продуктовый успех.
- `.dev/ci-package-source/deb822-after.log`: **142 passed /38.08s**.
  В текущей параметризации25 resource состояний ×3 caller =75; остаются67
  прежних проверок файла. Успешный итог увиден в завершённом журнале.
- SHA-256 before log:
  `89b269af1768d5d2228fe75c29110d7147a1348025248acc7b751434fdd78f06`.
  SHA-256 after log:
  `c642bf78806bf51eb7aa53c13567aa771455f088001c8ce6387317ae90cba4f7`.

Это журналы прогонов основного исполнителя, просмотренные независимо;
рецензент сам команды тестов не запускал. Они подтверждают локальные
синтетические APT/command пробы, не реальную загрузку пакетов или скорость
GitHub. Криптографическая APT-проверка в этих пробах не выполнялась: здесь
проверяются сохранность конфигурации доверия и распространение отказов.

## Остальные проверенные свойства

- Diff YAML по-прежнему добавляет ровно3 source вызова: governance-fast:255,
  release-full:298 и447. Они стоят перед условной ffmpeg установкой и перед
  Playwright APT; исправные ffmpeg/ffprobe не исключают подготовку зеркала.
- Governance caller остаётся внутри server-ветви и вне text-only. Имена
  required checks, scopes/events, permissions, timeout, concurrency, exact
  SHA/base и evidence не изменены.
- GitHub Linux guard, запрет symlink/не обычных source/mirror файлов,
  побайтный strict3-or2 mirror-list и сохранение priorities/LF соблюдаются.
  Уже исправленный mirror не переписывается, запись проверяется чтением.
  Source metadata/keyrings и чужие репозитории не изменяются; проверки
  подписей, пакеты и прежние команды установки сохранены.
- Sourced helper использует set -euo pipefail; ошибка его подготовки и
  update/install/media/npm/Playwright не превращается в PASS. Bash и
  системный Python3 доступны в предусмотренном Ubuntu runner; ни нового
  интерпретатора, ни внешней зависимости не требуется.
- Harness исполняет настоящие три YAML блока и копию helper с заменой только
  `/etc/apt` на временный корень; реальные sudo/APT/npm/Playwright не вызываются.
  Проверены no-op, порядок, ошибки, byte preservation, исправные/отсутствующие
  media и non-server. Text-only guard сохранён в YAML.
- T099 и T100 привязаны к #7738. Changelog сохраняет локальную/hosted границу
  и остаток общей F211/F263. Валидация exact PR checks, merge и T100 нужна далее.

## Границы и оставшиеся действия

Рецензент изменил только этот отчёт и свой checklist. Код/spec/plan/tasks,
Git/GitHub, приложение и данные не менялись; сеть, тесты и установки не
выполнялись. В больших исторических F211 документах прочитаны изменённые
секции и применимые T089; не заявляется повторное чтение всей истории фичи.
Проверенные ниже11 файлов включают собственный первоначальный requirements
отчёт: это исторический снимок, актуальное уточнение и хеши находятся здесь.

На момент чтения `validation-ci-package-source-20261023.md` ещё содержал
старые127-case/29-line значения и хеш предыдущей реализации. Его обновление
принадлежит основному исполнителю: перед commit нужно записать142 PASS,
закрытие F1/F2 и новые хеши, выполнить convergence/актуальные scoped static
checks. Старый локальный результат нельзя выдавать за проверку нового кода.
Это открытое оформление доказательств, а не оставшийся дефект реализации.

Затем обязательны3 exact-SHA/base PR checks и общий validator. После merge
T100 требует настоящий server-change CI на новой основе с endpoint/временем
и всем успешным набором. Full остаётся frozen-release gate; production,
выпуск и установленное приложение этим review не подтверждаются.

## Контрольные суммы11 проверенных файлов

| Файл | SHA-256 |
|---|---|
| `infra/scripts/prepare-ci-apt.sh` | `acb7a1a0b114d0446e893bf8961e0992d04c65078a7184ef3ac8072eba82d25f` |
| `.github/workflows/governance-fast.yml` | `18d429b8ff8cc9210cec2097c675396dca1a70dacf9d06df5cb17967572eec0b` |
| `.github/workflows/release-full.yml` | `22a9ba6d7c1e5db47359fcb2e3097b1078c7fb99d903d71205d0cc069a935987` |
| `tests/governance/test_governance_workflow.py` | `00ef8bb79c4305b384690e0c8cfb38a67d6b2ab91a43699f31a77f2b4f98b95f` |
| `specs/211-optimize-ci-cd/spec.md` | `a7624896ef6212f426ecd171707d742092ea14932f98f7988fc9847eccc81009` |
| `specs/211-optimize-ci-cd/plan.md` | `a4b36c0edbef3b9972177996a8ef1b6f5952e6c36860a6dd6a8cab984c0ba9a6` |
| `specs/211-optimize-ci-cd/tasks.md` | `49dd3b258563e99bfe65b85ce496daa7f165efe481770eed8856a3fd657c8deb` |
| `specs/211-optimize-ci-cd/quickstart.md` | `6f0e6dd4cfeda39f64954a3b6bdfb3546a90257dc7afed948b421097d2671dc1` |
| `specs/211-optimize-ci-cd/checklists/ci-package-source.md` | `26408d167f3a20caa3a53a83eba55d54f0f15c4a9592f4bc3da63503762969c2` |
| `specs/211-optimize-ci-cd/review-ci-package-source-requirements-20261023.md` | `8ed5a9c9d9e887642aca5cdeb4b173a5dceaf698a79e885c7c7d6093ad9480fb` |
| `changes/unreleased/F211.yaml` | `d5327243334e11da35ea34651b8d86629738aeaa2dec575a30b03012e32e2a48` |
