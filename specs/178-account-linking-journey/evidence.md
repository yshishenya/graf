# Evidence: Подключение email без тупиков

**Date**: 2026-08-20

**Final closeout status**: PR validation complete; production release pending.
Финальный fast gate ниже привязан к exact tested commit и retained artifact;
production evidence добавляется только после release gate и deploy.

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
| Repository fast gate | 1120 passed, lint/compile/legacy-audio guard passed on exact tested SHA |
| Ruff | passed |
| Whitespace | `git diff --check` passed |

Последний review-fix проход после independent correctness и Ponytail review:
`18 passed` на focused PostgreSQL matrix. Он включает account-closure
finalization, forced-RLS activation boundary, exact provider proof и полный
upgrade → downgrade → upgrade regression. Durable переход в `finalizing`
теперь в той же транзакции закрывает identity, поэтому повторная активация
fail closed даже когда closure-row не видна текущему RLS context. Downgrade
сравнивает полные канонические PostgreSQL predicates с pre-upgrade snapshot,
а не отдельные фрагменты строк. Два dependency warning остаются известными и
не относятся к Feature 178.

Предыдущий fast gate выполнен командой `infra/scripts/ci-local.sh --fast` на
feature diff поверх base SHA
`43e20fea95e1d2bce1c44a647069b93ef5527722`. Первый closeout проход выявил и
закрыл два тестовых хвоста: старый sidebar breakpoint contract стал проверять
только геометрию app shell, а worker schema-head contract обновлён до packaged
migration `0074_linked_workspace_proofs`. Повторный gate для того snapshot
завершился: `1116 passed`, server lint/compile и legacy-audio guard passed,
warnings — два существующих dependency warnings. Дополнительно focused
PostgreSQL exact-role closeout завершился: `3 passed`.

Предыдущий snapshot не использовался как финальное evidence. Итоговый committed
review diff проверен отдельно, поэтому closeout-поля заполнены его значениями:

- `tested_commit_sha`: `26d25163549d887a10e7b28eb02ade7fdbf8e4f0`;
- `fast_gate_artifact`: `feature178-fast-ci-26d25163-20260820T2211Z`;
- `fast_gate_artifact_sha256`:
  `8523d8c95e3186d7110f19f7e6b85f1a0de1c92a2ee5541952c46a392900c202`;
- `fast_gate_run_at`: `2026-08-20T22:12:06Z`.

Production deploy повторно проверит неизменяемый merged SHA полным release gate
и добавит отдельное production evidence.

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

- Канонический synthetic capture bundle ID и fixture digest записаны один раз в
  `design-qa.md`; bundle и fixture остаются вне git, живые локальные пути в
  evidence не сохраняются.
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

Следующие пункты относятся к предыдущему проверенному snapshot:

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
  scope. Для того snapshot повторные независимые review завершились с
  `findings: none`; Ponytail: Lean already.
- Предыдущий repository fast gate пройден для описанного snapshot. Финальный
  review status, exact SHA и artifact reference остаются pending до нового
  review-fix gate T043; production evidence добавляется release-процессом.
- Последний Ponytail проход удалил отдельный 19-строчный self-test приватного
  test-harness helper; сам helper продолжает использоваться всеми exact app-role
  regression checks. Повторный targeted matrix прошёл.
- Финальный immutable security diff scan
  `51d8e705-729f-49ed-8438-53ed74bb0334` проверил точный диапазон
  `43e20fea95e1d2bce1c44a647069b93ef5527722..d3ef2cb22aa930ca67ca90ba318afdf163d5c692`:
  26 из 26 source surfaces покрыты, findings и deferred items отсутствуют.
  Scan завершён `2026-08-20T22:04:16Z`; TAC connector был недоступен, поэтому
  видимость protected output отдельно не подтверждена и не использовалась как
  основание для security-вывода.
- Первый review-fix fast gate на `8f79cdaab693b4b5ccfc310baaa7ccacf5d63432`
  выявил deadlock между конкурентными accept/reject join-offer: audit insert и
  activation guard брали offer/identity locks в разном порядке. Общий путь
  исправлен на SHA `26d25163549d887a10e7b28eb02ade7fdbf8e4f0` — обе команды сначала
  сериализуются на offer row, затем победивший accept проверяет account closure.
  Focused PostgreSQL regression прошёл.
- Post-fix immutable security scan `edf464f9-a3e4-4a81-b314-21c3659f29b8`
  проверил точный диапазон
  `8f79cdaab693b4b5ccfc310baaa7ccacf5d63432..26d25163549d887a10e7b28eb02ade7fdbf8e4f0`:
  1 из 1 surface покрыта, findings и deferred items отсутствуют.
- Финальный `infra/scripts/ci-local.sh --fast` завершён
  `2026-08-20T22:12:06Z` на committed SHA
  `26d25163549d887a10e7b28eb02ade7fdbf8e4f0`: `1120 passed`, server lint и
  Python compile прошли, exit code `0`. Retained artifact ID:
  `feature178-fast-ci-26d25163-20260820T2211Z`; SHA-256:
  `8523d8c95e3186d7110f19f7e6b85f1a0de1c92a2ee5541952c46a392900c202`.
