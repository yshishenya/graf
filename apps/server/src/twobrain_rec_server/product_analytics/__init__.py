"""Safe product activation analytics contracts.

The package is intentionally provider-agnostic. It validates the approved
activation contract and keeps live provider delivery disabled until rollout
gates are passed.
"""

from twobrain_rec_server.product_analytics.event_catalog import (
    PRODUCT_ACTIVATION_EVENT_NAMES,
    YANDEX_OFFLINE_CONVERSION_EVENTS,
    event_names,
)

__all__ = [
    "PRODUCT_ACTIVATION_EVENT_NAMES",
    "YANDEX_OFFLINE_CONVERSION_EVENTS",
    "event_names",
]
