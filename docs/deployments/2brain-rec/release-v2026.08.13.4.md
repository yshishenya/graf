# Production receipt: v2026.08.13.4

Дата: 2026-08-14  
Контур: `https://rec.2brain.pro`  
Deploy SHA: `faeefd574a05cf9bdc77482f857471a62c27041c`

## Выкладка

- `infra/scripts/cd-remote.sh --execute --branch master` — `deploy_result=pass`.
- Backup/restore rehearsal, миграции, runtime identity, production smoke,
  Temporal, processing worker и automatic dispatch — PASS.
- Smoke cleanup удалил 39 записей и 3 объектных ключа; остатка не обнаружено.
- Live `/download` отдаёт universal notarized PKG:
  6 241 392 bytes, SHA-256
  `2fee7e9cfb70e2894680f4b956a4bfc4105c6501cc71808343a26fae17962970`.
- PKG подписан Developer ID Installer и принят Apple Notary Service.

## macOS и Intel

- Пакет содержит `GRAF.app` с архитектурами `arm64` и `x86_64`.
- На Apple Silicon выполнен запуск `x86_64`-среза через Rosetta 2; процесс
  стартовал и был остановлен после smoke timeout.
- Физического Intel Mac в доступной среде нет; отдельная аппаратная проверка
  остаётся ручным follow-up.

## Ограничения

- GitHub Actions не запускались; проверки выполнены локальными скриптами.
- Checkout YooKassa остаётся выключенным.

Receipt содержит только технические метаданные и не содержит пользовательских
данных, аудио, транскриптов, секретов или приватных ключей.
