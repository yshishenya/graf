# Data Model: Cabinet Web Split

073 does not add database tables or application data models. The model below
defines the refactor concepts used by tasks and validation.

## CabinetWebRouter

- `public_import`: `twobrain_rec_server.cabinet.web.router`
- `owner`: cabinet web layer
- `routes`: all existing browser and desktop cabinet web routes
- `invariant`: import path and route contracts stay stable

## RouteFamily

- `name`: static icons, browser auth, browser meetings/settings, calendar
  settings, desktop embedded pages, deletion, or shared support
- `paths`: existing HTTP paths owned by the family
- `dependencies`: existing FastAPI dependencies and helpers used by the family
- `validation`: focused tests proving moved routes still behave the same

## SharedWebDependency

- `name`: tenant scope, principal, CSRF, database session, storage, query/form
  parsing, HX detection, browser auth cookie, or safe redirect helper
- `current_behavior`: existing behavior before split
- `invariant`: no dependency weakening or duplication

## RouteContract

- `path`: existing route path
- `method`: existing HTTP method
- `response_class`: existing response class
- `status_or_redirect`: existing status/redirect behavior
- `security_guards`: auth/session/tenant/CSRF dependencies
- `fragment_behavior`: existing HX behavior if applicable
