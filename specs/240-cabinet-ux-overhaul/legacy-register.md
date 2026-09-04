# Реестр легаси-кандидатов

Проверка выполнена 4 сентября 2026 года по server-rendered cabinet и его
контрактным тестам. Поиск был ограничен presentation/UI-слоем и не являлся
основанием удалять доменную совместимость.

Команда поиска:

```sh
rg -n -i "legacy|deprecated|TODO|new-button|old-|unused|dead" \
  apps/server/src/twobrain_rec_server/cabinet \
  apps/server/tests/contract apps/server/tests/unit
```

| Кандидат | Где найден | Runtime-ссылки и evidence | Решение | Причина |
|---|---|---|---|---|
| `new-button` | Поиск по cabinet, contract и unit | Совпадений в рабочем UI-коде нет; отрицательные проверки уже есть в `test_cabinet_static_assets_contract.py` и `test_cabinet_web_shell.py` | Ничего не удалять | Удалять нечего; отрицательный контракт оставлен как защита от возврата старой разметки |
| `cabinet-mobile-noscript` | `components/sections.html`, ранние responsive-правила CSS | Разметка находится в `<noscript>` и отдельно покрывает браузер без JavaScript | Оставить | Это рабочий fallback, а не легаси: enhanced-навигация добавлена рядом и не заменяет его |
| `desktop-embedded` и rail-селекторы | `sections.html`, `cabinet.css`, `cabinet.js`, native/WebKit contract tests | `cabinet.js` определяет breakpoint и состояние rail; embedded shell используется отдельным маршрутом | Оставить | Это обязательный контракт встроенного macOS кабинета |
| `legacy_linked`, legacy media/result compatibility | `cabinet/access.py`, `rendering.py`, `view_models.py`, `egress.py` | Есть runtime-ветки, миграционные чтения и unit/contract tests | Оставить | Это не UI-легаси; удаление изменило бы совместимость данных и truth boundary |
| старые `TODO`/`deprecated` в тестах и API-проверках | `apps/server/tests/**` и связанный кабинетный код | Часть относится к проверке устаревших API/миграционных состояний, а не к видимым компонентам | Оставить | Нет доказательства, что элементы недостижимы; задача не разрешает чистить функциональные контракты |

Итог: доказанных безопасных к удалению presentation-only элементов не найдено.
В рамках этой фичи легаси-код не удалялся. Это намеренное решение: отсутствие
визуального использования имени или класса само по себе не доказывает отсутствие
runtime-ссылки.
