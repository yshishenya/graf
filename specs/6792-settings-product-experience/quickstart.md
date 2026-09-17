# Проверка F6792

## Первый локальный цикл

Перед PR просмотреть общий выбор через `infra/scripts/ci-local.sh --plan` и
выполнить `infra/scripts/ci-local.sh --focused` в подготовленном окружении.
Карта F211 включает существующие проверки общих assets, меню и настроек при
изменении связанных исходников, даже если сами тесты не менялись; точный
состав и окружение — в [quickstart F211](../211-optimize-ci-cd/quickstart.md).
Пустой выбор не означает успешную проверку. Для изменений связанных API,
календарей, браузерных или native-границ дополнительно действуют сценарии ниже.

## До изменения установленного приложения
1. Прочитать `docs/agent-guidance/local-development.md`, проверить `infra/scripts/dev-harness.sh status --json`.
2. Выполнить целевые pytest: `apps/server/tests/contract/test_settings_ui_contract.py`, `test_calendar_settings_contract.py`, `apps/server/tests/unit/test_settings_view_models.py`, `test_settings_outcomes.py`, `apps/server/tests/integration/test_settings_ia_flow.py`, `test_calendar_settings_flow.py` в существующем окружении тестов проекта.
3. `node --test apps/server/tests/browser/timezone-settings.test.cjs`.
4. Из `apps/macos` выполнить целевые Swift tests для DesktopMeetingShellWebViewBoundaryTests, CabinetSidebarRuntimeTests, EmbeddedCabinetRecordingSettingsBridgeTests, EmbeddedCabinetNotificationSettingsBridgeTests, DesktopCabinetWorkspaceTests.
5. Пройти макет `prototype.html`: семь вкладок, светлая/тёмная темы, поиск, редактирование/отмена, раскрытия. Макет синтетический и не подтверждает работоспособность продукта.

## После проверок и разрешённого коммита
Из чистого checkout выполнить штатный harness build → promote → status → smoke; при несовместимом runtime использовать документированный previous-checkout. Только `/Applications/GRAF Dev.app`, без копий приложения и обхода dirty check.

## Матрица ручной приёмки
- Все 7 разделов: 1040×680, широкое окно, узкая веб-область 360 px, 200%, обе темы и системная тема с соответствием текущей теме ОС.
- Навигация мышью и клавиатурой, Escape, назад/вперёд, явное возвращение к встречам; названия доступны.
- Аккаунт: изменение и отмена имени/темы/времени; входы; раскрыть/закрыть закрытие аккаунта без отправки; ожидающее закрытие и его отмена видны без раскрытия.
- Пространства: текущий выбор/приглашения; проверка прав на синтетических данных.
- Запись: найти Zoom и Телемост, сбросить поиск, осмотреть полный список/три правила/массовый выбор; не менять реальные правила без необходимости. Регрессия состояния и version guards покрывается tests.
- Итоги: основной формат, встроенные/личные, создание/копия и отмена формы; синтетические скрытие/удаление личного формата и сохранность старых итогов.
- Календари: пустой/подключённый/недоступный, выбор сервиса, отмена формы подключения, фильтры. Не вводить реальные credentials.
- Уведомления: local/browser state, зависимость времени от напоминания, звук, названия, история. Локальные изменения в tests.
- Оплата: owner/member/unavailable, отсутствие вымышленных цен; не проводить платежи.
- Активная запись: persistent indicator и one-action Stop защищены runtime tests, затем ручной синтетический сценарий на Dev при доступном стенде.
- Ошибки, конфликт и offline: прежние значения не выдаются за сохранённые; доступен повтор и отмена.

## Closeout
`git diff --check`, целевой lint, Spec Kit analyze/converge, changelog fragment; required governance-fast на точном PR SHA после разрешённого коммита. native acceptance, CI, merge и release фиксируются отдельно. При недоступном ручном сценарии прямо указать pending, не отмечать выполнение.
