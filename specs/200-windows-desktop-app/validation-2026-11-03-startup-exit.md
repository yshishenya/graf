# T108: первый выход после частично неудачного запуска

Дата: 2026-11-03. Существующий F200, `high-risk-product`, T108 / #7342.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; проверяется рабочий снимок.
Рабочая копия: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.

**Нативная регрессия PASS: исправленный порядок закрывает окно после одного
нажатия; контроль с прежним порядком не закрывает окно без повторного Quit.**
Это приёмка ограниченного случая в WinUI, не всего T108 или Windows-продукта.

## Что именно проверено

Предыдущее независимое shell review обнаружило пропуск повторного exit polling:
если startup завершался ошибкой после запуска фоновой работы, ранний return
при shellReady=false пропускал создание stateTimer. Первый Quit запрашивал
остановку, но не дожидался ещё работающего потока. После его завершения
некому было повторно проверить exitWorkDrained и закрыть окно.

Продуктовый timer уже перенесён перед ранним return; этот проход не меняет
AppMain.cpp, а добавляет исполняемую нативную регрессию ранее проверенной правки.
Она сохраняется в существующем генераторе `prepare-appmain-problem-ui.mjs`
как сценарий `startup-exit` и в `AppMainStartupExitUiLaunch.inc`.
Существующий friend peer получил один управляемый startup-поток.

В производной тестовой копии сохранены исходные Closing/Closed, stateTimer
с его настоящим расположением, requestExit/beginExit/exitWorkDrained,
refreshNativeState и showStartupError. Генератор проверяет совпадение блока
Closing/Closed/timer и 14 именованных неизменённых участков исходника.
Подменён только ранний attribution/activation preamble, добавлен наблюдатель,
capture создан с отдельным несуществующим GUID-путём и неготовым тестовым AEC,
вместо дисковой startup validation установлен управляемый нативный поток,
после чего вызвана искусственная startup-ошибка до создания reminders.
Заголовок явно обозначает тестовое окно. Настоящие аккаунты, настройки,
установленный пакет, WebView, микрофон, запись и trust не используются.

Контролируемый поток владеет настоящим Windows handle и StorageStartupWork.
Он не выполняет дисковую/криптографическую проверку: ожидает тестовый event,
затем устанавливает terminal и завершается. Поэтому здесь принимается
реальная проверка окончания потока и цикл выхода WinUI, а не storage IO.
Ожидание потока ограничено 10 секундами; наблюдатель имеет отдельные deadlines.

Наблюдатель через существующий SDK ButtonAutomationPeer вызывает реальное
событие кнопки «Закрыть GRAF» один раз, проверяет exitRequested и незавершённый
drain. UI продолжает получать ticks, пока поток удерживается. После release
наблюдатель не вызывает refreshNativeState или повторный Quit: штатный
stateTimer должен сам довести окно до Closed. Спасательный повторный Quit
после deadline навсегда устанавливает failed и не может получить PASS.
Отдельный launcher ограничивает процесс 20 секундами; forced cleanup — FAIL.

## Нативные результаты

Обе сборки: Visual Studio Release/x64 в Parallels Windows, MSBuild exit 0;
222 frozen source-файла совпали до/после сборки и запуска.

| Проверка | Исправленный порядок (GREEN) | Контроль прежнего порядка (RED) |
| --- | --- | --- |
| PE SHA-256 | `fb9763242b8446bcf67f4c2b8384b7db8ec8bf89eb04a1b0b153b149195da9ba` | `380f4beb0680e67e52bda240a983ab541766d29f1824e61a984579d21937d61a` |
| Первый Quit при занятом потоке | first_quit=1, held=1 | first_quit=1, held=1 |
| Ticks во время удержания | 4 | 5 |
| Число вызовов выхода | 1 | 2, второй только rescue |
| Завершение потока / drain | 1 / 1 | 1 / 1 после rescue |
| Созданные файлы capture root | Нет | Нет |
| Нативный exit | 73 | 3 |
| Результат launcher | native_pass=true | native_pass=false, red_rejected=true |
| Установленный EXE | Не изменён | Не изменён |

RED меняет только один файл производной копии: тот же неизменённый timer-блок
переносится ниже return при shellReady=false. Это контролируемое возвращение
прежнего расположения, а не утверждение о запуске старого выпущенного пакета.
Остальные входы и проверяемые методы совпадают. GREEN не использует rescue;
RED потребовал его и был отвергнут — проверка различает нужное поведение.

После RED возвращены все 222 GREEN-входа и точный GREEN EXE. Удалён только
тестовый RED AppMain.obj, чтобы последующая линковка не использовала объект
с другим расположением timer. Временная копия green.exe также удалена.
Postflight: app=0, owned browser=0, установленный GRAF `0.1.0.14 / Ok`.
Основные продуктовые исходники не изменялись; текущие 222 Windows-входа
совпадают с исходным source.json этого опыта.

