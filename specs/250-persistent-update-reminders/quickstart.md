# Проверка Feature 250

## Автоматически

```sh
swift test --package-path apps/macos --filter 'AppUpdateControllerTests|EmbeddedCabinetUpdateBridgeTests|DesktopCalendarReminderTests|InstallerLifecycleEvidenceTests'
swift build --package-path apps/macos --product TwoBrainRecApp
sh -n apps/macos/Installer/Scripts/build-local-installer.sh
sh -n apps/macos/Scripts/validate-app-updates.sh
python3 scripts/check_spec_kit_governance.py
git diff --check
```

Проверить: восстановление новой версии; отказ от кэша при обновленном приложении, новой ОС/доверии или повреждении; skip/dismiss/error сохраняют сигнал; подтвержденный отзыв убирает его; загрузка и готовность видимы; каждое protectedWork блокирует relaunch и продолжение вызывается один раз. Builder/configuration = 14400; validator также допускает прежний 86400 для continuity.

## Синтетическая проверка интерфейса

Изолированно от /Applications/GRAF.app показать AppUpdateNotice и CalendarTrayView с синтетической версией. Проверить основной и узкий вид 360pt, keyboard/VoiceOver labels, версии/ошибку/отсрочку, отметку строки меню. Никаких реальных встреч, записи, публикации и установки. Если полноценный GUI недоступен, честно указать непроверенные сценарии; не считать unit-тесты доказательством живого обновления.

## Перед выпуском

GitHub governance-fast на точном PR SHA; затем один release-full на замороженном кандидате, notarization/stapling/Gatekeeper и update continuity. Проверить реальный переход предыдущая→новая версия, сохранение разрешений, отсутствие перезапуска при записи/финализации, отзыв из подписанной тестовой ленты, загрузку опубликованного appcast и архивов. Эти проверки требуют отдельного разрешенного выпуска.

Уточнение расписания: 4 часа — настроенный период, когда нет активной сессии Sparkle или уже загруженного отложенного обновления. В этих состояниях штатный планировщик может отложить следующую проверку. Старое продуктовое значение 86400 мигрирует в 14400 один раз; другие явно настроенные интервалы сохраняются. Флага включения автоматического поиска миграция не меняет. Интерфейса настройки периода в GRAF сейчас нет.
