# Задачи F281

Umbrella issue: #7391

## Редакционное дополнение 2026-10-16

- [X] T017 Дополнить `public/templates/public/meeting_protocol_guide.html` разделом о встрече с клиентом и шаблоном письма по FR029–30; проверить по quickstart, открыть отдельный PR и получить exact-SHA checks. Выпуск не входит. (Issue #7634)
- [X] T018 После завершения общего выпуска F280/F289 опубликовать редакционное дополнение штатным процессом и проверить live содержание, canonical, ссылки и защищенные страницы по FR031. До реального выпуска оставить открытой. (Issue #7635)

T017 → T018. Предыдущие исторические задачи и их статусы не пересматриваются этим срезом.

T017 принята в PR #7637 на source `71f44385611f96a43740416a22d96fefe10c999e`,
merge `431a7857221c2bad1fe27bf1d5b80fee385670fc`; #7634 закрыта после live closeout.
T018 подтверждена в опубликованном серверном выпуске `v2026.10.17.1`, source
`f9ed447e878581f7ec49003d5ab10864426071db`: authoritative Full39020099599,
decision/publication/CD и фактическое содержание проверены 18.10.2026.
[Итог и границы проверки](client-meeting-publication-closeout.md).
Issue #7635 закрывается только после принятия этой документальной сверки и
штатного live closeout; общая F281 и исторические T011/T013 остаются отдельно.

- [x] T001 Подготовить отдельное руководство, маршрут и sitemap; сверить утверждения и protected diff.
- [x] T002 Проверить HTTP, canonical, ссылки, tracking, mobile 360/390/768 и регрессии public pages.
- [x] T003 Пройти exact-SHA CI и штатный ограниченный выпуск с production read-back.
- [x] T004 Подготовить отдельный учебный guide протокола, маркировку, route/sitemap и копируемый шаблон.
- [x] T005 Проверить metadata/условия/ссылки/copy/mobile, exact-SHA CI и штатную публикацию нового guide.


Предыдущая публикация подтверждена: первый материал `v2026.09.30.2`, второй `v2026.10.01.3`, PR7411/7415, source/runtime/tag216ab38e6eeb112aefa23f8c87cf69bf6f064b08; Full36927435763 SUCCESS и production200/readback PASS.

- [x] T006 Реализовать и проверить `/guides`, типы/реестр публичного контента, взаимные ссылки и единственную footer-ссылку главной; FR006–FR010, (Issue #7419), parent #7391.
- [x] T007 Пройти exact-SHA CI/provenance и штатную публикацию hub с backup, Full/CD и protected production readback; FR010, (Issue #7419), parent #7391.

Hub опубликован в v2026.10.02.2: source/runtime/tag540f322b4de8016d3b920c74fb8a72c3881ad915, Full36941465329 PASS, CD/backup/smoke cleanup/public readback PASS. Доказательства: evidence/guides-hub-publication.json.

- [x] T008 Подготовить третью статью о проверке качества расшифровки, учебные пометки/первоисточники, route/registry/sitemap/related links и прежний L1 surface; FR011–FR015 (Issue #7429).
- [x] T009 Проверить copy/metadata/links/mobile/measurements/protected diff, exact-SHA CI и штатную публикацию с production readback; FR011–FR015 (Issue #7429).

Третья статья опубликована v2026.10.02.3, source721b5125d, Full36949473232 PASS, CD/backup/readback PASS.
- [x] T010 Реализовать и проверить общую шапку и ссылку главной, current/mobile/keyboard/no-JS/unchanged body; FR016–18 (Issue #7431).
- [x] T011 Пройти exact-SHA PR/Full/CD, backup/recovery и live readback; FR016–18 (Issue #7431).

- [x] T012 Унифицировать оформление трех статей с лендингом; сохранить текст/SEO/ссылки и проверить mobile/text200%/keyboard; FR019–20 (Issue #7435).
- [x] T013 Пройти exact-SHA CI и штатную публикацию общего дизайна с protected readback; FR019–20 (Issue #7435).

## Предметная помощь по двум источникам звука

- [x] T014 [US4] Подготовить и локально проверить `/help` и статью одной стороны записи в `public/content.py`, `public/web.py`, `public/templates/public/help.html`, `one_sided_audio_help.html`, общую навигацию и `tests/contract/test_public_audio_help.py`; FR021–26 (Issue #7544).
- [x] T015 [US4] Создать узкий draft PR, проверить exact-SHA `governance-fast`, `macos-pr`, `pr-metadata` общим `scripts/validate-pr-checks.py` и записать ограничения в `specs/281-mac-meeting-guide/audio-help-evidence.md`; FR026 (Issue #7544). Исходный draft-срез не включает merge/release/deploy.

T015 подтверждена на исходном head `6fe34ead257b8c10fecde4605c5ca7f4af17a4b6`: PR7545, governance-fast37364831663 attempt2, macos-pr37364831594 attempt2, pr-metadata37364833578 attempt1 SUCCESS, общий exact-SHA validator PASS. При обновлении базы требуется новый proof; прежний PASS его не заменяет.

- [x] T016 [US4] Выполнить отдельно разрешенную публикацию Help: актуальный exact-SHA PR proof, завершенный чужой baseline, frozen Full, штатные backup/CD/health и production HTTP200/canonical/sitemap/navigation/mobile/protected readback; FR027–28 (Issue #7544). Свежая штатная копия GRAF разрешена владельцем 2026-10-06; новое хранилище и резервный PostHog исключены. Незавершенный F286 автоматически не выпускать.

Условие отдельной базы T016 подтверждено: F286 v2026.10.06.1 опубликован 2026-10-06 на29264c66520ee36b1a2f287fa7edd6e92139dd9f, Full37527256994 SUCCESS; CD durable result deployed, migration0104, live/ready200 и lock освобожден. Это не proof собственного будущего Help Full/CD.

T016 завершена: v2026.10.07.1 опубликован 2026-10-06T22:25:10Z, source
`ad597c114e3bf9e627525c578ec68e353d54a44e`. Единственный Full37537979359 SUCCESS,
candidate `rc-20261006T220142Z-95a12ddbc931`, train/decision go. Штатный CD PASS,
attempt `599561ecaa474082b65ce28cfe345373`, свежий backup
`/opt/projects/2brain-rec/backups/20261006T221459Z`; публикация подтверждена
immutable attestation 22:25:18Z. Live Help/guides/canonical/sitemap/navigation,
Chromium320/390/768/1440,text200%,keyboard/noJS и protected/source readback PASS.
Полные границы проверки и доказательства — в `audio-help-evidence.md`.

## Отдельная сверка T011/T013 — 2026-10-17

Публикация и исходные критерии T011/T013 проверены отдельно от T016.
PR7432/7437 подтверждены общим валидатором на точных head/base/merge.
Работающий v2026.10.16.6/source
`834bdc87e3c83ebd86e1afd2c6e7760229b7297d` содержит оба изменения;
Full38933940635 attempt1 SUCCESS, durable CD deployed, backup PASS.
В четырех службах 11 файлов совпали с Git; публичные CSS/JS совпали
побайтово, live/ready200. Три статьи прошли Chromium360/390/768/1440
с обычным и удвоенным текстом (24 сочетания), клавиатуру, контраст
и работу без JavaScript. Подробности и границы —
[publication-reconciliation.md](publication-reconciliation.md).
Отметки относятся к проверенной реализации и публикации; issues7431/7435
закрываются после принятия этой документальной сверки и отдельной
проверки фактических комментариев. Общая F281 этим не закрывается.


## Структурированные данные руководств — G041, 21.10.2026

- [X] T019 Подготовить и локально проверить Article/BreadcrumbList для Zoom и протокола в `public/templates/public/zoom_recording_guide.html`, `meeting_protocol_guide.html` и профильных contract tests; JSON-LD только по видимым фактам, без вымышленных дат, отзывов и изображений. После проверки — коммит, PR и exact-SHA checks; владелец отменил отдельное подтверждение коммитов 21.10.2026. Публикация/индексация не входят; связь с umbrella #7391 частичная.

## Переход из руководств к готовой записи — G065, 21.10.2026

- [X] T020 Исправить обычные ссылки действия Zoom на `/meetings`, добавить один абзац загрузки готового файла в протоколе; файлы `public/templates/public/zoom_recording_guide.html`, `meeting_protocol_guide.html` и их существующие contract tests. Lane: docs-only / mechanical within F281, без изменения auth, загрузчика, маршрутов, аналитики и защищённой главной. Проверить HTML Accept и штатный 303 на вход с `next=/meetings`, прежний учебный текст/metadata/якоря, focused проверки двух файлов и protected diff. Отдельное подтверждение коммита отменено владельцем 21.10.2026; CI, выпуск и публичный переход остаются отдельной приёмкой.


## Проверяемый учебный результат — G035, 22.10.2026

- [X] T021 Дополнить Zoom-инструкцию одним разделом о разрешённом учебном результате по FR033: реальные наблюдения/ошибка/ограничения без закрытых материалов; добавить один пункт содержания, сохранить прежний текст/metadata/CTA/главную и активы. Проверить существующие контракты, mobile320/390/768/1440 и no-JS, сохранить/открыть PR с exact-SHA checks. Рабочая публикация и public readback обязательны для полного завершения; трафик и продажи не выводятся из этого текста.


T021 принята27.10 в v2026.10.27.1, source
`7e32f0da25db5d78d742f9cde1ed59a49ffcaf1a`: существующие локальные
контракты/mobile/no-JS и exact-SHA PR proof приняты общим train;
Full40491725053, штатный CD и публичное чтение #demo-result/CTA PASS.
[Выпускной отчёт](../../docs/deployments/2brain-rec/release-v2026.10.27.1.md).
G035 остаётся частичной по дополнительному материалу протокола;
индексация, внешний трафик и продажи не подтверждены этой приёмкой.


## Сверка принятых T019/T020 — 28.10.2026

T019/T020 выполнены в PR #7684 и исправляющем PR #7703. Оба заново прошли
общий валидатор на своих точных SHA/основах/merge; оба merge входят в
опубликованный `v2026.10.22.1`, Candidate
`8e37e0e3570372d7375151bf6624d5f0dcc3e627`, Full39687378196 PASS.
28.10 публичное чтение подтвердило обе Article/BreadcrumbList, три ссылки
Zoom и одну ссылку протокола на `/meetings`, штатный303 на вход с
`next=/meetings`. Новый тест входа с учетной записью и загрузка не выполнялись.
[Доказательства и оставшиеся ограничения](tracker-reconciliation-20261028.md).
Общая #7391 остается открытой: обязательна сверка владельцев исторических
задач; отдельно подтверждено переполнение `/guides` при увеличении текста.

## Перенос увеличенного текста — FR034

- [X] T022 Сначала воспроизвести переполнение настоящих public templates в `apps/server/tests/browser/public-audio-help.test.cjs`, сохранить обнаружение в вызывающем `apps/server/tests/contract/test_public_audio_help.py`, затем исправить перенос в `apps/server/src/twobrain_rec_server/public/static/public/content.css`; пройти70 сочетаний FR034, прежние keyboard/no-JS/reduced-motion и focused contracts, независимый checklist, convergence и exact-SHA/base PR gates. (Issue #7796)
- [X] T023 После T022 включить исправление в согласованный штатный выпуск и подтвердить FR034 на публичных7 страницах; записать candidate/Full/CD и live70 в `specs/281-mac-meeting-guide/text-reflow-validation-20261028.md`. До публикации оставить задачу открытой. (Issue #7797)

Прежняя локальная проверка28.10 сохранена: исходный отказ
471px воспроизведён, CSS-перенос проходит70 сочетаний, все20 профильных
контрактов PASS. [Отчёт и границы](text-reflow-validation-20261028.md).
На source `b35ace2074d530f9938dfb4cb16a0f4c428070f0` GitHub
`governance-fast40629252793` выявил выход четырёх стрелок карточек за границы
при320px/200% текста. T022 возвращена в незавершённое состояние: нужны
исправление и новые exact-SHA/base GitHub checks с общим валидатором.
Прежний локальный PASS не заменяет отказ CI. T023 не выполнена.

Последующее исправление T022 принято на source
`abcb60e3ecf8a8b0c8cf5cd1313bef0d81c9449f`, проверенная основа
`2b361954a7f19a8017fccea7d4e4063039aa5180`: governance-fast40631411105,
macos-pr40631411026 и pr-metadata40631430421 SUCCESS, общий
`validate-pr-checks.py` PASS. После переноса на эту основу повторены все20
профильных контрактов и70 браузерных сочетаний,0FAIL/0SKIP.
Отметка T022 опирается на этот новый результат; прежний отказ сохранён выше.
Документальный коммит этой отметки требует собственных окончательных checks
до merge #7798. Закрытие #7796 — после принятого merge и live-валидатора;
публикация T023/#7797 и общая #7391 остаются открытыми.

## Приёмка опубликованного FR034 — 29.10.2026

T022 окончательно принята в PR #7798 на source
`240fcbc919a81c626c884f8bbfed494957e8f00f`, merge
`312b9cbbcb2d666832a9c8b583e7b7bb08d8ff2c`; промежуточные проверки выше
сохранены как история. T023 подтверждена в опубликованном `v2026.10.29.1`,
Candidate SHA `976f310f9fff09b96a1e6fcec99cb43f4bb706ae`:
Full40873789634 attempt1, decision/штатные CD/backup/health/tag/Release и
publication attestation проверены отдельно. Повторная настоящая публичная
матрица29.10:70 PASS,0FAIL;17 страниц и сохранение защищённых ресурсов PASS.
[Доказательства и ограничения](text-reflow-validation-20261028.md).
#7797 закрывается после принятия документального PR и release-gated
live-проверки. Общая #7391 остаётся открытой для сверки исторических владельцев.


## Итоговая сверка владельцев — 29.10.2026

Восстановлены явные связи восьми исторических задач с их существующим
владельцем #7391. Исходные 23 checkbox-строки, описания, порядок, состояния
и прежние владельцы сохранены. Новых задач и issues нет.

- T001 (Issue #7391)
- T002 (Issue #7391)
- T003 (Issue #7391)
- T004 (Issue #7391)
- T005 (Issue #7391)
- T019 (Issue #7391)
- T020 (Issue #7391)
- T021 (Issue #7391)

Основания в исходных PR, история временного T000 и индивидуальные условия
общей приёмки — [в дополнении к сверке](tracker-reconciliation-20261028.md#итоговая-сверка-владельцев--29102026).
T023/#7797 принята в PR #7812, source
`6c8b5d1357028e2b1a68833b4b7c7ff924ab1c0a`, merge
`316515ead603d8110c11b1b3a06252c9be31be54`; три проверки точного SHA/основы
и live closeout PASS. Общую #7391 закрывать последней только после принятия
этой сверки, индивидуальной проверки девяти детей и итогового live feature mode.