## Привязка свидетельств

Отдельный каталог проверки:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/startup-exit-sahz6bkv`.
В нём Build.ps1 / Build-Red.ps1, Run.ps1 и Restore-Green.ps1 сохраняют точные
входы, code/PE pins, stdout/stderr и terminal-квитанции. Это временный стенд,
не часть поставки. Для подготовки исходников используется:

```sh
node apps/windows/scripts/prepare-appmain-problem-ui.mjs \
  <repository> <empty-directory-outside-repository> <AppMain-SHA256> startup-exit
```

| Артефакт | SHA-256 |
| --- | --- |
| source.json | `f872955666384058c2683ee4ddb722abebf41b378e05164ab1a2ac428210ffb1` |
| test-source.json | `a0539dfae584c74b873ff721c23437583d976a6d3c9a6cd82707ee2ca7bd9054` |
| appmain-test-bindings.json | `9afc51665e35758a1e243317309909b4cd00acdf97288f8133c5aa866e8ee759` |
| build-result.json | `7722fffd48fde74b6eaee236f0ff4b94e42bf388cd6041a6866a2dcf0450157f` |
| green-ui.err | `786f61d366c6e401272721adf590bdaba43c01f4c25a7691b7b33d71a734f4fb` |
| green-result.json | `bf383e698ba6b59f2e97e8bb8de2f9574507429600f94cf85a0bb0d194c8dc86` |
| red-control.json | `35f4130929c8b603a8412ebdcaabce1a10bb1afcf25350628d0b49bce87e706e` |
| red-test-source.json | `988cb30be591cbe153d09a0db1519651d84b3d426d380645520b99b75a776ba2` |
| red-build-result.json | `ff249d237230d8bfc81954443a51c165a995117ff3b4726b85c985c158e5821a` |
| red-ui.err | `50a029283ecd916b85ba91426b1342985a1a5556e488f9d5c989b33c1d18a2de` |
| red-result.json | `6b4f09c88dbda73d5fcee8c7d3763c9dab9859bb31e855659a373854911998a0` |
| restore-green.json | `893a9b522c17d5a54ca773ebeefaba1947122f91d78b84a7ef70abfc2de892e0` |

## Что этим не закрывается

T108 и issue #7342 остаются открытыми: запись/пауза/finalizing, крестик при
доступном/потерянном трее, возврат той же сессии и Stop ещё требуют полной
приёмки установленного MSIX. Работа реального storage worker с IO не заменена
данным управляемым потоком в требованиях T116/T118. Не принимаются аппаратная
x64-матрица, 60 минут записи, доступность, авторизация/загрузка или выпуск.
Всего по tasks.md остаются 27 открытых задач; их маркеры не менялись.

Live issue #7342 проверен: OPEN,
`[200][P1][ux] T108: Закрывать окно без остановки записи`, labels feature:200,
priority:P1, area:ux, gate:pr-blocker, type:bug. GitHub-состояние не изменялось.
Коммит, push, PR, merge и установка в этом проходе не выполнялись.


## Финальная проверка после устранения зависимости теста от задержки VM

Ponytail review обнаружил конкретную неточность fixture: если первый tick после
Invoke задержится дольше 500 мс, прежний код освободит поток при heldTicks=1,
а Closed отклонит исправное приложение, поскольку требует минимум два ticks.
Условие release дополнено `heldTicks >= 2`. Это единственная следующая правка;
она не меняет ни один продуктовый метод и не может разрешить PASS после rescue.
Временной deadline и независимый внешний timeout сохранены. Дополнительные
зависимости или механизмы финализации не добавлялись.

Для точных новых байтов выполнен отдельный повтор в
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/startup-exit-final-2ywiz46z`.
Прежние квитанции sahz6bkv остаются свидетельствами предыдущего варианта.

Первый финальный RED build **отклонён**, несмотря на MSBuild exit 0:
Copy-Item сохранил раннее время заранее созданного исходника, и сборка
использовала старый AppMain.obj. Проверка свежести обнаружила
`STALE_APPMAIN_COMPILE`; EXE совпадал с GREEN. Нативный RED-тест на нём не
запускался. Неудачная попытка сохранена как red-stale-build-result.json,
red-stale-build.log/err. Повтор Build-Red-Retry.ps1 сверил RED-входы и сохранённый
GREEN pin, удалил только точный промежуточный AppMain.obj и получил новую
реальную компиляцию/линковку. Общая очистка проекта/данных не выполнялась.

Финальный результат:

