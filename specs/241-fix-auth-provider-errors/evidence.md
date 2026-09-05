# Evidence: непрерывность способов входа при ошибках

## Scope and cause

- Исходный `GET /login` и `GET /sign-up` читают workspace provider policy через
  `_load_browser_login_providers()`.
- Восстановимые POST/provider-start ошибки обходили этот источник и передавали
  `providers=[]`, поэтому Яндекс ID/VK исчезали, а planned disabled entries
  оставались.
- `email_start_unavailable` возникает до почтовой доставки, когда ordinary
  login не может безопасно выбрать активную email identity; прежний текст про
  неотправленный код был неточным.

## TDD evidence

- До production-изменения новый rendering contract test завершился ожидаемым
  `TypeError`: `render_login_page()` не принимал `email_value`.
- Прямой pytest без wrapper был намеренно отклонён fixture-гейтом из-за
  отсутствия `TWOBRAIN_DATABASE_URL`; последующие интеграционные проверки
  выполнялись только штатным disposable PostgreSQL wrapper.
- После реализации новый focused набор: `13 passed`.
- Расширенная итоговая auth-матрица из quickstart: `39 passed, 163 deselected`.
- Disposable PostgreSQL container был удалён wrapper-ом после каждого запуска.

## Covered behavior

- Unknown/unselectable email, invalid input, durable rate limit и фактический
  delivery failure сохраняют допустимые provider actions.
- Sign-up rate limit, invalid input и delivery failure остаются на редактируемой
  email-форме и показывают доступные альтернативы.
- Provider future, disabled, missing-adapter и rate-limit paths сохраняют
  соседние действия; выключенный policy provider остаётся скрыт.
- Browser и embedded `/desktop/meetings` сохраняют только first-party `next`;
  embedded error page не показывает download CTA.
- Нормализованный корректный email сохраняется; неверный HTML-подобный ввод не
  отражается; rendering contract отдельно подтверждает Jinja escaping.
- Искусственная `ProblemDetail` при чтении provider snapshot оставляет экран
  fail closed без активных Яндекс ID/VK.

## Static audit

Команда:

```sh
rg -n "providers\s*=\s*\[\]|render_(login|signup)_page\(" \
  apps/server/src apps/macos packages
```

Результат:

- production-вызовы `render_login_page` / `render_signup_page` принадлежат
  только `cabinet/web_routes/auth.py`;
- ни один восстановимый route error больше не передаёт `providers=[]` напрямую;
- оставшиеся `providers = []` — начальные локальные значения перед policy read,
  fail-closed значение общего helper и намеренный ambiguous-email recovery
  fallback;
- других связанных legacy route/render owners не найдено; несвязанный auth-код
  не изменялся.

## Completed local checks

```text
Focused disposable PostgreSQL auth matrix: PASS (39 passed)
Fast governance tests: PASS (224 passed)
Fast server unit tests: PASS (1391 passed)
Changed server contract/integration tests: PASS (202 passed)
CI contract tests: PASS (66 passed)
Ruff, touched Python files: PASS
Python compileall, touched server modules: PASS
Spec Kit governance: PASS
Changelog fragments: PASS
git diff --check: PASS
```

`infra/scripts/ci-local.sh --fast` завершён на SHA
`cbc3a22f78b2b7c04797bf9a612f0eae441a0694`: `requested=fast`,
`effective=fast`, `components=server,infra,docs`, `coverage=partial`,
`next_gate=full_before_release`, `result=pass`, `duration_seconds=555`.
Локальный receipt:
`.dev/ci-evidence/ci-fast-cbc3a22f78b2-ab2f6cf1de74.json`.

Две предварительные попытки не считаются пройденным gate: первая была
остановлена защитой `dirty_worktree`, вторая — preflight из-за устаревшего
локального `.specify/feature.json`. После обновления служебного контекста и
добавления обязательного `Legacy Impact` выполнен указанный выше чистый проход.

## Pending PR gates

- PR metadata validation на финальном 40-символьном SHA.
- GitHub Actions `governance-fast` на том же PR SHA.

Production deploy, реальная почтовая доставка, merge и release не входят в эту
задачу.
