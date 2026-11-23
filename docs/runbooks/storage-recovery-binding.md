# Storage recovery binding для production

Этот документ объясняет обязательное условие выкатки, из-за которого
`cd-remote.sh --execute` останавливается с
`reason=storage_recovery_binding_unverified`.

## Зачем это нужно

Строгий журнал загрузки и восстановление хранилища работают только с
проверенной привязкой: приложение и деплой должны видеть один и тот же
операторский том и один и тот же идентификатор операции восстановления.
Если привязки нет, деплой закрывается fail-closed, потому что старт нового
рантайма на непроверенном хранилище может испортить данные.

Проверка выполняется в `infra/scripts/cd-remote-runtime.sh` через
`release-images.py storage-state`. Она требует:

- внешний Docker-том с точным именем `twobrain-rec-storage-recovery`;
- переменные окружения деплоя `TWOBRAIN_STRICT_STORAGE_SCOPE` и
  `TWOBRAIN_STRICT_STORAGE_RECOVERY_ID` (UUID) для режима `reconciled`,
  либо явное `TWOBRAIN_STRICT_STORAGE_RECOVERY_ALLOW_LEGACY=true`
  для режима `legacy`.

Том объявлен в `infra/docker-compose.yml` как `external`, поэтому Compose
не создаёт его сам: это осознанное операторское действие.

## Режим legacy: хранилище ещё не активировано

Это честное состояние, пока восстановление хранилища не введено в работу.
Том должен существовать и быть пустым.

```sh
cd /opt/projects/2brain-rec
cp -p .env ".env.backup-before-storage-recovery-$(date -u +%Y%m%dT%H%M%SZ)"
docker volume create twobrain-rec-storage-recovery
printf '\nTWOBRAIN_STRICT_STORAGE_RECOVERY_ALLOW_LEGACY=true\n' >> .env
```

После этого деплой печатает `storage_recovery_start_mode=legacy` и
продолжает работу. Не добавляйте в том файлы вручную: как только в нём
появляется запись, legacy-режим перестаёт считаться доказанным и деплой
снова закрывается.

## Режим reconciled: хранилище проверено оператором

Используйте его только после реальной сверки хранилища. Приложение не
создаёт запись `reconciled` само: это подтверждение оператора.

В томе должен лежать файл `state.json` со схемой:

```json
{
  "schema": 1,
  "scope": "<TWOBRAIN_STRICT_STORAGE_SCOPE>",
  "state": "reconciled",
  "recovery_id": "<TWOBRAIN_STRICT_STORAGE_RECOVERY_ID>"
}
```

Права: каталог `0700`, файл `0644`, владелец — тот, от кого запускаются
контейнеры. Рядом должен существовать `state.json.lock` (обычный файл,
приложение блокирует его через `flock`).

Затем задайте в `.env`:

```sh
TWOBRAIN_STRICT_STORAGE_SCOPE=<scope>
TWOBRAIN_STRICT_STORAGE_RECOVERY_ID=<uuid>
TWOBRAIN_STRICT_STORAGE_RECOVERY_ALLOW_LEGACY=false
```

## Проверка перед выкаткой

`cd-remote.sh --dry-run` до удалённых шагов не доходит, поэтому сам по себе
привязку не проверяет: он только печатает список шагов. Проверяйте привязку
напрямую на хосте:

```sh
ssh 2brain.dev 'docker volume inspect twobrain-rec-storage-recovery >/dev/null \
  && grep -Eq "^TWOBRAIN_STRICT_STORAGE_RECOVERY_ALLOW_LEGACY=true$" /opt/projects/2brain-rec/.env'
```

Для режима `reconciled` вместо этого проверьте, что в `.env` заданы
`TWOBRAIN_STRICT_STORAGE_SCOPE` и `TWOBRAIN_STRICT_STORAGE_RECOVERY_ID`, а в
томе лежит согласованный `state.json`.

Авторитетная проверка выполняется внутри `--execute` на хосте, до миграций и
до старта новых контейнеров. Если привязки нет, деплой печатает
`reason=storage_recovery_binding_unverified` и `reason_hint` со ссылкой на
этот runbook, а staged rollout откатывается на прежний рантайм.

## Откат

- Верните прежний `.env` из резервной копии.
- Том удаляйте только после явного решения оператора:
  `docker volume rm twobrain-rec-storage-recovery`. Удаление тома стирает
  только управляющую запись, но повторное включение потребует новой
  проверки хранилища.

## Что уже произошло 2026-11-23

Первый `--execute` для `v2026.11.22.1` остановился именно на этой проверке:
тома не было, переменных не было. Staged rollout автоматически вернул
production на прежний рантайм `aae5fce2d`, миграции не применялись. После
создания пустого тома и явного `ALLOW_LEGACY=true` повторная выкатка
прошла: `deploy_result=pass`, `deployed_sha=9fa919d7b`, backup
`/opt/projects/2brain-rec/backups/20261123T185426Z`.
