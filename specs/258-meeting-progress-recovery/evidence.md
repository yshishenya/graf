# F258 — исправления готовности встречи

Дата: 2026-09-08. Lane: **high-risk-product**. База:
`e81b412dff920cc29ed37de60be13dd8fc4d1c43`. Финальный source SHA и
авторитетный GitHub governance-fast фиксируются в PR; этот документ не является
разрешением на merge, релиз или production deploy.

## Причины и исправления

| Симптом | Подтверждённая причина | Изменение |
|---|---|---|
| Нет ожидаемых уведомлений F249 | Foreground подавлял реальные события; нет нативного события готовности; календарь был условием контекста | Проверенный native context независимо от календаря, отдельная категория готовности, актуальный владелец и версия события; F255 menu сохранён |
| Противоречивый экран итогов | Старое поле ProcessingResult расходилось со slot/attempt; partial и ожидание не учитывались согласованно | Общая безопасная проекция для HTML, processing API и desktop sync |
| Ложное отсутствие звука | Пустой default summary slot прекращал выбор пригодной audio revision | Пустой slot не скрывает звук; невалидный опубликованный pointer по-прежнему закрывает доступ, а не подменяет исходник |
| Нужно вручную обновлять страницу | Опрос обрывался после пяти минут/40 попыток или сети; reload после replaceState конфликтовал с WebKit navigation guard | Повторные GET с задержкой, fragment refresh выбранного формата, защита от старых ответов и сохранение проигрывателя/ввода |
| Задержка продолжения обработки | Media worker запрашивал всю строку processing_workflows без прав | SELECT только восьми необходимых полей; прежние RLS и запрет DML сохранены |

На исходной встрече read-only проверка подтвердила пригодность звука, наличие
расшифровки и опубликованных автоматических итогов. Сбой интерфейса не равен
утрате записи. Исходная встреча, её результаты и production не изменялись.
Частное содержимое и идентификаторы в evidence не включены.

## Проверки до коммита

- Исходный baseline: 68 PASS. Новые регрессии пустого slot сначала воспроизвели
  ошибку (4 FAIL на отсутствии audio), затем прошли с исправлением.
- Поведенческие Node-проверки исполняют реальные функции cabinet.js: ожидание
  сверх лимита, временный отказ сети, публикация между ответами, выбранный формат,
  partial, старые/отсоединённые страницы, отсутствие reload и вмешательства в player.
- Повторные группы server contract/integration выявляли устаревшие текстовые
  ожидания тестов; исправлена их согласованность с новым поведением, а не скрыты
  ошибки. Итоговый объединённый прогон: **1734 PASS**, 228.37 с, два предупреждения
  библиотек; весь server unit и перечисленные ниже contract/integration файлы.
  Команда: `bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/unit tests/integration/test_meeting_summary_slots.py tests/integration/test_recording_sync_processing.py tests/contract/test_cabinet_static_assets_contract.py tests/contract/test_summary_template_ui_contract.py tests/contract/test_processing_status_contract.py tests/contract/test_playback_status_contract.py -q --tb=short --show-capture=no`.
- Реальный PostgreSQL media role: **PASS**, собственный workflow доступен по
  метаданным, чужая scope пуста, полная ORM-строка и UPDATE запрещены.
- Полный runtime bootstrap: **SKIPPED**, disposable fixture уже создаёт роли.
  Пропуск не выдан за проверку idempotent bootstrap. Production grants не менялись.
- Spec Kit frozen doctor/governance: **PASS** с проектным specify 1.0.1 в
  изолированной среде. Глобальный specify 1.0.4 не изменялся.
- Первый прямой запуск всех server unit без PostgreSQL был ошибкой команды
  проверки; перезапущен через штатный disposable PostgreSQL runner. Он не
  является итоговым доказательством PASS.
- `ruff check` всех изменённых Python-файлов и новых progress/helper tests,
  `node --check cabinet.js`, `git diff --check`, `check-development-process.py`:
  **PASS**. Ошибочный вызов Ruff на JS/HTML заменён проверками соответствующих языков;
  его синтаксические сообщения не были дефектами продукта.
