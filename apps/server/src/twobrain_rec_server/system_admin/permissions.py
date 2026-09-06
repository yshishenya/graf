"""Fixed product permissions; PostgreSQL remains the enforcement boundary."""

from types import MappingProxyType

PERMISSIONS = frozenset(
    [
        "users.read",
        "meetings.metadata",
        "content.read",
        "audio.listen",
        "audio.download",
        "content.export",
        "diagnostics.content",
        "processing.read",
        "processing.reprocess",
        "billing.read",
        "billing.manage",
        "catalog.read",
        "catalog.draft",
        "catalog.publish",
        "promotions.read",
        "promotions.draft",
        "promotions.manage",
        "promotions.publish",
        "support.read",
        "support.manage",
        "devices.read",
        "sessions.manage",
        "integrations.read",
        "integrations.manage",
        "operations.read",
        "operations.manage",
        "settings.read",
        "settings.manage",
        "analytics.read",
        "audit.read",
        "exports.table",
        "deletion.manage",
        "fair_use.manage",
        "queue.manage",
        "notifications.retry",
        "admins.manage",
    ]
)
CONTENT_PERMISSIONS = frozenset(
    {
        "content.read",
        "audio.listen",
        "audio.download",
        "content.export",
        "diagnostics.content",
    }
)
ROLE_PERMISSIONS = MappingProxyType(
    {
        "superadmin": PERMISSIONS,
        "system_admin": frozenset(
            [
                "users.read",
                "meetings.metadata",
                "processing.read",
                "devices.read",
                "support.read",
                "integrations.read",
                "operations.read",
                "processing.reprocess",
                "support.manage",
                "operations.manage",
                "integrations.manage",
                "notifications.retry",
                "settings.read",
                "settings.manage",
                "exports.table",
            ]
        ),
        "support": frozenset(
            [
                "users.read",
                "meetings.metadata",
                "processing.read",
                "devices.read",
                "support.read",
                "integrations.read",
                "support.manage",
            ]
        ),
        "billing_manager": frozenset(
            [
                "users.read",
                "billing.read",
                "catalog.read",
                "catalog.draft",
                "promotions.read",
                "promotions.draft",
                "exports.table",
            ]
        ),
        "analyst": frozenset({"analytics.read", "exports.table"}),
        "auditor": frozenset({"audit.read", "exports.table"}),
    }
)
TARGET_TYPES = frozenset(
    {
        "meeting",
        "user",
        "workspace",
        "subscription",
        "invoice",
        "plan",
        "plan_version",
        "campaign",
        "device",
        "incident",
        "system",
    }
)
GRANT_TARGETS = MappingProxyType(
    {
        **{permission: frozenset({"meeting"}) for permission in CONTENT_PERMISSIONS},
        "billing.manage": frozenset({"user", "workspace", "subscription", "invoice"}),
        "catalog.publish": frozenset({"plan", "plan_version"}),
        "promotions.manage": frozenset({"campaign"}),
        "promotions.publish": frozenset({"campaign"}),
    }
)
