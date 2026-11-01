# T106 — независимое before-code ревью публичного контроля согласия

Дата: 01.11.2026. Проверяющий: `/root/public_counter_readiness_review`.
Полоса: high-risk active Spec Kit; только качество требований до кода.
Worktree: `/Users/yshishenya/.codex/worktrees/growth-protocol-result/crisp`.
Активный pointer: F273/T106, ветка `codex/f273-public-permission-20261101`,
source baseline `c6f42e8c7dec50ba769216feab4a80b70b50959a`.

**Первый проход — HOLD: checked 3 / unchecked 3; P1 1, P2 2.** На момент
первого прохода реализация не допускалась. Текущий результат повторной
проверки приведён в завершающем разделе ниже.
Основной агент получил причинный restore сценарий и полный список замечаний;
исправления договора обещаны, но ещё не прочитаны и не приняты этим проходом.

## Прочитанные доказательства и пределы

- Полный новый `contracts/public-consent-control.md`, SHA-256
  `efc0ede9219a81cea02871dff89509b50ce189033335c745f7746b9bf20b5e16`.
- Новый Session2026-11-01 clarify/spec appendix и применимые FR-001/002/003/
  004/006/007/008/048/049/050/051/059; plan/research/quickstart appendices,
  data-model добавление и существующие правила разделения/хранения.
- Существующий T106 и зависимые открытые lifecycle/runtime задачи; текущий
  .specify/feature.json. Задачи и общие reviewer отметки не изменялись.
- Конституция и guidance document-reading/spec-kit-flow/product-gates,
  release-and-validation; неизменность ранее прочитанного PRD/status/gates
  подтверждена SHA-256 в разрешённом владельцем scoped reread F273.
- Существующие browser relay/consent handlers, normalize/route/delivery,
  PostHog wrapper, PostgreSQL/advisory/file-lock примеры из предыдущего
  read-only прохода. Поведение same-category callback сверено с поставляемым
  настоящим `static/public/cookieconsent.umd.js`: change event вызывается
  при изменении категорий/сервисов, а не при повторе того же набора.

Это не live проверка. Кода ещё нет; PostgreSQL/браузер/сеть/сборки/тесты/
GitHub/runtime не запускались. Формальный последующий analyze/issue sync
остаётся обязательным. Документы основной фичи не переписывались.

## Проверка каждого пункта

| Пункт | Итог | Доказательство и предел |
| --- | --- | --- |
| CHK001 | PASS | Договор строки20–54: внутренний SHA-256 consentId, случайный epoch, закрытые категории/copy_version/server time, self-hosted PostHog, view_id сохранён; сырой ID/digest не экспортируются, не идут в уровни1/2 или аккаунт. RLS и bounded admission заявлены. Это контроль выбора, не новый аналитический профиль. |
| CHK002 | PASS | Строки64–81,99–117: read не разрешает, каждый revoke меняет epoch, grant CAS только текущего epoch/редакции после свежего явного выбора, нет auto-rebase/retry grant, ошибки не объявляют успех; grant меняет epoch и не оживляет старый payload. Смысл переходов определён. Исполнимость повторного UI выбора требует уточнения CHK004, restore имеет отдельный CHK005. |
| CHK003 | HOLD | Общий digest advisory lock и удержание до bounded transport заданы, включая отсутствующую строку, drain/cancellation/ambiguous. Но 5с относится только transport; нет конечного ожидания lock/DB/commit и порядка digest/admission lock. См.F2. |
| CHK004 | HOLD | RLS по transaction-local digest, deny при его отсутствии, named maintenance/без BYPASSRLS,16MiB admission, body1024/same-origin/no-store и pending role=status заданы. Но успешные ответы revoke/grant не определены точно; actual library same-category повтор не покрыт. См.F3. |
| CHK005 | HOLD | until_decision, обязательный отдельный случай удаления и full dump/inventory/lifecycle/restore quarantine заданы. Однако изменение epoch только положительных восстановленных строк позволяет повторить старый grant из отрицательной копии. См.F1. |
| CHK006 | PASS | Quickstart appendix требует реальную временную PostgreSQL, два процесса, causal transport baseline→revoke commit→0new, replay/новый grant/рестарт/restore/failures/cancellation, настоящую CookieConsent и отсутствие SDK. Runtime/readback/T0 и fullT106/T113 явно не принимаются. Это достаточные общие измеримые требования, уточняемые конкретными сценариями F1–F3. |