- Issue canon после ownership T012: **PASS**, 278 задач проверено. Issues
  не закрываются до полной приёмки; reviewer checklist не подменяет кодовые проверки.

## Review и converge

Независимый review требований принят 12/12, без изменения reviewer-owned
маркеров реализацией. Независимый нативный review выявил семь P1: ложный local
incident после успеха, потеря события между снимками/await, прерывание списка
чужим владельцем, смешение календарного и auth generation, единый claim для
ошибки/успеха, исторические recap, ложная готовность по review.available.
Исправления и последовательностные тесты рассматриваются отдельно от OS delivery.

Нативные focused tests после исправлений: **150 PASS** — Notifications 20,
RecapDelivery 11, UploadClient 50, UploadQueue 69. Новые тесты не создают системный
notification center: проверяют первый sync сразу ready, задержанный permission,
изменение snapshot/calendar во время ожидания/доставки/клика, logout, отказ доступа,
несколько владельцев, исторические события, failed→новый outcome, повтор события,
совместимое декодирование и ограниченное расхождение часов (-60…300 секунд).

Первый общий Swift прогон: 821 тест, одна ошибка старого текстового ожидания
подписи приглашения и один встроенный skip. Ожидание согласовано с «Записать
встречу?», countdown/auto-start/Stop проверки сохранены. Финальный прогон
`swift test --package-path apps/macos --skip 'DesktopCabinetWorkspaceTests|EmbeddedCabinetJavaScriptConfirmTests'`:
**821 тест: 820 PASS, 1 SKIPPED, 0 FAIL**, 38.214 с.
Группы `DesktopCabinetWorkspaceTests` и `EmbeddedCabinetJavaScriptConfirmTests`
исключены: они показывают окна вне единственного установленного GRAF Dev.
Встроенный skip относится к permission previews без `GRAF_PERMISSION_PREVIEW_DIR`.

Ponytail review: используются существующие polling, очередь sync, OS notification
center, scoped auth и PostgreSQL grants. Новых библиотек, очередей, таблиц
содержимого, обработчика capture или глобального notification framework нет.
Общая summary projection обслуживает три поверхности; защита источника не
дублируется в каждом UI. Legacy Impact: untouched; optional Codable поля
сохраняют чтение прежних локальных записей.

Converge: проверяемая область — 12 FR, 5 SC, 11 сценариев приёмки, 7 проектных
решений и 7 принципов конституции. Подтверждённый остающийся HIGH/partial gap —
установленная приёмка SC-003–005/US2. Добавлен T012 с ownership #6823; никаких
фиктивных PASS по экрану, Focus или настоящему баннеру. До закрытия T012 PR draft.

## Что не проверено и не выполнялось

- **BLOCKED — установленный GRAF Dev F258.** Стенд занимает F256, следом ожидает
  F257. Владелец F256 подтвердил занятость и схему 0090. Нет установки в обход
  harness, замены чужого стенда, отдельной копии приложения или downgrade.
- **NOT RUN — настоящий macOS banner/Focus/denied, ручной start/Stop и полный
  аппаратный путь** на F258. Автоматические permission/submission проверки не
  доказывают доставку баннера. Новая категория recap требует включения владельцем.
- **NOT RUN — runtime UI клавиатура, 200%, светлая/тёмная тема** на F258; это T012.
- **NOT RUN — внешний provider end-to-end.** В базовом Dev MediaScribe намеренно
  не настроен. Ни генерация, ни оплачиваемые запросы ради проверки не запускались.
- Full CI, release-full, CD dry-run/execute, merge, release, appcast, production
  install: **NOT APPLICABLE** к этой итерации по прямому указанию пользователя.

Krisp использован как наблюдаемый UX-ориентир: независимые Notes/Transcript/player,
категории уведомлений и понятный ход обработки. Доставка реальных Krisp баннеров
не измерялась. Извлечённые код/ресурсы, закрытые API и частные данные не использованы.
