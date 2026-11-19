# Чеклист требований: настоящая автоматическая обработка T014/#3361

**Purpose**: Независимая проверка полноты, ясности и согласованности требований
нового серверного этапа; не приёмка реализации.
**Created**: 2026-11-17
**Feature**: [spec.md](../spec.md)
**Note**: Создан через `$speckit-checklist`; строгая проверка high-risk требований.
**Review Ownership**: Состояние пунктов принадлежит независимому reviewer.
**Marker Semantics**: `[x]` означает достаточное качество требований, без
утверждения о выполнении сценариев, выпуске или закрытии issue.

## Полнота и границы

- [x] CHK001 Определена ли связь настоящей автоматической цепочки с исходными критериями T014/#3361, без замены критерия одним успешным WAV? [Полнота, Spec §Clarifications, Contract §Область и этапы]
- [x] CHK002 Сохранены ли все исходные format/copy/remux/track-selection, limits/failure/retry/recovery/backfill/lifecycle требования с отдельным открытым результатом до доказательств? [Покрытие, Quickstart §§3–9, Contract §Область и этапы]
- [x] CHK003 Ясно ли различаются слитый guard #8128, первый проверяемый этап A и полный closeout T014? [Ясность, Plan §настоящая автоматическая серверная цепочка]
- [x] CHK004 Согласованы ли новые источники с single-source F275, без разрешения создавать старые dual-source upload или provider submission? [Согласованность, Spec §Clarifications, Model §модель наблюдения]

## Изоляция и зависимости

- [x] CHK005 Определена ли изоляция окружения до collection/import/Alembic, включая предел `_env_file=None`, без чтения или изменения настоящего `.env`? [Полнота, Contract §Изоляция до импорта и collection]
- [x] CHK006 Определены ли запрет наследования рабочих интеграций/секретов и явные синтетические настройки всех зависимостей? [Безопасность, Contract §Изоляция до импорта и collection]
- [x] CHK007 Указаны ли границы локального Docker socket/config, случайных loopback портов, владельца ресурсов и запрета общих томов/remote daemon? [Полнота, Contract §Настоящие зависимости]
- [x] CHK008 Измеримы ли требования к фактическим PostgreSQL/MinIO image IDs и отказу при неизвестном или изменённом образе, без доверия одному tag? [Измеримость, Contract §Настоящие зависимости]
- [x] CHK009 Заданы ли точные SDK/CLI version/checksum, запрет default download, отсутствие fake fallback и отдельная граница для другой платформы? [Ясность, Research §настоящий transport, Contract §Настоящие зависимости]
- [x] CHK010 Различены ли restricted media-role/tenant fence и owner-backed API fixture, включая непроверенные production grants? [Согласованность, Contract §Настоящие зависимости, Model §модель наблюдения]

## Качество критериев результата

- [x] CHK011 Определено ли, что только HTTP acceptance запускает работу, а непосредственный запуск dispatcher/workflow/job не доказывает автоматичность? [Ясность, Contract §Сценарии этапа A]
- [x] CHK012 Различены ли наблюдение настоящего source verified-download и независимая проверка скачанного stored canonical, без подмены транспорта или результата? [Полнота, Contract §Сценарии этапа A]
- [x] CHK013 Измеримы ли A-success: одна lineage/job/canonical, published attempt, сохранность source, полный decode/profile/BMFF скачанного объекта и Range? [Измеримость, Contract §Сценарии этапа A]
- [x] CHK014 Определены ли accepted negative input, точный terminal reason, отсутствие retry/publication и различие с отказом API до acceptance? [Покрытие исключений, Contract §Сценарии этапа A]
- [x] CHK015 Ясно ли, что setup failure, skip, timeout, неожиданный reason и неполная очистка не являются PASS? [Ясность, Contract §§Сценарии этапа A, Ограничения времени и очистка]

## Ограничения и проверяемость

- [x] CHK016 Заданы ли ограниченные старт/ожидание/teardown/общий процессный срок, без объявления async context или SIGKILL гарантией очистки? [Измеримость, Contract §Ограничения времени и очистка]
- [x] CHK017 Указаны ли владелец cleanup, порядок остановки, безопасное поведение при остатках и запрет удаления чужих ресурсов? [Полнота, Contract §Ограничения времени и очистка]
- [x] CHK018 Определены ли безопасные evidence fields и запреты media/секретов/ключей/сырого stderr с сохранением точного source SHA и результатов каждого этапа? [Безопасность, Contract §Доказательства и оставшиеся ворота]
- [x] CHK019 Отделены ли factory/activity от run_worker startup/reconcile, host от non-root container, server от UI/Dev и focused от release/deploy приёмки? [Согласованность, Contract §Доказательства и оставшиеся ворота]
- [x] CHK020 Согласован ли порядок текущей T014 с обязательными независимым review/analyze/issue sync, exact-SHA/base PR gates и --verify-live до COMPLETED? [Прослеживаемость, Tasks §продолжение T014, Plan §настоящая автоматическая серверная цепочка]