## F1 — P1: восстановление отрицательной строки возвращает допустимый старый grant

Договор строки123–130 обновляет epoch только положительных записей.
Причинный контрпример:

1. Копия содержит necessary-only запись с epoch E.
2. После копии пользователь явно разрешает аналитику запросом grant(expected=E),
   затем отзывает её; текущий сервер хранит другой epoch и запрет.
3. Восстанавливается копия. Запись уже отрицательная, поэтому указанное
   правило её epoch E не меняет.
4. Повтор ранее отправленного grant(expected=E) проходит CAS без нового
   явного действия. После него может пройти новое событие.

Это нарушает FR-001/003/049 и обещание не оживлять старые решения.
Нужны инвалидизация epoch **всех** восстановленных контрольных строк до
снятия карантина либо эквивалентная серверная restore-generation и запрет
допуска до завершения этой операции. Отдельный causal профиль обязан
начинаться именно с отрицательной строки в копии; positive-only профиль
этого дефекта не видит. Прежние approved restore/lifecycle gates сохраняются.

## F2 — P2: нет конечной границы ожидания DB/блокировок

Договор строки49–53,78–95 задаёт admission и digest locks и transport5с.
Ожидание самой блокировки, DB connect/read/write/commit и всего control request
не имеет конечного принятого бюджета. Общий порядок захвата digest/admission
lock тоже не задан. Сериализация отдельных HTTP до5с не ограничивает очередь
запросов, удержание connection pool или ожидание недоступной БД.

Нужны конкретные бюджеты ожидания и ошибок для control route и pre-send path,
единый порядок блокировок, закрытый исход timeout/commit unknown без success
или автоматического grant. Требование drain не должно превращаться в
бесконечное ожидание или освобождение lock до завершения транспорта.
Приёмка: удержание lock из другого процесса, исчерпание бюджета, отсутствие
новой передачи/положительного ack, сохранение продукта и корректный drain.
Новые сервисы или дополнительные общие gates для этого не нужны.

## F3 — P2: недостаточно точный API handshake и повтор того же выбора

Read имеет описанный ответ, revoke/grant — только запрос и смысл перехода.
Успешные HTTP status/JSON для них не заданы, хотя browser обязан получить
новый epoch именно принятого revoke, затем сделать CAS grant этого решения.
Нужно явно описать success body/epoch и отправку ответа только после commit;
поздний read не должен автоматически подменять ожидаемый epoch/rebase grant.

Требование «выбор можно повторить» должно работать при прежнем наборе
категорий — например, после grant503/потери server epoch. В поставляемой
CookieConsent повтор того же набора не вызывает onChange, а onConsent по
договору запрещено использовать для выдачи grant. Нужен определённый путь
нового явного действия и actual library профиль: тот же набор после отказа,
первое согласие, дубли библиотечных callback, поздний ответ и чужая вкладка.
Автоматический grant из onConsent/storage либо вызовов без действия не
является исправлением. Дополнительное согласование владельца не требуется:
это исполнение уже выбранной обратимости, не новая цель обработки.

## Не закрытые этим узким ревью границы

Внешний SDK/Метрика/replay/offline/IP, опубликованные тексты, фактические права,
working backup/restore, provider readback, global basis register, полный T106,
T113/T0 и коммерческая цель сохраняют прежние HOLD. Отдельный контрольный
реестр не доказывает удаление ранее переданных данных или ответ получателя.
Пункты других security/privacy/infra checklist не изменены.

## Контрольные суммы прочитанных проектных документов

