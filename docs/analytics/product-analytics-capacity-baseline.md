# Product Analytics Capacity Baseline

Feature: `273-paid-traffic-analytics`

Status: `measurement_pending_operator_receipt`

This document is safe to commit. It records sizes, counts, and timestamps only:
no event payloads, no visitor or user data, no provider secrets, no personal
names or emails, and no private host paths.

## Purpose

FR-039 requires a load check before paid traffic starts and a recorded absolute
storage volume plus expected growth rate. SC-012 requires that a traffic spike
that multiplies the load on the site does not switch measurement off and does not
affect product availability.

This baseline is the number behind that promise:

- it fixes how much disk the self-hosted analytics node actually uses today;
- it fixes how fast that volume grows per day and per 1000 ingested events;
- it projects the volume for 12 and 36 months, so the planning horizons and the
  free-space guardrail can be checked against real data instead of an estimate;
- it gives the evidence needed to justify the analytics-scope alert thresholds
  without raising them by guesswork.

The measurement covers the analytics node only. The GRAF product stack keeps its
own storage accounting and is not restored, resized, or rescheduled from this
baseline.

## Measurement Method

The measurement is implemented by `infra/scripts/measure-posthog-storage-growth.sh`.
The script must report, per storage class, metadata only:

| Required output | Meaning |
| --- | --- |
| `storage_class` | Canonical class name, aligned with `infra/posthog/backup-volumes.txt` |
| `absolute_bytes` | Bytes currently used by the class |
| `window_hours` | Length of the measurement window |
| `events_in_window` | Events ingested during the same window, counted from the ClickHouse events table (`GRAF_POSTHOG_GUARD_EVENTS_TABLE`, default `events`) |
| `bytes_per_day` | Growth per 24 hours: the measured difference against the previous sample, or the event-rate estimate when no previous sample exists |
| `bytes_per_1000_events` | Bytes added per 1000 ingested events in the window |
| `projected_bytes_12_months` | Linear projection from the measured daily growth |
| `projected_bytes_36_months` | Linear projection from the measured daily growth |
| `analytics_disk_free_percent` | Free space on the analytics filesystem; on a shared filesystem this is the same resource as host disk free space, not independent analytics usage |
| `recorded_at` | UTC timestamp of the sample |
| `growth_basis` | `previous_sample` when the growth came from two samples, `event_rate_and_average_event_size` otherwise |

Growth is a difference, not a snapshot. The script is run twice: once at the
start of the measurement window and once at the end, with at least 24 hours of
ordinary traffic between the two runs. Each run stores its sample in
`/var/lib/graf-posthog-storage/storage-growth-state` (overridable with
`GRAF_POSTHOG_STORAGE_STATE_FILE` or `GRAF_POSTHOG_STORAGE_STATE_DIR`), so the
second run reports `growth_basis=previous_sample` with the measured daily
growth. A first run with no stored sample reports
`growth_basis=event_rate_and_average_event_size`, derived from the observed
event rate and the average stored event size. Record which basis the receipt
used: only `previous_sample` is a measured baseline.
`--window-hours <n>` widens the event window when traffic is uneven.

The guardrail is fixed: analytics storage free space must stay above `20 %`
(`GRAF_POSTHOG_GUARD_ANALYTICS_DISK_FREE_PERCENT`). A run that reports free
space at or below the guardrail is a blocker for the baseline, not a baseline
value.

The script above is committed with those exact key names, so a receipt can be
copied into the results table below without renaming anything. A report with
`unknown` in a numeric cell is an incomplete measurement: keep that class
`pending operator receipt` and record which probe was unavailable, rather than
substituting an estimate.

## Operator Command Sequence

Run on the analytics server, as a root-owned release/deploy step. The script is
installed next to the runtime guard so production never executes the mutable
application checkout:

