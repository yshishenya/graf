# F255: проверка реализации

Статус: это план проверки, не отчёт об успешно выполненных командах. Данные тестовые; реальные аудио/тексты встреч/секреты в evidence запрещены.

## Подготовка

Работать из корня текущего worktree. Убедиться в feature255 и branch, завершённых reviewer-owned checklists, чистом analyze и привязке tasks к GitHub. Зафиксировать проверяемый SHA и реальные состояния PR из inventory.md. Нужны Xcode 26 SDK, ресурсы существующего проекта и машины/окружения macOS 14.5 и 26. Только запуск на 26 не закрывает старую ОС.

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
python3 scripts/check_spec_kit_governance.py
```

## Профильные автоматические проверки

Из корня, используя существующее Python окружение сервера (при отсутствии локального .venv можно указать существующий интерпретатор, не устанавливать глобальные пакеты):

```sh
PYTHONPATH=apps/server/src apps/server/.venv/bin/python -m pytest \
  apps/server/tests/unit/test_cabinet_navigation_model.py \
  apps/server/tests/unit/test_cabinet_web_shell.py \
  apps/server/tests/unit/test_cabinet_template_sections.py \
  apps/server/tests/contract/test_cabinet_shell_response_contract.py
swift test --package-path apps/macos --filter 'DesktopCabinet|EmbeddedCabinet|DesktopMeetingShellWebViewBoundary'
swift build --package-path apps/macos --product TwoBrainRecApp
```

Добавленные в T003 проверки bridge входят в этот Swift filter. Тесты server shell обновляются для удаления заглушек и форм/передачи владения. Существующие проверки, фиксирующие старые заглушки F201, меняются только с явной ссылкой на новый контракт. После изменения соответствующих путей добавить их существующие профильные suites, не запускать full CI на каждой правке.

## Ранняя нативная проверка T002

Использовать только GRAF Dev по `docs/agent-guidance/local-development.md` и `development-process.md`: чистая проверенная ревизия → `dev-harness.sh build` → `promote` под блокировкой → `status` → `smoke`. Сборщик `apps/macos/Scripts/build-dev-app.sh` сохраняет bundle ID `pro.2brain.graf.dev`, подпись и точный SHA; установленная копия одна — `/Applications/GRAF Dev.app`. Перед продвижением проверить текущий манифест и владельца стенда. Не запускать install напрямую при работающем приложении. Сохранить версию ОС, SDK, SHA и обезличенные снимки. Приложение с системной sidebar должно показывать реальный материал, titlebar controls и один WebView без перезагрузки на resize/theme. Debug app не является public release. Если композиция не подтверждена, остановить интеграцию и исправить план; скриншот HTML недостаточен.

## Матрица приёмки T012

1. macOS 14.5 matte и macOS 26 system glass; light/dark/system, изменение System во время работы, Reduce Transparency/Motion, Increase Contrast, неактивное окно. Проверить контраст в устойчивых состояниях, стекло на светлом и тёмном содержимом.
2. Новый/новый, новый/старый, старый/новый клиент/сервер; неизвестная версия, неверный payload, iframe/foreign origin, старое поколение, logout/login и WebContent termination. Ожидания — contracts/interface.md: одна навигация, никаких прежних данных профиля, формы и CSRF сохраняются.
3. Каждый путь journeys.md, начиная с указанного состояния. Отдельно мышь и клавиатура/VoiceOver, Escape/возврат фокуса, deep link, назад/вперёд, refresh и rail/полное скрытие.
4. 1040×680 с правой панелью и 200% масштабом; веб 320/390/768/1024/1440 и no-JS. Штатные длинные подписи, имя, меню, фокус не обрезаны. Список/детали/общие встречи/настройки/календари/оплата/вход и admin shared-CSS consumers.
5. Готовые/нет разрешений, активная запись, сохранение/повтор отправки, локальный режим, сеть недоступна. Только синтетический звук для проверки; Stop одним действием, прежние три состояния автозаписи/таймер/защита quit сохранены. Смена материала/темы не меняет capture session, WebView identity и историю.
6. Повторить затронутые сценарии F245–F253 на фактически объединённых ревизиях; отдельно отметить ещё не объединённые зависимости. Не выдавать fixture 200 за реальные auth/payment/save.

В `validation/acceptance.md` записать версии, SHA, окружение, фактические шаги/результаты, контраст, снимки и открытые пункты. В `validation/cleanup.md` — поиск всех потребителей, обоснование каждого удаления и выполненная проверка. Незаполненная строка — открытый gate, а не успех.

## Закрытие и выпуск

T013: converge, review простоты и требований, changelog fragment. Получить явное разрешение владельца на implementation commit после validation; PR body на финальном SHA и GitHub governance-fast. Локальный fast только диагностический fallback согласно release-and-validation.md. Открытые custom checklists не закрываются реализацией.

T014: approved frozen candidate → один authoritative Full CI → CD dry-run → approved deployment. Для macOS обязательно Developer ID, notarization/stapling, Gatekeeper, Sparkle signature и live appcast по docs/agent-guidance/macos-notarization.md. Русские release notes, CalVer, SHA и post-deploy smoke. Без этих доказательств полный цикл не закрыт; no-deploy до соответствующего разрешения/gates.
