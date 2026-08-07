# Pricing and unit-economics evidence (interim)

**Дата**: 2026-08-07
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
`meeting-review.m4a`. Текущая инженерная оценка 29.4 MB/hour означает примерно
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
