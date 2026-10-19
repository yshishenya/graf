# F136: независимая проверка границы сеанса

Дата: 2026-10-18. Reviewer: `review_f290_infra`.
Ветка: `codex/136-auth-navigation-recovery`.
Базовый HEAD: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Изменения не закоммичены; HEAD является базой, а не SHA исправления.
Режим проверки: **high-risk-product** — авторизация и навигация macOS.

## Решение

**Request Changes.** Найден один дефект P2, воспроизведённый двумя адресными
сценариями. Находок P0/P1 нет. Текущий срез T005/T006/T010/T017 не готов к
принятию до устранения и повторной проверки этого дефекта.

Качество требований подтверждено отдельно: **35 checked / 0 unchecked**.
Отметки checklist не заменяют проверку реализации. Требование об устаревших
callbacks уже явно записано в spec; нового пробела требований не обнаружено.

## P2: старое перенаправление снимает защиту новой принятой навигации

Место: `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift:651–659`,
`navigationDidRedirect`. В строке 659 безусловно очищается `pendingNavigationURL`.
Проверка `activeNavigation === navigation` недостаточна: новая action B уже
может быть принята, но её `didStart` ещё не заменил текущую identity A.

Последовательность, воспроизведённая через настоящие методы Coordinator:

1. A имеет активный объект `WKNavigation`.
2. Разрешён новый POST формы B. `observeNavigationRequest` устанавливает
   `pendingNavigationURL`, а `didStart(B)` ещё не пришёл.
3. Приходит поздний `didReceiveServerRedirectForProvisionalNavigation(A)`.
   Identity A всё ещё активна; новый callback очищает pending B и присваивает
   его URL старой навигации A.
4. Поздний `didFinish(A)` проходит `isCurrentNavigation`, поскольку pending
   уже пуст. Он завершает загрузку B: `isLoading` становится `false`.
5. Если документ A — `/login` после выхода, тот же старый finish дополнительно
   публикует новый `sessionBoundaryID` во время незавершённого нового входа B.

Это один дефект с двумя наблюдаемыми последствиями. Обычная защита от старого
finish без перенаправления работает, поэтому существующий тест этого случая
не обнаруживал ошибку. Преждевременная смена identity может пересоздать WebView
и прервать новую форму входа; сам факт смены UUID подтверждён пробой.
Утечка данных, изменение настоящих cookies или воспроизведение сетевым сервером
этой конкретной последовательности не заявляются.

Исправление должно различать подтверждение перенаправления A и новую
принятую action B, сохраняя поддержку обычного POST → 303 → GET. Проверки
должны включать поздние redirect/finish, redirect/failure и актуальное
перенаправление; простое исключение всех redirect callbacks нарушит уже
проверенный сценарий 303. Reviewer продуктовый код не изменял.

## Собственная адресная проверка

Перед сборкой прочитан `local-development.md`, свободно 258 GiB. Использован
отдельный временный Swift package с зависимостью на текущий `apps/macos`;
приложения GRAF/GRAF Dev не запускались, настоящие аккаунты не использовались.
В пакет скопирован существующий набор `DesktopCabinetSessionBridgeTests`,
класс переименован в `F136IndependentReviewTests`; добавлены две пробы.
WebKit использует `.nonPersistent()`. Пробы детерминированно передают
синтетические `WKNavigation`/`WKNavigationAction` реальным callback-методам.
Это проверка переходов состояния, не ручная приёмка установленного приложения.

Команда финального запуска:

```sh
swift test --package-path /private/tmp/graf-f136-review-m91ds8o9 \
  --scratch-path /private/tmp/graf-f136-review-m91ds8o9/build \
  --filter 'F136IndependentReviewTests/(testPreviousRedirectCannotFinishNewPendingForm|testPreviousLogoutRedirectCannotCommitBoundaryOverPendingLogin|testSameURLFormRejectsPreviousNavigationFinishBeforeNewStart)'
```

Результат: **3 выполнено / 1 PASS / 2 FAIL / 0 unexpected**, exit code 1,
0.870 секунды. Сборка успешна; ошибки получены на проверках состояния.

| Сценарий | Результат |
|---|---|
| testPreviousRedirectCannotFinishNewPendingForm | FAIL: `isLoading == false` после старых redirect/finish |
| testPreviousLogoutRedirectCannotCommitBoundaryOverPendingLogin | FAIL: `sessionBoundaryID` изменился при pending новом входе |
| testSameURLFormRejectsPreviousNavigationFinishBeforeNewStart | PASS: контроль без позднего redirect |

Исходник пробы, Package.swift, итоговый журнал и receipt сохранены отдельно:
`/Users/yshishenya/Documents/Codex/2026-10-16/graf-issue-by-issue/F136-independent-review-20261018/`.
Для повторения нужно создать временный пакет с `Package.swift` и
`Tests/ReviewTests/ReviewTests.swift` из сохранённых файлов. Полная сборка и
промежуточные зависимости в доказательства не сохранялись.

