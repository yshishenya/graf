# T112 — проект до реализации, 16.11.2026

Основа `e44aae0a3c174249b72db77894ff761e67e2d962`, отдельная ветка
`codex/f273-result-visibility-20261116`. Полоса `high-risk-product` существующей
F273, стадия требований/проектирования. Код и рабочие настройки не менялись.

## Что подготовлено

После независимого [preflight D1–D7](t112-requirements-preflight-20261116.md)
подготовлен [конкретный договор показа](../contracts/result-visibility.md).
Он выбирает существующую source/audit цепочку вместо новой таблицы, отделяет
новый приём от физического capture и внешнего клиента, определяет короткий
render proof, видимость browser/native, свежую проверку владельца/версии/
удаления и атомарное принятие двух существующих вех. Старые HTTP client JSON
по-прежнему не должны иметь права объявлять результат просмотренным.

Согласованы ссылки в spec/plan/research/data-model/quickstart/tasks. Clarify
не потребовало новых ответов владельца: назначение вех и параллельный порядок
уже разрешены. Владелец не утверждал предлагаемые инженерные детали; их
достаточность ещё требует независимого ревью.

| Пробел preflight | Предлагаемое решение |
| --- | --- |
| D1 | Полное совпадение нового ingest/audit/source после started_at; известные smoke исключаются, внешний статус остальных unknown |
| D2 | Непустой конкретный блок и собственная версия, observer/focus/visible, HTMX, дополнительный native foreground |
| D3 | Подписанное session/owner/version подтверждение и повторные проверки на защищённом серверном входе после locks |
| D4 | Capture false только для доказанного manual upload, отсутствие при неизвестном capture; неявный true запрещён |
| D5 | Одна транзакция result/value, прежние account keys, без частичного нового набора и автоматического повтора неизвестного commit |
| D6 | Общая T113 boundary, свежий gate, ограниченная отдельная сессия; recovery-unverified не снимается |
| D7 | 25 причинных случаев DB/browser/native/отказов в quickstart, до кода — новый независимый gate |

Это предложения к проверке, **не закрытие D1–D7 и не PASS требований**.
В privacy-measurement добавлены семь открытых вопросов CHK046–052, остальные
отметки основным агентом не менялись. Старый PASS117/0 не выдаётся за ревью
этого проекта. Новый итог четырёх checklist пока117 подтверждённых исторических
отметок и7 новых открытых вопросов; реализация не разрешена.

## Проверки и связи

- `git diff --check` прошёл после записи проекта.
- Scoped проверка прошла:11 изменённых/новых путей — только Markdown F273;
  четыре локальные ссылки новых отчётов/договора существуют, T112 открыта,
  все семь новых reviewer-owned вопросов остаются `[ ]`.
- Тесты нового кода, PostgreSQL, browser и Swift не запускались: реализации нет.
  Команды quickstart описывают будущую проверку и не считаются выполненными.
- Live DNS/TLS/nginx/Postal/Stalwart, release/Full/CD, приватные встречи,
  регистрации, письма и публикации не проверялись и не менялись.
- Свежий read-only GitHub поиск подтвердил существующий открытый
  [#7698](https://github.com/yshishenya/graf/issues/7698), содержащий T112,
  и отдельный открытый [T113/#7804](https://github.com/yshishenya/graf/issues/7804).
  Отдельного title-mapping F273/T112 поиск не нашёл. Issue sync перед кодом
  остаётся отдельной стадией; новая issue/комментарий/закрытие не создавались.

## Следующее необходимое действие

Существующий `/root/public_counter_readiness_review` должен независимо
переоценить D1–D7 и все действующие вопросы четырёх checklist, изменяя только
чеклисты и свой отчёт. После исправления замечаний — scoped analyze и
issue mapping, затем RED/code/GREEN. В этом результате повторное ревью
нового проекта не получено; живой процесс ожидания не утверждается.

T112/T113, T098, измерение, неизменный T0 и коммерческие AC остаются открытыми.
Подготовка проекта не даёт визитов, регистраций, оплат или разрешения
публиковать Product Radar до исходных условий измерения.

## Входные SHA-256 проекта

Хеши фиксируют содержимое для последующего ревью, не приёмку требований или runtime.

| Путь | SHA-256 |
| --- | --- |
| `.specify/memory/constitution.md` | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| `docs/prd-voice-layer-final.md` | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| `docs/current-product-status.md` | `66ba7daa70519c8848a6daea51cd593220fccf75d4b5ea3a4a154e5ae139c3ca` |
| `docs/agent-guidance/product-gates.md` | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| `specs/273-paid-traffic-analytics/spec.md` | `a7f23904625df9b06aed1e09c05f2ffa75ec3e5ec9ac0eda0531cd88c949c645` |
| `specs/273-paid-traffic-analytics/plan.md` | `5207a988f666c47f65203718a1212cf352312009f1c3804163abd093318a8b3c` |
| `specs/273-paid-traffic-analytics/tasks.md` | `3870e4d091557e0c40dd5500aa8fb5932b933cfe877e684c930d7f7e4f93a7d5` |
| `specs/273-paid-traffic-analytics/research.md` | `64caef3d9a78f0021c2b37ca86e0f388724bf117e899bd044f4ca557a1ba094f` |
| `specs/273-paid-traffic-analytics/data-model.md` | `478c18546d1240c4a1c15c5b07e76f7aeb551082273b75bc1fbf4cdd8d1ae8ab` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `4f2488aa98a3fba478eed042304279f408dc2530bd3f2b0449cedabaf39dd074` |
| `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` | `4835c0c6672a464366c9657d9285b28429ec2ed4d4e234c0c4897a65ed5027c4` |
| `specs/273-paid-traffic-analytics/contracts/result-visibility.md` | `80f7d5eb7cd43bb9e3cff34bf689f9ce01f98095e527cb7afdaf3bca7f864f0e` |
| `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md` | `d550de9608410a64805bef5f644b24b7da4ec48289f7b22da78aa1700e7d5358` |
