import pytest

from twobrain_rec_server.billing.catalog import (
    ADDON_CAPACITY_BYTES,
    PERSONAL_STORAGE_BYTES,
    classify_storage_threshold,
    storage_capacity_bytes,
)
from twobrain_rec_server.billing.storage import (
    StorageAdmissionError,
    StorageProjection,
    StorageReservation,
    admit_storage,
    commit_object_bytes,
    release_storage,
)


def test_storage_projection_uses_exact_decimal_capacities_and_thresholds() -> None:
    projection = StorageProjection(used_bytes=1_600_000_000, reserved_bytes=0, capacity_bytes=PERSONAL_STORAGE_BYTES)
    assert projection.threshold == "80%"
    assert classify_storage_threshold(used_bytes=PERSONAL_STORAGE_BYTES, capacity_bytes=PERSONAL_STORAGE_BYTES) == "full"
    assert storage_capacity_bytes("personal", ADDON_CAPACITY_BYTES[0]) == ADDON_CAPACITY_BYTES[0]


def test_storage_reservation_rejects_admission_and_object_stat_overrun() -> None:
    with pytest.raises(StorageAdmissionError):
        admit_storage(StorageProjection(100, 50, 120), 1)
    reservation = StorageReservation("r1", 100)
    with pytest.raises(StorageAdmissionError):
        commit_object_bytes(reservation=reservation, actual_bytes=101)


def test_storage_projection_is_bounded_by_capacity() -> None:
    projection = StorageProjection(used_bytes=200, reserved_bytes=10, capacity_bytes=250)
    assert projection.available_bytes == 40


def test_storage_reservation_release_is_idempotent_and_capacity_validation_is_fail_closed() -> None:
    reservation = StorageReservation("r1", declared_bytes=100)
    release_storage(reservation)
    release_storage(reservation)
    assert reservation.state == "released"
