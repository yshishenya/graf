# Независимый визуальный обзор — документ F280

Дата: 2026-10-04. Reviewer только читает product/browser артефакты и пишет данный отчет. Synthetic данные; реальный GRAF Dev, деньги, почта, приватные документы и настройки не использовались. Область: invoice FR046–052 и согласование с принятым срезом subscription. Source/security имеет отдельный `review-invoice-consistency-source.md`.

## Заключение

**VISUAL PASS в проверенной области: 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM.** Широкий и узкий экран в обоих движках показывают понятную стабильную иерархию. Обычная помощь свернута и не оформлена предупреждением; предупреждение service-gap остается заметным до раскрытия. Дата покупки не выдается за действующий тариф. Масштабирование/клавиатурное поведение оцениваются отдельно по прочитанным assertions и отчету исполнителя, а не из одних PNG.

## Лично осмотренные изображения

| Артефакт вне git | Наблюдение |
| --- | --- |
| `/tmp/f280-invoice-chromium/shell-invoice-future-closed-1280-light.png` | Заголовок, короткая история сверху, карточка720; сумма/статус/период/объем/чек читаются без раскрытия. Технические сведения и помощь не занимают экран. |
| `/tmp/f280-invoice-webkit/shell-invoice-future-closed-1280-light.png` | Та же геометрия/порядок, без заметного различия layout между движками. Нет лишней доминирующей денежной кнопки у завершенного платежа. |
| `/tmp/f280-invoice-chromium/shell-invoice-service-gap-closed-320-dark.png` | Каждая подпись над значением, нет ступенчатых dd. Warning читабелен, safe_number переносится, сведения/помощь доступны ниже; действия не перекрываются. |
| `/tmp/f280-invoice-webkit/shell-invoice-service-gap-closed-320-dark.png` | Аналогичная последовательная мобильная компоновка и заметная проблема услуги; нет обрезанного срока/суммы либо горизонтального выхода. |
| `/tmp/f280-invoice-chromium/shell-subscription-off-no-card-1280-light.png` | Подписка использует тот же720, фон, радиус и пары подпись/значение. Invoice сохраняет собственную задачу просмотра исторической покупки, поэтому не копирует active badge или renewal CTA. Visible focus на summary показан; он не считается дефектом оформления. |
| `/tmp/f280-invoice-webkit/shell-invoice-intervals-320-dark.png` | При открытых сведениях точное время/зона и несколько storage интервалов сохраняются; длинный контакт переносится. Safe номер и copy доступны. PNG прокручен из-за фокуса — отсутствие заголовка в кадре не трактуется как исчезновение в продукте. |
| `/tmp/f280-invoice-chromium/shell-invoice-receipt-1280-light.png` | Документ — обычная ссылка. Открытая помощь имеет разные question/refund действия, сообщение об отсутствии автоматической отправки/возврата, отдельную связь управления продлением. Фокус заметен. Кадр также прокручен вслед за фокусом. |

Прочитан `/tmp/f280-invoice-browser-tests.md`: causal RED на старом шаблоне; после реализации Chromium16passed/66.50s, WebKit16passed/87.95s. Это результат browser исполнителя, не повторный запуск reviewer. Изображения соответствуют существующему cabinet shell, synthetic projection. Артефакты остаются вне git; реальных карточек/счетов в них нет.

## Требования и доказательства

