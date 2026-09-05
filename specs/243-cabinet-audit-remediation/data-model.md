# F243 data model

No schema/migrations or stored-data changes.

- Account preferences retain theme=system/light/dark, locale=ru-RU/en-US,
  timezone=Europe/Moscow/UTC; existing authenticated server writer.
- Confirmation: at most one alert/completion, idle→pending→accepted/cancelled;
  teardown cancels, callback exactly once, no private message logging.
- Route: configured origin, exact normalized path, valid identifiers/query;
  malformed/foreign/unknown blocked. Legal handoff without secrets.
- Shared meeting, session/device and personal format ownership stay server-owned;
  opening a URL grants no permission.
