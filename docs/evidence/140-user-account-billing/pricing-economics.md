# Pricing and unit-economics evidence (interim)

**Дата**: 2026-08-12
**Статус**: model ready, production approval отсутствует.

## Server-owned package

| Пакет | Цена | Processing | Playback storage |
|---|---:|---|---:|
| Free | 0 ₽ | 18 000 с / календарный месяц | 250 000 000 B |
| Trial Личного | 0 ₽, 7 дней | без лимита | 500 000 000 B |
| Личный месяц | 790 ₽ | без лимита | 2 000 000 000 B |
| Личный год | 7 900 ₽ | без лимита | 2 000 000 000 B |

Expansion ladder — **итоговая** ёмкость, не stacking: 5 / 20 / 100 / 500 GB.
Цены add-on не включаются до отдельной approved price version и COGS review.

## Нормализация единиц

Quota считается в decimal bytes только для валидированного
`meeting-review.m4a`. Текущая инженерная оценка (не воспроизводимый production benchmark) 29.4 MB/hour означает примерно
8.5 h для Free, 17 h для Trial и 68 h для Личного. Это estimate для понимания,
не обещание длительности: фактический размер зависит от записи и кодека.

## Required evidence before enabling checkout

Product/Finance должны загрузить обезличенные p50/p90/p99 accepted recording
seconds и playback bytes по cohort за ≥30 дней. Finance добавляет compute,
object storage, egress, backup и support COGS; затем считается contribution
margin по month/year и каждому add-on. Go/no-go decision фиксирует минимальную
gross-margin floor, fair-use sensitivity и stop threshold.

Пока этих данных нет, нельзя объявлять 790/7 900 ₽ или add-on ladder
доказанно оптимальными. Публичные USD pricing pages конкурентов используются
только как dated comparable context (см. `research.md` R11), без FX/PPP
экстраполяции.

## Dated comparable context и проверка единиц

`observed_at_utc` — момент нашей фиксации страницы, а не дата изменения
прайсинга провайдером. Цены указаны ровно в отображаемой валюте; tax/VAT,
региональный selector и FX/PPP нормализацию мы не применяем.

| Источник | observed_at_utc | География/locale/tax и selector | Аудитория/seat | Cadence и точные units | Что переносимо | Что не переносимо |
|---|---|---|---|---|---|---|
| Krisp pricing | 2026-08-07T17:27:43Z | USD; публичная глобальная страница; налог не указан | individual/small teams; Core $16 monthly или $8 monthly equivalent annually | 7-day trial без карты; Core 10 GB storage; Advanced 60 GB; цены per user/month | прозрачный trial, annual comparison, явное раскрытие storage | USD, география, seat и чужая storage semantics |
| Otter pricing | 2026-08-07T17:27:43Z | USD; страница показывает несколько региональных/selector блоков, поэтому значение нужно фиксировать вместе с выбранным блоком; tax не указан | Basic individual; Pro individuals/small teams, `/user/month` | Basic 300 transcription minutes/month; Pro 1,200 in-app recording minutes и unlimited storage; monthly/annual | необходимость отдельно объяснять processing usage и archive | минуты/seat, regional alternate values, pricing другой валюты |
| Notta pricing | 2026-08-07T17:27:43Z | USD; locale EN; annual selector показывает 40% OFF; tax не указан | Free/Pro one-seat individual; Business seats; Enterprise custom | Free 120 transcription minutes/month и 3 minutes/conversation; Pro 1,800 minutes/month; Business unlimited transcription | явный free ceiling, no-card copy, separate add-ons | bot/file quotas, seat semantics и currency |
| Fireflies pricing/storage | 2026-08-07T17:27:43Z | USD; monthly/annual selector; tax не указан | Free individuals; Pro/Business/Enterprise per seat | Pricing page показывает Free 400 mins/team и Pro 8,000 mins/seat; help page показывает 400/8,000 mins per user и unlimited team-wide для Business/Enterprise — source semantics конфликтуют | отдельное объяснение storage/credits и annual comparison | конфликт единиц, video/storage minute semantics и provider COGS |
| Krisp/Otter/Notta/Fireflies pages | 2026-08-07T17:27:43Z | сравнение без FX/PPP и без предположения одинаковых налогов | смешанные individual/team plans | cadence, quota unit и retention semantics различаются | показывать today/next amount и unit definition | нельзя выводить WTP РФ или оптимальность 790/7 900 ₽ |

## Формула до появления production telemetry

Для каждого cohort и cadence считать:

`price_net` — сумма до комиссии YooKassa, но после применённых скидок и ожидаемых возвратов/chargebacks; применимый НДС и налоговый режим фиксируются Finance/Legal для конкретного merchant entity и учитываются отдельно в этой net-of-tax базе. Тогда:

`contribution = price_net - compute - normalized_playback_storage - egress - backup - support - payment_fee`

Сохраняются p50/p90/p99 accepted seconds, normalized bytes, retry rate,
support contacts, refund/chargeback observations и attach/change add-on. До
накопления ≥30 дней реальных данных значения являются `unknown`, а не нулём;
checkout и add-on price version остаются fail-closed.

T085 остаётся открытой: внешнее сравнение теперь датировано и нормализовано,
но target-user comprehension/WTP, observed usage distribution, COGS и
gross-margin floor ещё не измерены. Рабочий guardrail из product-metrics — не менее 70% gross margin после перечисленных COGS; это provisional stop threshold до утверждения Finance.

## Предварительный production usage snapshot — 2026-08-12

Read-only SQL агрегировал только counts и percentiles за последние 30 дней, без
workspace/user/meeting identifiers и без raw content.

| Метрика | N | p50 | p90 | p99 | Ограничение |
|---|---:|---:|---:|---:|---|
| Длительность встречи, seconds | 80 | 39 | 2 283 | 4 560 | окно фактически 27 дней; fixture/internal activity не сегментирована |
| Committed billing usage entry, seconds | 0 | 0 | 0 | 0 | billing usage ledger ещё не накопил production cohort |
| Canonical playback object, bytes | 28 | 7 885 742 | 37 783 331 | 55 924 626 | только 2 workspaces |
| 30-day duration per workspace, seconds | 8 workspaces | 3 | 14 087 | 32 470 | слишком мало workspaces для pricing decision |
| 30-day playback per workspace, bytes | 2 workspaces | 205 706 018 | 336 475 628 | 365 898 790 | статистически непригодно для ladder approval |

Snapshot заменяет прежнее `данных нет` на измеренное `данных недостаточно`.
Он не закрывает T085: нужны минимум 30 полных дней устойчивого cohort,
достаточное число self-service workspaces, заполненный billing usage ledger,
сегментация accepted production use и утверждённые compute/storage/egress/
backup/support/payment-fee inputs. Нули не подставляются вместо unknown COGS.

Свежая проверка официальных comparables подтверждает прежнюю семантику:
[Krisp](https://krisp.ai/pricing/) показывает 7-day no-card trial, unlimited
core и 10/60 GB storage; [Otter](https://otter.ai/pricing) — 300 Free и 1 200
Pro minutes с unlimited storage; [Notta](https://www.notta.ai/pricing) — 120/
1 800 minutes и unlimited Business; [Fireflies](https://guide.fireflies.ai/articles/2631950139-learn-about-transcription-credits-storage-and-rate-limits-for-meetings)
разделяет monthly upload rate и cumulative meeting storage. Эти источники не
дают российского WTP и не утверждают 790 ₽/7 900 ₽.
