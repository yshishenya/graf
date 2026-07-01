# Contract: Dependency Graph Evidence

Each dependency graph section in `audit/dependency-graphs.md` must record:

```yaml
graph_id: python-server | swift-macos | shell-infra | docker-runtime
scope:
  - exact/path/or/glob
nodes:
  - "module, package, target, script, service, or runtime image"
edges:
  - from: "source node"
    to: "target node"
    type: import | target-dependency | script-call | service-dependency | runtime-command
interpretation:
  - "Boundary or risk conclusion"
limitations:
  - "Static-analysis blind spot or deferred proof"
```

## Rules

- Direct imports are evidence, not automatic refactor permission.
- Runtime-only dependencies must be checked against Docker, scripts, DB URLs,
  test config, and framework conventions before classification.
- Swift target dependencies must be taken from `apps/macos/Package.swift`.
- Shell and Docker relationships must distinguish entrypoints from helper
  scripts and production services from networks, volumes, and secrets.

