# Scoped analyze 2026-10-15

FR056–058 → T066 → contract/browser/storage regression; FR059 → T067 → existing email link/verify/unlink и live identity/subscription/contact; release → T068. Spec/plan/quickstart/tasks согласованы. Нет новой схемы/пакетов/платёжной модели. Existing addon_label/total_label/usage projection достаточны. Unknown/stale не становятся fresh. Денежные условия остаются на purchase preview. Старые full-price assertions адаптируются к явно подписанной иерархии, не удаляются. Проверки пока не выполнены. Critical/high противоречий в scoped документах не выявлено; до кода нужны independent checklist PASS и issue mapping.


## Сверка номеров 2026-10-16

Механическая перенумерация без изменения требований: FR053–056 → FR056–059; T062–064 → T066–068. Более ранние #7594–7597 сохраняют T062–065/FR053–055/SC018. Хранение использует T066/#7598, почта T067/#7599, проверка выпуска T068/#7600. Проверены определения FR, уникальность task ID, точные ссылки на три existing issues и отсутствие пересечения новых задач с текущей веткой повторного аудита. Critical/high противоречий нумерации не найдено. Продуктовая реализация и приемка этим анализом не подтверждаются; независимый refresh reviewer-owned checklist выполняется отдельно.

### Operator recovery FR059/T067, 16.10.2026

Явный запрос владельца заменил ожидание old mailbox. Новый verified Yandex proof уже существует. Локальный private script не подделывает callback/OTP, использует разрешённый account_merge maintenance. Scope включает пустой personal source, сохранённые personal83/corporate79, корпоративные creator/owner ресурсы и immutable history. Independent reviewer проверяет точный script/dry-run; HOLD до PASS и проверенного backup/restore. Это анализ ограничений, не доказательство applied recovery.

### Обнаруженный разрыв FR059/T067

После применённого восстановления ручной selector/profile/notifications выбирают новый verified контакт, но renewal planner читает только исторический paid invoice. Требование уточнено: общий существующий selector с приоритетом current owner, прежний historical fallback только при отсутствии текущего verified контакта. Scope не меняет старые финансовые строки/суммы/согласие/dispatch. Существующий T067 покрывает этот buildable gap; новый дублирующий task не нужен. До кода требуется independent refresh; UI48/48 и operator PASS не покрывают это исправление.
