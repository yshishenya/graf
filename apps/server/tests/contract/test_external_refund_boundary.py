import inspect

from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.db.models import BillingAuditEvent, BillingInvoice


def test_product_has_no_refund_mutation_and_no_support_correspondence_model() -> None:
    assert not hasattr(YooKassaClient, "create_refund")
    assert "support_email_body" not in BillingAuditEvent.__table__.c
    assert "support_email_body" not in BillingInvoice.__table__.c
    source = inspect.getsource(YooKassaClient)
    assert "POST\", \"/v3/refunds" not in source
