"""The scanner and dispatcher must receive the same sharing authority as API."""

from pathlib import Path

import yaml


def test_production_sharing_services_receive_matching_flags_and_identity_secret():
    root = Path(__file__).parents[4]
    services = yaml.safe_load((root / "infra/docker-compose.yml").read_text())["services"]
    flags = (
        "TWOBRAIN_SHARE_EXTERNAL_INVITATIONS_ENABLED",
        "TWOBRAIN_SHARE_PUBLIC_LINKS_ENABLED",
        "TWOBRAIN_SHARE_PUBLIC_LINKS_ABUSE_GATE_APPROVED",
    )
    for name in ("rec-api", "rec-processing-worker", "rec-maintenance"):
        service = services[name]
        for flag in flags:
            assert service["environment"][flag] == f"${{{flag}:-false}}"
        assert service["environment"]["TWOBRAIN_SHARE_IDENTITY_HASH_SECRET_FILE"] == (
            "/run/secrets/graf_share_identity_hash_secret"
        )
        secret = next(
            item
            for item in service["secrets"]
            if item["source"] == "graf_share_identity_hash_secret"
        )
        assert secret["target"] == "graf_share_identity_hash_secret"
        if name == "rec-maintenance":
            assert (secret["uid"], secret["gid"], secret["mode"]) == ("100", "101", 0o440)
        assert service["group_add"] == ["${TWOBRAIN_RUNTIME_SECRET_GID:-1001}"]


def test_dev_sharing_preserves_disabled_real_email_and_valid_settings():
    from twobrain_rec_server.config import Settings

    root = Path(__file__).parents[4]
    environment = yaml.safe_load(
        (root / "infra/docker-compose.dev.yml").read_text().split("services:", 1)[0]
    )[
        "x-server-env"
    ]
    assert environment["TWOBRAIN_SHARE_EXTERNAL_INVITATIONS_ENABLED"] == "false"
    assert environment["TWOBRAIN_EMAIL_LOGIN_DELIVERY_ENABLED"] == "false"
    Settings(
        env="development",
        public_base_url="http://127.0.0.1:8081",
        share_public_links_enabled=True,
        share_public_links_abuse_gate_approved=True,
        share_external_invitations_enabled=False,
        email_login_delivery_enabled=False,
    )
