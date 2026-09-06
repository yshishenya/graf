# F238: проверка отображения локальной записи и завершённости

Дата: 2026-09-06. PR: [#6504](https://github.com/yshishenya/graf/pull/6504).
Режим: `high-risk-feature follow-up` к F231, T007/T009. Рецензент — отдельный
агент выпуска; производственный JavaScript и XCTest им не изменялись.
Проверен исходный HEAD `6af20d3ba7eeaf87abd2043d898d8d58d8a359fc`.
Последующий коммит добавляет только этот отчёт и решение reviewer-owned
checklist; его точный SHA и новый governance-fast фиксируются в PR.

## Граница и решение

Изменение F238 ограничено читаемой датой, распознаванием технического заголовка
и пиктограммой удаления локальной строки. Новых функций записи, хранения,
удаления, отправки или открытия оно не добавляет. F231 spec/plan/tasks остаются
источником требований для существующих T007/T009; F238 — номер релизного
исправления, а не новая спецификация жизненного цикла.

Проверка качества всех 11 требований checklist завершена с отдельным
обоснованием каждого пункта. Сопоставление текущего кода с применимыми
требованиями и ограниченным изменением не выявило обязательных недоделок F238.
Это ограниченная проверка завершённости F238, не новое заявление о полной
convergence исторической F231. Старые задачи не переписываются и не получают
повторные отметки выполнения. Общее native/VoiceOver подтверждение выпуска
остаётся частью совместной приёмки интерфейса F240/F244.

## Проверенные границы

| Требование / задача | Наблюдаемое доказательство |
|---|---|
| FR-001, T007 | Русские названия проходят через textContent; небезопасная HTML-строка не вставляется как HTML. UTF-8 bridge не меняется. |
| FR-002–003, T007 | Пиктограмма аудио сохраняется; удаление использует существующую корзину, button/type и aria-label с отображаемым названием. Основное действие остаётся button с прежним data-meeting-open. |
| FR-004, FR-013 | canOpen/canDelete, непрозрачный local ID, main-frame/native policy и подтверждение удаления остаются в существующем потоке. Рецензент прочитал EmbeddedCabinetLocalRecordingBridge и renderer. |
| FR-005 | Код durationSeconds/sessionDurationSeconds и подпись неполной записи не изменены. |
| FR-009 | Отдельная локальная строка скрывается только при uploadComplete и существующей серверной строке; серверный DOM не получает local ID. |
| T007/T009, формат | Реальные функции из cabinet.js выполнены на синтетических значениях: 12 месяцев, ведущий ноль времени, 7 поддерживаемых технических префиксов, кириллица, пустое название, неверная дата и названия вне шаблона. |
| Plan / Constitution | Нет зависимостей, API, миграций, приватных путей, новых аудио/сетевых действий или изменений доверенной границы. SVG повторяет имеющуюся пиктограмму GRAF. |

Correctness/Ponytail review: блокирующих замечаний к этому diff нет.
Две небольшие функции и существующий renderer достаточны; новую библиотеку
форматирования или дополнительный путь действий вводить не требуется.

## Выполненная проверка

- `swift test --package-path apps/macos --disable-swift-testing --filter DesktopMeetingShellWebViewBoundaryTests`: **17 passed**, 0 failures.
- Исполнение извлечённых настоящих функций через Node `vm`: **27 примеров passed**;
  ещё **6 assertions passed** на textContent, aria-label, delete hook,
  canDelete/canOpen и условие uploadComplete.
- `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`: PASS.
- `python3 scripts/check_spec_kit_governance.py`: PASS.
- `git diff --check`: PASS перед коммитом.

Примеры были синтетическими; рабочие записи, аудио, серверные операции и
пользовательские данные не использовались. XCTest проверяет исходные контракты,
а не имитирует успешное нажатие в настоящем WKWebView.

Повторяемые примеры основных ветвей форматирования из корня репозитория:

```sh
node <<'JS'
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const s = fs.readFileSync('apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js', 'utf8');
const start = s.indexOf('  const SHORT_MEETING_MONTH_LABELS');
const end = s.indexOf('  let localRecordingRows', start);
assert.ok(start > 0 && end > start);
const api = vm.runInNewContext(s.slice(start, end) + '\n({formatMeetingListDate, localRecordingDisplayTitle})');
const startedAt = new Date(2026, 8, 6, 9, 5).toISOString();
assert.equal(api.formatMeetingListDate(startedAt), '6 сен, 09:05');
assert.equal(api.formatMeetingListDate('invalid'), 'На этом Mac');
assert.equal(api.localRecordingDisplayTitle({title: 'Zoom - 2026-09-06 09:05', startedAt}), 'Zoom — 6 сен, 09:05');
assert.equal(api.localRecordingDisplayTitle({title: 'План команды', startedAt}), 'План команды');
assert.equal(api.localRecordingDisplayTitle({title: '', startedAt}), 'Запись');
assert.equal(api.localRecordingDisplayTitle({title: 'Zoom - 2026-09-06', startedAt: 'invalid'}), 'Zoom - 2026-09-06');
console.log('F238 representative examples PASS');
JS
```

## Ограничения и следующий контроль

Название распознаётся по существующему ограниченному шаблону, потому что native
payload не содержит происхождение названия. Произвольный пользовательский текст
вне этого шаблона сохраняется; пользовательский текст, точно совпавший с шаблоном
технического названия, визуально форматируется так же. Это не изменение сохранённых
данных. Дата использует часовой пояс Mac, как прежний Intl.DateTimeFormat;
изменяется формат, а не политика часового пояса.

GitHub governance-fast обязателен на новом полном HEAD после документационного
коммита. Релизный Full CI, проверка объединённого интерфейса, подпись,
notarization и production gate принадлежат оператору общего выпуска.
F238 не закрывает umbrella F231; ссылки PR остаются Part of/Refs.
