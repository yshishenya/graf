# F257 — состояние реализации и приёмки

Дата: 2026-09-09. Объём: «Только страница и уже доступные функции GRAF». Lane: **high-risk-product / reference-fidelity**. [PR #6826](https://github.com/yshishenya/graf/pull/6826) прошёл установленную приёмку; снятие draft выполняется после GitHub governance-fast окончательного документационного SHA.

Подготовка завершена:52 наблюдения референса,19 FR/5 SC,3 пользовательские истории/10 сценариев приёмки; независимые UX8/8 и security5/5, analyze CRITICAL0/HIGH0/MEDIUM0. Требования, план и контрольные списки не ослаблялись. Все 10 задач имеют уникальные canonical issues; общая задача 6794 остаётся открыта до merge. [tasks.md](tasks.md) — источник выполнения, [issue-map.md](issue-map.md) — связь с GitHub.

Продуктовый SHA `4273ab10147fb0aa593cb979b9c377852054bb6d` включает оформление, безопасное прямое копирование, HTMX-возврат, общий расчёт видимой области текста и исправление начального открытия источника. Последний PostgreSQL/contract/runtime набор 64 PASS; runtime 3 PASS, ruff/node/diff PASS. Исправления независимо приняты reviewer и владельцем F256. Converge проверил 19 FR/5 SC/10 AC/8 решений плана/7 принципов, новых пробелов реализации 0; tasks.md во время анализа не менялся.

Установленный `deaebee4ce2a85004f161440cdff8a7dd2ab4b4c` прошёл штатные build/promote/status/smoke и независимый native source 100/200, паузу/устойчивый кадр/фокус возврата, compact/resize/expand. При 200% текст AX 199–349 полностью выше плеера≈375. Окончательный кандидат `7f39166caa604765aa611392d2111233bec0cf19` дополнительно содержит initial-source fix; прошёл build/promote/status/smoke13 PASS, Chromium 24/24 источника/возврата, WebKit 12/12 fullinitial и native source/return/compact/resize/expand 100/200%. Начальный и поздний кадры стабильны, JS errors 0;100%, размер 1040×680 и пауза восстановлены. Все продуктовые файлы совпадают с F256 `2db93353241297b835a922f59dcd22be20dde52f` + F257df223; это явно отдельный интеграционный SHA, не SHA PR.

SC-003 независимо принят: одинаковая AX-опора 204vsKrisp 198, отклонение 6 px при допуске 8 px; CSS unchanged. VoiceOver и тема приняты владельцем. Прямая загрузка экспортируемой ссылки проверяется в Chromium/WebKit; пользовательского direct-URL входа в GRAF Dev нет(N/A), кнопка источника проверяется в WKWebView отдельно.

Окончательные статусы, команды и границы доказательств — [validation/closeout.md](validation/closeout.md), история FAIL→исправление→повтор — [validation/ui-matrix.md](validation/ui-matrix.md). Старые CI и установки не квалифицируют новый SHA. T001–T010 выполнены. GitHub governance-fast продуктового 4273ab [PASS](https://github.com/yshishenya/graf/actions/runs/34287778786); для итогового документационного коммита проверка повторяется перед снятием draft.

Новые редакторы, AI Chat, папки и назначаемые задачи исключены пользователем. Провайдер AI в Dev отключён: реальный отказ с сохранением документа не называется успешной генерацией. F256 владеет плеером, F6788 — нативной навигацией и уведомлениями; эти продуктовые функции не включены в PR F257. Чужие изменения общих инструментов сохранены вне коммитов. Full CI/release-full, merge, production и выпуск не выполнялись.


## Готовность дополнения выбора формата — 2026-09-09

Требования FR-020–024, R53/R54, уточнение, plan/contracts/quickstart и T012–T015 готовы. Независимый reviewer: `checklists/format-picker-ux.md`8/8 PASS; analyze CRITICAL0/HIGH0/MEDIUM0, coverage5/5. Mandatory ensure PASS; новые задачи #6854–6857 имеют четыре уникальных владельца, обратное чтение и scoped `validate_issue`4/4 PASS. Можно начинать T012/T013. Глобальный mandatory validate выполнен, но FAIL на несвязанной F6790 #6852; это исходный дефект трекера, основной агент принял ограниченный gate F257 без правки чужой задачи.

Код, runtime, GRAF Dev и новый SHA этим заключением не проверены. T012–T015 открыты. Историческая приёмка выше не распространяется на дополнение. Коммит/установка не выполнены; T015 явно сохраняет отдельные разрешения и гейты.

Дополнительная локальная проверка `check_spec_kit_governance.py` запущена: FAIL окружения bootstrap frozen doctor — установлен specify1.0.4/ref cb610277 вместо закреплённого1.0.1/ref9118ed15, состояние github-issue-canon отличается от lock. Lock/toolchain этим дополнением не менялись. Это не PASS repository governance; требуется устранить/повторить перед PR.

`git diff --check` и `python3 scripts/validate-changelog-fragments.py`: PASS. Повторное обратное чтение #6854–6857 после уточнения путей T012: scoped validate4/4 PASS.


## Промежуточная проверка реализации — 2026-09-09

Независимый review нашёл P2 видимости назначения; причина устранена отдельной прокруткой списка, повторное чтение PASS. Duplicate Escape удалён. Продуктовых пробелов FR-020–024 в прочитанном объёме не выявлено; документационные названия initSummaryFormats/data-summary-format-extra приведены к реализации без изменения требований. Результаты178PASS/3FAIL/1SKIP и повтор исправленных3PASS, baseline15PASS, scoped16PASS/1SKIP записаны раздельно в validation/format-picker.md со ссылкой на сообщение исполнителя. Browser ещё выполняется; T014/T015 остаются открытыми. Tasks при промежуточном converge не менялись.


Итог дополнения: T012–T014 выполнены локально, Chromium/WebKit PASS, review/Ponytail исправления проверены, Ruff/node/diff/changelog PASS. Подробности и границы пересекающихся наборов — validation/format-picker.md. T015 и issue closeout открыты: новый коммит/PR/current-SHA governance, установленный GRAF Dev и полная приёмка не выполнены. Прежние ограничения local governance/глобального canon выше не скрыты.
