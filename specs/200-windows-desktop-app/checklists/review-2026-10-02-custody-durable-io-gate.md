# Независимый допуск durable protected IO — T116

Дата среза: **2026-10-02 UTC**. Местная дата Europe/Istanbul уже
2026-10-03; имя отчёта сохраняет заданную владельцем дату UTC-среза.

## Решение и область

**PASS требований для следующего ограниченного шага T116: confined protected
file/index IO после принятого codec. Новых блокирующих нормативных решений
в этой области не обнаружено.** Сначала регрессии на искусственных данных;
этот reviewer тесты не запускает. Это не обзор исходников durable IO, не
результат VM/устройства, не завершение полного T116 и не общий PASS F200.

Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Ветка: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Активная feature подтверждена текущим `.specify/feature.json`, Git branch/HEAD
и read-only `check-prerequisites.sh --json --paths-only`.
Risk/validation lane остаётся **high-risk-product**; это независимое обновление
requirements gate внутри принятого среза, не новый обход Spec Kit.

## Актуальность предыдущего полного review

Применено разрешённое владельцем повторное использование поэлементного review
`review-2026-10-02-storage-independent.md`, включая его status-only freshness
дополнение. Полные hashes текущих spec/plan/tasks/data-model/quickstart/contract
совпали с его последней привязкой. Совпали также 10/10 проверенных root/pointer/
constitution/product/guidance hashes из того отчёта; прежняя нормативная опора
не устарела. Повторный полный аудит чужих срезов и истории не заявляется.

Заново прочитаны все текущие checkbox markers по всем 31 Markdown-файлам
`checklists`: 5 checkbox-файлов, 26 отчётов без checkbox. Отсутствие checkbox
в отчёте не является FAIL. Все пять checklist-файлов побайтово совпадают с
предыдущим полным review; его поэлементное основание остаётся применимым.

| Файл | Всего | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| requirements.md | 22 | 22 | 0 | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| audio-capture.md | 24 | 24 | 0 | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| advanced-routing.md | 14 | 14 | 0 | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| security.md | 27 | 27 | 0 | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| ux.md | 25 | 25 | 0 | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |
| **Всего** | **112** | **112** | **0** | Все hashes совпали |

Reviewer-owned custom markers: **90/90**. Встроенные requirements: **22/22**,
не принадлежат этому reviewer для изменения. Новых/снятых отметок: **0/0**.
Отметки означают достаточное качество требований, не выполнение hardware gates.

## Конкретные условия ближайшего шага

Заново прочитаны contract §§1/2/4/6 и относящиеся к IO ограничения §5;
проверены действующий завершающий порядок plan и storage task statuses.
Источник формата — принятый §3, не исследовательский layout.

| Условие | Достаточное нормативное основание / обязательная граница |
| --- | --- |
| Confined filesystem и ACL | §2: проверенный user-scoped custodyRoot; запрет symlink/reparse, ADS, UNC/внешнего root и JSON paths. Проверяются открытые handles и фактическое расположение; `weakly_canonical` до открытия недостаточно. User-only ACL при создании **до первого content write**, без изменения ACL профиля/VM. |
| Fixed identity/layout | §§1–2: opaque store/object IDs и фиксированные roles/locations. Нет создания нового store ID поверх protected inventory; неизвестные файлы сохраняются, не превращаются в empty state. Временные content bytes только ciphertext. |
| Immutable block creation | §4: один writer под существующей process/lease защитой; `CREATE_NEW` для новой block version, существующий orphan не перезаписывается. Version/generation не wrap/reset; overflow/collision не разрешают overwrite. |
| Durable acknowledgment | §4: encrypt в памяти → полный write/`FlushFileBuffers` blocks → encrypted temporary index/flush → atomic publish alternating slot → flush опубликованного handle → validated reopen → ACK. До последнего ACK bytes не объявляются durable. Rename/flush не доказывают произвольную power-loss гарантию носителя. |
| Metadata birth pair | §4: g1 сначала slot0, затем независимо защищённый slot1 с теми же decoded bytes. Первый ACK только после проверки/flush/reopen обеих slots. Equal generation разрешена только для этой g1 pair; поздние generations идут в `(generation-1)%2`. |
| Restart authority | §4: любой singleton metadata, включая surviving g1, unreadable/invalid slot или referenced block блокирует authority контекста. Нет автоматической достройки pair, rollback ledger, empty queue, выбора temp/orphan по mtime. Прежний validated media snapshot возможен только как degraded/trusted prefix, не normal upload. |
| Ambiguous/sticky failure | §§4–5: ошибка после publish сохраняет ambiguous result, sticky failed writer и артефакты/последний checkpoint. Запрещены next generation/effects/GC до фонового reconciliation. Cancellation после начала publish не откатывает bytes и не становится доказанным not_committed. |
| Logical read/seek | §6: verified bytes pinned snapshot/exact tail; короткий EOF = `S_FALSE` с точным got. Native/semantic error sticky, got0; частичный buffer после ошибки не используется. Missing DATA не ZERO; extension/shrink/rewrite/Clone/CopyTo сохраняют identity, bounds и snapshot semantics. |
| Memory/worker lifetime | §5: 64 MiB owned budget до allocation, chunks ≤256 KiB, ограниченные dirty group/cache/pins, physical disk reserve для всей группы. UI/capture callbacks не делают disk/crypto IO. Candidate/lease/pins/results удерживаются до terminal result/adoption; persistent bool не подменяет typed ACK. |
| GC и отсутствие скрытого cleanup | §5: refs обеих slots/pins/candidate сохраняются; restart roots validated до GC. Invalid/unknown metadata или ambiguous writer запрещает соответствующий GC. Этот шаг не даёт полномочий очистить legacy original или ключи. |

