# T106 — независимое промежуточное ревью браузерного выбора

Дата: 01.11.2026. Reviewer: `/root/public_counter_readiness_review`.
Worktree: `/Users/yshishenya/.codex/worktrees/growth-protocol-result/crisp`.
Область: новый browser diff analytics.js, _analytics.html,
build_public_analytics_context, real-CookieConsent public-consent-control test
и обновлённый controller test. Требования public-consent-control6/0 и договор
`2bb000b982db96230c75d97037d85e91a3dd02ad7a24f5d892e42b08304e8f3e`
переиспользованы без изменения. Это implementation review browser source,
не runtime/T0 и не завершение общего среза.

**Первый проход — HOLD, P1 1 / P2 0.** Текущий результат повторной
проверки ниже. Конкретный B1 немедленно передан
основному агенту. Прочие перечисленные ниже условия выглядят сохранёнными
по исходнику; собственные сетевые запросы/браузерные тесты не выполнялись.

## B1 — P1: кнопка повторного сохранения отказа может выдать grant

Места в analytics.js: choicePendingStatus около699–705,
savePublicChoice около754–803, retry click handler около1447.

Причинный сценарий с настоящей CookieConsent:

1. Новый пользователь выбирает положительные категории. В localStorage
   остаётся положительный набор; browser начинает обязательный revoke
   перед CAS grant.
2. Первый revoke возвращает503 или теряет ответ. revoked=false,
   choicePendingStatus(cookie,true) выводит сообщение об отключении и
   кнопку «Повторить сохранение отказа». Категории cookie при этом
   остаются положительными.
3. Пользователь явно нажимает эту кнопку с текстом об отказе.
   Handler без определения вида повтора вызывает savePublicChoice().
4. Повторный revoke успешен; choiceNeedsGrant(cookie)=true. Код отправляет
   grant по оставшемуся положительному набору, сохраняет epoch и запускает
   измерение. Кнопка об отказе стала действием, разрешающим аналитику.

Нужен явный режим повтора: действие «Повторить сохранение отказа» выполняет
только revoke и не выдаёт grant. Положительный набор можно подтвердить
отдельным действием с соответствующим текстом и новой безопасной
последовательностью, либо pending UX должен точно отражать намерение.
Read/storage/pageshow/onConsent не могут использоваться для автоматического
продолжения старого grant. Нужно согласовать локальное состояние/сообщение,
чтобы после revoke-only положительный старый cookie не объявлялся новым
разрешением. Это исполнение уже принятого opt-in/обратимого выбора,
не новая цель и не запрос дополнительного согласования владельца.

Приёмка: actual CookieConsent, положительные категории, revoke503,
клавиатурное нажатие именно «Повторить сохранение отказа» после восстановления
API; в запросах только revoke, сервер necessary-only,0optional events.
Отдельное подтверждение положительного разрешения должно быть явным и иметь
положительный текст. Текущий real-browser test проверяет revoke503 после
переключения категорий на necessary-only; он не видит этот positive-cookie
сценарий. Заявленный PASS5 не закрывает B1.

## Сохранённые условия по исходнику

- publicContext принудительно закрывает внешний counter/replay и не выдаёт
  counter ID; publicConsentControl не вызывает product SDK start. Product-only
  контроллер по отсутствию publicConfig сохраняет прежнюю ветку.
- Consent settings/control доступны при disabled measurement; autoShow
  зависит от enabled, а choiceNeedsGrant запрещает положительную выдачу при
  disabled. В шаблоне есть role=status/aria-live и обычная кнопка retry;
  настройки cookies остаются доступны через data-cc.
- Public choice использует существующий UUIDv4 CookieConsent и stored record;
  сравнивает consentId/revision/lastConsentTimestamp/categories. Принятый epoch
  хранится в cookie data, идёт только во first-party relay, view_id не заменён.
- save немедленно запрещает sends, очищает epoch, получает revoke, затем
  выдаёт CAS grant только из результата этого revoke и после проверки
  generation/фактической cookie. Положительный результат также проверяет
  state/UUID/редакцию/категории до запуска.
- Read не выдаёт grant, требует совпадения серверного и сохранённого epoch,
  редакции/категорий, а stale/late callback не перезаписывает новый выбор.
  Storage/resume закрывает старый serverChoice и заново читает состояние.
