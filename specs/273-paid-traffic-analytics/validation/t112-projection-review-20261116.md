# T112 — независимый обзор общей проекции, 16.11.2026

Проверяющий: `/root/public_counter_readiness_review`.
Полоса: `high-risk-product`, следующий неполный шаг T112.
Проверенная основа: `f2e06822db8df2cd60de5c8a06e2d30f0603ec66` плюс четыре
рабочих файла с точными SHA-256 ниже; эти изменения ещё не часть HEAD.

## Решение

**PASS узкого шага общей текстовой проекции и её source binding;
P1=0, P2=0.** Блокирующих ошибок в проверенном изменении не найдено.
Ранее принятые требования124/0 и D1–D7 этим обзором не заменяются.
Полный T112/T113, рабочее измерение и выпуск не приняты.

## Что проверено

Прочитаны целиком текущий `result_visibility.py` и оба projection test-файла,
полный diff renderer и его затронутые функции, применимые §§2–6 договора,
связанные view-model/query/model участки выбора источника и исходного текста.

- `rendered_transcript_rows()` сохраняет прежний выбор speaker turns либо
  segments только при available/search_enabled. Renderer и аналитическая
  проекция вызывают одну функцию, без второго извлечения transcript.
- Порядок обычных outcome sections, доступность item, порядок частей
  протокола и извлечение `text`/`task` вынесены в общие функции. Renderer
  использует эти же функции. Порядок templates, fallback неизвестного
  template, объединение open questions/next steps и порядок topics/notes
  соответствуют прежнему коду.
- Кандидат создаётся отдельно для каждого непустого тела turn/item/строки
  протокола. Strip применяется только к решению о пустоте: исходный текст
  не переписывается. Heading, template name, author/due-date metadata,
  timestamp/source controls, placeholder и сообщения пустого состояния не
  входят в кандидаты. Полные протоколы не дублируются обычными categories.
- Закрытые details могут содержать кандидаты, но сам кандидат не доказывает
  показ. Будущий observer обязан проверять каждый соответствующий текстовый
  элемент, его ancestors/connectedness/размер/viewport/focus и native условия;
  видимость контейнера не достаточна.
- Digest строится из UTF-8 canonical JSON с sort_keys и compact separators:
  тип, собственные result ID/version, outcome ID при наличии и упорядоченные
  исходные непустые тексты. Тип ограничен прежним каталогом. Смена версии,
  результата, outcome или порядка текста меняет digest. Raw canonical JSON
  и тексты остаются локальными временными объектами, не возвращаются в
  binding/proof/event и не сохраняются в durable хранилище.
- `load_result_view_bindings()` документирует обязательный свежий
  authorized `get_cabinet_meeting_review()` от вызывающего кода. Защитные
  условия дополнительно требуют owner/full-view projection, revision,
  session UUID и известный допустимый период.
- Источник transcript определяется только по фактически выбранным rows:
  должен быть ровно один ненулевой processing result ID. Смешанное или
  неизвестное происхождение не получает fallback. Далее проверяется прежним
  source loader точная meeting/workspace/owner/revision/result lineage.
- Источник outcome читается по конкретному `review.template.outcome_set_id`,
  matching workspace/meeting/revision, active lifecycle и available/partial
  status. Используются собственные processing result ID и deletion epoch
  этого outcome; epoch обязан совпасть с проверенным source. Нет latest
  lookup, замены outcome на transcript или выбора неподтверждённого нового
  вывода вместо закреплённого. Нужен `source_basis="stored_output"`.
- На каждое тело создаётся отдельный frozen binding с собственным source,
  session/device, типом/digest/outcome ID. В нём нет текста и иных private
  payload. Существующий source loader и HMAC не ослаблены.

## Сохранение отображения и тестовое покрытие

Diff `rendering.py` меняет места вызова общих selectors. HTML templates,
экранирование текста, labels, содержимое, классы, атрибуты и порядок
сформированных элементов в затронутых функциях не изменены. Не добавлены
proof attributes, observer, POST или production caller загрузчика binding.
Поиск использования в `apps/server/src` не нашёл рабочего подключения новых
binding/digest функций вне самого модуля.

Unit-профиль проверяет turns/segments, unavailable/no-search, пустое тело,
недоступные items, metadata, протокол/порядок, уникальность block keys и
canonical digest/изменения собственных версий. Contract-профиль проверяет
закреплённые итоги своей старой версии рядом с новой расшифровкой, в том
числе через настоящий authorized query и summary slot с более новым
невыбранным outcome. Отдельные negative случаи покрывают чужие/missing
meeting/workspace/revision/outcome, inactive/status/epoch/source result,
нехранимый вывод, чужого owner/shared projection/неизвестный период и
неверное transcript происхождение. Ledger остаётся пустым.

Исполнитель сообщил GREEN161 unit/render и24/24 совпавших до/после HTML
хешей. В этом независимом проходе эти команды повторно не запускались;
session11054 не опрашивалась, итог ещё выполнявшегося общего280-профиля
не заявляется. Собственное заключение основано на чтении кода, diff,
зависимостей и сверке четырёх текущих хешей. Журналы и результаты полного
профиля должен приложить исполнитель отдельно к этому срезу.

## Обязательные пределы

Функция binding не перепроверяет самостоятельно свежие principal/session/
membership/access и выбор текущего authorized outcome под locks. Переданный
review — доверенная серверная проекция, не JSON клиента и не доказательство
свежести само по себе. Использование stale/самостоятельно собранного review
как рабочего разрешения будущим caller нарушило бы договор. При render и
при принятии показа нужно использовать одну свежую разрешённую проекцию и
повторить проверки после обязательных fences.

Для полного результата остаются render proof/private-no-store, browser/native
видимость каждого тела, renewal без счёта, защищённый bounded POST, свежие
identity/source/deletion/основание/отзыв/readiness/resource gates и атомарная
пара через общую T113. DB/browser/Swift/concurrency/failure матрица, converge
и точные выпускные проверки не заменены тестами этого шага. В проверенном
коде нет нового egress, записи milestone или обхода recovery-unverified.

Изменён только настоящий отчёт. Код, требования, plan/tasks/checklists,
Git/GitHub, runtime и внешние сообщения проверяющий не менял.

## Точные SHA-256

| Проверенный рабочий файл | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/result_visibility.py` | `bf7e12055b7db289cd9224a32e41beba7a0359df73de106cdc70705471795fa9` |
| `apps/server/src/twobrain_rec_server/cabinet/rendering.py` | `f2c8631f029d781fba39b2181dfb11d7ff056af6240901391e72edcd78568f74` |
| `apps/server/tests/unit/test_result_view_projection.py` | `eaa548280892b5b226ba1f7fad3a202e59e1c7b7f2067d4d15c99861a0503baa` |
| `apps/server/tests/contract/test_result_view_projection.py` | `9926f1c3e0941ee961c63663f80b245c06c3771a2c7a3df3a9c2392a4ff2b15c` |
