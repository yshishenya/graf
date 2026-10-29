# T113: остановка продуктовых служб и PostgreSQL перед восстановлением

30.10.2026; основа `40a8be0161fa3cbd12373381506dca2bb6cca62a`, ветка
`codex/f273-local-period-20261029`, полоса `high-risk-product`, T113/#7804.
Подготовлены два внутренних шага будущего доверенного оператора. Это локальная
проверка части T113; рабочего T0, включения аналитики и выпуска нет.

## Реализация

`product_analytics/activation_operator.py` переиспользует существующий
`ActivationFence` и установленный asyncpg. Нет новых зависимостей, службы,
универсального контроллера или командной оболочки. Внешний оператор обязан
владеть deployment lock, filesystem EX и физическими соединениями до окончания
работы/очистки. До любых subprocess/SQL проверяются EX, постоянный inode и
существующий revoked. Готовность, initial.json и новый T0 код не создаёт.

`stop_product_writers` проверяет выбранные Docker metadata, затем ровно один
раз останавливает присутствующие службы из фиксированного списка:
rec-api, rec-processing-worker, rec-media-worker, rec-maintenance,
rec-prompt-optimization-worker. Первые три обязательны; последние две могут
отсутствовать из-за профиля operations. Никогда не запускает отсутствующие
службы. Созданный, но никогда не работавший optional-контейнер допустим только
с PID0 и всеми inactive flags. После остановки остальные writers — только
exited; exit0 для остановленного writer не требуется.

Обязательные rec-migrate/rec-minio-init — exited0. rec-db-runtime-bootstrap
может отсутствовать: настоящий CD выполняет `run --rm --no-deps` на строке1270.
Это отсутствие не доказывает исторический успех bootstrap; полный verifier
позднее обязан проверить текущие роли и схему. Присутствующий initializer
должен быть exited0, без oneoff/дубликатов. Postgres/MinIO/Temporal остаются
работающими с прежними ID. Unknown/dead/removing/required-created, дубликат,
смена ID и чужой участник частных сетей дают HOLD. Сети, состав служб и IDs
сверяются до и после остановки.

`postal-network` — ключ Compose; фактическое имя по умолчанию
`postal_postal-network`, возможно переопределение. Проверенное имя передаётся
оператором обязательным аргументом. Участники общей почтовой сети не считаются
собственностью GRAF. Обе частные сети проверяются по ID/имени/project/internal
и полному составу участников. Env/Cmd и секреты не читаются и не выводятся.

Весь Docker-шаг имеет один deadline120с, включая оба чтения inventory. При
timeout/отмене собственный CLI child завершается и обязательно reap-ится;
повторная отмена не прерывает очистку, в том числе при незавершённом spawn.
Это не kill контейнера. Уже принятая Docker daemon операция остаётся неизвестной,
успех не возвращается, stop не повторяется. Очистка может превысить deadline
ради владения ресурсом; filesystem EX остаётся обязанностью вызывающего кода.

`drain_product_database` имеет один deadline30с до первого SQL. Уже открытые
owner-к-postgres и source maintenance сверяются по cluster/name/OID, identity,
ролям, RLS и отсутствию транзакции. Owner в autocommit закрывает новые source
подключения через ALLOW_CONNECTIONS=false; отдельное чтение подтверждает OID
и false. Source получает session EX `(273,3)`, ждёт **все** прочие PID и prepared
transactions этой БД, очищая статистический снимок перед чтениями. Фильтра
только по известным ролям/запросам нет. Финально повторяются identity/closed и
revoked. Session EX не снимается helper: он нужен до последующего экспорта.

Timeout/ошибка после отправки ALTER всегда HOLD, даже если БД уже закрыта.
Нет terminate-backend, DROP FORCE, автоматического открытия БД/запуска служб.
Отмена передаётся вызывающему коду, который обязан держать EX и соединения до
завершения SQL task/закрытия. Верхний владелец ещё не реализован этим модулем.

## Причинные проверки

- До реализации новый профиль дал RED на отсутствующем модуле при сборе тестов.
- Итоговая команда из apps/server: `PYTHONPATH=src .venv/bin/pytest -q tests/unit/test_activation_operator.py tests/unit/test_activation_fence.py tests/integration/test_activation_product_drain.py`.
- **62 passed, 2 warnings / 27.57s**. Два предупреждения — уже существующие
  pytest import rewriting и Starlette/httpx deprecation.
- Настоящий PostgreSQL17, собственный UUID-кластер: late PID; SH-транзакция;
  подготовленная транзакция при0 прочих PID; запрет нового подключения;
  invalid identity/active transaction до ALTER; отмена; timeout; неизвестный
  результат ALTER после фактического закрытия. Кластер удалён.
- Настоящий Compose-стенд: все пять writers остановлены, три инфраструктурные
  службы сохраняются. Фактический stop и итоговые состояния проверены. Существующие
  локальные рабочие сети не затрагивались: тест использует свои UUID-сети и
  заменяет только их имена в проверяемой функции. Все свои контейнеры/тома/сети
  удалены; после профиля список ресурсов с test-owner пуст.
- Локальные Docker default address pools исчерпаны. Без удаления чужих сетей
  тест выбирает три не пересекающиеся свободные /28 из198.19.0.0/16 только для
  своего стенда, проверив текущий Docker IPAM. Ошибка создания не стала PASS.
- Unit-матрица: optional/required/initializer состояния, missing/дубли/замена,
  неизвестные сети/oneoff; отдельные default/custom postal-name regression.
- Четыре настоящих spawn/cancel/timeout сценария подтверждают reap, включая
  отмену во время spawn и повторную отмену во время очистки.
- Один DB deadline подтверждён до первого identity SQL, без ALTER после истечения.
- Ruff по трём новым файлам, governance, development-process, changelog fragments,
  whitespace и103 локальные ссылки — PASS. Рабочий продукт, сеть и GRAF Dev не менялись.

## Независимое ревью и оставшийся объём

[Проект и уточнения D1–D3](t113-product-drain-design-review-20261030.md)
проверены до кода. Reviewer перечитал117 требований:117 подтверждены/0 открыты.
Первый HOLD сохранён как история; обязательные инженерные уточнения устранены.
[Ревью реализации](t113-product-drain-code-review-20261030.md): SCOPED PASS
замороженного снимка кода/тестов, без оставшихся блокирующих замечаний; исполнитель не меняет reviewer checklist.

Требования activation-milestones/operations и существующий T113 сохраняют
непроверенные части: верхний владелец deployment/EX/connections; неизменяемый
исходник и binding запуска; initial/verifier/ready; полный настоящий restore,
replay/resume/rollback; свежие resource/retention/backup receipts и T112.
Безусловный `activation_recovery_unverified` сохранён. T113/#7804, G010–G019 и
AC01–AC06 не закрываются. Отдельный PR/Full/CD для одного helper не создавался.

## Зафиксированные материалы

| Материал | SHA-256 |
| --- | --- |
| activation_operator.py | `9927e66cc96731b723c8a9689cbb65ec2f2a72af1fd157de2ef2b055504931a2` |
| unit test | `4f59426ba2d4bd018b61fdd47d229603b8826e9254cd8941741ae79c764497c3` |
| integration test | `4d0223b522cc8ec69ef14e005109e25a0e1eadc948f0b335548a0ce10abb2f1d` |
| итоговый ignored журнал | `519d80b8c60fd758fbcf58f6bd5c2fdd2ab686e7b78252527faedeb179e2b03e` |

Журнал: `.dev/growth/t113-product-drain-final.log`. В Git только исходники,
метаданные и отчёты; дампы, пароли и временные стенды не сохраняются.
