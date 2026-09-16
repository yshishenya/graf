# Контракт политики страниц и событий

**Фича**: `266-yandex-metrica-webvisor`

## Политика поверхностей

Источником истины является `product_analytics/page_inventory.py`. Каждый класс
явно содержит статусы `page_view_allowed`, `safe_event_allowed`,
`yandex_webvisor_allowed`, `click_map_allowed`, `scroll_map_allowed` и
`form_analytics_allowed`. Неизвестный класс получает `future_browser_page` и
закрывается.

| Класс | Безопасные метаданные | Яндекс/Webvisor/карты | Особое ограничение |
|---|---|---|---|
| `public_landing`, `public_download` | публичные просмотры и цели | только после соответствующего opt-in | без произвольного DOM и форм |
| `cabinet_home`, `settings`, `onboarding`, `recording_list`, `upload` | ограниченный продуктовый путь | запрещены | без названий встреч, файлов и путей |
| `meeting_result_detail`, `playback`, `deletion` | по умолчанию запрещены | запрещены | без аудио, расшифровки и итогов |
| `login_signup`, `auth_callback` | запрещены | запрещены | без email, кодов, cookies и токенов |
| финансовые и referral-классы | запрещены | запрещены | без сумм, счетов, скидок и токенов |
| `legal`, `admin`, `embedded_desktop_webview`, `error_pages`, `future_browser_page` | только явно разрешённые безопасные метаданные | запрещены | новый класс закрыт по умолчанию |

## Публичный каталог

Разрешённые имена:

```text
public_landing_viewed
public_landing_section_seen
public_landing_cta_clicked
public_download_viewed
public_installer_download_clicked
public_login_intent_clicked
public_product_tab_selected
public_pricing_cycle_selected
public_faq_opened
```

Стабильные значения берутся только из allowlist `public_analytics.py`:
`section_id`, `cta_location`, `target_kind`, `product_tab`, `pricing_cycle` и
`faq_item`. Полный URL, query, hash, заголовок, текст DOM и значение формы не
являются полями события.

## Внутренние действия

Внутренний браузерный сбор передаёт только существующие перечислимые поля:
`page_class`, `path_class`, `event_type`, `tag_name`, безопасные `role` и
утверждённые `analytics_action`/`analytics_target`, если они принадлежат
серверному каталогу. Клиентский allowlist не заменяет серверную проверку.

Запрещены email, телефон, имена, исходные user/workspace/account/meeting/device
ID, названия и ссылки встреч, файлы и пути, токены, cookies, платёжные сведения,
произвольный текст, URL, аудио и расшифровки. Идентичность — только
`graf_pseudo_*` или безопасный анонимный маркер.

## Достоверность сигналов

- `public_installer_download_clicked` фиксирует только намерение или начало
  загрузки.
- Событие успешной установки не создаётся браузерным контроллером.
- Повторная инициализация и повторные переходы не должны дублировать одну
  стабильную цель.
- Недоступность провайдера не создаёт событие ошибки с содержимым запроса.
