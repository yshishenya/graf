# Выпуск F286 — v2026.10.06.1

Обмен сохраненными итогами по ссылке включен на https://rec.2brain.pro. Сервер развернут, активация и публикация прошли. Пользователь разрешил реализацию, проверенные коммиты и production выпуск; реальные письма для проверки не отправлялись.

Полоса функции: high-risk-feature с полным Spec Kit и независимым ревью. Финальная запись доказательств и состояния задач: docs-only / mechanical; работа продукта не меняется.

## Точная версия и допуск

- Source, tag, deployed и runtime SHA: `29264c66520ee36b1a2f287fa7edd6e92139dd9f`.
- Train: `train-20261006T203128Z-29264c66520e`.
- Candidate: `rc-20261006T203243Z-ab47b37ce582`.
- Changelog digest: `sha256:38633f7a2d051c133d5e5cd3682e9a70bb07aa49bc5f99ffbd9220d0ca82d980`.
- Единственный authoritative [release-full 37527256994](https://github.com/yshishenya/graf/actions/runs/37527256994): PASS. Requested SHA, observed SHA start/end и source совпадают; skipped gates пуст. Static/governance, strict PostgreSQL/performance, восемь серверных частей, macOS и aggregate успешны.
- Train attestation и candidate decision GO совпадают с source и полным receipt. Выпуск [v2026.10.06.1](https://github.com/yshishenya/graf/releases/tag/v2026.10.06.1) опубликован 2026-10-06T20:48:54Z, draft=false, prerelease=false; tag разрешается в точный source. Штатная release attestation PASS.

Состав от последнего опубликованного v2026.10.04.6 проверен штатным current-check validator при freeze/decide. Финальные изменения:

| PR | Source SHA | Merge SHA | Проверки |
| --- | --- | --- | --- |
| #7565 | `30ca64ec7319ce66aca675b9a23b6c6736edcfe1` | `6502bcf6b5cc379cab745a5c4edc13d8a0374084` | реализация и независимое ревью |
| #7569 | `47ea28967f9cca89f793b50cef8371ee36f3a381` | `889eb6bd3505957cf7f82e21091cb48df47464f9` | исправления перед полным прогоном |
| #7571 | `a0d27e5f5a939d845cb1606dc1d639de4a366ad3` | `21145f865911f66e27d4672b8ca8d52ff6ea52e7` | ожидание текста приглашения |
| #7574 | `a0d765dc5a6645658bd5e0abaa1bf90dcdc56e37` | `45089a56eb68808e0e4716b654aa034658753cdb` | canonical current-check PASS: governance37525082804, macos37525082799, metadata37525080775; base de255 |
| #7575 | `52d74af9cb78309f75fe4515b88cf03b4cfad134` | `29264c66520ee36b1a2f287fa7edd6e92139dd9f` | подготовка; governance37526898285, macos37526898452, metadata37526898664 |

В диапазон также входят прежние подготовительные PR #7567, #7570, #7572 и #7543; train проверил весь фактический диапазон, а не только последние PR.

## Развертывание и включение

CD dry-run PASS; execute `deploy_result=pass`. Remote deploy216с, driver225с. Резервная копия `20261006T204202Z`, migration head `0104_summary_share_scope_cascade`. Закрепленные образы соответствуют source, checkout чистый. CD подтвердил runtime identity, секреты служб без их вывода, Temporal/processing/media readiness, upload/processing smoke и итоговую готовность. Public live/ready HTTP200 (`ok`/`ready`).

Перед включением новой версии штатные maintenance helpers очистили только прежний синтетический run `smoke-f286-post-enable-de255e0d7f72-1791317026`; auth cleanup и artifacts cleanup PASS, остатки пусты. Использованы новый установленный образ, production lock, точный HEAD и проверенный blob исправленного helper; локальная подмена runtime не выполнялась.

Повторная активация закончилась `f286_activation=pass source=29264c66520ee36b1a2f287fa7edd6e92139dd9f`:

- nginx installer dry-run/execute, backup, drift comparison, nginx test/reload, headers/health PASS;
- HTTP redirect privacy, shared limiter429/error headers PASS; синтетический секретный URI отсутствует в журналах;
- public links, abuse gate и external invitations включены; конфигурация API, processing и maintenance проверена отдельно и прошла во всех трех постоянных службах;
- реальный HTTPS synthetic summary-only setup/prove/cleanup PASS: JSON/HTML200 без входа/cookie, текст расшифровки отсутствует, revoke404; mail=none, residue=none;
- общий upload/processing smoke PASS, `readiness_verdict=infra_smoke_ready`; run `smoke-f286-post-enable-29264c66520e-1791319639`; auth rows2, database records44, object keys4 удалены, residue=[];
- итоговая runtime readiness API/processing/media/maintenance/Temporal и публичные live/ready PASS.

Контрольные суммы выполненных процедур:

- activation: `7b2f1c62f25f579c2d247cd9c7dd184ed3ee101e539ea919bea5451e94a7708f`;
- edge proof: `07f21e752b68392ab18acb1f082020219b643d9db3ad532be467a49078ce3e21`;
- sharing smoke: `6b3c8142b37ec30322f80a401d4a18a4c43800e8ce89cc298357cd679897db78`;
- previous-run cleanup procedure: `8ec03b67b66d144aad9cc7bb9041020bc9074fc29f4b6b60ba2317e478f1f4ea`.

Activation и точечная очистка используют `--env-file .env`. Общий production smoke сам читает корневую .env, но одноразовые Compose проверки не доказывают sharing flags постоянных служб; поэтому flags проверены отдельно.

## Сохранение macOS и интерфейс

Серверный выпуск сохранил все98 публичных ZIP/PKG/appcast: фактическая карта SHA256 до и после совпала.

- graf.pkg: `b5df859986d0ad36a07302c87c598b7a7d6e027a65e4024dd70fe0cba3338662`.
- graf-appcast.xml: `a41579d1b65a44ec2a6e33a4efb33aa1841f8ea4d1d5d44445f3ef8138d7711a`.
- GRAF-2026.10.04.6.zip: `df9817ab93757e0bbed0fcb6ad3841a6c2cf18947445fce263b3d2cd375b2836`.

Единственный GRAF Dev проверялся штатным harness на47ea; build/promote/smoke и фактическое окно/reader PASS. Source diff по apps/macos и apps/server/src между47ea и финальным source пуст. Установленный Dev не называется сборкой29264. Проверки320/390, обеих тем, keyboard/focus и no-JS записаны в validation.md с исходными SHA.

## История остановленных попыток

- Candidates `rc-20261005T235931Z-f3b87b44222a` / Full37391541791 и `rc-20261006T003217Z-ec639d836515` / Full37394531573 не допущены из-за замечаний полной проверки. Их результаты не переиспользованы.
- Candidate `rc-20261006T005745Z-ad663a04a781`, source `de255e0d7f72ed5123f9f0ffffe34f586723cba6`, прошел Full37396717004 и первый CD (backup20261006T010805Z), но активация не завершилась. Неопубликованный кандидат отдельно оставлен без выпуска; draft/tag удалены до подготовки нового.
- Первая активация выявила Compose interpolation без явного env-file. Три флага автоматически возвращены; добавлен только `--env-file .env`, независимо проверено HIGH/MEDIUM0.
- Вторая активация прошла специальное HTTPS sharing доказательство, но общий cleanup отказал на FK storage_reservations/track_artifacts. Ссылки автоматически выключены. T021 исправила порядок удаления с parent lock;25 PostgreSQL/unit/context проверок и независимое exact-a0 ревью PASS. Новый кандидат получил отдельные Full/CD/activation, прежние доказательства не заменяли новые.

## Задачи и пределы подтверждения

T001–T021 выполнены. Canonical live feature closeout прошел до закрытия общей задачи и повторно после него, с require-release-full на точном source29264. Все21 дочерняя задача и umbrella7546 перечитаны:22 CLOSED,0 OPEN. Общая закрыта строго позже дочерних; потерянных задач и дублирующихся владельцев нет. Перед закрытием каждой опубликован подробный русский комментарий с PR SHA, Candidate SHA, успешными governance/full и пределами подтверждения. Операторский результат: `f286_closeout=complete; child_issues=21; umbrella=closed_last; total_closed=22`.

По умолчанию предложение поделиться включено, AUTO выключен. AUTO требует явного правила для встречи или будущих встреч серии и проверенного полного состава участников Google Calendar внутри пространства. Неизвестная доставка автоматически не повторяется. Реальное получение писем во входящие, AUTO с живым календарем и измеренный рост пользователей этим выпуском не подтверждены.

CD оставил `automatic_retry/backfill_inventory/range_playback/normalization_cleanup` в `required_post_deploy`: этот выпуск подтверждает существующую готовность инфраструктуры и возможность worker, а не отдельную живую приемку этих процессов. Ни один частный текст, адрес, capability token или секрет в доказательства не включен. Проверка оформления всех22 issues F286 прошла; общая проверка проекта отдельно сообщает о чужой #7544 без area/type меток. Это не нормализовалось в рамках F286 и не называется общим PASS трекера проекта.