Эти правила задают наблюдаемые результаты ошибок и authority, а не только
счастливый путь. Конкретная реализация открытия handles, публикации и доказательства
границ принадлежит main и последующему обзору кода. Новый нормативный выбор для
начала этого ограниченного слоя не требуется; нельзя заменить правила удобным
generic plaintext AtomicFileStore или неподтверждённым IO helper.

## Последовательность и отдельные доказательства

Последний раздел plan разрешает после codec/hash именно durable logical IO,
затем adapters и все producers/readers/queue/finalizer/upload/playback/delete.
T114/T115 отмечены принятыми в их ограниченном объёме; T116/T117/T118 открыты.
Scoped storage analyze CRITICAL=0/HIGH=0 и owner mapping #7443–#7446 сохранены
в тех же нормативных байтах и предыдущем review; связь T116 → #7444 неизменна.
Новый analyze или GitHub query/sync этим reviewer не выполнялся. Это PASS
независимого requirements gate, не повторная live-проверка всех внешних gates.

`review-2026-10-02-custody-codec-source.md` прочитан в части заключения:
**Approved source only**, 0 blocking findings в codec-срезе. Его исходники
заново не аудировались. Сообщённые владельцем native VM **35/35** принимаются
как отдельное сообщение, не как лично выполненный опыт и не как evidence
работоспособности ещё не реализованного durable IO. Установленные обновления
этим решением не утверждаются и не разрешаются.

Clock T094–T096, физическая/audio/60min/AEC матрица, calendar T119, migration
T117 и установленная/полная storage приёмка T118 остаются открытыми. Они не
новые зависимости разработки принятого independent storage-среза; их собственные
проверки и общая готовность Windows/выпуск не ослаблены. Реальная миграция,
cleanup, установка, production и публичный выпуск не входят в разрешение.

## Хеши проверенного снимка

Это SHA-256 локальных байтов, не committed или installed evidence. Пути от
`specs/200-windows-desktop-app`, кроме явно обозначенных root-путей.

| Артефакт | SHA-256 |
| --- | --- |
| spec.md | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| plan.md | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` |
| tasks.md | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` |
| contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| Contract от `## 1.` до EOF, нормативные §§1–9 | `fc831b083699fb7e96f17cb642ad9a50b79d68bb2130fff69d4e2500b3151c6b` |
| data-model.md | `b494c57fa6cff34c0128d674677f5fca09e647aabbf60aea15c2a53603c43848` |
| quickstart.md | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` |
| Root .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| Root AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| checklists/review-2026-10-02-storage-independent.md | `4d6a6c32a6513f7a4ab796490ab6cfb173d1faaa3cca0bca7142bd64e4d90d94` |
| checklists/review-2026-10-02-custody-codec-gate.md | `ca14a08aa09d1472778395130b228a33fcb28d157cabe7d69069595cfa021b28` |
| checklists/review-2026-10-02-custody-codec-source.md | `0bb8f155bb414a56ae355214e8fdf328ca0bb1bac197b7e282d37c98937ae409` |

Единственное изменение reviewer — этот новый отчёт. Существующие markers,
отчёты, код/spec/plan/tasks/constitution и чужие рабочие изменения сохранены.
Код и actual IO/proof flow не инспектировались; tests/build/VM/devices,
GitHub mutations, commits, установка и выпуск не выполнялись. При дрейфе
нормативных bytes/условий нужен новый scoped freshness/review.
