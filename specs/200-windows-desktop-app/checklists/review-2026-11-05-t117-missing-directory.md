# T117: качество требований к отсутствующему конечному каталогу

**Назначение**: независимая проверка только уточнения «Отсутствующий конечный package directory (T117)» в custody §8.
**Дата**: 2026-11-05.
**Feature**: [spec.md](../spec.md), FR-012/013/022; [tasks.md](../tasks.md), существующий T117; [contract §8](../contracts/windows-protected-local-custody.md); [quickstart §12](../quickstart.md).
**Область**: high-risk-product; один same-root переход, прежние форматы, права и границы приёмки. Требования, не реализация и не выполнение испытаний.

**Владелец проверки**: независимый рецензент. `[x]` означает достаточность качества требований по данному вопросу. Основной исполнитель не изменяет отметки. Этот список не завершает T117/T118 и не принимает production-кандидат, реальный профиль, installed/hardware/release.

## Полнота и ясность

- [x] CHK001 Определён ли закрытый критерий именно generic-quarantined строки: strict whole-ledger validation, однозначные identities/path, сохранение непрозрачной пустой/неизвестной допустимой причины и исключение трёх специальных причин, без whitelist либо требования доказать writer? [Полнота, custody §8: отсутствующий конечный каталог; FR-013]
- [x] CHK002 Однозначно ли исключена reservation/deletion ambiguity, включая `deletionBlocks` и любой matching non-rejected directory/meeting target независимо от actor/owner, без удаления unrelated operations/ACK? [Ясность, custody §8: predicate; FR-013/022]
- [x] CHK003 Отличены ли доказанное отсутствие exact final child под существующим проверенным parent/root от missing member, произвольной ошибки открытия, denied/busy/reparse/parent failure и неизвестного исхода? [Покрытие отказов, custody §8: native absence proof]

## Согласованность доказательства и срока действия

- [x] CHK004 Определены ли привязка volatile proof к удержанным native root/parent identities, exact child/row и whole source-ledger stamp, ограниченность числа/памяти и сохранение прежних cancellation/job/pin/bounds без выдуманного FileID или нового persistent record? [Полнота, custody §§3,5,8]
- [x] CHK005 Перечислены ли обязательные rechecks до первой записи, при source/copy/switch и package transitions, через retirement до возврата coordinator Owner; отделён ли этот конец proof от последующего Native ACK и от недоказанного атомарного namespace snapshot? [Согласованность, custody §§5,8]
- [x] CHK006 Ясно ли разделены отказ при наблюдённом появлении объекта в текущем проходе и fresh strict normal/migration validation после restart, без вечного missing-маркера, name/status-only authority либо нового запрета lawful interrupted states? [Восстановление, custody §8: уточнение и таблица interruption]

## Сохранность и полномочия

- [x] CHK007 Согласованы ли exact initial whole-ledger copy/original со всеми owner/range/operation/ACK значениями, прежняя проверка присутствующих packages и запрет создавать отсутствующему пакету state/content/intent/success/removed receipt, при допустимых дальнейших обычных queue mutations? [Целостность, custody §§7.1,8,8.1; FR-012/013]
- [x] CHK008 Сохранены ли запрет owner claim/effect authority из отсутствия, прежняя защита fresh IDs от всех row/deletion aliases и отдельная cleanup authority на все historical ledger rows, включая unknown owner? [Минимальные полномочия, custody §§7,8,8.1 cleanup_authorization; FR-022]
- [x] CHK009 Согласовано ли уточнение с прежними barrier/BOTH/ambiguous/old-reader/expiry правилами, unknown-quarantine сохранностью и запретом объявлять originals/backup полностью зашифрованными; остаются ли изменения в существующих FR и T117 без новой схемы/UI/задачи? [Зависимости, custody §§8–9; plan: переход старого inventory; tasks T117/T118]

## Проверяемость и предел принятия

- [x] CHK010 Разделены ли требования первого конечного RED «один настоящий пакет + одна отсутствующая строка» и последующей успешной новой generated записи после adoption: create+finish, durable readback/adoption и cold проверка с сохранением прежних данных, без подмены результата одной reservation или завершением T117/T118 по частичному свидетельству? [Проверяемость, custody §§5,8–9; quickstart §12; tasks T117/T118; независимый отчёт этого review]

## Результат и привязка

Независимый разбор каждого пункта: **10 checked / 0 unchecked; C0/H0/M0** в указанной области требований. Отметки не утверждают наличие missing-set реализации или пройденного RED/GREEN.

Принят ровно contract-only вариант: 42 добавленные строки §8. Дублирование уточнения в spec/plan/quickstart не требуется: FR-012/013/022, same-root/exact-copy plan, T117 и generated migration/Native §12 уже задают применимые обязанности. CHK010 уточняет наблюдаемый результат в рамках существующего generated whole-pipeline требования, не добавляет новую матрицу.

Значение «unknown quarantine остаётся blocked» относится к прежним неизвестным quarantine artifacts/barriers, а не возвращает whitelist для непрозрачного `safe_reason` строки.

SHA256 contract: `ce1271df342ed49cccb8151dd7451d93593c7e9af92293228af9e89ae2b1297f`.
Неизменные SHA256: spec `34341183dfd7b68fb8886ec23bca4bccc9e0200202e9b1825751f16a37b80855`; plan `214098fbc0ce9d64236a05700c7d391f812a04a0cfeef9e31eef0fd9876de8fc`; tasks `5d8a25afe51044a109c94689f4762da967c65c36cb2f48b3819fe4a78097087b`; quickstart `68432031888324f66ee7d75003585a6a86a9f271ffb3649a0a925a12ec4ab310`.

Старые checklist/отчёты не изменены. Независимый scoped consistency-анализ — C0/H0/M0; это не утверждение о запуске общей команды analyze или о её последующем результате Main. Допуск данного reviewer: подготовка узкого test-only RED; фактический тестовый diff/runner проходят отдельный SOURCE review до выполнения. Production-код — после квалифицированного RED и своего SOURCE gate.
