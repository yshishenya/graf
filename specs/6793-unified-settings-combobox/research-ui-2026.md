# Исследование списков настроек: 2026-09-12

## Основание решения
Пользовательские снимки текущего GRAF показывают четыре конкретных недостатка: NSPopover выглядит как округлая подсказка с указателем; короткое меню обрезает третье правило; каталог растянут на всё окно; синяя рамка вложена в другую рамку поля. Исправление относится к раскрытым спискам, а не ко всем карточкам настроек.

Это исследование действующих первичных источников, а не подборка «трендов». Дата проверки не заменяет дату публикации. Примеры продуктов изучены по официальной документации и опубликованным изображениям, не путём запуска чужих частных аккаунтов. Никакие сторонние активы не включаются в GRAF.

## Что действительно относится к 2026 году
- [Apple WWDC26: Rediscover the HTML select element](https://developer.apple.com/videos/play/wwdc2026/315/): прочитан transcript. 0:38 — customizable select в Safari27/Chrome135; 4:28 — сохранять различимость выбранного; 5:46 — избегать повторного объявления декоративных изображений; 7:46 — fallback; 8:40 — Safari27 preview/beta. Используется appearance:base-select, ::picker(select), ::checkmark. Это настройка внешнего вида HTML select, а не автоматически редактируемый поиск.
- [MDN Customizable select](https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Forms/Customizable_select): last modified 2026-08-13, Limited availability. [Текущий BCD](https://raw.githubusercontent.com/mdn/browser-compat-data/main/css/properties/appearance.json): Chrome135, Safari27; Firefox149 за флагом. Минимальная macOS14 GRAF не даёт общей гарантии поддержки в WKWebView. Поэтому это направление будущего улучшения простых select, не основание менять текущий рабочий контракт.
- [VS Code Settings](https://code.visualstudio.com/docs/configure/settings): текущая страница отображает 02/04/2026, точный формат даты не утверждаем. Официальный снимок показывает поиск и обычные строки настроек, а не отдельные капсулы каждого значения.

- [Apple WWDC26 Design intuitive search experiences](https://developer.apple.com/videos/play/wwdc2026/292/?time=536), datePublished 2026-06-08: Freeform фильтрует доски непосредственно под полем; размещение поиска сообщает область действия. [Principles of great design](https://developer.apple.com/videos/play/wwdc2026/250/?time=732), та же дата: ясность создаётся порядком, отступами и контрастом. [Modernize your AppKit app](https://developer.apple.com/videos/play/wwdc2026/289/?time=351), та же дата: клавиатурный ввод важен для скорости и доступности. Даты и цитаты независимо сверены с официальными метаданными/transcripts; показанные Freeform/Settings/Stocks не запускались локально.

## Устойчивые рекомендации, проверенные сейчас
| Источник | Подтверждённый принцип | Применение и ограничение |
|---|---|---|
| [WAI-ARIA Combobox pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/) | Editable combobox может искать только среди допустимых значений; focus и selection различаются | Query не сохраняется; Escape отменяет, Enter подтверждает; один фокус |
| [React Aria ComboBox](https://react-aria.adobe.com/ComboBox) | ComboBox выбирает значение; Autocomplete фильтрует коллекцию | Поле приложений GRAF остаётся фильтром строк; popup показывает доступные названия по прямому запросу пользователя |
| [Adobe Spectrum Combo box](https://spectrum.adobe.com/page/combo-box/) | Большие каталоги требуют поиска; для fewer than6 предлагаются radio. Открытие при фокусе — отдельный режим | Не выдаём одинаковый editable control для3 правил за общую норму. Здесь он сохраняется по прямому требованию пользователя |
| [Carbon dropdown usage](https://carbondesignsystem.com/components/dropdown/usage/) | Плотность и размер зависят от контекста; длинные подписи требуют доступности | Единый ритм строк, ограниченная ширина, перенос; исходная web страница403, исследован официальный MDX |
| [Apple combo boxes](https://developer.apple.com/design/human-interface-guidelines/combo-boxes) | Ввод и выбор существуют в одном контроле | Не возвращаем отдельный поиск над select; геометрия отдельно проверяется в AppKit |
| [Vercel Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md) | Видимый клавиатурный фокус, accessible name, устойчивый layout | Проверка общего CSS и длинных/пустых состояний; это рекомендации web, не инструкция рисовать native macOS |

## Сравнение приложений
| Продукт и первичный источник | Что проверено | Что применимо к GRAF |
|---|---|---|
| [VS Code](https://code.visualstudio.com/docs/configure/settings) | Официальный screenshot: поиск сверху, подписи/описания и поля в строках | Плоская структура и выравнивание, без копирования глобальной навигации |
| [Raycast Settings](https://manual.raycast.com/settings), [Search Bar](https://manual.raycast.com/search-bar) | Просмотрены официальные Applications/Shortcuts screenshots. Документация per-app: search field → inline alias/hotkey/checkbox. Скруглённые группы действительно присутствуют | Редактировать свойство рядом с приложением; это не доказательство универсального отказа от скруглений |
| [Linear Filters](https://linear.app/docs/filters) | Официальный screenshot с капсулами нескольких условий; поиск вариантов | Капсулы имеют смысл для независимых условий, не для единственного правила записи |
| [Notion database properties](https://www.notion.com/help/database-properties) | Текст документации: редактирование Select/Multi-select в ячейке, создание цветных тегов | Редактирование на месте применимо; создание произвольных тегов и случайные цвета не соответствуют закрытому набору GRAF |

У Raycast/Linear/Notion дата публикации и дата снимков не указана; проверены 2026-09-12. Их нельзя называть новыми интерфейсами, выпущенными именно в2026. Официальные опубликованные изображения VS Code/Raycast/Linear просмотрены; внешний вид Notion не выводится из текста.

## Выбор реализации
Сохранить field/table/coordinator и подтверждённую границу сохранения; заменить NSPopover на публичный borderless nonactivating child NSPanel. NSTableView получает .plain и явные insets; высота опирается на фактические строки, а не сумму предполагаемых32. Текущий .automatic способен давать inset presentation — это объясняет симптом обрезания, но окончательное доказательство дают измерения viewport/rect(ofRow:) нового кандидата.

Размеры/состояния определены в [compact-dropdown.md](contracts/compact-dropdown.md). Радиус6, ширина каталога380, одна рамка фокуса — решение GRAF по замечаниям пользователя; источники не предписывают эти числа. Три правила видны целиком, длинный каталог прокручивается, выбранное обозначается галочкой, навигация отдельным выделением. Существующие API/хранение/правила записи не меняются.

Отклонены: приватное удаление стрелки NSPopover (хрупко); новая UI библиотека (не нужна); повтор NSComboBox (установленная проверка уже выявила ошибки подтверждения); повсеместный base-select (поддержка WKWebView и отсутствие редактируемого фильтра); перенос цветных тегов Notion (другая модель данных); замена коротких полей radio (противоречит исходному требованию единого поля).

Пределы: исследование и HTML макет не доказывают AppKit event loop, VoiceOver speech или вид установленного GRAF. PR остаётся draft до новой реализации и приёмки T010/T011.
