# F211/T109 — независимое ревью реализации confirm

Дата: 2026-10-31. Основа `9b3edf7351b1421bac821db04b061a71891057c8`,
ветка `codex/211-macos-runner-migration`.
Полоса: `active Spec Kit slice`, FR064/SC026 → T109 → T106.

**SCOPED PASS реализации на просмотренном diff и завершённых локальных
доказательствах. Открытые P1: 0; P2: 0; CRITICAL: 0; HIGH: 0.**
Новый закреплённый native Swift6.0.3/SDK15.2 ещё обязателен; этот вывод
не принимает T109/T108/T106 или #7834 как завершённые.

## Область и прочитанные источники

Прочитаны полное назначение `/tmp/f211-t109-review-request.txt`, весь product
diff, актуальные дополнения FR064 в spec/plan/tasks/quickstart, validation,
fragment F211 и весь checklist runner-image. Требования и исходный failure
ранее проверены непосредственно в том же диалоге; их новая реализация
сопоставлена с принятым CHK008 и конституционными ограничениями II/VI/VII.

Заново прочитаны стандартный async wrapper, весь request/cancel/finish,
состояние Coordinator, trust predicate, dismantle/detach и все вызовы отмены
при навигации/ошибке/закрытии/завершении WebKit процесса. Полный файл шести
confirm tests прочитан при requirements review; при этом проходе подтверждены
его неизменный SHA256/байты HEAD и настоящие завершённые результаты каждого
из шести случаев. Общая новая приёмка остальных подсистем GRAF не заявляется.

Владение reviewer: только этот новый отчёт. Checklist и прежняя история не
редактировались. Все восемь пунктов перечитаны: **8 отмечено / 0 не отмечено**.

## Проверка diff и безопасности

Продуктовый diff строго ограничен одним файлом: **8 добавленных / 9 удалённых
строк**. Удалено только объявление confirm alias; optional callback method
заменён стандартным async WKUIDelegate requirement с `withCheckedContinuation`.
Других продуктовых правок в этом diff нет.

- **Правильная граница WebKit.** Метод больше не объявляет неподходящий
  callback `@MainActor @Sendable(Bool)`. Используется объявленный в SDK async
  requirement. Нет второго overload/delegate, `@objc`-подавления ошибки,
  условной SDK ветви или перехода на mock. Четыре других alias неизменны;
  рабочих consumers удалённого alias после замены не осталось.
- **Параметры и поток.** Сохранены те же webView, message, frame.documentRequestURL
  и frame.isMainFrame. Coordinator остаётся MainActor. Closure
  `withCheckedContinuation` непосредственно вызывает прежний request;
  новая Task/очередь/внешний исполнитель не добавлены.
- **Немедленный отказ.** Любой прежний guard вызывает callback(false) и сразу
  возвращает. Этот путь возобновляет continuation ровно один раз, не создаёт
  pending и не выдаёт неявное согласие.
- **Отложенный ответ.** При допустимом запросе единственный сохранённый callback
  содержит `continuation.resume(returning:)`. Продолжение не возобновляется
  в других новых местах; результата по умолчанию или отдельного timeout нет.
- **Однократность и повторный вход.** `finish` сначала проверяет UUID, затем
  очищает pending, keyboard monitor и observer, снимает sheet и лишь после
  этого отвечает. Поздний старый UUID, повторная отмена и повторный AppKit
  callback не могут повторно возобновить continuation. Второй одновременный
  request немедленно получает false и не заменяет первый.
- **Удержание и жизненный цикл.** Async вызов сохраняет состояние до ответа,
  что необходимо ожидающему WebKit. Pending callback захватывает continuation,
  а не новый замыкающий self helper. Существующие observers/monitor/alert
  callbacks используют weak self; завершение удаляет их. Закрытие окна,
  навигация, ошибки, WebKit process termination и явный detach разрешают
  pending через тот же false-path. SwiftUI dismantle действительно вызывает
  detach; освобождение suspended вызова не зависит от deinit coordinator.
- **Доверие и интерфейс.** Сохранились same-origin, main frame, отсутствие
  user/password в URL, разрешённые routes, attached/active/not-loading и
  not-terminated, видимое окно, отсутствие чужого sheet/pending. Настоящий
  NSAlert и кнопки прежние: Return/Cancel/Escape=false, явное Continue=true.

Независимая байтовая сверка доказала: от начала
`func requestJavaScriptConfirmation` **до конца исходного файла** всё совпадает
с HEAD. Confirm test также побайтно равен HEAD. Следовательно, существующие
guards, UI, lifecycle и проверки не переписаны ради прохождения.

## Исходный RED и фактические локальные результаты

