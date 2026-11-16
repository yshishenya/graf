# T112 — подтверждение только у своего текстового тела

Дата: 16.11.2026. Полоса: `high-risk-product`, существующая T112/FR-021/025.
Рабочая копия: `/private/tmp/graf-f273-result-visibility-20261116`.
Ветка: `codex/f273-result-visibility-20261116`.
Входной HEAD: `09228887cfe66b1ee2b79f3cbfb4c0828cd24134`.
Это следующий частичный шаг после общей проекции, не закрытие T112.

## Область и результат

Оба detail renderer (страница и HTMX-фрагмент, browser/embedded) принимают
необязательный `result_view_proofs`. Карта передаётся к существующим рендерам
расшифровки, обычных итогов и полного протокола. Ключи точно соответствуют
`result_view_text_blocks()`, включая объединённые open_questions/next_steps,
таблицу задач, каждую часть каждой темы и примечания. Неизвестные ключи
игнорируются. Индексы сохраняются при пустом теле.

Атрибут `data-result-view-proof` добавляется только к `div.text` расшифровки
или `p.outcome-item-text` итогов/протокола. Значение экранируется `html.escape`.
Пустое или состоящее только из пробелов тело не получает атрибут даже при
переданной карте. Заголовки, имена, метаданные, source controls и placeholder
не получают подтверждения. Ни текст, ни расположение элементов не меняются.
Кандидат внутри закрытого details пока не означает наблюдаемый показ.

Рабочие маршруты и прочие public/shared callers сохраняют отсутствие карты.
Этот шаг не выдаёт подписанные подтверждения, не меняет cache policy и не
подключает JS/native/POST/readiness/admission. Допустимость выдачи, fresh
auth/owner/source/fences, private/no-store и проверка видимости остаются
обязанностью будущего рабочего подключения по принятому договору.

## Ворота и проверка

Существующий независимый reviewer до кода подтвердил14/14 неизменных
документов требований/checklists/review/analyze, списки124/0, допустимость
именно необязательных атрибутов по §3 договора и отсутствие новых препятствий.
Основной агент сверил12/12 хешей базовых документов/проекта с принятым
design report, восстановил применимые положения spec/plan/tasks/quickstart,
договора, server/privacy/Spec Kit guidance. Issue mapping T112→#7698 и
scoped analyze сохраняются; новых issues/вопросов владельцу нет.

Затронуты8 renderer-функций, один маленький общий helper экранирования,
unit-проверки и собственный changelog fragment. Все callers найдены перед
правкой; необязательные аргументы сохраняют прежние вызовы. Governance,
требования, списки и task markers не менялись.

- Исходные8 новых параметризованных случаев отказали из-за отсутствующего
  аргумента renderer (`TypeError`); это RED отсутствующего интерфейса, не
  поведенческий отказ существующего рабочего измерения.
- Итог: **156 passed,1 прежний fixture warning,0 skipped**,3.63s, EXIT0.
  Включены12 вариантов атрибутов (6 состояний × browser/embedded; каждый
  проверяет page/fragment), экранирование, пустое/недоступное тело,
  unit-регрессии cabinet/protocol, detail reference contract и настоящий
  Chromium-сценарий summary picker. Протокол дополнен несколькими строками
  каждой части/темы, next_steps и notes; проверяется уникальность каждого proof.
- Удаление только новых атрибутов восстанавливает прежний HTML побайтово.
  Без карты и с пустой картой HTML одинаков; все24 исходных HTML-хеша
  до предыдущего изменения renderer также совпали.
  SHA-256 манифеста: `b60a6774ef4ecba311c7b39be74ecb926d18c0073bebf0f0a7b2ea8885b8f062`.
- Ruff и `git diff --check` PASS.
- [Независимый обзор](t112-proof-attributes-review-20261116.md) существующего
  reviewer: PASS узкого шага, P1=0/P2=0; оба точных хеша совпали. Его отчёт
  честно оставляет окончательный GREEN расширенной fixture исполнителю;
  приведённый выше terminal156 относится именно к этим итоговым хешам.
- Первый общий запуск:149 passed и1 ошибка предпосылки browser из-за
  отсутствия локального `node_modules`. Повтор использовал уже установленные
  Playwright1.63.0/Chromium через штатный `GRAF_NODE_MODULES`; зависимости и
  браузеры не устанавливались. Этот отказ не выдаётся за дефект продукта.
- Доступно169451296KiB, выше резерва80ГБ; сборки, архивы, Docker не запускались.

Точная команда из корня копии:

```sh
PYTHONPATH="$PWD/apps/server/src:$PWD/apps/server" \
GRAF_NODE_MODULES=/Users/yshishenya/Documents/crisp/apps/server/tests/browser/node_modules \
UV_PROJECT_ENVIRONMENT=/Users/yshishenya/Documents/crisp/apps/server/.venv \
UV_NO_SYNC=1 uv run --project apps/server pytest \
  apps/server/tests/unit/test_result_view_projection.py \
  apps/server/tests/unit/test_cabinet_web_shell.py \
  apps/server/tests/unit/test_meeting_protocol_rendering.py \
  apps/server/tests/contract/test_meeting_detail_reference_contract.py -q --tb=short
```

Журнал: `/private/tmp/graf-t112-proof-attributes-validation-20261116.log`,
SHA-256 `3146bbf5a6ea4d974212e7751230dc433d2e053897d427438a102561193b65a0`.
Terminal session4700 завершилась EXIT0; повторно не опрашивать.

## Точные проверенные файлы

| Путь относительно корня | SHA-256 |
| --- | --- |
| `apps/server/src/twobrain_rec_server/cabinet/rendering.py` | `7b3145108fa5b4d5059266ae334b24f420d496d9c229fbf7fa63aaa43c9ba11d` |
| `apps/server/tests/unit/test_result_view_projection.py` | `8311b43dad9c83ffe1253768ed282230dd5b56beae0ea79051a58a807357a471` |

## Открытая область

Нужны общий observer видимости и native foreground bridge, защищённые оба
POST, выдача/обновление proof из свежей проекции, bounded locks/повторные
auth/source/deletion/gate проверки и атомарная пара через общую T113.
Реальный `activation_recovery_unverified` и client `trigger_unverified`
сохраняются. Новые DB/browser/Swift/failure сценарии и полная converge,
exact-SHA GitHub gates, выпуск и рабочая приёмка остаются впереди.

Только синтетические fixture; DB source/admission не менялись, их прежний
принятый280-профиль не повторялся без основания. Native/production не
проверялись. Postal, общие службы, nginx/DNS/Compose, очереди, письма,
резервные копии и рабочие настройки аналитики не менялись. T112/T113/#7698,
T0, Product Radar и коммерческая цель остаются открытыми. Трафик, регистрации
и продажи этим шагом не подтверждаются.
