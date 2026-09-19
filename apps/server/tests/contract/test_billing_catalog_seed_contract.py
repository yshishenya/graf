"""The seeded catalog must stay identical to what the product advertises.

The migration owns the rows; the public page owns the promise. If the two drift
apart, checkout silently stops approving plans or, worse, advertises one price
and charges another.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from twobrain_rec_server.billing.catalog import plan_descriptor
from twobrain_rec_server.public.offers import (
    PUBLIC_ANNUAL_AMOUNT_MINOR,
    PUBLIC_APPROVED_OFFER_VERSION,
    PUBLIC_MONTHLY_AMOUNT_MINOR,
)

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "twobrain_rec_server"
    / "db"
    / "migrations"
    / "versions"
    / "0093_billing_catalog_seed.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("billing_catalog_seed_0093", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_seed_uses_the_approved_offer_revision() -> None:
    migration = _load_migration()

    assert migration.OFFER_VERSION == PUBLIC_APPROVED_OFFER_VERSION


def test_catalog_seed_amounts_match_the_public_offer() -> None:
    migration = _load_migration()
    amounts = {row["cycle"]: row["amount_minor"] for row in migration.APPROVED_ROWS}

    assert amounts == {
        "month": PUBLIC_MONTHLY_AMOUNT_MINOR,
        "year": PUBLIC_ANNUAL_AMOUNT_MINOR,
    }


def test_catalog_seed_matches_the_personal_plan_descriptor() -> None:
    migration = _load_migration()
    descriptor = plan_descriptor("personal")
    descriptor_amounts = {
        "month": descriptor.monthly_amount_minor,
        "year": descriptor.annual_amount_minor,
    }

    for row in migration.APPROVED_ROWS:
        assert row["amount_minor"] == descriptor_amounts[row["cycle"]]
    assert descriptor.storage_bytes == migration.STORAGE_BYTES
    assert descriptor.processing_mode == migration.PROCESSING_MODE
    assert migration.CURRENCY == "RUB"


def test_catalog_seed_revision_extends_the_current_chain() -> None:
    migration = _load_migration()

    assert migration.revision == "0093_billing_catalog_seed"
    assert migration.down_revision == "0092_recording_origin_cancel"