- constitution: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`
- PRD: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`
- current status: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`
- product gates: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`
- release guidance: `ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f`
- spec: `97663e9c246c20d1f95fef2a85968638deecc4550c62f990089c05f3a9f91925`
- plan: `c1233f0fa723af1cc835ce57390e9ae10cfe06553c8027e5392171f494834a30`
- tasks: `a2f641d6e6b21830260232daed6c414002dcf175eb96414a2c837c1cf77e1ae4`
- quickstart: `cbdcfd084b9cbedb87ca29ace1dd7663a8eadc2145508422b349a3afa5228de1`
- data-model: `a167c60afd0bdc85d05b6243c43e6ad7708d2c9d54703ff8a37b3b112f8b3893`
- research: `973bc558431f4522f325f03ab5d54200a5dacdaf57377183606b9246e1f52069`

Изменены только reviewer-owned checklist и этот отдельный отчёт. Итоговый
checklist перечитан после правки: checked3/unchecked3. Никаких решений за
основного агента в spec/plan/tasks/code/Git/runtime не внесено.


## Повторная независимая проверка исправлений F1–F3, 01.11.2026

**Текущий итог: PASS требований до кода; checked6 / unchecked0;
незакрытых P1/P2/HIGH в проверенном узком договоре нет.**
Это заменяет первый HOLD как текущий вердикт, сохраняя его причинную историю.

Полностью перечитаны изменённый договор и весь новый quickstart-сценарий;
остальные spec/plan/data-model/research/tasks имеют прежние SHA-256.

- Договор: `2bb000b982db96230c75d97037d85e91a3dd02ad7a24f5d892e42b08304e8f3e`.
- Quickstart: `9ebf2119dd16e932331b464ab722ed7b71808713b0d1dd67ac22f7f44902f4a0`.

| Пункт | Повторный итог | Прямое доказательство |
| --- | --- | --- |
| CHK003 / F2 | PASS | Единый порядок digest→admission только для отсутствующей строки; второй digest не берётся, admission-владелец не ждёт digest. Для control request/delivery общий6с, включая connection/context/locks/read/write/transport/commit; transport≤5с внутри остатка. Timeout до доказанного commit даёт503 choice_unavailable без accepted/epoch/auto-grant. Отмена не освобождает lock раньше bounded drain. |
| CHK004 / F3 | PASS | Точные revoke/grant HTTP200 bodies только после commit; read без accepted; error без epoch. expected_epoch берётся только из принятого revoke текущего явного выбора, не из read/rebase. role=status имеет доступные кнопки повторить отказ/подтвердить выбранное разрешение; повтор тех же категорий не зависит от onChange. Quickstart требует actual CookieConsent профиль после503/утраты epoch. |
| CHK005 / F1 | PASS | До снятия restore quarantine сбрасываются все строки, включая necessary-only, с новыми случайными epoch. Quickstart прямо требует отрицательную строкуE в копии, последующие grant(E)/revoke и отказ replay grant(E) после восстановления. until_decision/отдельное обязательное удаление/full dump/inventory/lifecycle и working gates сохранены. |

CHK001/002/006 повторно сверены на согласованность с этими изменениями;
добавленные ответы/бюджеты/restore не меняют их ранее принятые границы.
Шесть флажков подтверждают качество требований, а не пройденные тесты:
реализация и причинные проверки ещё впереди. Общие security/privacy/infra
HOLD, внешний SDK/Метрика, actual provider/readback, опубликованные тексты,
backup/restore runtime, полный T106/T113/T0 и коммерческая цель открыты.

Следующий gate основного агента — analyze C/H0 и связь существующей T106/#7696,
затем реализация с обозначенной RED/GREEN и независимым code review/converge.
Новые решения/разрешения владельца этим ревью не подменяются.
Тесты/сеть/БД/код/Git/GitHub/runtime не трогались. Изменены только данный отчёт
и reviewer-owned checklist; итоговый checklist полностью перечитан:
**checked6 / unchecked0**.
