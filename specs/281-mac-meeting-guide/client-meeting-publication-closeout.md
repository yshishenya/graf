# Публикация дополнения протокола: T018 / #7635

Проверено 18.10.2026. Lane: docs-only, сверка уже выполненной публикации внутри
F281. Поведение приложения, правила выпуска и исходные критерии не меняются.
Новый выпуск, развёртывание или установщик macOS для этой отметки не нужны.

## Принятый и опубликованный источник

T017/#7634 принята в PR [#7637](https://github.com/yshishenya/graf/pull/7637):
PR SHA `71f44385611f96a43740416a22d96fefe10c999e`, проверенная основа
`c6c5441c930b8c1ecffed6de9b80773aa0e757e5`, merge
`431a7857221c2bad1fe27bf1d5b80fee385670fc`. Текущий общий
`scripts/validate-pr-checks.py` повторно подтвердил обязательный набор:

- governance-fast: PASS, [39011846917](https://github.com/yshishenya/graf/actions/runs/39011846917), attempt 2;
- macos-pr: PASS, [39011846882](https://github.com/yshishenya/graf/actions/runs/39011846882), attempt 2;
- pr-metadata: PASS, [39011846945](https://github.com/yshishenya/graf/actions/runs/39011846945), attempt 1.

Merge является предком опубликованного source
`f9ed447e878581f7ec49003d5ab10864426071db`.
Общий выпуск F280/F289 `v2026.10.16.6` завершён раньше; новый выпуск
[v2026.10.17.1](https://github.com/yshishenya/graf/releases/tag/v2026.10.17.1)
явно включает дополнение руководства. Подготовка — PR #7650.

## Доказательства выпуска

- Candidate: `rc-20261017T091007Z-8b77e6c0cda8`;
  train: `train-20261017T090846Z-f9ed447e8785`, включает #7637/F281.
- release-full: PASS, [39020099599](https://github.com/yshishenya/graf/actions/runs/39020099599),
  workflow `release-full`, event `workflow_dispatch`, тот же source SHA.
  Локальная authoritative запись побайтно совпала со свежим файлом из GitHub;
  `authoritative_full=true`, `skipped_gates=[]`, все компоненты имеют тот же SHA.
- Штатные валидаторы candidate, decision, train и CI evidence — PASS.
  Проверены неизменяемые контрольные записи, digest authoritative evidence,
  digest решения в publication attestation и CHANGELOG именно выпущенного SHA.
- Неизменяемая публикация: `pa-rc-20261017T091007Z-8b77e6c0cda8`,
  `2026-10-17T09:26:30Z`. Штатная проверка GitHub подтвердила стабильный Release,
  его описание и разрешение тега в тот же source SHA.
- Сохранённый CD dry-run: `candidate_gates=passed`, `release_candidate=go`,
  `local_ci=authoritative_full_reused`. Сохранённый execute: `backup_result=pass`,
  `smoke_result=pass`, `deploy_result=pass`, `readiness_verdict=infra_smoke_ready`,
  `deployed_sha=runtime_sha=f9ed447e878581f7ec49003d5ab10864426071db`.
  Публичные download/update и финальные проверки фоновых обработчиков прошли.

Это повторная проверка исходных записей, без нового Full/CD/rollback.
Их контрольные суммы и безопасные метаданные — в
[evidence/client-meeting-publication-20261018.json](evidence/client-meeting-publication-20261018.json).

## Фактическая публикация и защищённые страницы

GET [статьи](https://rec.2brain.pro/guides/protokol-vstrechi-iz-zapisi) с
`GRAF-SEOBot` вернул HTTP200. Раздел `client-meeting` с копируемым шаблоном
письма побайтно равен разделу шаблона в выпущенном source; SHA-256
`3e139d998e7aa4538ddf608465a7f2cdaf0a4bb99be624c7b6d83f11c2eb8d93`.
На странице один H1, правильный canonical, все внутренние якоря существуют.
Все восемь связанных публичных страниц вернули 200 и свои canonical, включая
главную, download, privacy и analytics-consent. Сравнение полного HTML между
разными моментами не используется как неизменяемая идентичность страницы.

В продуктовой части PR #7637 изменён только
`public/templates/public/meeting_protocol_guide.html`; другие изменения —
фрагмент выпуска и документы F281. Главная, download, политики, CSS/JS,
маршруты, sitemap и обработка данных этим срезом не менялись.
Ранее принятые локальные проверки 360/390/768 px относятся к T017 и её точному
источнику; повторная установка или проверка приложения здесь не заявляется.

## Сверка приёмки и границы

| Критерий #7635 | Доказательство |
|---|---|
| T017 принята после общего F280/F289 | #7637, закрытая #7634, опубликованные v2026.10.16.6 и v2026.10.17.1 |
| Одна версия Full/CD/publication | Exact source f9ed447e878581f7ec49003d5ab10864426071db, candidate, train, decision, attestation и CD выше |
| Новое содержание, canonical, ссылки и защищённые страницы | Побайтовое сравнение раздела, public GET, восемь ссылок, protected source diff |

Технические условия T018 выполнены. Закрытие GitHub issue #7635 выполняется
только после принятия этой сверки и live `validate-issue-closeout.py` с точными
PR SHA, Candidate SHA и обоими наборами run URL. До этого статус —
`publication verified; tracker pending`.

Общая F281/#7391, исторические T011/T013, индексация, рост трафика и продажи не
закрываются. Маркеры CD `required_post_deploy` для retry/backfill/range/cleanup
не выдаются за выполненную приёмку F290. Финансовая F278 и совместимость
установленного приложения имеют отдельные условия. Новые события аналитики,
платежи, возвраты, письма и действия с записями людей не выполнялись.
