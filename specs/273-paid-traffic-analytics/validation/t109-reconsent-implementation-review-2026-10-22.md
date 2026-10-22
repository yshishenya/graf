# T109/T111 — независимое ревью smoke и повторного согласия

Дата: 22.10.2026. Проверяющий: `/root/growth_security_gate`.
Рабочая копия: `/Users/yshishenya/.codex/worktrees/growth-guide-links/crisp`.
Ветка: `codex/273-retention-until-decision`.
HEAD: `4533aee7d7c312c2f2dd72ec6b1d494e74eb487a` плюс рассматриваемый diff.
Полоса `high-risk-product`, PR #7707, существующие T109/T111.

## Окончательное решение v2

**PASS локальной реализации двух исправлений после устранения найденного P1.**
В окончательном v2-кандидате открытых блокирующих дефектов не обнаружено.
Ни рабочее включение, ни T109/T111 целиком не принимаются. Первый FAIL и
его воспроизведение сохранены ниже; v2 повторно проверен независимо.

## Первоначальный результат реализации

**FAIL первого кандидата: один воспроизведённый P1 в последовательности callbacks.**
PASS требований из `t109-reconsent-requirements-review-2026-10-22.md` сохраняется;
он не заменяет проверку реализации. Рабочие настройки/согласия не менялись.

### P1 — последующий onConsent обходит отказ проверки сохранённого решения

В первом кандидате `handleConsent` передаёт ожидаемые категории в
`persistConsentMetadata` только при `explicitChoice`; обычный `onConsent`
передаёт `null`. Поэтому повторное чтение revision/categories выполняется
для первого callback и обходится следующим callback той же библиотеки.

Собственный сценарий reviewer выполнен в памяти с настоящим controller через
существующий synthetic harness. У CookieConsent отдельное текущее внутреннее
cookie и persisted localStorage. Внутреннее cookie имеет текущую revision,
necessary+analytics и прежнюю custom data. Заглушка `setCookieData` обновляет
custom data внутреннего cookie, но запись localStorage содержит неверные
categories либо старую revision. Это контролируемая ошибка сохранения, которую
новая readback-проверка специально обязана отвергать.

В обоих вариантах:

1. `onFirstConsent` честно отвергает запись: state=`unknown`, relay calls=0.
2. Следующий `onConsent` с обновлённым внутренним cookie принимает текущую
   metadata, пропускает проверку persisted categories/revision и включает
   аналитику: state=`customized`, relay calls=1.

| Ошибка сохранённого cookie | После fresh callback | После следующего onConsent |
| --- | --- | --- |
| Categories содержат только necessary | unknown / 0 отправок | customized / 1 отправка |
| Revision остаётся прежней | unknown / 0 отправок | customized / 1 отправка |

Это нарушает уже принятую границу FR-059: проверка полного сохранённого
решения должна оставаться действующей до включения провайдера, в том числе
в реальной последовательности callbacks. Существующие новые synthetic tests
проверяют только первый отказ, поэтому не обнаруживают обход.

Минимальное направление исправления — всегда проверять сохранённые текущие
revision и normalized categories перед включением, включая строгий `onConsent`,
и добавить последовательный regression. Строгое автоматическое чтение старой
редакции не должно автоматически повышать её. Reviewer код не менял.

## Прочитанные доказательства первого кандидата

Прочитаны diff четырёх runtime/test файлов, настоящий vendored CookieConsent
3.1.0, принятые требования и шесть журналов snapshot. Первоначальный снимок
`.dev/growth/t109-reconsent-implementation-snapshot-2026-10-22.json` перечисляет
четыре хеша кода/тестов и шесть хешей журналов. К моменту итоговой сверки этого
первого снимка исполнитель уже исправлял P1, поэтому подтверждение неизменности
первых байтов не заявляется. Собственное воспроизведение относится к фактически
прочитанному первому diff; окончательная сверка ниже относится к v2.

Предоставленные журналы подтверждают:

- до исправления smoke — три фактических contract FAIL `provider smoke failed`;
- после исправления smoke — три contract PASS;
- настоящий браузер до исправления сохраняет старую custom copy после нового
  выбора; после исправления три варианта all/necessary/customized и reload PASS;