- Без server epoch положительный старый cookie не запускает события;
  общий canUseAnalytics дополнительно требует serverChoiceMatchesCookie и
  сохраняет прежние проверки local consent metadata.
- Control fetch omit credentials/no-store/redirect:error, с abort deadline;
  ошибки остаются локальным запретом, поля произвольного provider payload
  не добавляются. Отсутствие server accepted не объявляется успешным.
- startPublicTracking сохраняет dispatchOnce/каталог и session view_id;
  controller API sentEvents не приравнивается к provider readback.

Это source conclusions, а не пройденная эксплуатационная матрица.

## Прочитанный профиль и пределы доказательства

public-consent-control.test.cjs использует настоящую vendored CookieConsent,
loopback fake control и закрывает external routes. Прочитаны пять сценариев:
первый revoke→grant/read-only reload, отсутствие epoch+same-category retry,
necessary-only revoke503/keyboard retry, disabled measurement и late grant
с manual shared-storage refusal/resume. Последний подтверждает локальный
fail-closed, но manual localStorage write сам по себе не доказывает
server-accepted revoke из второй настоящей контролируемой вкладки.
Полный сценарий с двумя контроллерами и настоящим backend остаётся частью
итоговой causal приёмки; это не самостоятельная обнаруженная ошибка кода.

Обновлённый unit-style controller test сохраняет public control и product-only
ветку. Reviewer тесты не запускал; переданные PASS5/public+product-only
не объявляются собственными. Modal прогон во время поручения шёл и здесь
не принимается завершённым. Lifecycle/restore ещё WIP, внешнее включение
запрещено; общие privacy/security/infra HOLD, fullT106/T113/T0 остаются.

## Хеши прочитанного снимка

- analytics.js: `2e57a04acd1fb2f0e93b584e109b5de515fe2e8706f1c52a850916ae9885f8dd`
- _analytics.html: `9ead2649ee49c3d05c8739193f4a1f72c1f41c19cb6036eb33514aaa591a3c8d`
- analytics.py: `422cddff32102fd2428514f0109100b3d7a10d802228ed789e180e806a4dc818`
- public-consent-control.test.cjs: `b7d02a8404960bf1e5b1c2ae33220a78be06e91e670fb697027c6c6e32cb5352`
- public-analytics-consent.test.cjs: `9e8d83e759de9251b63f8eabf017f6872c31aaa501bc68a2ef664dc5baf7eb91`

Изменён только этот новый reviewer report. Код/spec/plan/tasks/checklist/
Git/GitHub/runtime и чужие изменения не менялись. Сеть/БД/браузерные
запуски reviewer не выполнял; другие агенты не создавались.


## Повторная проверка B1 после исправления

**Текущий узкий source-вердикт: B1 закрыт; новых P1/P2 в просмотренной
браузерной границе не найдено.** Общий срез WIP/HOLD сохраняется.

Полностью перечитаны изменённые choicePendingStatus/savePublicChoice/retry
handler и новый actual-CookieConsent сценарий положительного выбора с
revoke503. Текущие контрольные суммы:

- analytics.js: `14e8bbd3477465113241c6a361b751787fb0954d1e31430a2ba7de1e2038b265`
- public-consent-control.test.cjs: `0346bc100379c2e99ca0717d6d4c7a9e77336900ef1ad026a4c20bd914f49f21`

Status фиксирует retryRevokeOnly согласно своему тексту. Кнопка передаёт
этот режим в savePublicChoice; ветка выдачи grant теперь требует
!revokeOnly. После положительной cookie + отказного повтора сервер получает
только revoke, local epoch остаётсяnull/serverChoice отсутствует, поэтому
canUseAnalytics закрыт. UI сообщает сохранённый отказ и предлагает отдельное
«Подтвердить выбранное разрешение». Это уже новое явное положительное
действие; оно проходит собственную revoke→grant последовательность.
Ни read, ни resume, ни поздний ответ сами grant не выдают.

