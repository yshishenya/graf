# Контракт: скачивание аудио из меню встречи

## Доступный сценарий

- Given карточка встречи содержит доступный audio artifact и menu item `Скачать аудио…`.
- When пользователь нажимает menu item в браузере или embedded macOS WebView.
- Then стандартное действие ссылки запускает существующий server-mediated download; menu закрывается после передачи действия браузеру/WebKit.
- Then browser сохраняет attachment, а macOS открывает существующий save panel.
- Состояние доступности и egress аудио определяется валидированным playback M4A;
  устаревшая текстовая ревизия не блокирует доступный аудиоартефакт.

## Отмена и повтор

- Given save panel открыт.
- When пользователь отменяет сохранение.
- Then документ встречи не заменяется, bytes не считаются успешно сохранёнными, menu остаётся закрытым, повторное нажатие запускает новый download.

## Ошибка и отказ

- Given policy запрещает download, artifact отсутствует/устарел, сессия истекла или server отвечает ошибкой.
- When пользователь выбирает действие.
- Then существующие server/WebKit fail-closed policies остаются действующими: случайный private document или storage URL не открывается как UI navigation.

## Ограничения

- Не добавлять новый endpoint, JS `fetch`/Blob audio path, storage URL, client-side credential или изменение retention/deletion policy.
- В evidence допустимы только metadata-only результаты: тип сценария, HTTP/status class, policy decision и test outcome; не raw audio, transcript, filename/path с meeting content или signed URL.