- **FR046**: основные факты/результат сразу, история до карточки, одна primary status link только при recovery; помощь вторична. Desktop и320 проверены лично по PNG; width720 и dd margin0 также имеют browser assertions.
- **FR047/048**: закрытый экран показывает краткий оплаченный срок; открытый — точное время/зону/created label/safe номер и интервалы. Создание не названо временем settlement; future invoice не использует active badge. Истинность nullable/discount/timezone/foreign payer проверяют source и отдельные DB тесты, не картинки.
- **FR049/050**: открытая помощь различает вопрос и возврат, не обещает отправку/возврат. Чек с URL виден ссылкой, без URL соответствующее действие отсутствует в fixture/assertions. Browser не открывает mailto/провайдера; allowlist/privacy подтверждаются route source/tests отдельно.
- **FR051**: status diff только dlclass, прежние live/actions/контроллер сохранены. Browser прогон включает прежние status/checkout/subscription assertions; dedicated payment-return полная матрица принадлежит общему validation gate.
- **FR052**: нативные details раскрываются клавишейSpace, ссылки и button имеют существующие focus-visible правила; report/assertions покрывают обе темы,320/360/390/768/1280,100/200%, contrast/targets/overflow, JS-off details и отсутствие POST. Reviewer лично видит читабельность/переносы и focus в перечисленных кадрах; VoiceOver/установленный WKWebView не проверены.

## Соответствие практике и минимальность

Решение сохраняет принципы прочитанных первичных источников: NN/g показывает частое первым и редкое раскрывает; GOV.UK details не прячет существенный результат; W3C status/финансовая достоверность не подменяются косметикой. Аналогия с Krisp — компактные группы billing и простой доступ к документам. Pixel parity текущего авторизованного Krisp этим отчетом не заявляется; цены/правовые условия/активы Krisp не поставляются. Собственный GRAF shell и компоненты переиспользуются, новая история/вкладки/библиотека/иллюстрации отсутствуют.

Все видимые линии обслуживают существующие читаемые пары сведений, один наружный контур согласован с подпиской. Нет причины добавлять новый слой карточек, дополнительные экраны или скрывать проблему услуги ради меньшей высоты.

## Пределы готовности

Это visual/source evidence рабочего среза. Browser fixtures не являются route→DB/provider доказательством; PNG не закрывает current frozen SHA CI, реальную финансовую/человеческую приемку, deployment/live и установленный GRAF Dev. S001 source fix проверен отдельно; текущий isolated DB лог25PASS проверен reviewer с указанным digest в source report. Финальная readiness остается у координатора после всех текущих тестов и release gates.

Координатор сообщил отдельно диагностируемые отказы полной status guards/lifecycle матрицы; VISUAL PASS invoice области не закрывает этот общий validation blocker и не разрешает выпуск самостоятельно.


## Независимый визуальный повтор после уплотнения — 2026-10-04

**VISUAL PASS: 0 CRITICAL, 0 HIGH, 0 исправимых MEDIUM** в текущем invoice срезе. Координатор передал прямое решение владельца «Сделать карточку плотнее». Два узких правила меняют gap/padding карточки и вертикальные отступы строк; font/width720/native controls/семантика/guards неизменны. Повтор подтверждает более плотную карточку с сохранением читаемых фактов, существенных сообщений и доступных раскрытий.

Лично осмотрены свежие изображения, сохранённые после двух CSS правил. Все данные synthetic (`INV-SYNTHETIC`, example.test, masked fixture card); реальная личная/платёжная информация не используется и изображения не поставляются в продукт.