Прочитанный новый сценарий моделирует именно найденный контрпример:
положительный выбор → revoke503 → кнопка с отказным текстом → ровно один
revoke/0sentEvents → отдельная кнопка положительного подтверждения →
revoke,grant. Таким образом, прежний positive-cookie пробел не скрыт
necessary-only сценарием.

Проверки generation/фактической cookie, принятого epoch из revoke,
serverChoiceMatchesCookie и блокировка SDK/replay в новом изменении не
ослаблены. Product-only путь и доступные status/retry остаются отдельными.
Собственного запуска нового профиля reviewer не выполнял; в момент сообщения
основного агента этот прогон и focused45 ещё шли. Сообщённый standalone
modal PASS отмечается как переданное, а не самостоятельно повторённое
доказательство. Завершённые результаты должны войти в последующую общую
приёмку вместе с настоящим cross-tab server revoke и failure профилем.

Изменён только этот отчёт. Checklist6/0, код/spec/plan/tasks/Git/GitHub и
runtime не менялись, сеть/БД/браузерные тесты reviewer не запускались.
Lifecycle/restore, общие privacy/security/infra HOLD, внешний SDK,
полный T106/T113 и T0 не принимаются этим узким source-выводом.

## Финальное чтение nonmutating read и обновления кэша CookieConsent

Дата: 01.11.2026. **Узкий source-вердикт браузерной реализации: PASS;
новых конкретных P1/P2 в прочитанной границе не найдено.** Общие рабочие
ограничения и отдельная приёмка исполнения остаются в силе.

Снимок:

- analytics.js: `7df8e31fe61bceef93d5911ed768700ff987c78fec027a4bc9185ccba9ab8ce4`.
- public-consent-control.test.cjs: `319b69179aa4a7f48200dfb645753d0fb782ebb32017371a7bd6ffe702e38aa0`.

Дополнительно прочитана настоящая vendored CookieConsent: `getCookie`
обращается к общему хранилищу, `setCookieData` при изменении metadata сохраняет
кэш cookie библиотеки. `reset(false)` не удаляет сохранённый выбор, сбрасывает
экземпляр и обработчики библиотеки, позволяя `run` загрузить фактический cookie.

Теперь `acceptPublicChoice(cookie, epoch, persist)` пишет metadata/epoch только
при явном `persist=true` из save. Ветка read вызывает её без этого признака:
проверяет ранее сохранённую metadata, фактический cookie и epoch; ошибок
metadata не исправляет. В этой ветке нет `setCookieData`, записи-пробы
localStorage или сохранения категорий. Таким образом source-level путь,
способный записать старый кэш библиотеки при фоновом чтении, устранён.

Явная status-кнопка до записи делает `reset(false)` и `await run` с прежними
options и `autoShow=false`. В этот период установлен `choiceInFlight`, поэтому
автоматический `onConsent` не начинает read/grant. После загрузки повторно
проверяются generation и фактический выбор; затем сохраняется null epoch и
выполняется прежняя revoke/CAS-grant последовательность. Отказной повтор по B1
по-прежнему не выдаёт grant. Подтверждённая сервером выдача и локальные проверки
не подменяются одним успешным переинициализированием библиотеки.

Прочитаны два новых настоящих browser-сценария: вторая вкладка действительно
сохраняет отказ через control API, первая читает известный новый epoch и
сохраняет necessary-only cookie; затем неполная metadata с правильным epoch
не переписывается фоновым read, а явный повтор обновляет кэш и сохраняет отказ.
Control API в этом профиле — loopback fake, а не настоящий PostgreSQL backend.
Сценарий поэтому подтверждает browser/CookieConsent границу, но не заменяет
общую браузерно-серверную приёмку и фактическое чтение внешним получателем.

Доказательства не преувеличены: исходный обычный двухвкладочный сценарий
проходил и до этой правки, потому что при неизменной metadata библиотека не
записывала cookie. Воспроизведённый RED для этой гипотезы не заявляется.
Усиленный сценарий неполной metadata добавлен после правки. Основной агент
сообщил 8 пройденных browser-сценариев; проверяющий читал код, самостоятельно
прогон не выполнял и исходный журнал не принимал.

Изменён только собственный отчёт. Общее T106/T113, рабочее включение,
SDK/replay, T0 и коммерческий результат остаются за пределами этого PASS.
