# A7 fixture requirements review

Owner: independent reviewer. FR-042 / SC-020, T064–T066. Implementation may not check items.

- [x] CHK001 Is the exact allowlist and all six real-state exceptions explicit, including indirect comments callers?
- [x] CHK002 Does the design preserve assertions, tuple/resource behavior and fail on missing state rather than supply fabricated IDs?
- [x] CHK003 Are comparable before/after collection/outcomes, frozen environment, timing scope and full-candidate limits complete?

## Независимая проверка требований — 2026-09-13

Рецензент: `fixture_research`, отдельно от исполнителя A7. Проверены новые A7
секции `spec.md`, `plan.md`, `research.md`, `quickstart.md`, `tasks.md` в ветке
`codex/211-delivery-cutover`, исходный HEAD
`a5f0c2a690bf01878c48e8d7f1b4d3cf1812b7f2`. Использовано уже выполненное
подробное исследование разрешённых callers; полный повторный поиск не
проводился. Выборочно сверены существующий ready helper, tuple
`setup_comments` и наличие всех шести именованных исключений. Код, другие
документы и работа коллег не изменялись. Сеть, Docker, браузер, тесты и
коммиты не запускались.

- **CHK001 PASS.** Таблица A7 в `research.md` ограничивает прямые замены
  девятью именованными файлами и их direct seed callers за вычетом четырёх
  точных исключений: 14 + 10 + 8 + 26 + 15 + 6 + 5 + 1 + 4 = 89 функций.
  Для пяти comments-файлов отдельно перечислены 26 косвенных callers по
  семействам и два точных исключения, то есть 24 замены. Общий объём 113
  относится к функциям до параметризации, а не к числу pytest cases.
  Перечень 14 файлов в A7 quickstart совпадает с этой границей. Все шесть
  исключений названы и существуют; сохранение реальных объектов особенно
  важно для inaccessible-existing 404 и чужого processing source.
- **CHK002 PASS.** FR-042 запрещает менять assertions, общий полный seed
  и подставлять выдуманные/None идентификаторы. A7 plan сохраняет tuple и
  `ready_id` через `SimpleNamespace`, поэтому обращение к не созданному
  состоянию завершится ошибкой. Только два именованных comment callers
  выбирают `full_seed=True`; четыре прямых исключения сохраняют полный seed.
  Сам `create_ready_meeting` уже имеет прежние ID/title defaults и проходит
  настоящий ingest с созданием прежних связанных result/media строк.
  DB/browser действия проверяемых операций остаются в тех же тестах.
- **CHK003 PASS.** SC-020, T064–T066 и A7 quickstart требуют одинаковые
  файлы, Python/lock/workers, равенство collection IDs и итоговых outcomes,
  отсутствие пропусков и отдельное подтверждение шести отрицательных
  сценариев. До/после используется существующий isolated runner,
  xdist 4/loadfile и новый каталог безопасных отчётов каждой попытки;
  setup/call/teardown сравниваются отдельно. Локальное измерение не объявляет
  ускорение hosted Full; окончательный кандидат сохраняет свой полный gate.

Уточнение для записи evidence: в `research.md` дано правило выбора с файлами,
количествами и именованными исключениями, а не отдельные 113 строк с именами
функций. Оно достаточно для этой фиксированной области; новые callers не
получают разрешение автоматически. В T064/T066 фактическая коллекция и diff
должны подтвердить именно рассмотренный исходный состав. Для браузерного
comments-файла сохраняется подготовленная среда A5; требование нуля skips
не позволяет заменить реальное выполнение отсутствием зависимости.

Итог требований A7: **PASS 3/3; CRITICAL 0, HIGH 0, MEDIUM 0**.
Базовый прогон выполняется главным агентом; его результат здесь не заявлен.
Реализация, сравнение результатов и измерений, analyze, issue ownership,
review/converge и Full подтверждаются соответствующими последующими записями.