```sh
install -o root -g root -m 0755 infra/scripts/measure-posthog-storage-growth.sh /usr/local/libexec/graf-posthog-storage-growth.sh
set -a
. /etc/graf-posthog-runtime-guard.env
set +a
/usr/local/libexec/graf-posthog-storage-growth.sh
```

Then:

1. Confirm the runtime guard reports the analytics scope as `pass`; a baseline
   taken while measurement is degraded is not a baseline. The guard state file
   is `$GRAF_POSTHOG_GUARD_STATE_DIR/alert-state`, default
   `/var/lib/graf-posthog-runtime-guard/alert-state`.
2. Record the first sample, wait at least 24 hours of ordinary traffic, and
   record the second sample.
3. Copy the reported values into the results table below, one row per storage
   class, with the UTC measurement timestamp.
4. Compare `analytics_disk_free_percent` with the `20 %` guardrail and record
   the comparison, not the raw filesystem listing.
5. Keep only class names, byte counts, event counts, percentages, and
   timestamps. Do not record container file listings, payload samples, provider
   identifiers, or private filesystem paths.

## Baseline Results

Every cell below is `pending operator receipt`: no measurement has been executed
and recorded yet. Replace a cell only with a value produced by the sequence
above, taken from the script output. Never estimate, never copy a number from a
different environment, and never fill a cell from a projection.

| Storage class | Absolute size | Growth per day | Growth per 1000 events | Projected 12 months | Projected 36 months | Measured at |
| --- | --- | --- | --- | --- | --- | --- |
| `relational` — PostHog relational data (`graf-posthog_postgres-data`) | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt |
| `events` — measurement events (`graf-posthog_clickhouse-data`) | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt |
| `object_storage` — session-recording and media objects (`graf-posthog_objectstorage`, `graf-posthog_seaweedfs`) | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt |
| `queue_cache` — queue and cache durability (`graf-posthog_redis7-data`) | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt |
| `broker` — ingest broker state (`graf-posthog_kafka-data`, `graf-posthog_redpanda-data`) | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt |
| `coordination` — coordination state (`graf-posthog_zookeeper-*`) | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt |
| `analytics_filesystem_total` — whole analytics filesystem | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt |
| `backup_artifacts` — local backup copies on the measured server | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt | pending operator receipt |

Storage classes follow the volume classes in `infra/posthog/backup-volumes.txt`.
A class marked optional there is measured only when the reviewed runtime uses
it; a class absent from the reviewed runtime is recorded as
`not present in reviewed runtime` instead of a number.

## Expected Order Of Magnitude

The specification expects hundreds to thousands of visits per day at launch,
with the analytics node running on the same server as the product (FR-039,
plan scale assumptions). Two consequences fix the measurement scale:

- event counts are small enough that ingest processing, not raw event volume, is
  the first limit to watch;
- the analytics node shares the host disk with the product, so the disk
  guardrails are the real product-availability guardrail.

The expected magnitude is a planning statement, not a receipt. It must never be
written into the results table as a measured value.

## How The Numbers Feed The Guard Thresholds

| Guard threshold | Default | How the baseline sets it |
| --- | --- | --- |
| `GRAF_POSTHOG_GUARD_ANALYTICS_QUEUE_GROWTH_PER_MIN` | `5000` per minute | The baseline converts the measured event rate into events per minute. The threshold must sit above the expected peak ingest rate — including the fivefold traffic spike in SC-012 — so ordinary traffic and a spike raise an alert without disabling measurement. |
| `GRAF_POSTHOG_GUARD_ANALYTICS_DISK_FREE_PERCENT` | `20` (`<20 %` free disables measurement) | The baseline projects daily growth from the measured absolute size, so the free-space floor can be checked against the date it would be reached. If the projection crosses the floor before the next planned capacity action, the capacity action — not the threshold — has to change. |

