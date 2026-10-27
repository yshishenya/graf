# F224/T009: независимое ревью реализации, 27.10.2026

**APPROVE изолированной реализации. CRITICAL 0, HIGH 0, открытых замечаний 0.**
R1 снят после авторского уточнения договора, без изменения проверенного кода.

Проверяется `codex/224-preserved-archives` на основе
`5dffd0537e66e7f4e88bd0d4fd5103393fc7c486`; lane high-risk-product.
Проверяющий не является автором реализации, использует code-reviewer и
владеет только этим отчётом и двумя reviewer-owned чеклистами. Код,
договоры, tasks, Git/GitHub и состояние стенда не изменяет; тесты не запускает.

## R1 — снят: проверка sibling app у preserved-state

В `scripts/dev-harness.py`, `_classification_build_archives` (строки341–359),
sibling `GRAF Dev.app` проверяется как безопасный существующий каталог.
Bundle ID/source SHA/подпись/entitlements сверяются в `_classification_artifacts`
(строки514–548), вызываемом только для `artifact-only` (строки623–628).
Для `selected`/`preserved-state` формат требует пустой `artifacts`, поэтому
исторические signer/source facts для такой сверки вообще не передаются.
Положительный `test_classification_preserves_explicit_build_archives` для
preserved-state намеренно создаёт пустые sibling app каталоги.

В прежней проверенной редакции `contracts/state-ownership.md:160–168` говорилось «sibling GRAF Dev.app
проверяется отдельно» и «Для каждого app проверяются Dev bundle ID, полный
source SHA, строгая подпись…»; `data-model.md:79–80` запрещал разрешать
непроверенные app/build одним названием. Автору передано согласовать границу:
либо добавить обещанную проверку, либо явно ограничить её перечисленными
app в `artifacts[]` вида artifact-only, сохранив другие архивные app как
неприменяемые неизвестные байты со снимком и проверкой безопасности.
Последний вариант не даёт права исполнения/восстановления и не требует нового
механизма. Промежуточный PASS был удержан до согласованного договора.

Повторное чтение: автор явно выбрал второй вариант. Contract и data-model
полностью перечитаны после правки: сведения об идентичности и подписи
обязательны только для artifacts[] artifact-only. Архивные app selected и
preserved-state сохраняются как неизвестные байты; безопасный sibling каталог
не становится проверенным кандидатом. Отдельные active manifest/runtime guards
сохраняются. Полностью прочитаны обновлённые infra/dev/README.md,
local-development.md и F224.yaml: та же граница, без обещания живой приёмки.
CHK031 и Q003 вновь отмечены; R1 закрыт. Код и тесты остались побайтно прежними.

## Проверенные свойства

- Полный новый код helpers, adoption caller и parser прочитан; смежные
  path/binding/lock/state/schema/PID/signature функции проверены на отсутствие
  изменений в соседях, запуска build и импортов образов при классификации.
- Snapshot соответствует каноническому JSON формату POSIX полей, включает
  байты обычных файлов и raw link targets; lstat-обход не следует по ссылкам.
  Read/open и after-read проверки ловят подмены файлов. Atime исключён явно.
- Build разрешается только по явному уникальному относительному пути
  `artifacts/<candidate>/build`; небезопасные объекты и ссылки отвергаются.
  Проверяются конечная цель и каждый префикс; все вложенные symlink также
  обходятся как объекты, поэтому промежуточный выход с возвратом не скрывается.
- Registration lock предшествует отсортированным operational locks.
  Соседние locks открываются с create=False, без O_CREAT; inode после ожидания
  сверяется. После каждого ожидания и перед binding повторяется весь план,
  root set, device/inode и снимки.
- fd контекста `_state_file_lock` сохранён; прежний state_lock передаёт его
  в механизм T010. Код promotion/recovery/retention и frozen adapters не менялся.
- Существующий binding неизменяем и идемпотентен. Соседи не становятся
  управляющими roots, не получают новых locks, binding или иных файлов.

## Журналы и пределы доказательства

Прочитан `f224-build-contract-red.log`: 2 ожидаемых отказа старого06ad,
но оба на проверке строгого формата нового поля build_archives. Поэтому
дополнительно прочитан f224-build-contract-old-format-red.log: удалено только
build_archives из каждой записи плана, архивные bytes/links сохранены;
оба положительных сценария отказали на старом06ad именно в tree digest:
`classified symlink leaves its archived app`. Это адресный RED архивных ссылок,
не подмена новым неподдерживаемым полем схемы. Временный исходник RED автор
удалил; reviewer проверил журнал, но отдельный опыт не исполнял.

Прочитаны `f224-classification-regressions.log` и XML: 475 уникальных testcase,
0 failures/errors/skipped, 14 профильных suites. Результаты получены автором;
проверяющий их не перезапускал. Проверены положительные архивные случаи,
18 отказных build cases, изменения build/link/metadata во время настоящего
ожидания и build/link непосредственно перед binding, ошибки публикации и
прерывание до/после неё. Ownership suite содержит 150 успешных случаев,
promotion transaction 132, schema transition 51, остальные 11 suites — 142.

Оба итоговых чеклиста перечитаны целиком: infrastructure 34 отмечено /
0 открыто; requirements 16 отмечено / 0 открыто. Это качество требований,
не автоматическое принятие установленного приложения. git diff --check
разрешённых файлов прошёл. До коммита обновить analyze/sync на окончательные
документы; последующие PR проверки связываются с новым точным SHA и основой.

Реальный adopt-state, приложение, Docker, TCC, release и deploy этим ревью
не выполнялись. T009/T011/T012/T013 и #6180 не принимаются числом тестов.

## SHA-256 проверенных входов и журналов

- scripts/dev-harness.py: `98300cb86cb2986e3f342dc22c05b8332ed1e486da6f5b6036990d4f4817a4e9`
- tests/governance/test_dev_state_ownership.py: `2b7435d0d6bc4d122857ca29dfb95db4caf36f7834f4ae76f90c421f98ac2047`
- contracts/state-ownership.md: `97f117233d8bf3fb95d568c2a56c0df32905f281a187449988991e414d3ad78d`
- data-model.md: `cdd783aa71dcca720a9889577e6066341f21505b6a1a4fba5297db1de62aee5d`
- infra/dev/README.md: `aafc46f71542d33b15eec75ebb6b4206c1806493b176d58146e32f4a3343e128`
- docs/agent-guidance/local-development.md: `d88ca6b7b6868917bb8a5668d0d620af04469d9f6666f1ea3983d7c669a165fe`
- changes/unreleased/F224.yaml: `2a1f7338a7a1d28fee7ed943b7758789e80b8ec25ebfcd4769138eb0967bf8cd`
- f224-build-contract-old-format-red.log: `ea044fb431c9493bf54251d54c2247317bcb3bb8edd0939bcfff3b94c0f02ae1`
- f224-classification-regressions.xml: `5ce15c1a3c0fa8b27653a625bd0103f5397cfb5cb3d53ab85d3feebf7bb7a5f1`
- f224-classification-regressions.log: `16a2a5b270a6463e857d309618f475596b5045345958aef67ad34b67fae6ef76`