- synthetic harness PASS, включая missing actual cookie, old actual revision,
  несовпадение categories и отказ записи на первом callback;
- профильный PostgreSQL/browser набор — **81 passed, 1 warning**, digest
  `35a49e1226ea40e9b78e22a34da48181df290375891ca1f65e07a0dfcf28db4f`,
  runner сообщает удаление изолированного контейнера.

Эти положительные результаты не покрывают найденную последовательность двух
callbacks и не отменяют P1. Reviewer широкий pytest не перезапускал,
к рабочим службам/БД/провайдерам не подключался.

## Оставшаяся приёмка

Для повторного PASS потребовались исправление найденного P1, новый regression и
актуальный снимок; результат этой проверки приведён ниже. После локального PASS всё равно обязательны convergence,
точные SHA/base проверки PR, штатный выпуск и отдельная рабочая приёмка.
T105/T106/T109/T111/T118, опубликованная редакция, правовое основание IP и
рабочее включение измерения не закрываются этим ревью.

Reviewer изменил только этот отчёт. Требования/tasks/checklists, Git/GitHub,
production, state files и данные не менялись; внешних отправок не было.

## Проверка исправления v2

Исполнитель устранил условный обход: каждый `handleConsent`, включая
последующий `onConsent`, вызывает `persistConsentMetadata(nextState, categories)`.
Readback безусловно требует текущие custom metadata, библиотечную revision и
тот же нормализованный набор categories. Параметр `explicitChoice` удалён.
Обе последовательные regression-проверки сохранены в synthetic harness.

Снимок `.dev/growth/t109-reconsent-implementation-snapshot-v2-2026-10-22.json`:
SHA-256 `7b909bb1596297a2e3db7d2902e0367e758286897be55844ae2ee957b723a4bb`.
**4/4 source/test и 6/6 log hashes совпали** при независимой проверке и после
записи отчёта. HEAD остался указанным выше. Отдельная параллельная правка
changelog исполнителем не входит в эти четыре runtime/test файла и не менялась
reviewer. Все **7/7** обязательных хешей разрешения scoped reading F273 также
совпали; полное новое чтение PRD не заявляется.

| Проверяемое свойство v2 | Результат |
| --- | --- |
| Smoke receipt | Версия 2 и текущий epoch добавлены только в учебный receipt; контроль fresh evidence не ослаблен, реальные настройки/откат не затронуты. |
| Свежий выбор | `onFirstConsent/onChange` требуют настоящее current cookie через `getCookie`, текущую revision в callback и совпадающие допустимые категории. Только после этого заменяются старые custom metadata. |
| Автоматическое чтение | `onConsent` сохраняет строгую проверку версии; fallback preferences, который выдумывал current revision, удалён. Старое согласие не повышается автоматически. |
| Повторный callback после отказа | P1 закрыт: persisted revision/categories обязательны на каждом callback. При несоответствии нет ID/relay и состояние остаётся unknown. |
| Раздельность целей/отказ | Нормализатор/consentStateFor и transitions сохранены; necessary-only не включает провайдера, отзыв запрещает следующую отправку. |
| Передача/получатели | До успешного readback не вызываются enable/start; новых endpoint, внешних скриптов, payload-полей и получателей нет. |

### Собственные проверки v2

Reviewer независимо выполнил **16 утверждений в памяти** с настоящим
`analytics.js`, используя функции существующего synthetic harness без вызова
его общей main и без записи файлов. Внешних запросов нет.

- Для каждой ошибки categories/revision воспроизведены `onFirstConsent` →
  `onConsent` с отдельными внутренним cookie библиотеки и persisted cookie:
  после обоих callbacks state unknown, relay=0, sessionStorage пусто.
- Автоматическое чтение прежней custom data оставляет unknown и сохраняет
  прежнюю редакцию, не превращая её в новое разрешение.
- Новый действительный выбор после этого даёт customized. Следующий
  onConsent не удваивает relay-событие.
- После принятого выбора новый necessary-only через onChange даёт revoked;
  последующий onConsent сохраняет revoked; следующий dispatch отвергнут,
  число relay-вызовов не растёт.

