"""Internal, support, test and automated traffic stay out of reports (FR-013).

Reports must answer "what did paid traffic bring". A visit from the operator's
own browser, from a smoke check or from a crawler would answer that question
wrongly, so it is excluded. The distinction is preserved instead of dropped:
the visit is still classified and stored with its class, and reports read only
the reported classes. Nothing in this module looks at, keeps or returns an
identifier: the user agent and the network address are read transiently to
classify one request and are never part of any stored value.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable, Mapping
from typing import Any

TRAFFIC_CLASSES = (
    "external",
    "internal",
    "support",
    "test",
    "automated",
)
# Reports read exactly these classes; everything else is measurement hygiene.
REPORTED_TRAFFIC_CLASSES = ("external",)
DEFAULT_TRAFFIC_CLASS = "external"

# An operator-controlled marker for browsers, smoke runners and support tools.
# Mislabeling can only remove visits from reports, never add invented ones, and
# the default for an unknown or malformed marker stays "external".
TRAFFIC_CLASS_HEADER = "x-graf-traffic-class"
TRAFFIC_CLASS_QUERY_PARAM = "graf_traffic_class"

_AUTOMATED_USER_AGENT_MARKERS = (
    "bot",
    "crawler",
    "spider",
    "curl/",
    "wget/",
    "python-requests/",
    "python-urllib/",
    "go-http-client/",
    "headlesschrome",
    "lighthouse",
    "pagespeed",
    "uptime",
    "monitoring",
    "kube-probe",
    "healthcheck",
    "grafana",
    "posthog",
    "zgrab",
    "masscan",
)


def normalize_traffic_class(value: Any) -> str:
    """Return a known class; anything unknown falls back to external.

    Falling back to ``external`` keeps real visitors counted: an unreadable
    marker must reduce reporting hygiene, never silently drop a visit.
    """
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_")
        if normalized in TRAFFIC_CLASSES:
            return normalized
    return DEFAULT_TRAFFIC_CLASS


def classify_public_traffic(
    *,
    headers: Mapping[str, Any] | None = None,
    query_params: Any | None = None,
    user_agent: str | None = None,
    client_host: str | None = None,
    internal_hosts: Iterable[str] = (),
) -> str:
    """Classify one public request without keeping any identifier.

    Evidence order: a trusted explicit operator marker from the internal request
    path, then a configured operator address, then automated-client markers in the
    user agent. Public query parameters are intentionally not trusted: a visitor
    must not be able to remove their own visit from paid-traffic reports.
    """
    explicit = normalize_traffic_class(_header_value(headers, TRAFFIC_CLASS_HEADER))
    if explicit != DEFAULT_TRAFFIC_CLASS and client_host and _is_operator_address(client_host, internal_hosts):
        return explicit
    if client_host and _is_operator_address(client_host, internal_hosts):
        # A trusted operator address is always internal unless it carries an
        # explicit, trusted class marker. Never let a public request choose an
        # excluded class merely by adding a header.
        return "internal"
    if user_agent and is_automated_user_agent(user_agent):
        return "automated"
    return DEFAULT_TRAFFIC_CLASS


def is_automated_user_agent(user_agent: str) -> bool:
    lowered = user_agent.lower()
    return any(marker in lowered for marker in _AUTOMATED_USER_AGENT_MARKERS)


def is_reportable_traffic(traffic_class: Any) -> bool:
    """Fail closed: only explicitly reported classes reach reports."""
    return isinstance(traffic_class, str) and traffic_class in REPORTED_TRAFFIC_CLASSES


def reportable_traffic_classes() -> tuple[str, ...]:
    return REPORTED_TRAFFIC_CLASSES


def build_traffic_class_disclosure() -> dict[str, Any]:
    """Report caveat text: what is excluded and why the share is disclosed."""
    return {
        "reported_classes": list(REPORTED_TRAFFIC_CLASSES),
        "excluded_classes": [
            traffic_class
            for traffic_class in TRAFFIC_CLASSES
            if traffic_class not in REPORTED_TRAFFIC_CLASSES
        ],
        "exclusion_marker": TRAFFIC_CLASS_HEADER,
        "caveat": (
            "Internal, support, test and automated visits are counted with their own "
            "class and excluded from reports, so reported numbers describe external "
            "traffic only."
        ),
    }


def _header_value(headers: Mapping[str, Any] | None, name: str) -> Any:
    if headers is None:
        return None
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    value = getter(name)
    if value is None:
        value = getter(name.title())
    return value


def _query_value(query_params: Any | None, name: str) -> Any:
    if query_params is None:
        return None
    getter = getattr(query_params, "get", None)
    if getter is None:
        return None
    value = getter(name)
    if isinstance(value, list | tuple):
        return value[0] if value else None
    return value


def _is_operator_address(client_host: str, internal_hosts: Iterable[str]) -> bool:
    """Match a connection address against exact addresses or configured networks.

    The source is the ASGI connection address, not a client-controlled forwarding
    header. Invalid entries fail closed and do not classify a visitor as internal.
    """
    try:
        address = ipaddress.ip_address(client_host.strip())
    except ValueError:
        return False
    for configured in internal_hosts:
        value = configured.strip()
        if not value:
            continue
        try:
            if "/" in value:
                if address in ipaddress.ip_network(value, strict=False):
                    return True
            elif address == ipaddress.ip_address(value):
                return True
        except ValueError:
            continue
    return False