Сохранён исходный [run41222159260](https://github.com/yshishenya/graf/actions/runs/41222159260)
на указанном HEAD: compiler nearly-matches, selector=false, затем отсутствие
настоящего alert; 1296 total, 9 прежних SKIP, 4 failures/1 unexpected.
Новая локальная компиляция другой среды сама по себе не закрывает этот RED
на закреплённом SDK; новый CI требуется отдельно.

Исполнитель явно подтвердил завершение полного локального XCTest и
ContractValidation с exit0. Reviewer прочитал законченные журналы, проверил
итоги и разобрал все testcase records:

| Проверка | Реальный итог |
| --- | --- |
| Шесть прежних confirm tests | 6 PASS / 0 SKIP / 0 FAIL, 7.165 s |
| Полный XCTest | 1296 total / 1287 PASS / 9 SKIP / 0 FAIL, 165.567 s |
| ContractValidation | PASS после штатного ожидания SwiftPM scratch lock |
| Discovery ↔ execution | 1296 уникальных IDs в обоих множествах, точное совпадение, дублей нет |

Все шесть имён confirm присутствуют с `passed`, включая настоящий
`testRealJavaScriptCancelAndKeyboardNeverRunProtectedAction`. Он сохранил
selector assertion, JavaScript completion, реальный sheet/alert и Return/Escape;
его локальный PASS подтверждает исполнение этих assertions в данном запуске.

Набор всех девяти skipped testcase IDs непосредственно сравнен с исходным
native журналом: **точное совпадение**, новых пропусков нет. Повторы suite
summary не суммируются; строка Swift Testing `0 tests` относится к отдельному
runner и не заменяет 1296 завершённых XCTest. В новых локальных журналах не
найдено nearly-matches для confirm или предупреждений этого wrapper о
continuation. Focused шесть пересекаются с полным прогоном и не складываются
в отдельный общий результат.

## Ограничения и следующие обязательные действия

Предметная реализация FR064 минимальна и не требует нового адаптера или
дополнительной тестовой службы. Это scoped code review, а не новый глобальный
анализ/приёмка всей F211, установленного приложения или релиза.

После коммита и синхронизации основы требуются неизменность просмотренного
macOS source, новый native build/XCTest/ContractValidation именно на
Swift6.0.3/SDK15.2, все три exact-SHA/base проверки и общий validator.
Планируемая основа `837594c9c2b61d440a64efd89970695050b768b3` в данном
отчёте ещё не принимается как выполненный rebase или проверка нового коммита.
T109/T108/T106 и #7834 остаются открытыми до этих ворот; выпуск, release-full,
GRAF Dev и production не выполнялись и не принимались.

Reviewer лично выполнял только чтение/search/diff/status, read-only сравнение
байтов/хешей, разбор завершённых журналов и testcase IDs, перечитывание checklist
и `git diff --check` (PASS). Тесты, сборки, приложение, БД, сеть, CI и
Git/GitHub mutations reviewer не запускал. Изменён только этот отчёт.
Контрольные суммы validation/документов ниже фиксируют именно просмотренную
версию; последующее документальное дополнение не переопределяет source proof.

## SHA256 просмотренных источников

| Путь | SHA256 |
| --- | --- |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `5c6b2f3cee584fa13765b00cfe27a17cbff2465eab615e85b373dbbd12fe96d2` |
| `apps/macos/Shared/Tests/EmbeddedCabinetJavaScriptConfirmTests.swift` | `2e6e3043b5228f7590bb8ac45a44568dcaa40d3f16313c3737072735b50b338e` |
| `specs/211-optimize-ci-cd/spec.md` | `79dc194215121e2298f7383ac2533e168abac6d88f1cf9feca982cc38da67d0d` |
| `specs/211-optimize-ci-cd/plan.md` | `75f3a225908cf9196d814a987ec3cecae8390f312d81517ebbf8a766d3807725` |
| `specs/211-optimize-ci-cd/tasks.md` | `eea9be4f7077df62d75fd2abb05f0a35a646383bc329fe763a71259fbc573d03` |
| `specs/211-optimize-ci-cd/quickstart.md` | `280b5746004b6aadd4cb462057ae47b4c203649894a5c3d09eb8689959ad4923` |
| `specs/211-optimize-ci-cd/checklists/runner-image.md` | `47859126f192e155da8d4c2ff87ccb726a78b9f59dd1bec7dd77af1507771e90` |
| `specs/211-optimize-ci-cd/review-confirm-requirements-20261031.md` | `cbe490ebe325ba2a29686e4d5f47fa36ce9a6ab07d1920e2abead7c7b21c6704` |
| `specs/211-optimize-ci-cd/validation-runner-image-20261031.md` | `3bb484f796f6641b6c2302fbef8310e278953821fc8bb1906321c540de7b5bf4` |
| `changes/unreleased/F211.yaml` | `266014f396905757d0031540cffc50934eb66615df6c02614c774c65af732b40` |
| `/tmp/f211-confirm-mismatch-excerpt.txt` | `74c84f5badd26398ae86b5c9af973873996208dde5a13bfb3049d831f3fad02b` |
| `/tmp/f211-native-attempt4.log` | `5f55af55b9467d3f37655b3fafba3dae5357158440f20e2f50fc050d28494d6d` |
| `/tmp/f211-t109-confirm-local.log` | `229d90fabbe9f45df2ff1d452602e4e6ecc39e524f46482b864d76f5fd2017c2` |
| `/tmp/f211-t109-all-local.log` | `f96bd823a01feaa85d7c63f342a9382dd68bf16faaa731f8beb3fff937a8d8ae` |
| `/tmp/f211-t109-contracts-local.log` | `f292705df22d1a5ab2b59d091d962c3d92ffb29646499f9a8739dafc411957db` |
| `/tmp/f211-t109-discovery.log` | `693e13ad8576e49303f682a2b937e29ff46e006359f1cc0e4155785c1355bc40` |
