# Public search pages contract

| URL | H1 | Путь к продукту |
| --- | --- | --- |
| /transcription | Расшифровка аудио и видео в текст | /login?next=/meetings, /download |
| /meeting-minutes | Протокол встречи из записи: итоги, решения и задачи | /login?next=/meetings, /download |
| /record-without-bot | Запись и расшифровка звонков без бота | /download |

GET без auth → HTML 200 с существующими security headers, lang ru, unique title/description, self canonical от public_base_url без query, один h1. Без внешних ресурсов и новых JS, _analytics.html не подключается. Shared best-effort response применяется без изменения. Три пути в sitemap, обычные доступные ссылки между материалами и на главной в footer. Любой неизвестный путь → существующий 404.

Главная: прежний шаблон полностью совпадает после удаления трёх новых строк ссылок; head/hero/main/CTA и CSS/JS совпадают до и после. При footer links остальные строки footer сохраняются. Новые страницы имеют skip-link, visible focus, headings h1/h2, no horizontal overflow 320–1440, image alt и width/height; при недоступности изображения инструкция остаётся доступна. Нет фиксированных toolbar/overlay, формы/новые действия отсутствуют. Полезные действия — только переходы в действующий продукт.
