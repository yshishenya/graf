# F259 — фактический остаток и порядок завершения

Снимок GitHub: 2026-09-09T18:42:48.929631+00:00. Прочитаны состояния, тела и все доступные комментарии 279 исходных issues; пагинация комментариев полная. Статус GitHub — инвентарь, не новая содержательная приёмка.

**Решение владельца 2026-09-09:** до выкатки завершить весь бэклог аудита F259. Публикация и production-изменения отложены. Новые исходные требования не отменяются только ради уменьшения остатка.

**Остаток:** 257 OPEN, 22 CLOSED. Закрытые 22 относятся к B025/B026; их evidence проверяется отдельно перед итоговой приёмкой направлений. Родитель #6827 и этап #6837 не входят в исходные 279.

| Направление | Всего | Открыто | Закрыто |
| --- | ---: | ---: | ---: |
| B001 — Запуск записи и календарные уведомления | 9 | 9 | 0 |
| B002 — Сохранность локальных записей и отдельные инциденты | 3 | 3 | 0 |
| B003 — Сквозной путь запись → отправка → просмотр | 2 | 2 | 0 |
| B004 — Часовой установленный macOS pipeline | 1 | 1 | 0 |
| B005 — Восстановление обработки и правдивые состояния | 3 | 3 | 0 |
| B006 — Пустой экран после обновления Sparkle | 1 | 1 | 0 |
| B007 — Вход, привязка провайдера и история переходов | 7 | 7 | 0 |
| B008 — Незавершённые функции и приёмка биллинга | 16 | 16 | 0 |
| B009 — Решения по размещению данных и оплате | 2 | 2 | 0 |
| B010 — Биллинг в установленном приложении | 2 | 2 | 0 |
| B011 — Контакты, приглашения и реферальный цикл | 7 | 7 | 0 |
| B012 — Поддерживаемые приложения на живых звонках | 1 | 1 | 0 |
| B013 — Удобство экспорта для пользователей | 1 | 1 | 0 |
| B014 — Качество и задержка девяти форматов итогов | 1 | 1 | 0 |
| B015 — Эксплуатационная приёмка PostHog | 2 | 2 | 0 |
| B016 — Эксплуатационные хвосты выпуска | 1 | 1 | 0 |
| B017 — Общая приёмка среды разработки | 5 | 5 | 0 |
| B018 — Единая идентичность репозитория в рабочих копиях | 9 | 9 | 0 |
| B019 — Корректное выделение номера фичи | 8 | 8 | 0 |
| B020 — Настоящая проверка очереди слияния GitHub | 5 | 5 | 0 |
| B021 — Управляемое выведение legacy | 32 | 32 | 0 |
| B022 — Проверка соблюдения процесса разработки | 12 | 12 | 0 |
| B023 — Зависимость: Windows | 78 | 78 | 0 |
| B024 — Зависимость: системная админка | 40 | 40 | 0 |
| B025 — Зависимость: панель проигрывателя | 13 | 1 | 12 |
| B026 — Зависимость: страница итогов встречи | 11 | 1 | 10 |
| B027 — Зависимость: объединённые исправления встречи и уведомлений | 7 | 7 | 0 |

## Порядок завершения

1. Закончить уже начатый B019: общий PR F225/F259, генератор канонического umbrella, исходная приёмка F225, обязательный CI на точном SHA, слияние и live closeout. Ремонт последовательности из 67376a2ff включён в текущую ветку; повторная реализация не нужна.
2. B002/B004/B009: судьба трёх локальных записей, матрица часового macOS-прогона, подтверждения оператора по данным и оплате. Необратимые действия и реальные списания требуют отдельного конкретного разрешения.
3. B001/B003/B005–B007: сквозная запись, восстановление, обновление, OAuth. Проверки установленного приложения только в GRAF Dev, с согласованной версией и без конфликта с другими активными задачами.
4. B008/B010–B018/B020–B022: биллинг, контакты, качество, поддержка, окружение и процесс. Для каждого исходного issue восстановить точного владельца tasks.md и сверить все критерии; локальный [X] не равен принятому issue.
5. B023/B024: Windows (78) и системная админка (40) — отдельные существенные объёмы. Исходники Windows есть в отдельной ветке origin/codex/200-windows-desktop-app (54c897c16), но отсутствуют в master. Открыты T070/T071/T080–T083/T063: пакет/physical x64, WebView2, native UX, автозапись, актуальные server-контракты и итоговая приёмка. Админка существует в открытом PR #6788. Чужие изменения не перезаписываются, интеграция проводится через проверенный результат владельца.
6. B025–B027: проверить принятые интеграции и остающиеся umbrella; B028 учесть тестовые объекты; B029 — финальная сверка всех исходных issues и общего состава.

