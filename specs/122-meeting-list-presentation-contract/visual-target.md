# Visual Target: Meeting List Presentation Contract

## Source And Approval Boundary

Этот target заменяет внешний Figma-прототип по явному решению пользователя. Он основан на:

- актуальном установленном GRAF и его accessibility tree;
- предоставленных пользователем состояниях GRAF и Krisp;
- clean-room выводах из feature 104;
- текущих server-owned meeting-list контрактах после calendar и playback фич.

Реальные скриншоты содержат приватные названия и account context, поэтому остаются локальным исследовательским входом и не добавляются в git. После реализации target проверяется на синтетических данных сопоставимыми before/after screenshots.

Krisp используется только как ориентир по плотности, иерархии, progressive disclosure и отделению записи от списка. Target не переносит его тексты, icons, palette, композицию, folders/tags/star/save-later или proprietary behavior.

## Element Inventory And Decisions

| Текущий элемент | Решение | Целевая роль |
|---|---|---|
| `Мои встречи` | оставить | единственный заголовок страницы |
| `Недавно обновлённые` рядом с заголовком | убрать | текущий выбор живёт только в sort-control |
| Поиск | оставить | единственная постоянная точка поиска |
| `Фильтры` | оставить и упростить | раскрытие по намерению; число активных фильтров видно в trigger |
| `Сортировка` | упростить | trigger показывает текущий выбор, по умолчанию `Сначала новые` |
| `Сбросить` | оставить контекстно | видно только при query или активных фильтрах |
| `Загрузить` | уточнить | постоянное реальное действие `Загрузить запись` |
| `Записи встреч` | убрать | повторяет заголовок страницы |
| Количество результатов | добавить контекстно | только `Найдено: N` после поиска/фильтрации |
| Иконка источника | оставить тихой | помогает отличить capture/upload без отдельной подписи |
| Checkbox | показывать по намерению | hover, focus, selection; постоянный доступ на non-hover surface |
| Название | оставить главным | основное действие открывает встречу |
| Длительность | оставить | компактная неизменная метаинформация |
| `Готово` | убрать из обычной строки | готовность следует из доступности результата |
| `Аудио готово` | убрать | штатная доступность аудио не является исключением |
| `Без календарного контекста` | убрать | нормальный fallback, не ошибка |
| `Из календаря` / `Выбрано вами` | убрать из строки | provenance доступен в деталях |
| `Нужно выбрать встречу` | объединить | статус `Нужен выбор` плюс отдельное действие `Выбрать встречу` |
| Проблемные/processing подписи | объединить | один статус по каноническому приоритету |
| Удаление строки | оставить контекстно | прямая кнопка при hover/focus; существующее подтверждение |
| Правая дата | уточнить | дата и время встречи; при updated-sort явно помечается обновление |
| Permanent batch toolbar | не показывать | появляется после первого выбора |
| Delete feedback после списка | перенести | видимая live-region над списком |
| Пустой upcoming | не добавлять | только авторитетная будущая календарная проекция в отдельной фиче |
| Native capture rail | оставить без изменений | отдельная авторитетная запись/Stop поверхность |

## Toolbar Copy

| Намерение | Точная подпись |
|---|---|
| Заголовок | `Мои встречи` |
| Search placeholder и accessible name | `Поиск встреч` |
| Filter trigger без условий | `Фильтры` |
| Filter trigger с условиями | `Фильтры: N` |
| Filter reset | `Сбросить` |
| Upload | `Загрузить запись` |
| Refined result count | `Найдено: N` |

### Filter Vocabulary

| Группа | Варианты |
|---|---|
| Состояние | `Все состояния`, `Готовые`, `В обработке`, `С ограничениями`, `Требуют внимания` |
| Доступ | `Любой доступ`, `Мои`, `Команда`, `Со мной поделились` |

### Sort Vocabulary

| Значение | Подпись |
|---|---|
| meeting date descending | `Сначала новые` |
| meeting date ascending | `Сначала старые` |
| last meaningful update | `Недавно обновлённые` |
| oldest meaningful update | `Давно обновлённые` |
| duration ascending | `Сначала короткие` |
| duration descending | `Сначала длинные` |
| title ascending | `По названию` |

`Сначала новые` является default. При сортировке по обновлению правая подпись имеет форму `Обновлено 21 июл, 19:22` или `Без даты`, если реального времени обновления нет; во всех остальных режимах она описывает саму встречу: `21 июл, 19:22` либо `Без даты`.

## Row Content Contract

| Зона | Обычная готовая строка | Исключительная строка | Hover / focus / selection |
|---|---|---|---|
| Intent | тихая source-icon | та же source-icon | checkbox становится доступен без сдвига content |
| Primary content | title + duration | title + duration | основное действие остаётся открыть встречу |
| Secondary content | отсутствует | один приоритетный status; отдельное действие только если требуется | не меняет высоту из-за появления controls |
| Context action | скрыто | скрыто | `Удалить встречу` |
| Time | meeting date/time | meeting date/time | остаётся на месте |

Правила названия:

1. Осмысленное пользовательское или календарное название сохраняется.
2. Распознанный generated capture title отображается как `Запись`.
3. Техническое имя manual upload без пользовательского смысла отображается как `Загруженная запись`.
4. Дата не дублируется в нейтральном visible title.
5. Accessible name добавляет дату/время для уникальности: например, `Открыть встречу Запись, 21 июля, 19:22`.
6. Длительность использует существующий русский формат: `27 с`, `14 мин`, `1 ч 14 мин`.

## One-Status Matrix

Порядок сверху вниз является полным приоритетом. Первая истинная строка определяет единственный compact status.

