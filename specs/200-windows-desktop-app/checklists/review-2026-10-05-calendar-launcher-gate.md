# T119 Round236: ограниченная проверка требований launcher adapter

Дата: 2026-10-05. Независимый reviewer-owned результат.

**Вердикт: требования приняты; C0 / H0 / M0; 5 checked / 0 unchecked.**
Блокирующих дефектов требований в пяти пунктах `calendar-launcher.md` нет.
Допуск относится только к описанному минимальному adapter и последующей
независимой проверке его исходников. Наличие будущего кода, тестов SDK и
установленного приложения не требуется для отметки качества требований и
не утверждается этим отчётом.

## Основание и границы

Лично прочитаны текущий подраздел plan «T119: Windows launcher adapter —
2026-10-05», затронутые положения bridge §10, дополнения data-model §8,
quickstart §13 и research. Прежние утверждённые требования operation/lease,
FR-002/005/006/015 и SC-002/006/009 использованы только в затронутом контексте;
весь Feature200, transport, storage, capture и остальные задачи не проверялись
заново. Канонические branch/HEAD и хеши прочитаны заново, dirty работа сохранена.

Применён проектный `speckit-checklist`: отметки означают качество требований,
а не выполнение реализации. Прочитаны применимые AGENTS/guidance/constitution;
их неизменные ранее прочитанные части не расширяют область этой проверки.
Полоса проверки — ограниченный requirements gate внутри существующего
high-risk T119, а не перевод задачи в low-risk. Более широкие обязательные
проверки и release gates остаются в силе.

Собственный pinned Mac `CalendarMeetingOpener.swift` повторно прочитан для
преобразования целей, pin `721b5125d799ea798a4af0b3625e18d3c1109039`.
Оценка не основана на предварительном C0/H0/M0 основного агента.

## Независимая оценка всех пяти пунктов

| Пункт | Решение и фактическое основание |
| --- | --- |
| CHK001 | Принят. Bridge §10 и plan:1259–1267 разделяют validated HTTPS, native target и browser-only. Zoom host/path/digits и фильтрация query `action`/`confno`, Teams `/l/meetup-join/`, Telemost HTTPS association соответствуют собственному pinned Mac; native port только отсутствующий/443, остальные поддержанные HTTPS — browser-only. Нет выбора приложения по `provider_family`, произвольной схеме или EXE discovery. SDK Available/launch true не подтверждают личность получателя или вход во встречу. |
| CHK002 | Принят. Plan:1269–1277, bridge:482–486, data-model:329–335, quickstart:486–489 явно разделяют discard-only отмену, natural Completed/Error и indeterminate Status/Canceled. Последнее не разрешает drain: безопасный terminal UI без handoff/Record, busy/handle удерживаются до доказанного natural completion либо явного выхода/перезапуска. Нет принудительного освобождения по таймеру; resolver 15s не становится сроком OS query/launch или ожидания пользователя. |
| CHK003 | Принят. Plan:1279–1287 и bridge:487–492 различают rejected до OS-вызова, busy без изменения старого child, startFailed после throw/null без полученного handle и started с удержанием handle даже после reentrant cancel. StartFailed разрешает завершить только синхронный dispatch scope и его ticket; отсутствие OS side effect/underlying exit не обещается. Автоматический fallback запрещён. Это устраняет прежнюю неоднозначность основания completion, не подменяя его физическим доказательством. |
| CHK004 | Принят. Plan:1265–1267,1285–1293 и прежний operation lifecycle bridge §10 сохраняют одного общего owner, отдельные operation/work identities и matching drain. Guard ставится до подготовки/current predicate/dispatch/poll; fresh current проверяется непосредственно перед OS dispatch. Query сам ничего не запускает; следующий child выбирает owner после соответствующего completion и fresh current. Никаких автоматических launch/recovery/Record; свежий resolver после явного подтверждения сохраняет original request opening и исходный action expiry. |
| CHK005 | Принят. Quickstart:484–493 и plan:1294–1300 задают проверяемые target/SDK outcomes, reentry, delayed Started, no-Cancel, indeterminate faults, browser flags и границы TU-local fake statics с настоящими WinRT interfaces. Эти проверки не являются реальным запуском приложения. Installed receiver, auth, dialog, bridge/current owner, launcher и Record остаются отдельными доказательствами; T119 и SC не объявлены выполненными, capture/release gates не изменены. |