## Внешние условия и граница выкатки

- #5092 требует подтверждений размещения/трансграничной обработки и уведомлений; последние комментарии оставляют вопрос за оператором. Запрошено актуальное evidence.
- #5093 требует финансового/юридического согласования и реального подтверждения YooKassa. Зелёные локальные тесты этого не заменяют. Запрошено актуальное evidence.
- #3688 требует реального 60-минутного аппаратного прогона. Короткая или синтетическая запись его не заменяет.
- Часть исходных issues требует проверки после выпуска (production, Sparkle update). До выкатки можно завершить код, подготовку и предрелизные проверки; такие issues остаются открыты до фактического post-release evidence. Это не разрешение начинать выкатку и не основание объявить весь F259 завершённым.

## Исходные issues — текущие состояния

| Направление | Issue | Состояние GitHub |
| --- | --- | --- |
| B001 | [#6635](https://github.com/yshishenya/graf/issues/6635) | OPEN |
| B001 | [#6678](https://github.com/yshishenya/graf/issues/6678) | OPEN |
| B001 | [#6686](https://github.com/yshishenya/graf/issues/6686) | OPEN |
| B001 | [#6689](https://github.com/yshishenya/graf/issues/6689) | OPEN |
| B001 | [#6690](https://github.com/yshishenya/graf/issues/6690) | OPEN |
| B001 | [#6691](https://github.com/yshishenya/graf/issues/6691) | OPEN |
| B001 | [#6758](https://github.com/yshishenya/graf/issues/6758) | OPEN |
| B001 | [#6779](https://github.com/yshishenya/graf/issues/6779) | OPEN |
| B001 | [#6780](https://github.com/yshishenya/graf/issues/6780) | OPEN |
| B002 | [#4460](https://github.com/yshishenya/graf/issues/4460) | OPEN |
| B002 | [#4535](https://github.com/yshishenya/graf/issues/4535) | OPEN |
| B002 | [#5268](https://github.com/yshishenya/graf/issues/5268) | OPEN |
| B003 | [#1818](https://github.com/yshishenya/graf/issues/1818) | OPEN |
| B003 | [#1819](https://github.com/yshishenya/graf/issues/1819) | OPEN |
| B004 | [#3688](https://github.com/yshishenya/graf/issues/3688) | OPEN / REOPENED |
| B005 | [#5893](https://github.com/yshishenya/graf/issues/5893) | OPEN |
| B005 | [#5895](https://github.com/yshishenya/graf/issues/5895) | OPEN |
| B005 | [#5896](https://github.com/yshishenya/graf/issues/5896) | OPEN |
| B006 | [#5472](https://github.com/yshishenya/graf/issues/5472) | OPEN |
| B007 | [#4731](https://github.com/yshishenya/graf/issues/4731) | OPEN |
| B007 | [#4732](https://github.com/yshishenya/graf/issues/4732) | OPEN |
| B007 | [#4733](https://github.com/yshishenya/graf/issues/4733) | OPEN |
| B007 | [#4737](https://github.com/yshishenya/graf/issues/4737) | OPEN |
| B007 | [#4738](https://github.com/yshishenya/graf/issues/4738) | OPEN |
| B007 | [#4739](https://github.com/yshishenya/graf/issues/4739) | OPEN |
| B007 | [#4743](https://github.com/yshishenya/graf/issues/4743) | OPEN |
| B008 | [#4877](https://github.com/yshishenya/graf/issues/4877) | OPEN / REOPENED |
| B008 | [#4897](https://github.com/yshishenya/graf/issues/4897) | OPEN / REOPENED |
| B008 | [#4903](https://github.com/yshishenya/graf/issues/4903) | OPEN / REOPENED |
| B008 | [#4917](https://github.com/yshishenya/graf/issues/4917) | OPEN / REOPENED |
| B008 | [#4922](https://github.com/yshishenya/graf/issues/4922) | OPEN / REOPENED |
| B008 | [#4926](https://github.com/yshishenya/graf/issues/4926) | OPEN / REOPENED |
| B008 | [#4928](https://github.com/yshishenya/graf/issues/4928) | OPEN / REOPENED |
| B008 | [#4930](https://github.com/yshishenya/graf/issues/4930) | OPEN / REOPENED |
| B008 | [#4932](https://github.com/yshishenya/graf/issues/4932) | OPEN / REOPENED |
| B008 | [#4933](https://github.com/yshishenya/graf/issues/4933) | OPEN |
| B008 | [#4936](https://github.com/yshishenya/graf/issues/4936) | OPEN |
| B008 | [#4937](https://github.com/yshishenya/graf/issues/4937) | OPEN |
| B008 | [#4938](https://github.com/yshishenya/graf/issues/4938) | OPEN |
| B008 | [#5017](https://github.com/yshishenya/graf/issues/5017) | OPEN |
| B008 | [#5018](https://github.com/yshishenya/graf/issues/5018) | OPEN |
| B008 | [#5019](https://github.com/yshishenya/graf/issues/5019) | OPEN |
| B009 | [#5092](https://github.com/yshishenya/graf/issues/5092) | OPEN |
| B009 | [#5093](https://github.com/yshishenya/graf/issues/5093) | OPEN |
| B010 | [#5961](https://github.com/yshishenya/graf/issues/5961) | OPEN |
| B010 | [#5962](https://github.com/yshishenya/graf/issues/5962) | OPEN |
| B011 | [#4448](https://github.com/yshishenya/graf/issues/4448) | OPEN |
| B011 | [#4449](https://github.com/yshishenya/graf/issues/4449) | OPEN |
| B011 | [#4450](https://github.com/yshishenya/graf/issues/4450) | OPEN |
| B011 | [#4451](https://github.com/yshishenya/graf/issues/4451) | OPEN |
| B011 | [#4452](https://github.com/yshishenya/graf/issues/4452) | OPEN |
| B011 | [#4453](https://github.com/yshishenya/graf/issues/4453) | OPEN |
| B011 | [#4454](https://github.com/yshishenya/graf/issues/4454) | OPEN |
| B012 | [#3992](https://github.com/yshishenya/graf/issues/3992) | OPEN |
| B013 | [#4083](https://github.com/yshishenya/graf/issues/4083) | OPEN |
| B014 | [#5513](https://github.com/yshishenya/graf/issues/5513) | OPEN |
| B015 | [#3857](https://github.com/yshishenya/graf/issues/3857) | OPEN |
| B015 | [#3860](https://github.com/yshishenya/graf/issues/3860) | OPEN / REOPENED |
| B016 | [#6501](https://github.com/yshishenya/graf/issues/6501) | OPEN |
| B017 | [#6090](https://github.com/yshishenya/graf/issues/6090) | OPEN |
| B017 | [#6125](https://github.com/yshishenya/graf/issues/6125) | OPEN |
| B017 | [#6128](https://github.com/yshishenya/graf/issues/6128) | OPEN |
| B017 | [#6132](https://github.com/yshishenya/graf/issues/6132) | OPEN |
| B017 | [#6139](https://github.com/yshishenya/graf/issues/6139) | OPEN |
| B018 | [#6180](https://github.com/yshishenya/graf/issues/6180) | OPEN |
| B018 | [#6181](https://github.com/yshishenya/graf/issues/6181) | OPEN |
| B018 | [#6182](https://github.com/yshishenya/graf/issues/6182) | OPEN |
| B018 | [#6183](https://github.com/yshishenya/graf/issues/6183) | OPEN |
| B018 | [#6184](https://github.com/yshishenya/graf/issues/6184) | OPEN |
| B018 | [#6185](https://github.com/yshishenya/graf/issues/6185) | OPEN |
| B018 | [#6186](https://github.com/yshishenya/graf/issues/6186) | OPEN |
| B018 | [#6187](https://github.com/yshishenya/graf/issues/6187) | OPEN |
| B018 | [#6188](https://github.com/yshishenya/graf/issues/6188) | OPEN |
| B019 | [#6189](https://github.com/yshishenya/graf/issues/6189) | OPEN |
| B019 | [#6190](https://github.com/yshishenya/graf/issues/6190) | OPEN |
| B019 | [#6191](https://github.com/yshishenya/graf/issues/6191) | OPEN |
| B019 | [#6192](https://github.com/yshishenya/graf/issues/6192) | OPEN |
| B019 | [#6193](https://github.com/yshishenya/graf/issues/6193) | OPEN |
| B019 | [#6194](https://github.com/yshishenya/graf/issues/6194) | OPEN |
| B019 | [#6195](https://github.com/yshishenya/graf/issues/6195) | OPEN |
| B019 | [#6196](https://github.com/yshishenya/graf/issues/6196) | OPEN |
| B020 | [#6207](https://github.com/yshishenya/graf/issues/6207) | OPEN |
| B020 | [#6233](https://github.com/yshishenya/graf/issues/6233) | OPEN |
| B020 | [#6236](https://github.com/yshishenya/graf/issues/6236) | OPEN |
| B020 | [#6237](https://github.com/yshishenya/graf/issues/6237) | OPEN |
| B020 | [#6274](https://github.com/yshishenya/graf/issues/6274) | OPEN |
| B021 | [#6238](https://github.com/yshishenya/graf/issues/6238) | OPEN |
| B021 | [#6243](https://github.com/yshishenya/graf/issues/6243) | OPEN |
| B021 | [#6244](https://github.com/yshishenya/graf/issues/6244) | OPEN |
| B021 | [#6245](https://github.com/yshishenya/graf/issues/6245) | OPEN |
| B021 | [#6246](https://github.com/yshishenya/graf/issues/6246) | OPEN |
| B021 | [#6247](https://github.com/yshishenya/graf/issues/6247) | OPEN |
| B021 | [#6248](https://github.com/yshishenya/graf/issues/6248) | OPEN |
| B021 | [#6249](https://github.com/yshishenya/graf/issues/6249) | OPEN |
| B021 | [#6250](https://github.com/yshishenya/graf/issues/6250) | OPEN |
| B021 | [#6251](https://github.com/yshishenya/graf/issues/6251) | OPEN |
| B021 | [#6252](https://github.com/yshishenya/graf/issues/6252) | OPEN |
| B021 | [#6253](https://github.com/yshishenya/graf/issues/6253) | OPEN |
| B021 | [#6254](https://github.com/yshishenya/graf/issues/6254) | OPEN |
| B021 | [#6255](https://github.com/yshishenya/graf/issues/6255) | OPEN |
| B021 | [#6256](https://github.com/yshishenya/graf/issues/6256) | OPEN |
| B021 | [#6257](https://github.com/yshishenya/graf/issues/6257) | OPEN |
| B021 | [#6258](https://github.com/yshishenya/graf/issues/6258) | OPEN |
| B021 | [#6259](https://github.com/yshishenya/graf/issues/6259) | OPEN |
| B021 | [#6260](https://github.com/yshishenya/graf/issues/6260) | OPEN |
| B021 | [#6261](https://github.com/yshishenya/graf/issues/6261) | OPEN |
| B021 | [#6262](https://github.com/yshishenya/graf/issues/6262) | OPEN |
| B021 | [#6263](https://github.com/yshishenya/graf/issues/6263) | OPEN |
| B021 | [#6264](https://github.com/yshishenya/graf/issues/6264) | OPEN |
| B021 | [#6265](https://github.com/yshishenya/graf/issues/6265) | OPEN |
| B021 | [#6266](https://github.com/yshishenya/graf/issues/6266) | OPEN |
| B021 | [#6267](https://github.com/yshishenya/graf/issues/6267) | OPEN |
| B021 | [#6268](https://github.com/yshishenya/graf/issues/6268) | OPEN |
| B021 | [#6269](https://github.com/yshishenya/graf/issues/6269) | OPEN |
| B021 | [#6270](https://github.com/yshishenya/graf/issues/6270) | OPEN |
| B021 | [#6271](https://github.com/yshishenya/graf/issues/6271) | OPEN |
| B021 | [#6272](https://github.com/yshishenya/graf/issues/6272) | OPEN |
| B021 | [#6273](https://github.com/yshishenya/graf/issues/6273) | OPEN |
| B022 | [#6314](https://github.com/yshishenya/graf/issues/6314) | OPEN |
| B022 | [#6315](https://github.com/yshishenya/graf/issues/6315) | OPEN |
| B022 | [#6316](https://github.com/yshishenya/graf/issues/6316) | OPEN |
| B022 | [#6321](https://github.com/yshishenya/graf/issues/6321) | OPEN |
| B022 | [#6327](https://github.com/yshishenya/graf/issues/6327) | OPEN |
| B022 | [#6328](https://github.com/yshishenya/graf/issues/6328) | OPEN |
| B022 | [#6329](https://github.com/yshishenya/graf/issues/6329) | OPEN |
| B022 | [#6330](https://github.com/yshishenya/graf/issues/6330) | OPEN |
| B022 | [#6331](https://github.com/yshishenya/graf/issues/6331) | OPEN |
| B022 | [#6332](https://github.com/yshishenya/graf/issues/6332) | OPEN |
| B022 | [#6333](https://github.com/yshishenya/graf/issues/6333) | OPEN |
| B022 | [#6334](https://github.com/yshishenya/graf/issues/6334) | OPEN |
| B023 | [#5662](https://github.com/yshishenya/graf/issues/5662) | OPEN |
| B023 | [#5663](https://github.com/yshishenya/graf/issues/5663) | OPEN |
| B023 | [#5664](https://github.com/yshishenya/graf/issues/5664) | OPEN |
| B023 | [#5665](https://github.com/yshishenya/graf/issues/5665) | OPEN |
| B023 | [#5666](https://github.com/yshishenya/graf/issues/5666) | OPEN |
| B023 | [#5667](https://github.com/yshishenya/graf/issues/5667) | OPEN |
| B023 | [#5668](https://github.com/yshishenya/graf/issues/5668) | OPEN |
| B023 | [#5669](https://github.com/yshishenya/graf/issues/5669) | OPEN |
| B023 | [#5670](https://github.com/yshishenya/graf/issues/5670) | OPEN |
| B023 | [#5671](https://github.com/yshishenya/graf/issues/5671) | OPEN |
| B023 | [#5672](https://github.com/yshishenya/graf/issues/5672) | OPEN |
| B023 | [#5673](https://github.com/yshishenya/graf/issues/5673) | OPEN |
| B023 | [#5674](https://github.com/yshishenya/graf/issues/5674) | OPEN |
| B023 | [#5675](https://github.com/yshishenya/graf/issues/5675) | OPEN |
| B023 | [#5676](https://github.com/yshishenya/graf/issues/5676) | OPEN |
| B023 | [#5677](https://github.com/yshishenya/graf/issues/5677) | OPEN |
| B023 | [#5678](https://github.com/yshishenya/graf/issues/5678) | OPEN |
| B023 | [#5679](https://github.com/yshishenya/graf/issues/5679) | OPEN |
| B023 | [#5680](https://github.com/yshishenya/graf/issues/5680) | OPEN |
| B023 | [#5681](https://github.com/yshishenya/graf/issues/5681) | OPEN |
| B023 | [#5682](https://github.com/yshishenya/graf/issues/5682) | OPEN |
| B023 | [#5683](https://github.com/yshishenya/graf/issues/5683) | OPEN |
| B023 | [#5684](https://github.com/yshishenya/graf/issues/5684) | OPEN |
| B023 | [#5685](https://github.com/yshishenya/graf/issues/5685) | OPEN |
| B023 | [#5686](https://github.com/yshishenya/graf/issues/5686) | OPEN |
| B023 | [#5687](https://github.com/yshishenya/graf/issues/5687) | OPEN |
| B023 | [#5688](https://github.com/yshishenya/graf/issues/5688) | OPEN |
| B023 | [#5689](https://github.com/yshishenya/graf/issues/5689) | OPEN |
| B023 | [#5690](https://github.com/yshishenya/graf/issues/5690) | OPEN |
| B023 | [#5691](https://github.com/yshishenya/graf/issues/5691) | OPEN |
| B023 | [#5692](https://github.com/yshishenya/graf/issues/5692) | OPEN |
| B023 | [#5693](https://github.com/yshishenya/graf/issues/5693) | OPEN |
| B023 | [#5694](https://github.com/yshishenya/graf/issues/5694) | OPEN |
| B023 | [#5695](https://github.com/yshishenya/graf/issues/5695) | OPEN |
| B023 | [#5696](https://github.com/yshishenya/graf/issues/5696) | OPEN |
| B023 | [#5697](https://github.com/yshishenya/graf/issues/5697) | OPEN |
| B023 | [#5698](https://github.com/yshishenya/graf/issues/5698) | OPEN |
| B023 | [#5699](https://github.com/yshishenya/graf/issues/5699) | OPEN |
| B023 | [#5700](https://github.com/yshishenya/graf/issues/5700) | OPEN |
| B023 | [#5701](https://github.com/yshishenya/graf/issues/5701) | OPEN |
| B023 | [#5702](https://github.com/yshishenya/graf/issues/5702) | OPEN |
| B023 | [#5703](https://github.com/yshishenya/graf/issues/5703) | OPEN |
| B023 | [#5704](https://github.com/yshishenya/graf/issues/5704) | OPEN |
| B023 | [#5705](https://github.com/yshishenya/graf/issues/5705) | OPEN |
| B023 | [#5706](https://github.com/yshishenya/graf/issues/5706) | OPEN |
| B023 | [#5707](https://github.com/yshishenya/graf/issues/5707) | OPEN |
| B023 | [#5708](https://github.com/yshishenya/graf/issues/5708) | OPEN |
| B023 | [#5709](https://github.com/yshishenya/graf/issues/5709) | OPEN |
| B023 | [#5710](https://github.com/yshishenya/graf/issues/5710) | OPEN |
| B023 | [#5711](https://github.com/yshishenya/graf/issues/5711) | OPEN |
| B023 | [#5712](https://github.com/yshishenya/graf/issues/5712) | OPEN |
| B023 | [#5713](https://github.com/yshishenya/graf/issues/5713) | OPEN |
| B023 | [#5714](https://github.com/yshishenya/graf/issues/5714) | OPEN |
| B023 | [#5715](https://github.com/yshishenya/graf/issues/5715) | OPEN |
| B023 | [#5716](https://github.com/yshishenya/graf/issues/5716) | OPEN |
| B023 | [#5717](https://github.com/yshishenya/graf/issues/5717) | OPEN |
| B023 | [#5718](https://github.com/yshishenya/graf/issues/5718) | OPEN |
| B023 | [#5719](https://github.com/yshishenya/graf/issues/5719) | OPEN |
| B023 | [#5720](https://github.com/yshishenya/graf/issues/5720) | OPEN |
| B023 | [#5721](https://github.com/yshishenya/graf/issues/5721) | OPEN |
| B023 | [#5722](https://github.com/yshishenya/graf/issues/5722) | OPEN |
| B023 | [#5723](https://github.com/yshishenya/graf/issues/5723) | OPEN |
| B023 | [#5724](https://github.com/yshishenya/graf/issues/5724) | OPEN |
| B023 | [#5725](https://github.com/yshishenya/graf/issues/5725) | OPEN |
| B023 | [#5777](https://github.com/yshishenya/graf/issues/5777) | OPEN |
| B023 | [#5778](https://github.com/yshishenya/graf/issues/5778) | OPEN |
| B023 | [#5779](https://github.com/yshishenya/graf/issues/5779) | OPEN |
| B023 | [#5780](https://github.com/yshishenya/graf/issues/5780) | OPEN |
| B023 | [#5781](https://github.com/yshishenya/graf/issues/5781) | OPEN |
| B023 | [#5782](https://github.com/yshishenya/graf/issues/5782) | OPEN |
| B023 | [#5783](https://github.com/yshishenya/graf/issues/5783) | OPEN |
| B023 | [#6636](https://github.com/yshishenya/graf/issues/6636) | OPEN |
| B023 | [#6637](https://github.com/yshishenya/graf/issues/6637) | OPEN |
| B023 | [#6638](https://github.com/yshishenya/graf/issues/6638) | OPEN |
| B023 | [#6639](https://github.com/yshishenya/graf/issues/6639) | OPEN |
| B023 | [#6640](https://github.com/yshishenya/graf/issues/6640) | OPEN |
| B023 | [#6641](https://github.com/yshishenya/graf/issues/6641) | OPEN |
| B023 | [#6781](https://github.com/yshishenya/graf/issues/6781) | OPEN |
| B024 | [#6708](https://github.com/yshishenya/graf/issues/6708) | OPEN |
| B024 | [#6712](https://github.com/yshishenya/graf/issues/6712) | OPEN |
| B024 | [#6713](https://github.com/yshishenya/graf/issues/6713) | OPEN |
| B024 | [#6714](https://github.com/yshishenya/graf/issues/6714) | OPEN |
| B024 | [#6715](https://github.com/yshishenya/graf/issues/6715) | OPEN |
| B024 | [#6716](https://github.com/yshishenya/graf/issues/6716) | OPEN |
| B024 | [#6717](https://github.com/yshishenya/graf/issues/6717) | OPEN |
| B024 | [#6718](https://github.com/yshishenya/graf/issues/6718) | OPEN |
| B024 | [#6719](https://github.com/yshishenya/graf/issues/6719) | OPEN |
| B024 | [#6720](https://github.com/yshishenya/graf/issues/6720) | OPEN |
| B024 | [#6721](https://github.com/yshishenya/graf/issues/6721) | OPEN |
| B024 | [#6722](https://github.com/yshishenya/graf/issues/6722) | OPEN |
| B024 | [#6723](https://github.com/yshishenya/graf/issues/6723) | OPEN |
| B024 | [#6724](https://github.com/yshishenya/graf/issues/6724) | OPEN |
| B024 | [#6725](https://github.com/yshishenya/graf/issues/6725) | OPEN |
| B024 | [#6726](https://github.com/yshishenya/graf/issues/6726) | OPEN |
| B024 | [#6727](https://github.com/yshishenya/graf/issues/6727) | OPEN |
| B024 | [#6728](https://github.com/yshishenya/graf/issues/6728) | OPEN |
| B024 | [#6729](https://github.com/yshishenya/graf/issues/6729) | OPEN |
| B024 | [#6730](https://github.com/yshishenya/graf/issues/6730) | OPEN |
| B024 | [#6731](https://github.com/yshishenya/graf/issues/6731) | OPEN |
| B024 | [#6732](https://github.com/yshishenya/graf/issues/6732) | OPEN |
| B024 | [#6733](https://github.com/yshishenya/graf/issues/6733) | OPEN |
| B024 | [#6734](https://github.com/yshishenya/graf/issues/6734) | OPEN |
| B024 | [#6735](https://github.com/yshishenya/graf/issues/6735) | OPEN |
| B024 | [#6736](https://github.com/yshishenya/graf/issues/6736) | OPEN |
| B024 | [#6737](https://github.com/yshishenya/graf/issues/6737) | OPEN |
| B024 | [#6738](https://github.com/yshishenya/graf/issues/6738) | OPEN |
| B024 | [#6739](https://github.com/yshishenya/graf/issues/6739) | OPEN |
| B024 | [#6740](https://github.com/yshishenya/graf/issues/6740) | OPEN |
| B024 | [#6741](https://github.com/yshishenya/graf/issues/6741) | OPEN |
| B024 | [#6742](https://github.com/yshishenya/graf/issues/6742) | OPEN |
| B024 | [#6743](https://github.com/yshishenya/graf/issues/6743) | OPEN |
| B024 | [#6744](https://github.com/yshishenya/graf/issues/6744) | OPEN |
| B024 | [#6745](https://github.com/yshishenya/graf/issues/6745) | OPEN |
| B024 | [#6746](https://github.com/yshishenya/graf/issues/6746) | OPEN |
| B024 | [#6747](https://github.com/yshishenya/graf/issues/6747) | OPEN |
| B024 | [#6748](https://github.com/yshishenya/graf/issues/6748) | OPEN |
| B024 | [#6749](https://github.com/yshishenya/graf/issues/6749) | OPEN |
| B024 | [#6750](https://github.com/yshishenya/graf/issues/6750) | OPEN |
| B025 | [#6793](https://github.com/yshishenya/graf/issues/6793) | OPEN |
| B025 | [#6795](https://github.com/yshishenya/graf/issues/6795) | CLOSED / COMPLETED |
| B025 | [#6796](https://github.com/yshishenya/graf/issues/6796) | CLOSED / COMPLETED |
| B025 | [#6799](https://github.com/yshishenya/graf/issues/6799) | CLOSED / COMPLETED |
| B025 | [#6802](https://github.com/yshishenya/graf/issues/6802) | CLOSED / COMPLETED |
| B025 | [#6805](https://github.com/yshishenya/graf/issues/6805) | CLOSED / COMPLETED |
| B025 | [#6807](https://github.com/yshishenya/graf/issues/6807) | CLOSED / COMPLETED |
| B025 | [#6811](https://github.com/yshishenya/graf/issues/6811) | CLOSED / COMPLETED |
| B025 | [#6812](https://github.com/yshishenya/graf/issues/6812) | CLOSED / COMPLETED |
| B025 | [#6813](https://github.com/yshishenya/graf/issues/6813) | CLOSED / COMPLETED |
| B025 | [#6814](https://github.com/yshishenya/graf/issues/6814) | CLOSED / COMPLETED |
| B025 | [#6815](https://github.com/yshishenya/graf/issues/6815) | CLOSED / COMPLETED |
| B025 | [#6816](https://github.com/yshishenya/graf/issues/6816) | CLOSED / COMPLETED |
| B026 | [#6794](https://github.com/yshishenya/graf/issues/6794) | OPEN |
| B026 | [#6797](https://github.com/yshishenya/graf/issues/6797) | CLOSED / COMPLETED |
| B026 | [#6798](https://github.com/yshishenya/graf/issues/6798) | CLOSED / COMPLETED |
| B026 | [#6800](https://github.com/yshishenya/graf/issues/6800) | CLOSED / COMPLETED |
| B026 | [#6801](https://github.com/yshishenya/graf/issues/6801) | CLOSED / COMPLETED |
| B026 | [#6803](https://github.com/yshishenya/graf/issues/6803) | CLOSED / COMPLETED |
| B026 | [#6804](https://github.com/yshishenya/graf/issues/6804) | CLOSED / COMPLETED |
| B026 | [#6806](https://github.com/yshishenya/graf/issues/6806) | CLOSED / COMPLETED |
| B026 | [#6808](https://github.com/yshishenya/graf/issues/6808) | CLOSED / COMPLETED |
| B026 | [#6809](https://github.com/yshishenya/graf/issues/6809) | CLOSED / COMPLETED |
| B026 | [#6810](https://github.com/yshishenya/graf/issues/6810) | CLOSED / COMPLETED |
| B027 | [#6818](https://github.com/yshishenya/graf/issues/6818) | OPEN |
| B027 | [#6819](https://github.com/yshishenya/graf/issues/6819) | OPEN |
| B027 | [#6820](https://github.com/yshishenya/graf/issues/6820) | OPEN |
| B027 | [#6821](https://github.com/yshishenya/graf/issues/6821) | OPEN |
| B027 | [#6822](https://github.com/yshishenya/graf/issues/6822) | OPEN |
| B027 | [#6823](https://github.com/yshishenya/graf/issues/6823) | OPEN |
| B027 | [#6825](https://github.com/yshishenya/graf/issues/6825) | OPEN |
