# Независимый допуск codec-шага T116 — 2026-10-02

## Решение

**PASS: разрешён ближайший ограниченный шаг T116 — wire/identity/bounds/integrity codec по принятому custody contract, сначала регрессии на искусственных данных.**
Блокирующих находок качества требований в этой области нет. Это обновление
независимого checklist gate, не проверка реализации, не новый общий analyze
и не закрытие T116/#7444 или F200. Самостоятельный codec не доказывает защиту
приложения: durable IO, adapters и подключение всех producers/readers остаются
последующими обязательными частями T116.

Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Ветка: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Активная feature подтверждена `.specify/feature.json` и read-only
`check-prerequisites.sh --json --require-tasks --include-tasks`.
Risk/validation lane: `high-risk-product`; выполнена только независимая
проверка требований и их актуальности, без ослабления полного Spec Kit пути.

## Доказательства допуска

1. Явное разрешение владельца в текущем запросе совпадает со spec Clarifications
   «Session 2026-10-02 — независимый срез защищённого хранения», завершающим
   разделом plan «Актуальный порядок», tasks Phase18 и quickstart §12.
   T094–T096 и T119 не зависимости разработки T115–T118; их открытые условия
   продолжают блокировать общую приёмку Windows и выпуск.
2. T115 отмечен как принятое проектирование; контракт сохраняет логические v5
   bytes, ledger v3/read v2, identity/ranges/hashes/deletion receipts. Прочитан
   целиком текущий `contracts/windows-protected-local-custody.md` (§§1–9).
   В §§3/8.1 определены явный little-endian, headers 16/104/112 B, фиксированные
   roles/IDs, native context, exact lengths/checksums, overflow до allocation,
   missing-vs-ZERO и строгие JSON records. Неизвестные schema/flags/keys,
   truncation, integrity/key failure не дают plaintext fallback или authority.
3. Bounds однозначны: block 256 KiB, logical length ≤64 GiB, count ≤262144,
   role-specific metadata caps; owned memory ≤64 MiB, bounded chunks/cache/pins.
   Это требования к будущей реализации, не измеренные свойства продукта.
   Metadata singleton/invalid slot, ambiguous commit, stale callback и GC roots
   остаются запрещающими условиями; codec не заменяет durable acknowledgment.
4. Все пять файлов с checkbox перечитаны, включая встроенный requirements.
   Проверены их актуальные формулировки и совпадение полных байтов с
   `review-2026-10-02-storage-independent.md`, включая status-only freshness
   дополнение. Поэлементное основание 112 критериев из предыдущего полного
   review сохраняется на тех же байтах spec/plan/tasks/contracts и guidance.
   Текущие root/constitution/product guides также совпадают с его hashes;
   относящиеся к этому допуску правила сверены. Полный повтор аудита прочих
   срезов или длинной истории исследований этим отчётом не заявляется.
5. `validation-2026-10-02.md`, раунд203: записан scoped storage analyze
   CRITICAL=0/HIGH=0 и повторная проверка после принятия T115. Текущие hashes
   tasks/plan/contract совпали с последней привязкой независимого storage review,
   нормативный хвост contract неизменен. Это проверка сохранённого analyze gate,
   не самостоятельный запуск `speckit-analyze`; общие findings не объявлены
   устранёнными.
6. T116 имеет текущего canonical owner #7444. Read-only GitHub fetch в этом
   review независимо подтвердил OPEN, точный title `[200][P0][storage] T116`,
   базовый HEAD и acceptance полного protected logical IO. Отдельный primitive
   не закрывает issue. Повторная синхронизация других задач не выполнялась.

## Все checkbox-файлы и владение отметками

Просканированы все 29 Markdown-файлов checklists до добавления этого отчёта:
5 с checkbox, 24 без них. Отчёты без checkbox не считаются пустыми FAIL.

| Файл | Всего | Checked | Unchecked | Владелец отметок |
| --- | ---: | ---: | ---: | --- |
| requirements.md | 22 | 22 | 0 | Встроенный specify/clarify; не менялся |
| audio-capture.md | 24 | 24 | 0 | Независимый reviewer |
| advanced-routing.md | 14 | 14 | 0 | Независимый reviewer |
| security.md | 27 | 27 | 0 | Независимый reviewer |
| ux.md | 25 | 25 | 0 | Независимый reviewer |
| **Всего** | **112** | **112** | **0** | Custom: **90/90**, built-in: **22/22** |

Новых/снятых отметок: **0/0**. Изменять их объективно не требуется.
Hardware/runtime пункты не отмечались выполненными: custom `[X]` остаётся
оценкой качества требований, не результатом аппаратного испытания.

| Checklist | SHA-256 текущих байтов, совпадает с предыдущим review |
| --- | --- |
| requirements.md | `91fecd3ca4c79eba15faa3543fce18f8d5db1eb7a6664701c683c460d0d5bc55` |
| audio-capture.md | `4471fb8dc0fa82851c57c3c5e0bf49f4a5f94d838c082998488ecbdc15280cfd` |
| advanced-routing.md | `bd88f0588e806b16e93f7031645ed56384245343d20c7c41ab610a532620da12` |
| security.md | `50a47dd3ff25223665a77dae3ba163c8732fe52a9e7705a019544be563d817f9` |
| ux.md | `1a5a28f7226d7fc25bafdb8239b3d4bea2aeae0d4aad969eb89b45ec5b855801` |

## Точная привязка нормативных документов

SHA-256 локальных байтов, не committed/installed evidence. Пути ниже относительно
`specs/200-windows-desktop-app`, кроме явно указанных root-путей. Все значения
совпали с последней принятой привязкой storage review; до записи этого отчёта
дрейфа этих документов и всех 29 прежних checklist/report файлов не обнаружено.

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

## Сохранённые границы и изменения

T116 остаётся открытым; T117 migration/retirement и T118 full-pipeline acceptance
не приняты. Codec PASS не принимает clock, calendar, физический x64/60min/AEC,
installed MSIX/EXE, accessibility, Home/Pro/N, update/rollback, actual key-loss,
power-loss, реальные legacy cleanup, серверные ограничения или выпуск.
Не вводятся новая cryptographic-erasure гарантия и разрешение на реальные данные.
При изменении нормативных bytes/условий требуется новый scoped freshness/review.

Единственный записанный путь — этот новый отчёт. Прежний storage-independent
report и все checklist markers сохранены. Код/spec/plan/tasks/constitution,
GitHub state и Git state не менялись. Код и producers не аудировались: это
работа main. Тесты, сборки, VM, устройства, записи, миграции, установка,
commit/push/deploy/release не выполнялись.
