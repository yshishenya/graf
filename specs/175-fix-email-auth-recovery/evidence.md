# Evidence: надёжный вход по email и восстановление аккаунта

Дата проверки: 2026-08-19
Risk lane: `high-risk-feature`

## Что проверено

- Вход по email завершает создание сессии и exact callback-state одной транзакцией под forced PostgreSQL RLS.
- Ошибка подготовки ответа откатывает сессию, callback и связанные изменения.
- Неверный, истёкший, повторный и конкурентно использованный код не создаёт вторую сессию; failure/expiry audit записывается до terminal callback transition.
- Раннее и позднее неоднозначное совпадение email завершается fail closed и показывает настроенные Яндекс ID/VK без раскрытия данных аккаунтов.
- Email/OAuth linking использует классификацию `0/1/>1` других пользователей, повторно активирует ранее отключённый email и никогда не объединяет аккаунты автоматически.
- Merge intent создаётся через savepoint, после чего восстанавливается разрешённый RLS-контекст; web и desktop-маршруты ведут на явный preview/confirm.
- Merge preview объясняет основной аккаунт, сохранение способов входа и данных, отдельные пространства и отзыв сессий/устройств.

## Автоматические проверки

### Канонический quickstart selector

Команда из `quickstart.md` для `email_auth|email_link|provider_link`:

- Финальный расширенный selector: `37 passed`, `120 deselected`;
- disposable PostgreSQL container удалён после проверки;
- охвачены success, invalid, expiry, concurrent valid-code/replay, rollback,
  inactive-email relink, same-state provider replay, different-state active-intent
  race, email/OAuth merge-context restore, recovery provider/fallback,
  web/desktop parity и empty-account preview.

### Дополнительные focused проверки

- Review-fix PostgreSQL matrix: `13 passed`.
- Финальная concurrent/relink/audit matrix: `4 passed`.
- Account-link route contracts и merge policy: `27 passed`.
- Ruff по затронутым server/test файлам: `PASS`.
- Python compile и `git diff --check`: `PASS`.

Pytest сообщил только известные предупреждения сторонних библиотек о fixture rewrite и deprecated TestClient import; падений и новых product warnings нет.

## Review

- Correctness review нашёл и исправил: повторное подключение неактивного email, отсутствующий email-link failure audit и пробелы forced-RLS merge/replay/expiry/rollback coverage.
- Ponytail review удалил отменённую auto-confirm семантику, лишние поля результата и дублирование response/context/test setup без изменения trust boundaries.
- Codex Security diff scan исходного auth snapshot: полное покрытие `8/8`, reportable findings `0`.
- Финальный Codex Security diff scan после всех review-исправлений: scan `6fb45867-0c0e-4975-94aa-dd90e7f47da8`, snapshot `d5f3a4a474d4bc984c47b3189e46c57dc109492c600ed8945fd48dcd459cc31b`, полное покрытие `9/9`, reportable findings `0`.
- TAC-статус проверить не удалось, потому что access connector не подключён; это advisory-ограничение не использовалось как основание для пропуска проверки.
- Финальный delta повторно прошёл независимый correctness review без новых findings; focused regression matrix перед fast CI прошла.
- Review PR #5412 дополнительно нашёл и исправил блокировку одного provider-link
  через `FOR UPDATE`, absent-row race двух разных proof-state через savepoint и
  переиспользование active intent, ложное обещание немедленного merge после
  обычного OAuth-входа, отсутствующий fallback при выключенных провайдерах,
  повторяемую тупиковую email-форму и технический термин в confirmation copy.
- Ponytail review: новые trust-boundary проверки размещены в существующих
  helper/route/template, новая зависимость и параллельный recovery-механизм не
  добавлены; production-refactor `create_merge_intent` стал короче.

## Визуальная проверка

- In-app Browser: desktop viewport и `390x844`, доступные Яндекс ID/VK/Mail.ru/
  Одноклассники, fallback без провайдеров и фактический click-through Яндекс ID.
- Provider actions ведут на first-party `/settings/account`; recovery не
  показывает повторную email-форму, будущие provider placeholders или SSO-заглушку.
- DOM/ARIA: заголовок `Восстановить доступ`, alert и semantic links доступны;
  clipping/overlap не найден, console warning/error: `0`.

## Privacy и production safety

- Использованы только синтетические данные домена `example.test` и disposable PostgreSQL.
- Реальные production-аккаунты, коды, токены, письма и встречи не читались и не изменялись.
- Production deploy в этой проверке не запускался; перед `--execute` обязателен отдельный dry-run и явное подтверждение владельца.

## Closeout

- `infra/scripts/ci-local.sh --fast`: `PASS` — `1103 passed`, server lint `PASS`, Python compile `PASS`, isolated PostgreSQL container удалён.
- Implementation commit / PR / merge: ожидают T024.
