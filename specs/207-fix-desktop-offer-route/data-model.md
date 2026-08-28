# Data Model: Safe Desktop Offer Route

Feature не создаёт и не изменяет persistent entities.

## Runtime values

- **Source URL**: same-origin HTTPS URL, который пользователь открыл из checkout.
- **Canonical external URL**: production scheme/host/port и путь `/offer` без user info, query и fragment.
- **Route decision**: внешнее открытие для точного `/offer`; fail-closed для неизвестных sibling routes.

## State transitions

Persistent state transitions отсутствуют. Открытие оферты не меняет payment, subscription, consent или checkout state.
