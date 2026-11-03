# F292 — проверка

## Предпосылки

Синтетическая встреча с двумя говорящими, готовым текущим transcript/audio и итогами, второй внешний пользователь и чистый браузер без входа. Никаких реальных записей, адресатов или секретов в отчётах. Перед крупной сборкой `df -h /System/Volumes/Data`; соблюдать local-development.md.

## Автоматические проверки

Из корня, штатным disposable PostgreSQL runner (он создаёт и удаляет собственный контейнер/БД), Python >=3.13:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_meeting_sharing_parity.py tests/contract/test_meeting_sharing_parity_ui.py tests/integration/test_summary_sharing.py tests/integration/test_recording_share_public_link.py tests/integration/test_meeting_share_links.py tests/integration/test_cabinet_playback_route.py tests/contract/test_recording_share_ui_contract.py tests/contract/test_recording_share_link_contract.py
node --test apps/server/tests/browser/summary-sharing-state.test.cjs
# Проверка Contacts/адресатов запускается contract-тестом с настоящим шаблоном:
bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_meeting_sharing_contract.py -q
swift test --package-path apps/macos --filter 'DesktopCabinet|SharedMeeting|ProductActivationAnalyticsContract'
python3 scripts/check_spec_kit_governance.py
```

Проверить стабильную ссылку/409, legacy summary-only, null summary full, narrow projection, чужой workspace/result, revoke/expire/rotate/scope/deletion и каждый Range, 200/206/416/буфер4MiB, headers и отсутствие секретов, безопасный cookie/redirect, parser scheme/query/position/cold pending и сохранение route после входа.

## Живая матрица

1. Владелец в браузере и GRAF Dev: открыть без публикации, invitation/roles/revoke, workspace audience, scope, expiry, stable copy, export и F286 delivery unknown/retry без дублей. Внешние письма заменять локальным тестовым транспортом.
2. Анонимный получатель: первое приглашение → просмотр → обе вкладки → copy/search → play/pause/±15/speed/seek и текущая реплика → вход/регистрация → возврат. Отдельно «своя встреча» в своём пространстве. Не регистрировать настоящий аккаунт для теста.
3. Summary-only не содержит transcript/audio в DOM/JSON/network. Две вкладки владельца: stale409. Отзыв/сужение/срок/удаление при открытой записи закрывают следующие запросы. Внутренних metadata и получателей нет.
4. Приложение только /Applications/GRAF Dev.app через dev-harness build/promote/status/smoke с чистого exact SHA: cold/warm, свой/другой аккаунт, expired session, вкладка/позиция, отказ системного открытия и отсутствие app. Не угадывать успех таймером. Браузер остаётся доступным.
5. 320/390/1440 px, светлая/тёмная тема, длинный заголовок/текст, keyboard/Escape/focus, отказ буфера/сети, без JS, пустые материалы. Сохранить только обезличенные итоговые журналы/скриншоты и ссылки на commit, без полных сборок.

## Ворота

Независимые security/ux checklist PASS до кода; analyze CRITICAL0/HIGH0; task issue sync. После кода converge и focused checks. PR: governance-fast/macos-pr/pr-metadata exact SHA/base. Production/release разрешены пользователем 2026-11-03 и выполняются после полного release gate из release-and-validation.md и macos-notarization.md. Не называть live acceptance пройденной без фактической проверки.

## Сквозная проверка Dev

`sharing-live.test.cjs` запускается только явно через `GRAF_SHARING_LIVE=1`, на loopback 8081 и на отдельной синтетической встрече существующего `local@graf.test` в его личном пространстве. Нужен настоящий синтетический аудиофайл. Не использовать рабочие встречи. `GRAF_NODE_MODULES` задаёт существующую установку Playwright.

```sh
GRAF_SHARING_LIVE=1 GRAF_SOURCE_SHA=<installed-full-sha> node apps/server/tests/browser/sharing-live.test.cjs <synthetic-meeting-uuid> <temporary-evidence-dir>
```

Проверка выполняет два входа; соблюдать действующий лимит 3 запроса кода за 15 минут. Ссылка маскируется на снимке владельца, в итоговый JSON попадают только названия проверенных действий и SHA. После завершения общий доступ отзывается.

FR-026: сравнить на основной и общей странице один и тот же проигрыватель: дорожки/цвета и проценты, клик по интервалу, позиция/активная реплика, следующий спикер, выбор речи, сворачивание, изменение высоты и клавиатура. Проверять два спикера с одинаковым видимым именем отдельно. Гостевая страница не запрашивает комментарии/редактор/контакты; summary-only не получает ключи/интервалы.

## Проверка выпуска FR-027

После T012/T013: T015 фиксирует серверный release train и authoritative full CI; T016 выпускает нотарифицированное macOS-обновление; T017 проверяет опубликованные сервер/страницу/приложение и закрывает задачи только по evidence. Продакшен-проверка использует отдельные синтетические материалы без адресных писем и изменения рабочих встреч. Проверки внешних аккаунтов/истёкшего сеанса выполняются на Dev. Не копировать production backup на Mac; хранить его штатно в закрытом серверном хранилище.
