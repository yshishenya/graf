# Research: Восстановление скачивания аудио

## Наблюдения

1. `meeting_governance.html` уже рендерит аудио как обычную ссылку с `href` на server-mediated endpoint `/api/v1/cabinet/meetings/{meeting_id}/downloads/audio` и показывает её только при `audio_download_available`.
2. `cabinet.py` уже возвращает скачивание с `Content-Disposition: attachment`; policy проверяет доступ, lifecycle и наличие stored M4A до выдачи bytes.
3. macOS `DesktopCabinetRoutePolicy`, `DesktopCabinetNavigationResponsePolicy` и `WKDownloadDelegate` уже различают artifact download, проверяют same-origin/meeting и открывают системный `NSSavePanel`.
4. После упрощения меню действий общий `click`-обработчик синхронно выставляет `hidden` на родительском меню каждого `role="menuitem"`. Для ссылки это происходит внутри click event до стандартной навигации; embedded WebKit может отменить такой переход.

## Решение

Для `a[href]` сначала оставляем браузеру стандартное действие, а `closePanel(panel)` вызываем через `window.setTimeout(..., 0)`. Для кнопок меню сохраняем синхронное закрытие. Это исправляет общий shared handler и не требует нового endpoint, ручной загрузки через `fetch`, storage URL или native API.

## Отклонённые варианты

- Ручной `preventDefault` и программный `window.location`: дублирует навигационную политику и может обойти существующий WebKit download delegate.
- `fetch`/Blob в JS: перемещает audio bytes в UI слой и усложняет auth, память и диагностику.
- Изменение server endpoint или macOS policy: не устраняет отмену DOM default action и расширяет scope.
