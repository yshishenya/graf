# Temporal Web в production

## Доступ

- Публичный адрес: https://temporal.rec.2brain.pro
- TLS: Let's Encrypt, сертификат продлевается Certbot автоматически.
- Прямой порт Temporal Web `:18083` закрыт извне; публичный вход проходит через
  host Nginx.
- Перед UI установлен Basic Auth. Пароль хранится только на production-хосте;
  секреты и bcrypt-хэш в репозиторий не попадают.

Temporal Web не содержит локального хранилища пользователей и паролей. Его
встроенный production-вариант авторизации — OIDC/SSO через внешний Identity
Provider. До появления такой потребности Basic Auth на HTTPS остаётся текущей
операционной схемой.

## Развёртывание и жизненный цикл

- Отдельный persistent Compose-проект: `/opt/projects/temporal-ui`.
- UI подключается к Temporal Server по внутреннему адресу `rec-temporal:7233`.
- Используется namespace `default`.
- Контейнеры имеют `restart: unless-stopped`, поэтому UI возвращается после
  перезапуска Docker/хоста вместе с остальным production-стеком.

Состояние проекта на сервере проверяется без изменения конфигурации:

```sh
cd /opt/projects/temporal-ui
docker compose ps
docker compose logs --tail=100 temporal-ui
```

## Проверка после изменений

1. Без credentials запрос к `https://temporal.rec.2brain.pro` должен вернуть
   `401`.
2. С действующими credentials UI должен вернуть `200`.
3. API UI `/api/v1/namespaces` должен отвечать и показывать как минимум
   `default`.
4. После перезапуска Docker повторить пункты 1–3.

## Будущий переход на OIDC

Переход имеет смысл при появлении нескольких операторов, MFA, SSO,
централизованного отзыва доступа или аудита. Identity Provider и OIDC-клиент
нужно будет завести отдельно, после чего проверить callback, logout, роли и
сохранить Basic Auth как план отката до завершения проверки.
