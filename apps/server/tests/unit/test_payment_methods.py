from uuid import UUID

import pytest
from cryptography.fernet import Fernet

from twobrain_rec_server.billing.entitlements import recurring_actor_matches_current_owner
from twobrain_rec_server.billing.payment_methods import (
    BillingEncryptionKeyring,
    PaymentMethodEncryptionError,
)


def test_payment_method_keyring_writes_current_and_reads_previous_key() -> None:
    previous_key = Fernet.generate_key()
    current_key = Fernet.generate_key()
    previous_only = BillingEncryptionKeyring("billing-v1", {"billing-v1": previous_key})
    previous = previous_only.seal("pm_previous_123")
    keyring = BillingEncryptionKeyring(
        "billing-v2",
        {"billing-v1": previous_key, "billing-v2": current_key},
    )

    current = keyring.seal("pm_current_456")

    assert current.key_version == "billing-v2"
    assert keyring.open(ciphertext=current.ciphertext, key_version=current.key_version) == "pm_current_456"
    assert keyring.open(ciphertext=previous.ciphertext, key_version=previous.key_version) == "pm_previous_123"


def test_payment_method_keyring_rotation_reencrypts_with_current_key() -> None:
    previous_key = Fernet.generate_key()
    current_key = Fernet.generate_key()
    previous = BillingEncryptionKeyring("billing-v1", {"billing-v1": previous_key}).seal("pm_rotate_123")
    keyring = BillingEncryptionKeyring(
        "billing-v2",
        {"billing-v1": previous_key, "billing-v2": current_key},
    )

    rotated = keyring.rotate(ciphertext=previous.ciphertext, key_version=previous.key_version)

    assert rotated.key_version == "billing-v2"
    assert rotated.ciphertext != previous.ciphertext
    assert keyring.open(ciphertext=rotated.ciphertext, key_version=rotated.key_version) == "pm_rotate_123"


def test_payment_method_keyring_fails_closed_for_unknown_or_wrong_key() -> None:
    current_key = Fernet.generate_key()
    sealed = BillingEncryptionKeyring("billing-v2", {"billing-v2": current_key}).seal("pm_secret_123")

    with pytest.raises(PaymentMethodEncryptionError, match="version is unavailable"):
        BillingEncryptionKeyring("billing-v3", {"billing-v3": Fernet.generate_key()}).open(
            ciphertext=sealed.ciphertext,
            key_version="billing-v2",
        )
    with pytest.raises(PaymentMethodEncryptionError, match="reference is unavailable"):
        BillingEncryptionKeyring("billing-v2", {"billing-v2": Fernet.generate_key()}).open(
            ciphertext=sealed.ciphertext,
            key_version="billing-v2",
        )


def test_payment_method_crypto_objects_do_not_expose_keys_or_ciphertext_in_repr() -> None:
    key = Fernet.generate_key()
    keyring = BillingEncryptionKeyring("billing-v1", {"billing-v1": key})
    sealed = keyring.seal("pm_private_123")

    assert key.decode("ascii") not in repr(keyring)
    assert sealed.ciphertext not in repr(sealed)
    assert "pm_private_123" not in repr(sealed)


def test_recurring_authority_does_not_transfer_to_a_new_workspace_owner() -> None:
    checkout_owner = UUID("11111111-1111-4111-8111-111111111111")
    replacement_owner = UUID("22222222-2222-4222-8222-222222222222")

    assert recurring_actor_matches_current_owner(
        snapshot_actor=str(checkout_owner),
        current_owner_id=checkout_owner,
    )
    assert not recurring_actor_matches_current_owner(
        snapshot_actor=str(checkout_owner),
        current_owner_id=replacement_owner,
    )
    assert not recurring_actor_matches_current_owner(
        snapshot_actor=None,
        current_owner_id=replacement_owner,
    )