## Notes

Новые 20 пунктов оставлены непроверенными. Исторические шесть списков и их
100/0 относятся к прежнему guard и требуют повторного независимого рассмотрения
в применимой новой области. Основной агент markers не меняет.
`$speckit-implement` читает результат как ворота; незакрытые пункты блокируют
реализацию. A/B/C остаются неисполненными независимо от review quality PASS.

## Независимое ревью нового real-transport scope — 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы заново оценены по текущим требованиям. Старые STOP/PASS выше сохранены как история guard; новый общий допуск **STOP, implementation_admission=false**.
Итог файла: checked **14**, unchecked **6**, всего **20**. `[x]` означает только качество требований, не выполнение A/B/C и не закрытие T014.
- CHK005: H2: Launcher env описан, но default all-suite discovery test_*.py не требует launcher и остаётся неопределённым; pre-collection изоляция не замкнута для обычного CI.
- CHK007: H1: Local socket/config/MinIO ownership заданы, но common PG runner не выдаёт caller-owned identity для безопасной внешней очистки.
- CHK008: H1: Требование сверять фактический ID образа PG до сценарных данных ясно как цель, но existing runner не имеет imageID/ID output и план запрещает его менять; способ связать admitted image со своим PG не определён.
- CHK016: H1: Числа 60/120/60/30/600 определены, но нет проверяемого resource identity handoff/владельца после аварийного завершения и матрицы самопроверок TERM/KILL между create/registration/cleanup.
- CHK017: H1: Cleanup порядок и запрет чужих ресурсов заданы, однако сохранённые ID/labels PG не доступны через существующий interface; нельзя безопасно реализовать заявленный outer cleanup.
- CHK020: H2: Review/analyze/sync/SHA/base/verify-live порядок написан, но новый автоматически обнаруживаемый тест без режима ordinary CI конфликтует с обязательными PR/release gates; нужен явный критерий discovery/execution.
Полная карта всех 120 вопросов, исходники и H1/H2: внешний `f099-t014-real-transport-independent-requirements-review-20261117.md`. Неподтверждённые пункты блокируют реализацию; A/B/C остаются неисполненными независимо от отметок.


## Повторное независимое ревью real-transport — H1/H2, 2026-11-17

Проверяющий `/root/f099_download_requirements_review`; HEAD `193e01b2963700aaff9ed8e3f2fcabcd2e72083d`, ветка `codex/099-real-transport-acceptance`. Все исходные вопросы повторно сопоставлены с текущими оригиналами; прежние вопросы и заметки сохранены.
Итог файла: проверено **20**, непроверено **0**, всего **20**. Общий результат качества требований — **PASS, 120/0**. Это не допуск реализации: `implementation_admission=false` сохраняется; A/B/C не исполнены и T014 открыта.
- CHK005: PASS: H2 выносит acceptance/playback_normalization_real_transport.py вне testpaths и шаблона test_*.py/*_test.py. Stdlib guard проверяет контекст до app imports и tests.conftest plugin; H1 manifest проверяется runner до collection. Обычный CI не импортирует опыт.
- CHK007: PASS: Исходные local socket/config/loopback/no-volume ограничения сохранены; H1 добавляет заранее известные name/token/image и owner label, manifest/cidfile/state, точное доказательство владения перед удалением. Чужие ресурсы сохраняются.
- CHK008: PASS: H1 требует локально принятый sha256 image ID в manifest, docker run именно этого ID с --pull=never и проверку actual ID/name/label/image до первого SQL. MinIO сохраняет свой actual-image guard; mismatch/unknown — FAIL.
- CHK016: PASS: Сохраняются 60/120/60/30/600 секунд; PG starting phase и монотонное время перед bootstrap дают общий 60-секундный предел без сброса при повторе. TERM/KILL ожидания ограничены, внешний cleanup и граница смерти supervisor описаны.
- CHK017: PASS: H1 определяет порядок проверки/удаления по точному ID, отсутствие только по успешному lookup, поведение при unknown и явный дальнейший владелец cleanup_required после SIGKILL supervisor. Матрица служебных отказов предшествует A.
- CHK020: PASS: H2 требует настоящий pytest discovery в синтетическом проекте для ordinary collection/execution и явного выбора, без skip/xfail/CI config/selection правок. Plan/Tasks сохраняют reviewer → tasks reconciliation → analyze → issue sync, актуализацию базы до implementation/PR и точные PR/closeout ворота.
Полная карта 120 вопросов, контрольные суммы, собственные чтения и сохранность: новый внешний `f099-t014-real-transport-independent-requirements-rereview-20261117.md`. После этого назначения автоматического перехода к реализации нет.
