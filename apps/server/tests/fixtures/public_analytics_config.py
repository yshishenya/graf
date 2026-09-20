"""Print the public analytics page config the browser controller receives.

The browser scenario harness (``tests/browser/public-analytics-consent.test.cjs``)
must run against the real config shape instead of a hand-written copy, so this
fixture builds it with the production builder. Only the public config is printed:
it contains the counter id, stable label catalogs and the first-party relay path,
and no secret ever reaches the browser.
"""

import json
import sys

from twobrain_rec_server.config import Settings
from twobrain_rec_server.public.analytics import build_public_analytics_context


def build_config(path: str = "/download") -> dict:
    settings = Settings(
        database_url="postgresql+asyncpg://localhost/public_analytics_harness",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="12345678",
        public_analytics_replay_enabled=True,
    )
    return build_public_analytics_context(settings, path)


def main() -> int:
    # The page path decides the surface, and a scenario that renders the consent
    # modal needs the config of the page it stands on.
    path = sys.argv[1] if len(sys.argv) > 1 else "/download"
    json.dump(build_config(path), sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
