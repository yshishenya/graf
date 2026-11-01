# T106: промежуточная серверная реализация — 1 ноября 2026

Статус: **WIP, не готово к выпуску**. High-risk-product / существующая T106/#7696.
Основание c6f42e8c7dec50ba769216feab4a80b70b50959a; отдельная ветка
codex/f273-public-permission-20261101. Большая историческая F273 не переносится.

## Что реализовано и проверено

- [x] Строгий POST public-consent: обязательный точный Origin, тело≤1024байта,
  закрытые поля/UUIDv4, no-store; неизвестное/ошибочное состояние не разрешает.
- [x] Отдельная модель/миграция0108, forced RLS, digest-контекст, ограниченные
  app/maintenance права. Настоящие логины исполняют действительную миграцию:
  own1/без контекста0/чужой0, named maintenance2/неверная операция0.
- [x] Read не создаёт; revoke всегда новый epoch и commit до успеха при
  выключенной аналитике; grant CAS текущего epoch и глобального основания.
- [x] Одна межпроцессная PostgreSQL блокировка у транспорта; старое событие
  после принятого revoke не начинает новую передачу. Второй процесс реально
  наблюдается ожидающим pg_locks. Родительская отмена не освобождает его lock.
- [x] Admission16MiB не удаляет старые строки и оставляет существующий revoke.
  Бюджет6с/transport≤5с, ошибка commit не объявляет принятие выбора.
- [x] Неоднозначный transport имеет delivered=null/retryable=false; уже полученный
  HTTP2xx сохраняется после поздней ошибки. Подготовка не владеет DB; закрытая
  попытка не начинает позднюю сеть. На процесс≤4 незавершённых подготовок,
  слот возвращается по фактическому выходу, отказ остаётся доступен.
- [x] Настоящий PostHog wrapper с учебным async transport сохраняет final gate,
  прежний view_id и не передаёт consentId/digest/epoch в receiver body.

## Проверки и найденные исправления

Только временные локальные PostgreSQL/учебные данные, без рабочего сервера
или внешнего получателя. Все созданные runner/role-test контейнеры убраны
штатной очисткой. Локальный Mac перед запусками:147GiB свободно.

| Профиль | До исправления | После |
| --- | --- | --- |
| Control API | 2FAIL/404 отсутствующего пути | 2PASS |
| Shared transport ordering | 1FAIL/3PASS отсутствующей реализации | 4PASS |
| Process/cap/timeout/commit | — | 7PASS |
| Late sender truth/budget | 1FAIL/7PASS, false после HTTP200 | 8PASS |
| Реальные роли | — | 9PASS |
| Ограничение подготовок | FAIL: больше2 sender при2 слотах | PASS |
| Public регрессии, четыре модуля | 2FAIL: startup child/старый fake app | 50PASS/1deselected |
| Новый модуль с настоящим wrapper | — | 11PASS/0skips |
| Отмена родителя у DB/network boundary | — | 2PASS/10deselected |

Два инфраструктурных предупреждения pytest/Starlette сохранены как предупреждения,
не результаты. Spawn/import ребёнка вынесен до начала product6s budget;
actual race задаёт IPC барьер и реальный PG wait. Старый global gate test
использует create_app вместо fake app без db_sessionmaker. Проверка настоящей
модальной формы в общем профиле явно deselected; её готовности здесь нет.
Исходные transient журналы остаются вне Git; опубликованы только итоги.
Ruff и git diff --check PASS, fragment validator PASS. GitHub PR/base gates
и выпуск не запускались.

Независимое ревью серверной границы сохранило историю S1/S2/S3 и после
исправлений не нашло новых P1/P2. Это scoped source review, не общая приёмка.

## Что делать следующим

- [ ] Браузер: настоящий CookieConsent, явный revoke→CASgrant, read-only
  onConsent, cookie epoch, поздние callbacks/cross-tab/resume, доступный
  pending и явный повтор неизменившихся категорий, product-only regression.
- [ ] Настройки отказа при выключенном measurement без automatic banner;
  внешний SDK/replay принудительно закрыты принятым public срезом.
- [ ] Категория until_decision, отдельное удаление и полное restore/inventory:
  все восстановленные строки, включая отрицательные, теряют прежний epoch.
- [ ] Итоговый failure/cancellation/restore/browser профиль, independent
  implementation review/converge, exact PR checks и только затем общий выпуск.
- [ ] Операционные права, тексты/provider readback, backup/restore/capacity,
  принятый фиксированный T0; затем три уже разрешённых Product Radar сообщения.

Настройки production/каталог не менялись. Никаких новых внешних визитов,
регистраций, оплат, T0 или внешних публикаций этим проходом не установлено.
Повторная CUA проверка: Mac locked; новой просьбы разблокировать не отправлено.

## Контрольные суммы серверного снимка

- `public/consent.py`: `8f9c7e7b1f1d57befb21cf80bfb82982ec2695b1d869404e43a0f8256322097f`
- `public/web.py`: `e8a80c667a8a6e378ecdaa896f476dcbae2a809c85cb6ee997c53df67e5a09a9`
- `public/analytics.py`: `6ef00ee65ecffd7431db71acf1cbd08fbf2044512e05e847763bae25d752d7f5`
- `db/tenant_context.py`: `a42161e70629b4c2ffd916110fece8f764e2e2569ea258d2ce7fda335eee3bd7`
- `db/models/public_consent.py`: `35ad147276b65907315181f6535ba0329f420dba519151b1464e1815d72b5194`
- `db/migrations/versions/0108_public_consent.py`: `b63793d10829de1a50fc0c38453bc9c0ae5320a4d87a209bfc1ed92bc0a576e6`
