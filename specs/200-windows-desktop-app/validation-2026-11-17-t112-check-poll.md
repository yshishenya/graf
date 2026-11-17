# F200/T112 — сохранность незавершённой проверки обновлений

Полоса: существующий высокорисковый срез Spec Kit F200/T112. Legacy Impact: untouched.
Источник задачи: T112, issue #7346. Это промежуточное исправление, не закрытие всей задачи.

При исключении poll контроллер преждевременно освобождал запрос и разрешал вторую
проверку. Теперь сохраняет объект, запрашивает отмену один раз и ждёт конечного
состояния. Поздний ответ после ошибки, закрытия или таймаута не предлагает
установку. Проверка не блокирует запись и Stop. GetResults после Completed
отделён от неизвестного Status. Install и формат данных не изменены.

Сверка с требованиями среза: R1–R10 подтверждены независимым ревью; десять
сочетаний исключения, отмены, вложенных вызовов и позднего ответа используют
существующие Probe/Operation. Новых непокрытых задач этого исправления не выявлено;
оставшаяся приёмка уже принадлежит T112. Это не полный converge F200.

Проверки на точных исходниках:

- Воспроизведение до исправления: exit17, retained0/destroyed1/restarted1/starts2.
- После исправления: exit0, retained1/destroyed0/restarted0/starts1.
- Полный WindowsAppUpdateTests на Mac: обычный, C++17/O2/DNDEBUG с assertions,
  AddressSanitizer и UndefinedBehaviorSanitizer — compile0/runtime0.
- Windows QA ARM, PE x64: обычный тест и --native-no-package, два отдельных exit0,
  пустые журналы. Естественное завершение всего Job175ms; Forced/TimedOut=false.
  Побайтная копия EXE с SHA440b67cedf3cbe0bd841ad87c8532fa9bb3286984518201b2ae241d2c3e8aa94
  запускалась как GrafCoreTests.exe с внешним asInvoker manifest. Применение
  sidecar Windows отдельно не утверждается. Доверие и UAC settings не менялись.
- Независимое source и actual review: блокирующих замечаний нет.
- Governance с закреплённым CLI1.0.7, changelog fragments и diff whitespace — PASS.

Диагностические материалы: .dev/t112-poll-exception-20261117/ и
.dev/t112-sidecar-20261117/. Runtime-response SHA
c6d0b61f925d50ad6eedf01c29b9374f977de06c54ea7764a26fe8319a559c1f;
actual review SHA431bc185ff25af63a26af0140c2d66bbf4d1765f919b2ee0e9845a028574cf1f.
Source hashes controller/header/tests соответственно:

- 9eb03a0c520142d0e0ab94e12cc02b583b57c21a90c490f300d5cc19ed092406
- 4c90c0e8cfda2ae05ee99a3c337fd237d9868dc8dcc87d9bbfc827e85c96abc4
- b9e81dd659afb8b9d9e2f6595abdfff00a5326f5a51797b009fe4e50e2f219d1

Ограничения: исходный compile Job остаётся UNKNOWN из-за vctip, первый runtime
UNKNOWN из-за запроса UAC сохранён; отдельный diagnostic PASS их не заменяет.
Установленное окно, зарегистрированный подписанный канал, физическая x64,
T112/#7346 и выпуск остаются открытыми. GitHub checks точного SHA и merge
должны быть приняты отдельно; этот отчёт не подтверждает CI или публикацию.
