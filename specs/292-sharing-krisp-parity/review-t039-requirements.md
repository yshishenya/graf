# T039 — независимая проверка требований до кода

2026-11-17. Исполнитель `/root/t039_requirements_review`, ветка `codex/f292-replacement-duration`, база `387c3290ae2d36f35fb67d7bf432e4a5873466e0`. Проверен текущий незакоммиченный срез документов. Приложение, БД и GitHub не изменялись; запись только в reviewer-owned checklist и этот отчёт.

**Результат: PASS требований, CRITICAL0/HIGH0; 3 отмечены / 0 открыто.** Это разрешает следующий этап только после отдельного analyze и issue sync; не является приёмкой реализации, приложения или выпуска.

## CHK001 — определённость поведения

`spec.md`, раздел Session 2026-11-17, однозначно закрепляет длительность каждой MediaRevision, точный fallback только при отсутствии ревизии/её длительности и текущую публичную проекцию. Это соответствует US2/AC1 и FR-019/020/025: новая версия воспроизводится, старый media_version409, недоступность не маскируется. Объём ограничен совместимостью существующего ingest; захват, обработка источника, права и новые зависимости исключены.

Прочитан обезличенный локальный `b-blocked-facts-20261117.json`: запрошено24, сохранено60, track24, revision2 accepted, normalization terminal/source_mismatch; старое аудио и Range409 shared_media_changed, новое409 playback_unavailable. Факт ошибки не выводится лишь из сообщения основного агента. Нормализатор `normalization/service.py:2638` использует revision.duration_seconds; проверку источника сохранять правильно.

## CHK002 — общая причина и границы

В `ingest/sessions.py:127–141` новая ревизия создаётся с duration запроса, повтор сравнивает это значение; `177–204` связывает MeetingRecord с новой ревизией и вызывает persist_meeting. `ingest/store.py:467` по-прежнему читает исходную длительность Meeting, а `380` затем ошибочно записывает её существующей ревизии. Поиск всех производственных присваиваний revision.duration_seconds нашёл только эту последующую запись; начальные значения задаются конструкторами. Поэтому удаление именно этой записи сохраняет отдельный источник истины и исправляет не только первый POST, но и ложный idempotency_conflict на повторе.

Просмотрены все9 вызовов persist_meeting: `meetings.py:226`, `sessions.py:204/299`, `finalize.py:175/789`, `lifecycle.py:82/144`, `lifecycle_guards.py:140`, `desktop_sync.py:725`. Первичное создание получает duration в конструкторах; остальные сохраняют состояние и не должны подменять длительность ревизии. План сохраняет source_kind/status, initial constructors, accepted/immutable, Meeting и транзакции/блокировки. Отмена/истечение восстанавливают прежнюю принятую ревизию существующим helper. Глобальная смена MeetingRecord.duration_seconds не требуется и запрещена планом.

`cabinet/public_sharing.py:139–182/244` уже выбирает current_media ревизию, но передаёт исходную длительность Meeting в transcript_state и JSON. Требование передать одно значение из текущей ревизии с проверкой None определено достаточно. Fallback не должен срабатывать для нуля посредством `or`, поскольку документы называют только отсутствие значения. Старая ошибочная accepted B остаётся неизменной; повтор приёмки через новый штатный local revision ID исключает скрытую правку принятого отпечатка.

## CHK003 — полнота будущих проверок

`quickstart.md:T039` называет имеющийся настоящий WAV/upload/finalize/normalization сценарий и конкретные assertions:24/90, БД после POST и finalize, JSON/HTML длительность, поздняя реплика B90, полный200, Range206, old409, квота и публикация outcomes. Прочитанный исходный test_public_playback_uses_the_versioned_revision_before_outcomes использует60 для обеих версий, поэтому новая параметризация обнаружит скрытый прежде дефект. Тест идемпотентного POST в test_media_revision_reprocess.py также использует60; план24/90 проверяет отдельный пользовательский сбой повторной отправки. Abort/expiry, initial/immutable, persistence order, stale rename и legacy duration=None явно включены.

Реальная native A/B проверка после clean Dev promotion и явное обновление без старой позиции обязательны отдельно. FR-027 и текущие plan/tasks сохраняют exact-SHA PR checks, согласованный frozen candidate, release-full и отдельную production приёмку. T017 сохраняет уборку только собственных завершённых материалов; локальный факт пока cleanup_executed=false не объявлен успехом. Тесты, приложение, CI и релиз данным reviewer не запускались.

## Проверенные документы

Прочитаны AGENTS.md, guidance index, spec-kit-flow/product-gates, нормативные разделы constitution7.1.0, активные spec/plan/tasks/quickstart/research T039 и указанная цепочка исходников/тестов. Prerequisites подтвердил тот же FEATURE_DIR через явный SPECIFY_FEATURE_DIRECTORY; физическое имя worktree не использовалось как источник фичи.

| Документ | SHA-256 текущего текста |
| --- | --- |
| `spec.md` | `bf8df754d85e812bfc0c6a0c7818fe76a678d4b281206bb7c30822b114ab7606` |
| `plan.md` | `54785a63fba8cf29d86b9fdabb8e8b1331f667fa3b9f78fc3b2e24c56ea76916` |
| `tasks.md` | `2b782e2350193b84b21d65a820c3f80cf1367aeb89f2cd844fe725fe0925b183` |
| `quickstart.md` | `21619beb26a780c1ce8757a31b2225280d897d0d875ec3ea80941cbfb876ae25` |
| `research.md` | `6d14206bed1e14d54a23482988cdcda75c9d8d9069063aa8dc828ac2adae4119` |

Суммы идентифицируют просмотренную редакцию документов, а не подтверждают будущую реализацию. Reviewer повторно прочитал записанный checklist: checked3, unchecked0. Остальные файлы и чужие изменения не менялись.
