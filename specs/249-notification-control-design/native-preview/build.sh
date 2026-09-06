#!/usr/bin/env sh
set -eu
cat >&2 <<'MESSAGE'
Этот путь отключён: локальные проверки выполняются в /Applications/GRAF Dev.app.
Используйте infra/scripts/dev-harness.sh: status --json, build, promote, smoke.
Инструкция: docs/agent-guidance/local-development.md и infra/dev/README.md.
Не создавайте отдельную копию приложения и не обходите проверки подписи/SHA.
MESSAGE
exit 1
