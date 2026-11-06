# Независимое узкое ревью medium launcher — 2026-10-01

Вердикт: APPROVED NARROW для кода disposable ContextProof и средства запуска; не приёмка protected storage или приложения.
Режим: read-only code review по code-reviewer; единственная правка reviewer — этот docs-only отчёт. Прогоны, VM, UI и устройства reviewer не использовал.

## Точная привязка

- ContextProof.cpp SHA256: `78c3576b3fd3404f86c175dfc194a33e25a4a95b2dbf92c31863dd838fcd80b3` — проверен чтением/хешированием.
- Context EXE SHA256: `fe4694df521254fd2aa44a31a1f49042c2e3f6b63408c72422018a4383dfc54e` — ожидаемый runner, сборка /W4 /WX exit 0 сообщена main.
- context-run.ps1 SHA256: `cb661045f5b0201d8d8d486025c1291947ae6543ef8d5180dd2fa89c94b35a0b` — проверен чтением/хешированием.
- Неизменённый ProtectedMfProof.cpp SHA256: `141b5a293748703bf52fc50ce5d8c92a6f6df39c6a9f8fe389023e1c40b2f490` — проверен; EXE `60ccffd7a3daa6cc5607e1213a4af4e97ec90ea8248df697aab5a0b1cdd728ea` проверяется runner до/после.

## Проверенные свойства кода и ограничения

- ContextProof.cpp:14–19,57–66: GRANT_ACCESS добавляет TokenUser GENERIC_ALL к существующему DefaultDacl только созданного filtered token; буферы живы до завершения вызовов, новый ACL освобождается LocalFree через RAII. Объединение ACL не обещает побайтового сохранения порядка ACE.
- ContextProof.cpp:74–87: точный соседний ProtectedMfProof.exe запускается с `--medium` и тем же токеном; новый токен внутри прежнего `--launch-medium` не создаётся. ProtectedMfProof.cpp:202–210,235–236 проверяет фактические RID 8192 и отсутствие enabled Administrators membership перед проверками данных.
- ContextProof.cpp:79–85: собственный безымянный ненаследуемый Job, KILL_ON_JOB_CLOSE, CREATE_SUSPENDED → AssignProcessToJobObject → ResumeThread; ошибка назначения не разрешает выполнение дочернего кода. Таймаут 35 s завершает Job; обычный MF CreateProcessW потомок без breakaway входит в тот же Job. Новых блокирующих ошибок в этой обвязке не найдено.
- context-run.ps1:13–17,27,35–42: MF-режим только x64 и несовместим с другими флагами; внешний таймаут 45 s; несовпадение MF-хеша до/после останавливает принятие; собственный GUID-результат содержит режим, хеши, код завершения и вывод. Ненулевой код не маскируется.
- Остаточные границы: Context EXE-хеш после запуска записывается, но повторно не сравнивается; exact-result требует его совпадения с ожидаемым. `files=false` в CONTEXT_RESULT:73 относится только к диагностике родителя, не MF-дереву. Предел stdout 4096 означает длину принимаемого текста, не предел памяти; private_delta не peak, elapsed не Stop, index_publish не полная длительность commit.

## Сообщённые main результаты, не воспроизведённые reviewer

- Прежний controlled A/B: source `f8407e32ee7621fbdaa83ccd254a7dd248e40d978ce993678503a6c5d24726cc`, EXE `a80f5b6420ff121132cbece275f3480844b06e258f803997b1353aad22ada387`: `--spawn` child 0xc0000142 против `--spawn-user-dacl` exit 0, medium/no-admin, user ACE false→true. Это причинное свидетельство влияния private TokenDefaultDacl на минимальный запуск в данной среде, не идентификация конкретного отказавшего DLL/объекта. Новая Job-сборка не является повтором этого A/B.
- Main сообщил exact MF PASS для final 78c357…/fe469…/cb661…: ContextExit 0, stderr 0, child medium_nonadmin_verified=true; результат `context-result-9759c81a-affc-49e7-b00b-82d6d86f8fbc.json`. Reviewer не запускал и самостоятельно не воспроизводил runtime, файл результата не инспектировал.
- Сообщено: canonical 3840123 bytes full identity, 64 ranges,15 checkpoints,index_publish 26722 us,stop_tail 8771 us; fallback 3670016 full identity, специфическое both-invalid rejection,17 собственных cipher files.
- Сообщено: MF logical 366529 bytes,PCM 2881536 bytes,2 SourceReader seeks,child reopen exit 0,4 checkpoints,2 rewrites,index_publish 4675 us,private_delta 7188480 bytes,elapsed 3876 ms,restricted_medium=true,6 собственных cipher media files.
- Допустимый вывод при этой exact-runtime привязке: частичное синтетическое доказательство DPAPI/MF-пути под primary same-user restricted medium token. Не отдельная обычная учётная запись, не аудит всего диска/temp и не пользовательское воспроизведение.

SOURCE IMPLEMENTATION NOT READY. Phase0/Phase1, T114 целиком, clock/storage model, Home/install/native playback, SC-003 и полная FR-012/product acceptance этим отчётом не закрываются. Новая архитектура или protected product code не разрешены; исходники продукта, планы, задачи, чеклисты и их отметки не изменены.