| Файл доказательства | SHA256 |
|---|---|
| ReviewTests.swift | `74c6659d6edf06e9816c3223fdc3faf41b5fc679d52a669e86fcc36ac17a3dd0` |
| Package.swift | `3311947d2be91c05dcf5ef1ba5f391b8f0b8eac21e9ebac0af2a1df770f5325d` |
| review-final.log | `28d8d1bc2263415f1342e6a924c50332b8e031cf67253eafa9190795b8c5b23c` |

## Привязка к текущим файлам и проверка прежних журналов

Хеши повторно вычислены после собственной проверки. Они совпадают с
`F136-current-validation-receipt-20261017.json` и
`F136-code-before-independent-review-20261017.json` во внешнем каталоге
`graf-issue-by-issue`. Базовый HEAD не выдаётся за SHA этих изменений.

| Текущий файл | SHA256 |
|---|---|
| apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift | `088f6cd4e39fbad420729c5c5cd799c52ee7b89c1ee2dfd52226a526917124f8` |
| apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift | `f5e6b28c65dd485dec56abc234f314e8b3e7db567a7b20039f5e27ef1ebf6e52` |
| changes/unreleased/F136.yaml | `53f19eff65ae9b8c88d6f03bc56f07daf5e3f1f545a08b480210d70ccc7c6c94` |

Проверены исходные журналы и их контрольные суммы:

- Исходный чистый RED: 8 сценариев, 1 PASS / 7 FAIL; отдельно redirect RED:
  1 FAIL. Первоначальный setup crash и промежуточный green с зависшей отменой
  явно исключены из приёмки.
- `F136-redirect-and-boundary-green-20261017.log`: 10 PASS.
- `F136-full-swift-20261017.log`: 1243 различных сценария, 1234 PASS,
  9 SKIP, 0 FAIL; 161.490 секунды. Собственным разбором журнала подтверждены
  1243 уникальных имени. SHA256:
  `ad4cd9dc0b91f26b00d0413cfc7d86b71a730c6d096f97faef39c60de12d8710`.
  Адресные 10 входят в полный набор и второй раз не суммируются.
- Пропуски: 7 проверок AppKit/focus и 2 необязательных экспорта изображений;
  они не считаются PASS. Receipt сообщает отсутствие принудительного skip override.
- ContractValidation PASS; SHA256 журнала
  `17189bd7192c0e37e850670a49ed6602566a183b4d772c368024c2674e389c87`.
- Governance PASS; SHA256 журнала
  `59cfeb588ee423427af9f09c0dfe4d3d2b36bbfcca7bbb8b49ba0f0b1ce6bceb`.

Эти результаты подтверждают проверенные сценарии, но не опровергают новый
адресный FAIL. Полный набор самостоятельно не перезапускался.

## Объём просмотра кода

Просмотрены diff реализации и регрессионных тестов, контроллер навигации,
attach/updateNSView, Coordinator policy/response/finish/failure/redirect/start,
download handoff/completion, popup, барьер авторизации и публикация SwiftUI
границы. Повторно найден каждый caller изменённых методов жизненного цикла.

- Обычные GET, POST200/error/cancel и POST303 представлены текущей матрицей.
  Отмена больше не оставляет `.loading`; это подтверждено журналами текущих файлов.
- Успешный `didFinish` сохраняет request identity, route и cabinet state до
  `commitPendingSessionBoundary`. Этот порядок верен для принятого актуального
  callback; найденный дефект позволяет ошибочно принять старый callback.
- При 401/выборе пространства `markSessionExpired` сразу закрывает защищённые
  команды и публикует границу; `canGoHome` учитывает `!sessionExpired`.
- Download callbacks завершают состояние по ожидаемому URL, исключая artifact
  из сохранения document history; сами по себе успешную session boundary не публикуют.
- Более поздний барьер авторизации F281 сохранён в diff. Старый ошибочно
  принятый finish также достигает `finishAuthNavigation`; изменение cookie или
  иной самостоятельный дефект безопасности этой проверкой не доказаны.

## Оставшиеся границы и checklist

T004/#4731, T011/#4738, T012/#4739 (OAuth/provider-link) и T016/#4743
(ручная проверка единственного GRAF Dev) остаются открытыми. Долг root-only
auth paths в `isSafeDocument`/`isSafeHistoryRequest` не объявляется устранённым;
историческая отметка T003 не считается текущей проверкой реализации.
T005/#4732, T006/#4733, T010/#4737 и T017 пока также не завершены.
Нельзя закрыть всю F136 по этому срезу даже после исправления находки.

Оба checklist перечитаны целиком после проверки. Основания всех отметок
остаются в [checklist-review-20261017.md](checklist-review-20261017.md).
Новый дефект противоречит уже существующему требованию CHK018 и spec о stale
callbacks; менять отметку качества требования из-за ошибки кода неверно.

| Checklist | Checked | Unchecked |
|---|---:|---:|
| requirements.md | 16 | 0 |
| auth-navigation.md | 19 | 0 |
| Всего | 35 | 0 |

Reviewer изменил только этот разрешённый отчёт, сохранил собственные небольшие
доказательства вне репозитория и удалил собственный временный пакет после их
сохранения. Код, тесты проекта, spec/plan/tasks, прежний отчёт требований,
GitHub, коммиты, выпуски и развёртывание reviewer не изменял.
