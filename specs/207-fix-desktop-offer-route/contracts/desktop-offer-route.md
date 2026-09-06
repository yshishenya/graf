# Contract: Desktop Offer Route

## Allowed source

- Scheme: HTTPS для production configuration.
- Origin: тот же origin, что у embedded cabinet.
- Path: ровно `/offer`.

## Decision

- Route action: open externally.
- External destination: тот же verified origin и `/offer`.
- Query: absent.
- Fragment: absent.
- User info: absent.

## Negative contract

- `/offer/extra`, сторонние hosts, HTTP и неизвестные legal-like paths не получают разрешение автоматически.
- Открытие не создаёт payment, subscription, consent или server-side mutation.
- Embedded checkout остаётся текущим рабочим экраном GRAF.