- GREEN: build exit 0, 222 source до/после; PE
  `5e1561ff9a9e1d8b2aa15d2e99af6f9f7f5dc5278594783486adbb0453327f28`;
  один Invoke, held_ticks=5, released/drained/no_files=1, native exit=73.
- RED attempt 2: build exit 0 с новым AppMain.obj, 222 source до/после; PE
  `9825523509ee9b38823736a72ffdf3b2687a5d79233d411967ca85b1c2aef0e0`;
  native_pass=false, red_rejected=true, exit=3, rescue не засчитан как PASS.
- После проверки восстановлены все 222 GREEN-входа и точный GREEN EXE;
  удалены точный RED AppMain.obj и временная копия EXE; app/browser=0.
  Установленный `0.1.0.14 / Ok` и его EXE не изменялись.
- Текущие 222 Windows-входа совпадают с финальным source.json;
  product AppMain SHA-256 по-прежнему
  `a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0`.
- node --check генератора, git diff --check и отдельный whitespace check нового
  Launch.inc прошли. Показатель маркеров перечитан: 31 checklist-файл,
  477 checked / 0 unchecked; это инвентаризация, не принятие всей реализации.
- Во временном отдельном UV Tool окружении установлен точный Spec Kit 1.0.7
  ref `fe1d00e3ccaf495880aaf90fb0e17679e82f065b`; doctor --frozen
  (bootstrap 0.11.0) и check_spec_kit_governance.py прошли. Временное окружение
  удалено, глобальные инструменты и lock проекта не изменялись.

Финальные SHA-256:

| Артефакт | SHA-256 |
| --- | --- |
| source.json | `367d4c1bca8205dd32a19a99ef9b1f55f0d8bfa71109303263656de9885e4f5b` |
| test-source.json | `1436258ede9646fb4130e320db0d013181ccd9db672e09dcdcb8f230ace897f4` |
| appmain-test-bindings.json | `e7eedcfa5aa8bb828d188e44fc0f9b28439fbe697c36cf57a185f5f36313b067` |
| build-result.json | `923f5d58dcacbf1d4f3e624d431a63916503200364b1fadafe5d14baa29e9caa` |
| green-ui.err | `f2d3c30f4cc660e2b17f7f81e6e5469f3bef7b287bff685692ca4ea41cd03404` |
| green-result.json | `5ab30fbd64ccdaa391d6f26c2dd5628df327c42e619d1d22ee2d877941d21900` |
| red-control.json | `4aabdb15972182fcbfedab879ddcac3fe3e6f45124f283a45aed53f3b0562f64` |
| red-test-source.json | `2be447171660b184246102df2f09a852dd4b2beab5c1d7ddad8cedace3ff67bf` |
| red-stale-build-result.json | `09e4760f727e15e6377428cf146c664599eb3807cfa9eaead04e9c4ef1f758d9` |
| red-build-result.json | `b8d6becf32903d54685ad1cb8c069281506da9ad5dc80daf84a626be9a0e9a95` |
| red-ui.err | `74574a936dee257f22669320af8af71750597f4c930c4059d04318ec3d6d8d2f` |
| red-result.json | `5bd8ee5a2ed3006dfe0e5810235e6930361fb9a283cec0777adacb3c47a87c8e` |
| restore-green.json | `08ed6fc7a9df67411c8293ed98c997b369622c52204ba820f0556c3f20b0ce2f` |
| pinned-governance.log | `477bfba45e58bf0057cdea475ee3a608b14acf0b6d35e1f82cc95ccb85b788de` |

Новые T108/T109 задачи не закрывались. Полоса и границы приёмки прежние.


## Заключительное ревью и очистка временных копий

Независимое финальное ревью `review-2026-11-03-startup-exit-native.md`
завершено: C0/H0 в границах трёх тестовых файлов и обоих финальных запусков.
Точный хеш проверенной версии validation в reviewer report относится к тексту
до этого заключительного добавления о выполненной очистке.
После сверки рецензентом удалены только созданные этим проходом source/
и red-source/ в двух startup-exit каталогах. Перед удалением каждый файл
проверен по сохранённому manifest, запрещены symlinks и посторонние файлы;
225 файлов source/ и один red-source файл каждого опыта совпали.
Итоговые manifests, скрипты запуска, журналы, квитанции и контрольные суммы
сохранены. Windows build base остаётся активным для следующего F200 native
среза; старые чужие/исторические стенды не удалялись.

SHA-256 квитанций очистки:

- startup-exit-sahz6bkv/host-source-cleanup.json: `5322a0e26fb0cc166e3fa299e52d7048b4fc63905a5108b9d04cb535c4069f1b`.
- startup-exit-final-2ywiz46z/host-source-cleanup.json: `e6cbe1e9dfcd878f0e9b0d112ea5091821c4759d4b5858b590c5d5522545d159`.