| Приоритет | Условие для пользователя | Compact status | Следующее действие |
|---:|---|---|---|
| 1 | удаление продолжается | `Удаляется` | отсутствует |
| 2 | отправка завершилась ошибкой/отменой/истечением или результат не удалось подготовить | `Не удалось обработать` | существующий recovery path |
| 3 | требуется выбрать календарное событие | `Нужен выбор` | `Выбрать встречу` |
| 4 | локальная копия ещё не принята сервером | `Сохранено на Mac` | существующий custody recovery |
| 5 | активная отправка с достоверным total | `Отправляем N%` | отсутствует |
| 6 | активная отправка без достоверного total | `Отправляем` | отсутствует |
| 7 | результат обрабатывается | `Обрабатывается` | отсутствует |
| 8 | материалы доступны, аудио временно готовится | `Аудио готовится` | открыть доступные материалы |
| 9 | готовый результат не имеет доступного аудио | `Без аудио` | открыть детали ограничения |
| 10 | другой готовый частичный результат | `Готово с ограничениями` | открыть доступные материалы |
| 11 | результат штатно готов | статус отсутствует | открыть встречу |

Не являются compact status: `Аудио готово`, `Из календаря`, `Выбрано вами`, `Без календарного контекста`, `Контекст убран вами`. Эти факты остаются доступны там, где объясняют provenance или recovery, но не конкурируют с результатом в списке.

## Interaction Contract

| Намерение | Pointer | Keyboard | VoiceOver result |
|---|---|---|---|
| Открыть | click на читаемую область/title | `Enter` на строке или основном действии | `Открыть встречу …` |
| Выбрать | checkbox | `Space` на selectable row/checkbox | `Выбрать встречу …` / selected state |
| Удалить одну | contextual delete | focus + activate | `Удалить встречу …` |
| Выбрать все видимые | batch control | focus + activate | `Выбрать все видимые встречи` |
| Снять выбор | batch control | focus + activate | `Снять выбор` |
| Удалить выбранные | batch control + confirmation | focus + activate | `Удалить выбранные встречи` |

Открытие никогда не меняет selection. Selection никогда не открывает встречу. Contextual controls не являются единственным путём на touch/non-hover поверхности.

### Batch Copy

| Элемент | Подпись |
|---|---|
| Count | `Выбрано: N` |
| Select all | `Выбрать все` |
| Clear | `Снять выбор` |
| Destructive action | `Удалить` |

## Empty, Loading And Recovery Copy

| Состояние | Заголовок | Пояснение | Действие в области списка |
|---|---|---|---|
| Первый пустой список | `Пока нет встреч` | `Начните запись или загрузите готовый файл.` | отсутствует; используются существующие controls |
| Search/filter no results | `Ничего не найдено` | `Измените запрос или сбросьте фильтры.` | `Сбросить` |
| Loading | accessible status `Загружаем встречи…` | визуально сохраняется геометрия строк | отсутствует |
| Нет сети | `Нет подключения` | `Запись на Mac продолжает работать.` | `Повторить` |
| Кабинет временно недоступен | `Не удалось загрузить встречи` | `Попробуйте ещё раз.` | `Повторить` |
| Сессия завершилась | `Нужно войти снова` | `Сессия завершилась.` | `Войти` |
| Доступ отозван | `Встреча больше недоступна` | приватные metadata не повторяются | вернуться к списку |
| Deletion accepted | status без заголовка | `Запись удалена из списка. Очистка данных GRAF продолжается.` | отсутствует |
| Partial batch delete failure | status/error | `Не удалось удалить N записей. Попробуйте ещё раз.` | `Повторить` в подтверждённом существующем flow |

Status и result-count announcements не перемещают focus. После исчезновения focused row фокус возвращается к следующей доступной строке, предыдущей строке либо заголовку списка в этом порядке.

## Geometry And Responsive Target

| Поверхность | Типовое окно `1280×760` | Минимальное окно `1040×680` |
|---|---|---|
| Meeting workspace | спокойные outer gutters и гибкая content column | уменьшенные gutters; без horizontal scroll |
| Toolbar | search, labeled filters, current sort, upload в одной hierarchy | labels могут компактно сворачиваться только при сохранении exact accessible names |
| Ready row | 48 px, одна content line | 48 px; длинный title обрезается без потери accessible name |
| Exceptional row | до 60 px для status/action line | status остаётся видимым; date и destructive action не перекрываются |
| Context targets | не меньше 32×32 CSS px | тот же минимум |
| Native rail | не затрагивается | остаётся видимым и независимым |

Контраст обычного текста и controls должен проходить применимый AA target; state не полагается только на цвет. Focus ring остаётся различимым. Необязательное движение отключается при Reduce Motion.

## Evidence Matrix

До implementation closeout нужны синтетические before/after screenshots и accessibility evidence для:

1. ready list;
2. one-status priority collisions;
3. upload measured/unmeasured;
4. processing;
5. calendar choice;
6. audio preparing/unavailable;
7. failure/recovery;
8. hover/focus;
9. single and multi-selection;
10. deletion accepted/partial failure;
11. first empty list;
12. search/filter no results;
13. loading;
14. offline/unavailable/session;
15. long title and no-date rows;
16. minimum window, keyboard, VoiceOver, increased contrast and Reduce Motion.

Layout-sensitive states are captured at both target sizes. Evidence contains no real meeting names, participants, transcript text, audio, account identifiers, credentials, tokens, signed URLs or live local paths.

## Implementation Boundary

Target определяет user-facing hierarchy, exact copy, state priority, interaction semantics, responsive behavior and evidence. Он не разрешает новые routes, persistence, lifecycle states, integrations, meeting-detail changes, rename functionality, component framework, external prototype dependency или Krisp-like organizational features.
