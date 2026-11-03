# F280 T051 — независимый повторный обзор браузера и доступности

Дата: 2026-10-04. Reviewer: `subscription_browser_final`, не автор реализации
или тестов. Lane: read-only independent review активного high-risk-product
среза US4. Изменен только этот отчет; чужие изменения сохранены.

**PASS: critical 0, high 0, применимых исправимых medium 0.** Проверены
актуальные требования T051/FR-042/044, план/quickstart/контракт, refresh
требований PASS14/0, реализация route/template, CSS и браузерные fixtures.
Свежие Web Interface Guidelines прочитаны из официального публичного источника
<https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md>.
Прежний отчет браузера остается историческим: его ожидание блокирования одного
`provider_key_expired` не определяет текущую редакцию T051.

## Привязка к исходникам

Branch `codex/280-subscription-clarity`; HEAD при проверке
`b3b3ac1c63f256c8d6b6d39710ed7406f6e90ecf`. T051 на момент проверки
незакоммичен, поэтому результаты привязаны к следующим Git blob fingerprints,
а не к одному HEAD. Fingerprints перечитаны после окончательных прогонов.

| Файл | Git blob fingerprint |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` | `bbcda962e18df9c8a2aa20092236569dadcf43c3` |
| `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html` | `55934f188ef6e08c338621e136418fbbb9e711e3` |
| `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` | `451f0ecbc7b7f11355adc542742a26b3aebbbe2e` |
| `apps/server/tests/browser/billing-accessibility.test.cjs` | `7e8816a5061263a0f8a389bb7b3f7e0a33885153` |
| `apps/server/tests/contract/test_billing_accessibility.py` | `0e289179d72f7c24cc749390aefb9085fc3a057e` |

## Свежие результаты

Команды из `apps/server`, существующий `.venv`, полный contract file,
browser subprocess timeout120 секунд:

```sh
.venv/bin/python -m pytest tests/contract/test_billing_accessibility.py -q
GRAF_BROWSER=webkit .venv/bin/python -m pytest tests/contract/test_billing_accessibility.py -q
```

| Проверка | Результат |
| --- | --- |
| Chromium, окончательное состояние T051 | **16 passed**, 73.60 с |
| WebKit, окончательное состояние T051 | **16 passed**, 89.61 с |
| Независимые точечные NoJS проверки трех новых состояний × два движка × обе темы, 320 CSS px/200% CSS zoom | **12 cases PASS**, раскрытие/история/фокус/переходы GET/без новой оплаты |

Полные прогоны сохраняют матрицу 320/360/768/1280 CSS px, light/dark,
100/200% CSS zoom, контраст текста, размеры основных элементов управления,
достижимость действий, keyboard/native details, начальный/ошибочный фокус,
отсутствие перехвата фокуса при повторной инициализации и фактическую
перехваченную отправку native checkout/resume/cancel форм без JavaScript.
В WebKit macOS используется Option-Tab для обхода всех элементов.
Два прежних предупреждения pytest про импорт/устаревший TestClient не являются
падением проверок.

Ранний Chromium прогон выявил оставшийся старый fixture
`subscription-uncertain-provider_key_expired`: **1 failed / 15 passed**,
30.60 с. Reviewer сообщил основной причине root, не меняя тесты. Root убрал
expired из resolution-only отрицательной матрицы и сохранил отдельный
положительный `subscription-key-expired`. Ранний WebKit был остановлен при
финализации wording/fixture; его результат не объявляется GREEN. Оба
окончательных прогона выше выполнены заново после подтвержденной готовности
и зафиксированы отдельно.

## Независимые наблюдения

- **Expired alone:** обычная ссылка «Продлить подписку» видна; нет ложного
  сообщения «Повторно платить не нужно». Ее переход — GET на существующий
  checkout, не действие списания. Route использует общий существующий
  `CHECKOUT_BLOCKING_STATES` без добавленного expired состояния; этот общий
  набор содержит `manual_resolution`. Сам истекший ключ не превращается в
  запрет или обещание отмены старого платежа.
- **Method required + pending, off/on:** «Проверить платёж» и «Проверить
  способ оплаты» одновременно доступны. Вторая ссылка ведет GET на
  `/billing/payment-method`. Manual/early/resume оплата не появляется.
  Текст сообщает «Результат платежа на … еще не подтвержден», не выводя
  факт отправки или отсутствия списания из method_required. При on прямая
  защищенная отмена остается доступна; ее пояснение «Этот платеж продолжит
  проверяться» также не утверждает отправку.
- **История:** native раскрытие теперь называется «Способ оплаты, условия и
  история». Из названия обнаружимо местоположение истории; Space раскрывает
  его без JavaScript. «История платежей» внутри ведет на прежний
  `/billing/history`; точный срок/условия сохраняются на одном уровне.
- **Клавиатура и узкий экран:** 12 независимых NoJS случаев фактически
  раскрывают новые сведения, проверяют видимый фокус безопасной основной
  ссылки, отсутствие общей горизонтальной прокрутки и выполняют переход.
  Перехваченные document requests все GET. На 320/200% название раскрытия и
  ссылки переносятся строками, остаются видимыми/достижимыми в обеих темах.
- **Остальные состояния:** полный текущий browser contract сохраняет
  no-card/off, on/cancel, explicit unchecked required resume, trial/free,
  prepared и pending/unknown/unknown_pending сценарии. Существующие CSRF,
  version/quote и native consent assertions не ослаблены.

Reviewer лично просмотрел новые synthetic screenshots: method-pending
1280 dark; key-expired320 light; key-expired с открытой историей320/200% NoJS
Chromium light; method-pending-on320/200% NoJS WebKit dark с видимым фокусом
проверки карты. Скриншоты/fixture JSON и вспомогательное средство проверки
остаются временными; пользовательские изображения и данные не сохранены.
`git diff --check` прошел.

## Пределы

Это браузерный обзор, не доказательство route→PostgreSQL, прав/tenant/session
или обработки provider_id: действительная DB матрица до/после dispatch и
financial source review принадлежат отдельным заключениям. Сам synthetic
HTML не моделирует банковскую операцию. Реальных платежей, списаний,
возвратов, grants и обращений к платежному провайдеру не выполнялось.

200% проверены через CSS zoom, не через все режимы системного увеличения.
VoiceOver, ручная приемка GRAF Dev, все устройства/данные, конверсия и желание
каждого человека платить не подтверждены. Настоящие деньги, чек/банк/возврат,
SC-005/006, T011/T012 и F278 остаются отдельными. PR checks, выпуск и
production также не подтверждаются этим PASS.
