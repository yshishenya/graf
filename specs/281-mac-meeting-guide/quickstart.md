# Проверка F281

Lane: tiny-low-risk content, без нового data/API contract.

`PYTHONPATH="$PWD/apps/server/src" bash apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_public_mac_meeting_guide.py tests/unit/test_public_landing.py tests/contract/test_public_landing_contract.py -q`

Проверить нулевой diff protected templates/assets. Mobile widths 360/390/768: overflow 0, один H1, ссылка download. Production: только после exact-SHA CI и штатного full release candidate с backup/rollback.