## Уточнения, закрывающие прежние вопросы к дизайну

1. **Неопределённое завершение.** Status exception и unsolicited Canceled
   нельзя превращать в matching drain или разрешение нового запуска. Явный
   выход/перезапуск — граница восстановления приложения, не доказательство,
   что уже переданная OS работа отменена или её последствия исчезли.
2. **Ошибка старта без handle.** Допускается завершение локального синхронного
   dispatch scope, не заявление «OS ничего не сделала». Поэтому запрещён
   автоматический fallback; дальнейшее действие/recovery должно быть явным и
   заново проходить разрешение/current проверки по bridge §10. При полученном
   handle эта ветка уже неприменима.
3. **Natural terminal и результат.** Достоверный Completed/Error завершает
   принадлежащий adapter API child; исключение GetResults после этого — ошибка
   результата, а не неопределённость Status. Это не доказательство входа во
   встречу, личности получателя или завершения работы запущенного приложения.

Эти различия поддерживаются первичными источниками: explicit Cancel способен
завершить клиентский proxy до underlying completion, поэтому обычный шаблон
update cancellation не переносится как доказательство drain.
[Microsoft: Async-Async cancellation](https://devblogs.microsoft.com/oldnewthing/20250212-00/?p=110857),
[Microsoft: C++/WinRT cancellation sequencing](https://devblogs.microsoft.com/oldnewthing/20220916-00/?p=107191).
Пять query statuses различаются; AppUnavailable/Unknown не означают доказанное
отсутствие приложения. Browser-only recovery использует IgnoreAppUriHandlers.
[Microsoft: LaunchQuerySupportStatus](https://learn.microsoft.com/en-us/uwp/api/windows.system.launchquerysupportstatus?view=winrt-26100),
[Microsoft: IgnoreAppUriHandlers](https://learn.microsoft.com/en-us/uwp/api/windows.system.launcheroptions.ignoreappurihandlers?view=winrt-26100).

## Условия последующей проверки реализации — не новые дефекты требований

Source review должен подтвердить фактическое удержание полученного handle,
отсутствие OS Cancel/Close при отмене действия, защиту от reentry до вызова
current predicate, различие Status/GetResults faults, сохранение старого child
при busy и отсутствие автоматического второго запуска. Fake SDK tests должны
проверить это на интерфейсной границе; они не доказывают physical receiver exit.
AppMain/owner/dialog integration и установленный сценарий потребуют собственных
доказательств. Этот gate не утверждает их наличие и не закрывает T119.

Новые build/test/VM/probe/GitHub операции не выполнялись. Нормы, product code,
tasks, прежние checklists/reports и dirty работа основного агента не изменены.
Единственные записи reviewer — `calendar-launcher.md` и этот отчёт.

## Точные байты рассмотренных документов

Канонический repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Это HEAD dirty worktree, не утверждение, что приведённые ниже документы входят
в этот commit.

| Документ | SHA-256 |
| --- | --- |
| plan.md | `671583ea24ede889639288a4cd1ae76084ceae7c79117999824d96f672cd77f9` |
| contracts/windows-native-web-bridge.md | `10c1eb80dbad80c3df77c94a3cf695706c4e366196357760bd4de93d1c0cecbe` |
| data-model.md | `2ed451fc65324392f29244cf1abb24ba7c5fa368e1e43136dcfff6a054f4322a` |
| quickstart.md | `345f6dd4093d5ac1a80de248419b793325a7f349ddb257fe9c594936798da256` |
| research.md | `d2dc903cadc10b0837f283a80bdc40cf53c1fa927dde2cf961ff4bfd1523a6fa` |
| spec.md, без изменения этого scope | `0073b6f2ff8e3e9f07389473cf7fc0f5c2eaf146961f08426d140163dd5d4fe2` |
| tasks.md, без изменения этого scope | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |

Итог: **C0 / H0 / M0, блокеров requirements gate нет; 5/0.**
Это reviewer-owned решение о требованиях к минимальному adapter, не source
approval, не functional handoff и не приёмка всего T119.
