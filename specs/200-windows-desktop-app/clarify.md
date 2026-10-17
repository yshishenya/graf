# Clarify: Windows desktop-приложение GRAF

Дата: 2026-08-23

Фича затрагивает capture, permissions, local custody, upload, high-risk UX и
WebView IPC, поэтому clarification обязательна. Пользовательский запрос уже
задаёт главную цель — Windows-версия должна быть семантически идентична macOS.
Оставшиеся решения зафиксированы как безопасные defaults, чтобы не блокировать
проектирование и не спрятать важные ограничения.

## Решения, принятые для планирования

| Область | Решение | Почему |
|---|---|---|
| Render capture | Полный default render mix через WASAPI shared loopback | Работает на Windows 10 22H2 и не требует Stereo Mix/драйвера |
| Process loopback | Не входит в первый Windows-срез | API требует более узкой build-матрицы и создаёт отдельный scope/identity contract |
| Microphone | Выбранный или approved default физический input через WASAPI shared mode | Сохраняет контроль пользователя и не зависит от виртуального маршрута |
| Clock/timeline | WASAPI timestamps + QPC mapping; одна bounded PTS timeline | Не склеивает независимые callback arrival times и wall clock |
| AEC | Тот же pinned WebRTC AEC3 C ABI, 48 kHz mono, 10 ms | Единый алгоритмический контракт с macOS |
| Web UI | Server-owned cabinet в WebView2, exact-origin route policy | Не создаёт второй кабинет и не даёт remote HTML native authority |
| Native UI | Record/Pause/Resume/Stop, indicator, permissions, custody, diagnostics | Эти состояния должны работать offline и при падении WebView |
| Auto-record | Verified target identity, countdown, explicit opt-in, reversible settings | Нельзя превращать Windows desktop app в скрытый global recorder |
| Distribution | MSIX/Windows App SDK stable, WebView2 Evergreen, signed package | Нужны rollback, runtime servicing и стандартный пользовательский install |

## Отложенные вопросы перед implementation

1. Утвердить список Windows meeting targets и способ доказать exact executable
   identity для каждого target. Имя процесса само по себе не является proof.
2. Подтвердить целевой порядок поддержки архитектур: x64 first с ARM64 gate или
   x64+ARM64 в первом public build.
3. Подтвердить product copy для предупреждения о full render mix: первый Windows-срез
   не изолирует звук Zoom/Teams от прочего звука устройства.
4. Провести hardware matrix для Media Foundation AAC encoder и Windows N;
   отсутствие encoder не должно скрыто превращать normal package в неполный.
5. После design review согласовать exact visual tokens/размеры с актуальным
   macOS build; web cabinet остаётся серверным, native shell допускает только
   необходимые Windows-specific affordances.

## Почему process-loopback отложен

Официальный Microsoft Application Loopback sample ограничивает захват деревом
процессов через `ActivateAudioInterfaceAsync`, но требует Windows 10 build
20348+. Это не покрывает Windows 10 22H2 build 19045, выбранный для совместимой
матрицы первого Windows-среза. Поэтому full render mix — честный общий знаменатель; isolation
может появиться только отдельной фичей с новым compatibility, identity,
privacy и rollback contract.
