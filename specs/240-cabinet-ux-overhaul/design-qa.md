# Design QA: UX/UI/IA GRAF — feature 240

Дата повторной проверки: 2026-09-04. Данные на снимках синтетические:
«Синтетический пользователь», «Синтетический проектный синк» и тестовые
календарные состояния. Реальные встречи, почта, аудио, расшифровки, токены и
секреты не использовались.

## Граница изменений

Изменены только визуальная оболочка кабинета и доступные имена мобильных ссылок:

- поздний CSS-каскад для общей типографики, поверхностей, границ, фокуса,
  плотности, списка встреч, detail/settings/state cards и responsive shell;
- enhanced mobile navigation для standalone browser;
- `aria-label`/`title` у мобильных ссылок для icon-only режима на 390 px;
- scoped contract assertion для сохранения no-JS fallback и standalone layout.

Не менялись маршруты, формы, HTTP-методы, CSRF, HTMX/data-hooks, IDs, обработчики
`cabinet.js`, запись, upload, processing, playback, deletion, sharing, export,
auth, privacy/deletion truth, схема и хранение.

## Findings до переработки

| Приоритет | Наблюдение | Evidence | Состояние после |
|---|---|---|---|
| P1 | На узком standalone-экране JS скрывал исходный rail, но не было отдельной рабочей навигации после исчезновения `<noscript>` | Рендер шаблона + browser snapshot 390 px | Закрыто: добавлена enhanced mobile nav |
| P1 | При `<=980px` существующее правило rail имело более высокую специфичность и сжимало main до 64 px | Реальный browser metric: main `64 px` при viewport `390 px` | Закрыто: standalone sidebar скрывается, main занимает одну колонку |
| P2 | В мобильной ленте все текстовые пункты не помещались одновременно | Browser metric: nav scroll width `457 px` при client width `390 px` | Закрыто: до 390 px icon-only с доступными именами |
| P2 | Список и карточки использовали разрозненные визуальные значения отступов/границ | Existing CSS audit и desktop screenshot | Закрыто общим поздним каскадом без изменения семантики |
| P3 | Неиспользуемые UI-кандидаты смешивались с рабочими миграционными compatibility-ветками | `legacy-register.md` | Закрыто классификацией; безопасного удаления не найдено |

## Повторная матрица

| Поверхность | Standalone | Embedded | Темы | Viewports | Результат |
|---|---:|---:|---|---|---|
| Meetings list, empty + calendar preview | browser harness | — | dark, light | 390, 1440 | PASS; навигация, toolbar, empty state читаемы |
| Meetings list shell | browser metrics | browser screenshot | dark | 320, 390, 768, 1024, 1440 | PASS; `document.scrollWidth == innerWidth` |
| Settings / calendar | browser screenshot | DOM/contract coverage | dark | 390, 1440 | PASS; section hierarchy, actions and switches readable |
| Detail, ready/partial/processing/failed/unavailable | contract/unit + source audit | contract/unit + source audit | dark/light tokens | 320–1440 rules | PASS по scoped contracts; fresh DB-backed browser screenshot blocked by missing local PostgreSQL URL |
| Auth, billing, shared, deletion states | contract/unit + source audit | contract/unit + source audit | dark/light tokens | responsive rules | PASS по no-change contracts; fresh DB-backed browser screenshot не заявляется |
| Keyboard/focus | browser snapshot and interaction smoke | existing contract coverage | dark | 390, 1440 | PASS: skip link, filter disclosure, upload dialog focus, profile popover |
| Reduced motion/transparency | CSS contract | CSS contract | обе темы | all | PASS: reduced motion/transparency guards retained |

Browser metric summary после исправления:

```text
320: document.scrollWidth=320, main=320, mobile-nav=flex, sidebar=none
390: document.scrollWidth=390, main=390, mobile-nav=flex, sidebar=none
768: document.scrollWidth=768, main=768, mobile-nav=flex, sidebar=none
1024: document.scrollWidth=1024, main=784, mobile-nav=none, sidebar=flex
1440: document.scrollWidth=1440, main=1200, mobile-nav=none, sidebar=flex
```

## Сравнение с observable Krisp

| Паттерн | GRAF после правки | Deliberate deviation |
|---|---|---|
| Устойчивый рабочий rail | Desktop rail сохранён; на узком standalone заменён компактной верхней навигацией | Mobile rail GRAF использует собственные ссылки и брендинг; private assets/code Krisp не копировались |
| Ясный главный столбец и компактный toolbar | Заголовок, поиск, фильтры, сортировка и upload выстроены в одной иерархии | Русские подписи длиннее; при 390 px часть навигации становится icon-only ради отсутствия клиппинга |
| Строки с заголовком, статусом, датой/длительностью | Существующие строки и статусы получили единые границы, hover/focus и плотность | Сохраняются GRAF-specific truth states и текстовые recovery actions |
| Detail с простой верхней иерархией и tabs | Общие tokens и поздние detail rules выравнивают header/tabs/panels | Playback, deletion и processing states остаются более подробными, потому что это продуктовая truth/accessibility граница |
| Компактные сгруппированные меню | Profile/settings cards получили спокойные поверхности и понятный focus | Недоступные действия остаются явно disabled, а не скрываются |

## Evidence

- [Meetings desktop dark](evidence/meetings-desktop-dark.png)
- [Meetings desktop light](evidence/meetings-desktop-light.png)
- [Meetings mobile 390 dark](evidence/meetings-mobile-dark.png)
- [Meetings embedded 1024 dark](evidence/meetings-embedded-1024-dark.png)
- [Settings desktop dark](evidence/settings-desktop-dark.png)
- [Settings mobile 390 dark](evidence/settings-mobile-dark.png)

Скриншоты сняты из локального `calendar_visual_ui_harness` с production
шаблонами и локальным `cabinet.css`, без реального сервера/аккаунта.

## Остаточные ограничения

- P2: нет свежего DB-backed browser screenshot для detail/auth/billing/shared;
  scoped contract и source-level проверки выполнены, но это не подменяет живой
  PostgreSQL smoke.
- P2: полноценный `infra/scripts/ci-local.sh --fast` и PostgreSQL integration
  lane нужно запускать в окружении с Docker/PostgreSQL и проверять на точном SHA PR.
- P3: reviewer-owned `checklists/ux.md` намеренно не отмечался автоматически.
- P3: независимые read-only задачи были запущены, но их client IDs не появились
  в доступном списке задач; выводы не использованы как доказательство и
  перепроверены локально.

## Вывод

После правки крупные наблюдаемые проблемы IA/responsive устранены, контент не
клиппится на проверенных ширинах, а standalone и embedded сохраняют разные
ожидаемые оболочки. Функциональные semantics не менялись.