Target accounting and action: `specs/273-paid-traffic-analytics/contracts/operations.md`
§Один физический диск продукта и аналитики. Record non-overlapping analytics
class bytes, one filesystem identity/free-space sample, accepted absolute budget,
growth and expansion deadline. On a shared filesystem `<20%` free triggers
analytics protection regardless of the unproven cause; `<10%` adds a critical
host alert. Emit both facts and one protective action. Do not count the same
free space twice or claim the analytics classes caused its depletion. A missing
measurement/budget blocks readiness; T097 is still pending.

Measured growth determines the capacity-action deadline under the accepted
`until_decision` mode. There is no age-based volume cap. Growth with flat
traffic calls for a measured cause investigation; it does not by itself mean
that a deletion task is broken. Do not raise thresholds or delete history to
hide an approaching capacity limit.

## Load Check And Traffic Spike Behaviour

FR-039 requires a load check, and SC-012 defines the measurable site profile.
The normative input, phases and acceptance are in
`specs/273-paid-traffic-analytics/contracts/operations.md`, «Нагрузка сайта»:
R is p95 HTML GET requests/second over 10,080 complete UTC minutes from the
specified five routes; each sample is the minute count divided by 60. Warm up
5 minutes at R, sustain 20 minutes at 5×R, recover 15 minutes at R. The p95
uses nearest rank ceil(0.95×N). Missing coverage/classification is unknown,
not zero; a separate 1→5→1 requests/second engineering probe does not prove
the measured-baseline criterion. No production load run is authorized here.

Record, per check run:

- the peak ingest rate in events per minute and the peak queue depth;
- the peak delivery lag and whether the guard reported any analytics-scope
  disable reason — it must not;
- all host-scope alerts and any shared-filesystem protection separately;
  a mere CPU/memory alert does not disable measurement, but shared-disk
  protection fails and stops the load run according to the operations contract;
- the `analytics_disk_free_percent` value after the spike.

Traffic generated by the check itself is not visitor traffic. Classify it as
internal, support, or test through the approved traffic-class marker so the
baseline and the reports describe real visitors only. The check and its
observations are `pending operator receipt`.

## Хранение и прогноз роста — актуализация 21.10.2026

Решение владельца отменяет возрастную очистку IP и допустимой аналитики:
явный режим `until_decision`, удаление по отдельному решению/обязательному
требованию. Прежние 365/1095 дней не ограничивают прогноз. Окно атрибуции
90 дней ограничивает применение источника, а не автоматически объём истории.

Прогнозы 12/36 месяцев остаются горизонтами планирования ёмкости. Плато объёма
из-за TTL предполагать нельзя. Нужно измерить абсолютный объём, рост в сутки,
запас и дату исчерпания; результаты T097 ещё ожидают оператора. При нехватке
места — оповещение и остановка новых необязательных записей, а не удаление истории.
Рабочая миграция T109 и восстановление старой копии требуют отдельной проверки.

## Evidence Rules

- Record classes, byte counts, event counts, percentages, and UTC timestamps
  only.
- Never record event payloads, visitor or user identifiers, provider secrets,
  account data, or private filesystem paths.
- Never record a value that no operator measured; `pending operator receipt`
  stays until the run happens and its output is filed.
- A capacity review that changes a guard threshold records the measured
  baseline reference together with the new value.


## Initial numeric envelope — 2026-10-22

F273 operations §Начальные численные пределы sets a 128 GiB total ceiling,
including analytics data, network metadata and local archives; 0.5 GiB/day
maximum measured aggregate growth and 90-day projected headroom are both
required. Role: infra_operator; reassess by 2026-11-21 UTC. Begin expansion
planning 28 days before forecast exhaustion, with an accepted operator action
within 7 days. Missing/incomplete measurements do not count as zero or PASS.
A read-only Docker sizing (~6.9 GB PostHog volumes, no analytics backup yet)
checks plausibility only; it does not close T097 or prove growth/load acceptance.
The exact byte values and decision limits are canonical in operations.md.
