"""Global user projection preserves payer scope and hides financial fields."""

import json
from uuid import uuid4

import asyncpg
import pytest

from tests.conftest import PERSONAL_WORKSPACE_ID, USER_ID, WORKSPACE_ID
from tests.integration import test_system_admin_security as security

system_database = security.system_database
pytestmark = pytest.mark.strict_rls


@pytest.mark.asyncio
@pytest.mark.parametrize("role,money", [("superadmin",True),("billing_manager",True),("support",False),("system_admin",False)])
async def test_user_projection_uses_only_personal_payer_money(system_database,role,money):
    db=system_database
    await db["owner"].execute("update system_control.role_assignments set role=$1",role)
    for workspace,amount in ((PERSONAL_WORKSPACE_ID,12345),(WORKSPACE_ID,99999)):
        operation=uuid4()
        await db["owner"].execute("""insert into billing_operations(id,workspace_id,kind,idempotency_key,state)
            values($1,$2,'purchase',$3,'succeeded')""",operation,workspace,str(operation))
        await db["owner"].execute("""insert into billing_invoices(id,workspace_id,operation_id,safe_number,amount_minor,currency,status)
            values($1,$2,$3,$4,$5,'RUB','succeeded')""",uuid4(),workspace,operation,str(operation),amount)
    conn=await asyncpg.connect(db["url"].replace("+asyncpg",""))
    try:
        async with conn.transaction():
            await security._context(conn,db,**{"app.system_permission":"users.read"})
            result=json.loads(await conn.fetchval("select system_control.list_users(null,null,null,null)"))
            user=next(row for row in result if row["id"]==str(USER_ID))
            assert user["paid_amount_minor_rub"] == (12345 if money else None)
            assert user["financial_fields_available"] is money
            for table in ("user_identities","external_identities","billing_invoices","billing_payment_methods"):
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    async with conn.transaction():
                        await conn.fetch(f"select * from {table}")
    finally:
        await conn.close()
