# T039 — исправление длительности замены

Текущая база после последовательного слияния T040: fff8ee9fe49bc25105a664874b218f94b2b4a057, отдельная ветка codex/f292-replacement-duration. Исходная база предметных RED/GREEN: 387c3290ae2d36f35fb67d7bf432e4a5873466e0. При переносе все четыре проверенных Python-файла побайтово сохранены. Active Spec Kit slice, high-risk storage/playback.

- Requirements review: review-t039-requirements.md,3/3, C0/H0.
- Analyze: analysis-t039.md, блокирующих противоречий нет. Issue sync: #8117; canon validator278 issues PASS.
- RED: два варианта24/90 прежнего create/retry теста упали с ложным409. Изолированный PostgreSQL контейнер удалён штатно.
- GREEN: 70passed,2warnings,99.93sec, focused104sec; collection digest a9483630104b130d5970517b3b745cb9e4d80d5f110ed275cbaf9b0e330ad46c.
- Команда: bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_media_revision_reprocess.py tests/integration/test_meeting_sharing_parity.py tests/unit/test_media_revision_persistence_order.py tests/integration/test_media_revision_identity.py tests/integration/test_cabinet_meeting_rename.py -q.
- Независимый read-only обзор revision_duration_audit: C0/H0/M0; все9 callers, initial/immutable/source/version safeguards сохранены.
- Ruff и git diff --check PASS.
- Локальный governance doctor не принят: глобальный specify1.2.6 отличается от закреплённого1.0.7; проект/глобальное окружение не менялись. Обязательная exact-SHA GitHub проверка впереди.
- Dev/native, production, новый релиз и уборка активной синтетической fixture ещё не подтверждены этим отчётом. T039 и прежние открытые задачи остаются открытыми.

Проверенные байты:

- `apps/server/src/twobrain_rec_server/ingest/store.py`: `98278003473d3a05c637fc950998fd912aba5431672ac040d24ef680a8e9ed42`
- `apps/server/src/twobrain_rec_server/cabinet/public_sharing.py`: `cec492bb21fee06059f72b7892de214b343c413a2737490a9a8777717b037bd4`
- `apps/server/tests/integration/test_media_revision_reprocess.py`: `80dbec8bbb1941024a79aa974d4e0273d315577cd91c69b3b79966bf77092c64`
- `apps/server/tests/integration/test_meeting_sharing_parity.py`: `6d2c4368e58b10319a6258de61571f08451b63a847eb2e9f3f94710dcce2143b`

## Дополнительная приёмка установленного выпуска

2026-11-17, основной `/Applications/GRAF.app` версии 2026.11.16.2, только разрешённый учебный материал без изменения доступа или данных. Окно «Поделиться»: визуально без перекрытий, основные параметры доступны. В системном сохранении отмена → один Escape закрывает панель и возвращает фокус на «Поделиться». Успешное сохранение → один Escape также закрывает панель и возвращает фокус на AXPopUpButton «Поделиться», системных sheets нет. Фактический непустой UTF-8 экспорт: 1995 байт, SHA-256 ce313162f1d94b9849f74aca8bea1026a588bc40e6b12fa781d2e6b7fef3e5b5; собственный временный файл удалён после проверки. Это подтверждает соответствующие действия уже установленного выпуска, но не native A/B для T039 и не приёмку нового выпуска. Полные AX-снимки и содержимое экспорта в git не включаются.
