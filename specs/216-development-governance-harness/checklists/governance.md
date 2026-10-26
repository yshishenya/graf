# Governance Review Checklist: Feature 216

**Purpose**: Reviewer-owned итоговая приёмка уже реализованного процесса, Dev
harness, CI и reusable package F216. Этот список не является разрешением начать
реализацию и не подменяет проверку качества требований в `requirements.md`.
**Feature**: [spec.md](../spec.md)

## Feature identity and context

- [x] Feature ID 216 не пересекается с локальными/remote refs, issues и PR
- [x] Umbrella issue #6090 связан со всеми task-backed issues
- [x] `.specify/feature.json` — единственный active pointer; mtime fallback отсутствует
- [x] Root `AGENTS.md` остаётся стабильным и не содержит текущий task

## Parallel agents and repository hygiene

- [ ] Один agent/worktree имеет одного owner и один branch
- [x] Changelog fragment namespace уникален; общий `CHANGELOG.md` меняется только release operator
- [x] Auto-commit hooks не создают неожиданные implementation commits
- [ ] Evidence metadata-only и не содержит secrets/private content

## Dev harness and macOS app

- [x] Build/promote/rollback/reset-data имеют dry-run; читающие status/smoke не требуют отдельного dry-run; все операции имеют fail-closed поведение
- [x] Active manifest единственный и SHA-consistent для backend/frontend/app
- [x] Promote lock и атомарная активация доказаны конкурентным тестом
- [x] `/Applications/GRAF Dev.app` сохраняет bundle ID, signing identity, designated requirement и permissions
- [x] Dev reset не может затронуть production

## CI and release

- [x] Stale SHA не считается evidence
- [x] Frozen candidate допускает один authoritative Full CI
- [x] Fast/full границы и cancellation описаны в PR/release templates
- [x] CalVer/tag/GitHub Release/Russian notes связаны с exact SHA
- [ ] Rollback и skipped gates имеют metadata-only evidence

## Legacy and extraction

- [x] Legacy Impact обязателен в spec и PR
- [x] Исключения имеют owner, expiry, trigger и retirement task
- [x] Existing legacy cleanup вынесен в отдельную Feature 217+ без опасного массового удаления
- [x] Generic harness отделён от GRAF-specific product gates
- [ ] Публикация reusable repo блокируется при secret/path/provenance нарушении

## Reviewer decision

- [ ] PASS — итоговая приёмка F216 подтверждена всеми предметными пунктами
- [ ] ACCEPT WITH RECORDED RISK — риск и владелец явно записаны
- [x] BLOCK — итоговое закрытие F216 заблокировано неподтверждёнными предметными пунктами

## Независимое повторное ревью 26.10.2026

Сохранены все 23 предметных критерия. Отметки подтверждают только указанную
в [отчёте reviewer](../checklist-review-20261026.md) область доказательства:
исходники, принятые требования или фактические результаты. Наличие теста не
объявлено его прохождением; изолированный тест не объявлен приёмкой стенда.

Повторно прочитана принятая историческая приёмка F229/F249: общий
manifest/SHA приложения и стенда, а также сохранение идентичности и разрешений
установленного GRAF Dev подтверждены. Это исторические результаты сентября
2026 года, а не заявление о текущем живом стенде. Реальный откат также
подтверждён, но составной пункт про откат и пропущенные проверки остаётся
открытым до полной записи пропусков.

Не подтверждены соблюдение ownership всеми действующими worktree, полный
набор внешних доказательств, полная запись пропущенных проверок и полный
gate публикации внешнего пакета. Связь опубликованного русского GitHub Release
v2026.09.04.1 с tag и принятым точным SHA дополнительно подтверждена прямыми
сохранёнными ответами GitHub. Подробные причины — в отчёте. Принятые
сценарии не требуется повторять ради отметок.

Предметные пункты: 19 checked / 4 unchecked. Решение: BLOCK; из трёх
альтернатив отмечена только эта. Всего в файле: 20 checked / 6 unchecked.


## Повторная проверка локальных связей задач

После минимального документального исправления G2 дополнительно подтверждён
самим `tasks.md`: каждая из 60 существующих задач имеет единственную
каноническую ссылку, совпадающую с сохранённым владельцем GitHub. Исходные
описания, порядок и 54 [X] / 6 [ ] не изменены. Прочитанные GREEN-журналы
подтверждают только структурную проверку подготовленных комментариев #6132 и
#7748; внешняя приёмка и live-проверка не заявляются. Новых отметок критериев
нет: предметно 19 checked / 4 unchecked, всего 20 checked / 6 unchecked;
G5/G8/G18/G23 и решение BLOCK сохранены.
