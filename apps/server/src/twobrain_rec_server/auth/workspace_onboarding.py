JOIN_OFFER_TRANSITIONS = {
    "offered": frozenset(("accepted", "rejected", "expired", "revoked")),
    "accepted": frozenset(),
    "rejected": frozenset(),
    "expired": frozenset(),
    "revoked": frozenset(),
}


def can_transition_join_offer(current: str, target: str) -> bool:
    return target in JOIN_OFFER_TRANSITIONS.get(current, frozenset())