Все 16 утверждений прошли. Это независимое повторение конкретного исправления;
настоящий браузерный прогон ниже — предоставленное доказательство, не свой
повторный запуск reviewer. Также независимо прошли `node --check` controller
и обоих изменённых CJS tests, `bash -n` smoke и `git diff --check`.

### Доказательства v2

Прочитан окончательный `.dev/growth/t111-reconsent-focused-v2.log`:
**81 passed, 1 warning in 13.86s**, collection count 81, digest
`35a49e1226ea40e9b78e22a34da48181df290375891ca1f65e07a0dfcf28db4f`.
Runner сообщает PASS и `isolated_container_removed`. SHA-256 журнала:
`27c5ed4716a51ea67eaefe9d977e0d0ce2ff55b781b5032561697418e330d962`.
Предупреждение о повторном импорте pytest fixture не является пропуском теста.

Окончательный synthetic log содержит отдельный
`ok repeated_callback_keeps_failed_readback_blocked` и остальные прежние
сценарии отказа/отзыва/раздельности поведения. Real modal log подтверждает
все три новых выбора с reload на настоящем CookieConsent 3.1.0 и прежние
одинаковые пути отказа/согласия. Smoke after log подтверждает три исполняемых
contract tests. Ни один из этих журналов не выдан за live provider delivery.

| Файл окончательного кандидата | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/public/static/public/analytics.js` | `cd777e2ab12a7de9860ef76c89972d8bf6a0dbd4e3742bccf23e7d50b065b2d0` |
| `apps/server/tests/browser/public-analytics-consent-modal.test.cjs` | `d670744d3b163a277ecf647f7a0aedb5cdd8ceaadd019b78407a8cc2abc10f3c` |
| `apps/server/tests/browser/public-analytics-consent.test.cjs` | `29d36bb568b042d46964c673843a55341bfe2a140fa07fc7cd6b6d13d656d3d3` |
| `infra/scripts/run-product-analytics-provider-smoke.sh` | `70402a7c8da2247a5f67bbad42b1842598c70e58285eee5ec397f672a9fc4094` |

| Прочитанный журнал | SHA-256 |
| --- | --- |
| `.dev/growth/t109-provider-smoke-before.log` | `1f92e5714d59925c5cff3457cc12cef2caa8c7d51ad462b14aa6013a67e202a6` |
| `.dev/growth/t109-provider-smoke-after.log` | `36c7e58ff2bbdb7013c8f64b7f4fff1f738daac87abdce08fdc367219b867c64` |
| `.dev/growth/t111-reconsent-before.log` | `778158cc10854cfaf8b800ee5a192acfc8ab2c8f13f572aed35b019e14803bf9` |
| `.dev/growth/t111-reconsent-after.log` | `dd75419b387c33716aaad37705610766cb64ad39d1c0ed85fa4e0b92f1f6d216` |
| `.dev/growth/t111-consent-after.log` | `03513c4c287dfcedaf5d2bf1d0479d902c88fc435376100bb3b94c2e3c3b6656` |
| `.dev/growth/t111-reconsent-focused-v2.log` | `27c5ed4716a51ea67eaefe9d977e0d0ce2ff55b781b5032561697418e330d962` |

### Ограничения окончательного PASS

Требования приняты отдельно; v2 закрывает именно локальные root causes двух
исправлений и последующего P1. После переноса на другую базу нужны побайтная
сверка этих четырёх файлов и обязательные проверки нового точного SHA/base.
Зелёный локальный набор не подтверждает текущий GitHub CI, merge или выпуск.

Действующие T105/T106, уже загруженный сторонний скрипт старой вкладки,
offline/advertising consent, правовое основание IP, полное restore T118,
операторская политика хранения, публикация и включение измерения остаются
за границей. Новое согласие не продлевает сессии и не разрешает новые категории.
Рабочий трафик/продажи не проверялись. Security checklist после сверки:
**25 отмечены, 0 открыты**, его содержимое не менялось.

Итоговое независимое изменение — только этот отчёт; код, spec/plan/tasks,
checklists, Git/GitHub, production и рабочие данные не изменялись.
