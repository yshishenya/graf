# T113: фактическое удаление в источнике перед копией

База `94e1d147bce2f90eb9bd4b16152e24d73964bc7d`, F273/T113/#7804,
`high-risk-product`, Legacy Impact: `untouched`.

## Исправление

Прежняя `_backup_lifecycle` принимала completed/purge metadata и реестр,
не проверяя оставшиеся строки журнала. Новый фиксированный EXISTS через
удержанную reduced source-сессию отклоняет остатки точного закрытого аккаунта
или всей категории при подтверждённом category-case. Payload не читается.
Проверяются штатный контекст, SELECT, ENABLE/FORCE RLS, ровно одна точная policy
из существующего rec-db-verify.py и каталог local_retention. Неполная видимость
не считается отсутствием строк. Всё читается в прежней RR read-only transaction.

Source-only helper переиспользует прежние parser/replay_accounts, проверяет
собственную хронологию scheduled/canceled/completed, отсутствие преждевременного
purge до cooling и противоречивых результатов. Просроченное незавершённое
закрытие отклоняется. Для category нужен applied и фактическое отсутствие строк;
accepted account допустим с authoritative DB purge-result. Новое applied может
быть идемпотентным повтором с 0 строк: его время/count не приравниваются старой
операции. Наблюдаемое applied после записанного срока подсчитывается отдельно
в digest, исторические сроки прямо остаются unverified; blanket вечного запрета
новой копии после исправленной просрочки нет.

## Проверки

- Unit RED:14 отказов из-за отсутствующего helper (не14 доказанных уязвимостей).
- Native RED: с настоящим finalizer/purge-result вставленная вновь строка
  закрытого аккаунта не вызвала отказ старого кода: DID NOT RAISE.
- Первый native запуск имел пропущенный тестовый импорт ActivationHold; после
  исправления импорта причинный RED повторён, журнал сохранён.
- Первые две проверки:16 passed/56 deselected/2 warnings.
- После форматирования imports: окончательный unit-профиль33 passed/2 warnings.
  Общий профиль завершён:365 passed/37 skipped/29 deselected/2 warnings
  за252,52с; включает21 native PG17 scenario (18 coherent-copy + source + account/category replay).
  Пропущенные Linux/прочие условия и29 исключённых тестов не объявляются пройденными.
- Ruff --ignore E721, git diff --check, Spec Kit governance и development-process
  проходят. В первом вызове имя development-process было ошибочно написано
  с подчёркиваниями; исправленный штатный check-development-process.py пройден.

Native matrix использует собственную PG17 с503 closure requests, настоящее
закрытие и8 оставшихся записей. Проверяет точные остатки/непричастные записи,
скрывающую/изменённую policy, NO FORCE/DISABLE RLS, отсутствие SELECT, неверную
роль/context, изменение закрытого реестра, overdue scheduled, accepted/applied
категорию с остатками и без них, отдельный идемпотентный повтор. После каждой
обратимой подмены baseline повторяется, транзакции закрыты. Общий профиль
включает старый account/category replay и все18 coherent-copy сценариев.
Ресурсы принадлежат штатным fixture, production/Dev не используются.

Журналы: `.dev/growth/t113-source-lifecycle-{red,native-red,first,second,profile,units-final}-20261030.log`.
Проект до кода: [независимый отчёт](t113-source-lifecycle-design-review-20261030.md).
[Независимое ревью кода](t113-source-lifecycle-code-review-20261030.md):
SCOPED CODE PASS, P1=0/P2=0,117 требований перечитаны/0 открыто.
Полная готовность не принимается этим результатом.

## Граница

Это только два уже поддержанных v2 scope. Lifecycle остальных трёх локальных
категорий, standalone functions/RLS dependencies/jobs, полная retention,
верхние initial/verify/actual restore/resume, shell/CD и T112 остаются прежним
объёмом T113. Учебный CLI по-прежнему ограничен собственными учебными именами;
его replay_accounts не изменён. Источник/реестр/writers не изменяются этим
reader. Оба общих unconditional HOLD сохранены. Рабочего T0, ready, IP или
аналитики, выпуска и закрытия #7804/AC01–AC06 нет. Это не трафик и не продажи.

## Сверка остатка

Фактические source postconditions сопоставлены с FR-025/048/050 и текущим
T113: новый дефект в этом участке устранён, новых неучтённых задач не найдено.
Полный converge F273 не выполнялся, состояние converged не заявляется; известные
незавершённые работы сохранены в существующих T109–T113/проекте оператора.
Расширять задачи дублями ради этого узкого изменения не требуется.
