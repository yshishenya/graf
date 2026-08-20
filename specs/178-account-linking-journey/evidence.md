# Evidence: Подключение email без тупиков

**Date**: 2026-08-20

Все проверки metadata-only. Реальные email, коды, cookies, tokens, account IDs и
содержимое встреч не записывались; browser fixtures использовали только
синтетические профили и метаданные.

## Focused validation

| Контракт | Результат |
| --- | --- |
| Swift route policy | 16 passed |
| Swift/WebKit sidebar, navigation continuity и 390px runtime regressions | 5 passed |
| Focused Python unit/contract/auth flow | 68 passed |
| PostgreSQL account merge, exact-role forced RLS, billing lineage и migration upgrade/downgrade regression | 31 passed, 2 existing dependency warnings |
| Focused sidebar static/runtime contracts | 4 passed |
| Repository fast gate | 1116 passed, lint/compile/legacy-audio guard passed |
| Ruff | passed |
| Whitespace | `git diff --check` passed |

Финальный fast gate выполнен командой `infra/scripts/ci-local.sh --fast` на
feature diff поверх `43e20fea95e1d2bce1c44a647069b93ef5527722`. Первый closeout
проход выявил и закрыл два тестовых хвоста: старый sidebar breakpoint contract
стал проверять только геометрию app shell, а worker schema-head contract обновлён
до packaged migration `0074_linked_workspace_proofs`. После финальных review
повторный gate завершился: `1116 passed`, server lint/compile и legacy-audio
guard passed, warnings — два существующих dependency warnings. Дополнительно
focused PostgreSQL exact-role closeout после review: `3 passed`. Exact
implementation SHA фиксируется PR после коммита; production deploy повторно
проверяет неизменяемый merged SHA полным release gate.

PostgreSQL matrix доказала отдельно:

- personal-профили сохраняют оба пространства, прежние workspace/meeting IDs и
  раздельные границы данных;
- merge требует точную живую сессию, подтверждённую source identity и consumed
  callback proof, а expired/revoked/mismatched proof fail closed;
- повтор с тем же idempotency key безопасен, а другой key не получает ложный
  success;
- trial, referral и fair-use history следуют merged lineage; survivor может
  увидеть и обжаловать ограничение сохранённого linked-пространства из primary
  контекста, но только через точную app role, active membership и ownership;
- downgrade fail closed, если уже существуют linked-пространства: это не даёт
  ошибочно превратить их в corporate и расширить права. После явного удаления
  linked fixture migration корректно возвращает прежние policies и удаляет
  новые helpers/proof columns.

## Visual and interaction evidence

- Wide 1280 × 720 и mobile 390 × 844 состояния проверены на локальном
  server-rendered flow; шесть synthetic captures хранятся вне git.
- Проверены preview, нижние primary/secondary actions, expired recovery,
  повторный вход и настоящий billing blocker с доступным действием.
- На 390 px нет горизонтальной прокрутки, обрезанных CTA или перекрытия compact
  sidebar; основное действие доступно с клавиатуры и имеет видимый focus.
- Один и тот же document/wording используется браузером и embedded macOS
  surface; WebKit подтверждает focus/disclosure/no-overflow, а route-policy
  regression не расширяет allowlist неизвестных URL.
- В отдельной одноразовой `GRAF Dev` сборке вручную проверены preview, billing
  blocker, expired и re-auth состояния: recovery actions доступны, native chrome
  не перекрывает контент, а sidebar сохраняет ручное состояние между маршрутами.
- Ручной выбор состояния sidebar сохраняется при переходах в текущей сессии;
  breakpoint применяется только до первого ручного выбора. Escape закрывает
  сначала открытое меню профиля и только повторным нажатием сворачивает sidebar.

## Review status

- Correctness/security review закрыт: exact-session ownership, архивный template
  collision, referral checkout retry и fail-closed downgrade покрыты
  регрессиями. Финальный проход также закрыл terminal blocked-intent restart,
  whole-account closure для primary и owned linked-пространств и fair-use
  enforcement без вечного blocker.
- UX review закрыл re-auth возврат к новому подключению, exact embedded fair-use
  routes, нейтральный blocker lead, continuity sidebar и порядок Escape.
- Ponytail review завершён: exact app-role context manager теперь сам владеет
  тестовым engine, закрывает его до удаления роли и убирает четыре повторных
  блока create/dispose. Лишний обход всех workspaces для trial lineage удалён:
  forced-RLS exact-role regression доказывает тот же результат из одного request
  scope. Повторные независимые review: findings none; Ponytail: Lean already.
- Repository fast gate пройден; PR exact SHA и production evidence добавляются
  после фиксации финального diff.
