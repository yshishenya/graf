# Contract: Cabinet Web Route Preservation

Each route moved by 073 must preserve this contract.

```yaml
route:
  path: "/existing/path"
  method: "GET|POST"
  include_in_schema: false
  response_class: "existing response class"
  owner_family: "browser-auth|browser-pages|calendar|desktop|deletion|static"
preserve:
  status_code: "same as before"
  redirect_target: "same as before when applicable"
  auth_dependency: "same as before"
  csrf_dependency: "same as before for POST routes"
  tenant_scope: "same as before"
  hx_fragment_behavior: "same as before when applicable"
  no_secret_content: true
forbidden:
  - template semantic changes
  - view-model semantic changes
  - deletion/retention semantic changes
  - egress/download/export semantic changes
  - auth provider semantic changes
  - route path or method changes
  - production deploy
```

## Validation Rule

A moved route is acceptable only when its focused tests pass without weakening
assertions. If no focused test covers the moved route family, add the smallest
test that fails if route registration or security dependency is lost.
