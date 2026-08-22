# Implementation Plan: Надёжное подключение способов входа

**Branch**: `180-account-linking-reliability` | **Date**: 2026-08-21 | **Spec**: [spec.md](spec.md)

## Summary

Исправить общий разрыв RLS-контекста в provider-link start, сделать merge и
recovery presentation зависимыми от фактического способа входа, убрать retry
loop устаревшего proof и закрепить весь путь production-equivalent тестами.
После merge оставить пользователю одно personal пространство: личные данные
source root переводятся в survivor root, а corporate memberships остаются
отдельными. Реализация переиспользует server-rendered кабинет и существующие
модели.

## Technical Context

- **Backend**: Python, FastAPI, SQLAlchemy AsyncSession, PostgreSQL RLS.
- **UI**: Jinja server-rendered cabinet, общие web/embedded templates и CSS.
- **Tests**: pytest unit/contract/integration, strict PostgreSQL app-role RLS,
  существующие macOS route/runtime проверки.
- **Storage**: существующие `auth_callback_states`,
  `workspace_provider_link_states`, `account_merge_intents`; миграция
  `0076_account_linking_rls` уточняет operation-specific RLS и
  exact semantic bindings без переноса пользовательских данных.
- **Security boundary**: callback state создаётся в bounded `auth_bootstrap`,
  merge подтверждается в exact `account_merge` context; обычный request не
  получает доступ к callback state.

## Constitution Check

- **Lane**: High-risk product area — auth, RLS, sessions и user-facing recovery.
- **Required flow**: specify → clarify → plan → security/UX checklist → tasks →
  analyze → issue sync → implement.
- **Privacy**: только synthetic fixtures и metadata-only evidence; реальные
  email, provider subjects, токены, state nonce и customer screenshots не
  попадают в git или отчёты.
- **Product gates**: fail-closed proofs/RLS, атомарность, доступность, одинаковый
  web/macOS путь и brand-distance сохраняются.
- **Release gate**: реализация и локальная проверка разрешены; commit и production
  deploy требуют отдельных approval после validation.
- **Ponytail**: общий helper и существующая presentation map; без нового wizard,
  schema, dependency или client-side state.

## Project Structure

```text
apps/server/src/twobrain_rec_server/
├── api/auth.py
├── auth/provider_links.py
└── cabinet/
    ├── auth_rendering.py
    ├── rendering.py
    ├── templates/cabinet/pages/
    │   ├── account_merge_content.html
    │   └── settings_account_content.html
    └── web_routes/
        ├── account_merge.py
        └── provider_links.py

apps/server/tests/
├── contract/
└── integration/
```

## Implementation Approach

1. Добавить в `auth/provider_links.py` один helper, переключающий уже
   авторизованный provider-link start в `WorkspaceAuthContext(...,
   context_kind="auth_bootstrap")`. Вызвать его в web и API после customer
   membership/session checks и до создания callback state.
2. Укрепить cross-profile eligibility: initiating session и сохранённая source
   identity должны принадлежать текущему пользователю, совпадать по provider и
   быть active. Подтверждение OAuth берётся из exact provider/subject callback
   proof; подтверждённый email обязателен только для email-originated flow.
   После этого provider-link-originated merge не зависит от того, был ли
   initiating provider email.
3. Получать фактический provider из proof-bound source external identity и
   передавать единый provider id/label в merge renderer. Использовать его для
   title, subtitle, CTA, blockers, restart и post-merge login result.
4. Для `proof_required`, expiry и stale preview не показывать старый confirm.
   OAuth restart отправлять напрямую новым POST в provider start; email и
   неизвестный provider возвращать к видимой форме способов входа.
5. Исправить внутреннюю строку «безопасный preview» и остальные email-only
   fallbacks на понятные provider-neutral/provider-aware формулировки.
6. Добавить strict app-role RLS regression, route/domain contract matrix,
   provider-aware template assertions, proof recovery и wide/390px checks.
7. Разделить RLS read/write policies по операциям callback, provider-link и
   account-merge и связать merge context с exact session, callback, identity и
   provider-link state.
8. Связать email/browser OAuth completion с initiating browser proof, хранить
   короткий email code как server-keyed HMAC, ограничить public OAuth до
   provider I/O и выполнять blocking adapter verification вне event loop.
9. При unlink атомарно отзывать sessions/device bindings отключаемого provider
   во всех доступных пользователю пространствах и вести текущую сессию прямо к
   повторному входу.
10. В merge confirm переместить личные workspace-scoped rows source personal
    root в survivor personal root; встречи и связанные audio/transcript/summary
    rows объединять простым сложением без dedupe. Corporate memberships не
    менять, активные billing/calendar состояния блокировать, source root удалить
    только после проверки отсутствия ссылок.

## Complexity Tracking

| Decision | Why it is needed | Simpler alternative rejected |
|---|---|---|
| Shared auth-bootstrap helper | Один trust-boundary fix для web и API | Два route-local переключения легко разойдутся |
| Provider presentation inputs | Один источник текста для всех состояний | Jinja-условия по provider дублируют copy |

Других новых abstractions, schema или dependencies нет.
