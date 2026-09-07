# Проверка Feature 245
## Automated
- swift test --package-path apps/macos --filter EmbeddedCabinetRecordingSettingsBridgeTests
- swift test --package-path apps/macos --filter MeetingDetectionPolicyTests
- swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests
- PYTHONPATH=apps/server/src pytest apps/server/tests/contract/test_settings_ui_contract.py
- node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
- python3 scripts/check_spec_kit_governance.py
## Synthetic UI / native bridge
Использовать только временный store и синтетические имена целей.
Проверить загрузку, 3 состояния, массовую операцию, сохранение при повторном чтении,
native notification, пустой список, ошибку записи, неподдерживаемый bridge,
timeout, клавиатуру и узкое окно. Проверить nonce/frame/source rejection в WebKit.
Проверить нативный build, маршруты общего входа и резервного окна.
## Production boundary
Не менять настройки установленного GRAF и не запускать реальную запись ради теста.
При выпуске отдельно проверить подписанное приложение, меню/⌘,/offline и реальный
detector/capture flow; текущая работа не публикует и не устанавливает сборку.