| Артефакт вне git | Наблюдение | SHA-256 |
|---|---|---|
| `/tmp/f280-invoice-density-chromium/shell-invoice-future-closed-1280-light.png` | Компактная карточка720, все основные факты и история без раскрытия; сведения и помощь вторичны. | `bccb129ffa64f09f92ae7cffa3298b3e37d6af28e584766f5c61d7050d368a02` |
| `/tmp/f280-invoice-density-chromium/shell-invoice-service-gap-closed-320-dark.png` | Читаемый service-gap вне details, одноуровневая мобильная компоновка, раскрытия доступны ниже. | `f23073c9d99fa61404e173717bdb59696e86eb81a54a225f7cfaa9c7c910ac8e` |
| `/tmp/f280-invoice-density-chromium/shell-invoice-service-gap-320-dark.png` | При раскрытии точные сроки/контакт/copy переносятся без выхода; фокусный scroll не означает исчезновение header. | `46317aac3f2286d065b244826eed816de54393300345aac5628b4a3992d70733` |
| `/tmp/f280-invoice-density-chromium/shell-invoice-receipt-1280-light.png` | Документ и две темы поддержки различимы, фокус ссылки возврата заметен; точные даты сохраняются. | `347cc5b8eeeb371c8bb80adc352fb9856aeef8c2f5e7e19044877691008624cc` |
| `/tmp/f280-invoice-density-webkit/shell-invoice-future-closed-1280-light.png` | Та же компактная геометрия720 и порядок в WebKit; нет лишнего денежного действия. | `78a7569ff7a36073fce6fc000d04460cc8c83de3ffd20c37ef10dfd12187d22e` |
| `/tmp/f280-invoice-density-webkit/shell-invoice-future-closed-320-dark.png` | Закрытая обычная карточка читается целиком, период/сумма/состояние видны; помощь ниже. | `ef3402e13f3a3edf3b9daa565afb57ff0bd35c0d9956f4fb8c1becdda114649b` |
| `/tmp/f280-invoice-density-webkit/shell-invoice-service-gap-closed-320-light.png` | Светлая320: warning заметен и не спрятан, строки/слова читаются, горизонтального выхода нет. | `42c295d6f3f428fd5cfa8f05771a3bc05017b3397075e9a4969816355d90e11d` |
| `/tmp/f280-invoice-density-webkit/shell-invoice-intervals-320-dark.png` | Открытые точные интервалы и длинный synthetic email полностью переносятся, кнопка copy остаётся доступной. | `b98015f4de6cda6dfd7062ec33071d365454668220e4e91325cf199c801ceead` |
| `/tmp/f280-invoice-density-webkit/shell-invoice-receipt-1280-light.png` | Открытая помощь и видимый фокус соответствуют Chromium; денежные обещания не изменены. | `a243c5799e3072b05fdc2fc2cad6c8a74744d40f59c07e645d63df4bdb516c20` |

Лично прочитаны свежие complete логи `/tmp/f280-invoice-density-chromium.log` —16passed52.71s и `/tmp/f280-invoice-density-webkit.log` —16passed59.51s; лог/files fingerprints записаны также в source report. Это прогоны основного исполнителя, reviewer не запускал новые browser/DB матрицы. Assertions прочитаны вновь: обе темы,320/360/390/768/1280 и100/200%, overflow, min target24px, contrast, width720, native Space/copy/фокус/help и JS-off0POST. Проверку200% подтверждает прочитанный актуальный тест и complete PASS; PNG100% не объявлены самостоятельным доказательством200%. Видимый фокус лично наблюдается в receipt1280 обоих движков.

Историческая заметка о status failure выше больше не описывает текущий тестовый результат. Reviewer прочитал serial full логи Chromium56PASS323.91s/WebKit56PASS348.98s. Эти проверки до уплотнения, а два новых CSS селектора применяются только к invoice: dedicated status класс/поведение не изменены. Current exact-SHA/base CI и frozen release остаются отдельными.

Проверенный текущий CSS SHA-256 `144b3649d73a02cf5b6634bc80c87b6e9162433aa561f2346a6739a9568e752d`; все текущие product/test fingerprints приведены в source report, HEAD `3cf989cd93f4d3d4b72f83068664f802a11a5eac` с рабочим diff. После записи reviewer повторно сверил13 product/test/log/pages fingerprints: все совпали; git diff --check по двум принадлежащим reviewer отчётам PASS. Список требований не изменён: это уже предусмотренная компактная геометрия/доступность FR046/052 и не новый информационный/денежный сценарий.

Reviewer изменил только свои source/visual отчёты; code/canonical/checklist/GitHub/commit/release не менял. VISUAL PASS сохраняет пределы: synthetic/source/browser проверка не является подтверждением live deployment, установленного Dev, реальной финансовой либо человеческой приёмки.
