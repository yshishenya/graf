"""A real old dump, current deletion cases, and an isolated one-shot process."""

import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.integration.test_deployment_backup_snapshot import REPO, capture, psql

pytestmark = pytest.mark.postgres
MODULE = "twobrain_rec_server.product_analytics.restore_replay"


def closed(path, value):
    path.write_text(value)
    path.chmod(0o600)
    return path


@pytest.fixture
def replay_world(postgres_isolated_cluster_database_url, tmp_path, monkeypatch, request):
    from twobrain_rec_server.product_analytics.restore_replay import digest

    tmp_path.chmod(0o700)
    # This fixture owns this fresh directory; retain logs, never fixture dumps/passwords.
    request.addfinalizer(lambda: shutil.rmtree(tmp_path))
    url = make_url(postgres_isolated_cluster_database_url)
    source_name = url.database
    suffix = source_name.removeprefix("twobrain_rec_test_")
    assert len(suffix) == 32 and all(c in "0123456789abcdef" for c in suffix)
    container = "graf-postgres-test-bootstrap-" + suffix
    spec = importlib.util.spec_from_file_location(
        "replay_bootstrap", REPO / "apps/server/scripts/bootstrap_runtime_database_roles.py")
    bootstrap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bootstrap)
    for key, value in (("HOST", url.host), ("PORT", str(url.port)), ("NAME", source_name)):
        monkeypatch.setenv("TWOBRAIN_DB_" + key, value)
    for role in ("OWNER", "APP", "MAINTENANCE", "MEDIA"):
        secret = closed(tmp_path / (role + "-password"),
                        url.password if role == "OWNER" else uuid4().hex)
        monkeypatch.setenv("TWOBRAIN_DB_" + role + "_PASSWORD_FILE", str(secret))
    asyncio.run(bootstrap._bootstrap())
    def owner(sql, db=source_name):
        return psql(container, sql, database=db, role="twobrain_rec")
    owner(f'ALTER DATABASE "{source_name}" RENAME TO twobrain_rec', "postgres")
    states = ["pending", "pre_send_retry", "dispatching", "submitted", "ambiguous",
              "confirmed", "cancelled", "rejected", "not_requested"]
    accounts = [uuid4() for _ in states]
    organization, workspace, closure = uuid4(), uuid4(), uuid4()
    now = datetime.now(UTC)
    owner(f"INSERT INTO organizations(id,slug,name) VALUES('{organization}','synthetic','Synthetic')",
          "twobrain_rec")
    for index, (account, state) in enumerate(zip(accounts, states, strict=True)):
        owner(f"""INSERT INTO user_identities(id,organization_id,external_subject,locale,theme,status)
            VALUES('{account}','{organization}','synthetic-{index}','ru-RU','system','active');
            INSERT INTO product_activation_milestones
              (id,account_id,event_name,event_id,occurred_at,accepted_at,safe_payload,source_kind,
               posthog_state,yandex_state) VALUES('{uuid4()}','{account}','first_result_viewed',
               '{uuid4()}',now(),now(),'{{}}','browser','{state}','{states[-index-1]}')""", "twobrain_rec")
    owner(f"""INSERT INTO workspaces(id,organization_id,slug,name,kind,owner_user_id,
                default_summary_template_key,default_summary_template_version)
          VALUES('{workspace}','{organization}','synthetic','Synthetic','personal','{accounts[0]}',
                 'graf-auto-v1',1);
        INSERT INTO account_closure_requests(id,workspace_id,requested_by_user_id,request_key,
                state,policy_version,requested_at,finalize_at,metadata_json)
          VALUES('{closure}','{workspace}','{accounts[0]}','synthetic-close','scheduled',
                 'account-close-v1','{now-timedelta(days=8)}','{now-timedelta(days=1)}','{{}}');
        INSERT INTO account_closure_requests(id,workspace_id,requested_by_user_id,request_key,
                state,policy_version,requested_at,finalize_at,metadata_json)
          SELECT md5('synthetic-request-'||g)::uuid,'{workspace}','{accounts[0]}',
                 'synthetic-'||g,'scheduled','account-close-v1',now(),now()+interval '7 days','{{}}'
          FROM generate_series(1,501) g;
        INSERT INTO account_closure_requests(id,workspace_id,requested_by_user_id,request_key,
                state,policy_version,requested_at,finalize_at,canceled_at,metadata_json)
          VALUES('{uuid4()}','{workspace}','{accounts[0]}','synthetic-canceled','canceled',
                 'account-close-v1',now(),now()+interval '7 days',now(),'{{}}')""", "twobrain_rec")
    # Both negative and positive decisions must lose their restored epoch.
    from twobrain_rec_server.public.consent import choice_digest
    choices = [(str(uuid4()), str(uuid4())), (str(uuid4()), str(uuid4()))]
    for index, (consent_id, epoch) in enumerate(choices):
        categories = '["necessary"]' if index == 0 else '["necessary","analytics"]'
        copy = 'NULL' if index == 0 else "'2026-10-22.1'"
        owner(f"""INSERT INTO public_analytics_choices(consent_digest,epoch,categories,copy_version)
              VALUES('{choice_digest(consent_id)}','{epoch}','{categories}',{copy})""", "twobrain_rec")
    reference = tmp_path / "reference"
    capture(container, "twobrain_rec", reference, dump=True)
    oid = int(owner("SELECT oid FROM pg_database WHERE datname='twobrain_rec'", "postgres"))
    owner(f'ALTER DATABASE twobrain_rec RENAME TO "{source_name}"', "postgres")
    assert oid == int(owner(f"SELECT oid FROM pg_database WHERE datname='{source_name}'", "postgres"))

    async def finalize():
        from twobrain_rec_server.auth.account_closure import finalize_account_close

        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine)() as db:
                await finalize_account_close(db, request_id=closure, now=datetime.now(UTC))
                await db.commit()
        finally:
            await engine.dispose()

    asyncio.run(finalize())
    case = (f"disposition_case case_ref=case_synthetic decision_ref=decision_synthetic "
            f"scope=account_closure selector_ref={closure} owner_role=operator reason=account_closed "
            f"decided_at={now.isoformat()} due_at={(now+timedelta(days=1)).isoformat()} stage=accepted")
    operator = closed(tmp_path / "register", "legal_basis_state_version=2\n" + case + "\n")
    staging = tmp_path / "staging"
    staging.mkdir(mode=0o700)
    token = uuid4().hex
    target = "rec_restore_rehearsal_" + token
    owner(f'CREATE DATABASE "{target}"', "postgres")
    with (reference / "postgres.dump").open("rb") as stream:
        subprocess.run(["docker", "exec", "-i", container, "pg_restore", "--exit-on-error", "-U",
                        "twobrain_rec", "-d", target], stdin=stream, capture_output=True, check=True)
    restored = tmp_path / "restored"
    capture(container, target, restored, dump=False)
    canonical_db = "rec_restore_schema_" + token
    owner(f'CREATE DATABASE "{canonical_db}"', "postgres")
    owner((reference / "schema.sql").read_text(), canonical_db)
    canonical = tmp_path / "canonical"
    capture(container, canonical_db, canonical, dump=False)
    subprocess.run([sys.executable, str(REPO / "infra/scripts/rec-db-verify.py"), str(reference),
                    str(restored), target, str(canonical), canonical_db],
                   check=True, capture_output=True)
    binding = {"version": 1, "token": token, "source_database": source_name, "source_oid": oid,
               "target_database": target,
               "target_oid": int(owner(f"SELECT oid FROM pg_database WHERE datname='{target}'", "postgres")),
               "backup_sha256": digest((reference / "postgres.dump").read_bytes())}
    ownership = closed(tmp_path / "ownership", json.dumps(binding))
    image = os.environ.get("GRAF_REPLAY_TEST_IMAGE")
    if image:
        assert image.startswith("sha256:") and len(image) == 71
    yield {"url": url, "container": container, "source": source_name, "target": target,
           "owner": owner, "binding": binding, "ownership": ownership, "operator": operator,
           "staging": staging, "root": tmp_path, "accounts": accounts, "case": case,
           "password": tmp_path / "MAINTENANCE-password", "closure": closure,
           "image": image, "choices": choices}
    # The existing owning cluster fixture removes all synthetic DBs and volumes.
    assert not list(staging.iterdir())


def launch(world):
    command = [sys.executable, "-m", MODULE, "--host", world["url"].host,
               "--port", str(world["url"].port)]
    options = (("password-file", "password"), ("operator-file", "operator"),
               ("ownership-file", "ownership"), ("staging", "staging"))
    if world["image"]:
        # The same executable proof can be repeated in an immutable server image.
        # Mount only the one DB password and closed case/binding files, never env-file.
        uid, gid = os.getuid(), os.getgid()
        docker = shutil.which("docker")
        assert docker is not None
        command = [docker, "run", "--rm", "--pull=never", "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", "--user", f"{uid}:{gid}",
                   "--network", "container:" + world["container"],
                   "--tmpfs", f"/run/replay:rw,noexec,nosuid,mode=0700,uid={uid},gid={gid}",
                   "--tmpfs", f"/staging:rw,noexec,nosuid,size=16m,mode=0700,uid={uid},gid={gid}"]
        for _name, key in options[:-1]:
            command += ["--mount", f"type=bind,src={world[key]},dst=/run/replay/{key},readonly"]
        # Same network namespace as the owned DB; it is not declared egress-free.
        # The audit hook permits DB sockets only and fails any attempted receiver call.
        audit = ("import runpy,sys\ndenied=[]\ndef guard(event,args):\n"
                 " if event=='socket.connect' and args[1]!=('127.0.0.1',5432):\n"
                 "  denied.append(True)\n  raise RuntimeError('non_database_socket')\n"
                 "sys.addaudithook(guard)\n"
                 f"runpy.run_module('{MODULE}',run_name='__main__')\n"
                 "assert not denied, 'receiver_call_attempted'\n")
        command += ["--entrypoint", "python", world["image"], "-c", audit,
                    "--host", "127.0.0.1", "--port", "5432"]
        for name, key in options:
            command += ["--" + name, "/staging" if key == "staging" else "/run/replay/" + key]
    else:
        for name, key in options:
            command += ["--" + name, str(world[key])]
    return subprocess.run(command, capture_output=True, text=True, timeout=45,
                          env={"PATH": os.defpath, "PYTHONPATH": str(REPO / "apps/server/src"),
                               "PYTHONDONTWRITEBYTECODE": "1"})


def test_old_copy_replays_only_exact_account_and_quarantines_both(replay_world):
    world = replay_world
    source_before = world["owner"]("SELECT count(*) FROM product_activation_milestones")
    assert int(source_before) == 8
    assert int(world["owner"]("SELECT count(*) FROM account_closure_requests")) == 503
    result = launch(world)
    assert result.returncode == 0, result.stderr + result.stdout
    receipt = json.loads(result.stdout)
    assert receipt["replay_result"] == "verified" and receipt["readiness"] == "hold"
    assert receipt["quarantined_intents"] == 8 and receipt["deleted_rows"] == 1
    assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 8
    assert world["owner"]("SELECT count(*) FROM product_activation_milestones") == source_before
    again = launch(world)
    assert again.returncode == 0, again.stderr + again.stdout
    repeated = json.loads(again.stdout)
    assert repeated["quarantined_intents"] == repeated["deleted_rows"] == 0
    assert not list(world["staging"].iterdir())


def test_incomplete_cases_and_wrong_targets_refuse_before_any_mutation(replay_world):
    world = replay_world
    before = world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])
    original = world["operator"].read_text()
    for broken in (original.replace("version=2", "version=1"), "legal_basis_state_version=2\n",
                   original.replace("stage=accepted", "stage=failed")):
        closed(world["operator"], broken)
        result = launch(world)
        assert result.returncode != 0 and json.loads(result.stdout)["readiness"] == "hold"
        assert world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"]) == before
    closed(world["operator"], original)
    for key, value in (("target_database", "twobrain_rec"), ("target_oid", 1),
                       ("source_database", "twobrain_rec")):
        closed(world["ownership"], json.dumps({**world["binding"], key: value}))
        assert launch(world).returncode != 0
    closed(world["ownership"], json.dumps(world["binding"]))
    world["operator"].chmod(0o644)
    assert launch(world).returncode != 0
    world["operator"].chmod(0o600)
    assert world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"]) == before


def test_category_case_erases_ledger_and_preserves_other_relations(replay_world):
    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
        apply_basis_loss_disposition,
        plan_processing_stop,
    )

    world = replay_world
    now = datetime.now(UTC)
    category = ("disposition_case case_ref=case_category decision_ref=decision_category "
                "scope=activation_milestone_decisions selector_ref=all owner_role=operator "
                f"reason=purpose_ended decided_at={now.isoformat()} "
                f"due_at={(now+timedelta(days=1)).isoformat()} stage=accepted")
    closed(world["operator"], world["operator"].read_text() + category + "\n")

    async def erase_source():
        engine = create_async_engine(world["url"], poolclass=NullPool)
        try:
            async with async_sessionmaker(engine)() as db:
                plan = plan_processing_stop(
                    level_key="attribution_profiles", basis_lost_at=now, reason="purpose_ended",
                    affected_categories=("activation_milestone_decisions",),
                    deletion_deadlines={"activation_milestone_decisions": now+timedelta(days=1)},
                )
                assert (await apply_basis_loss_disposition(db, plan))[0].rows_affected == 8
        finally:
            await engine.dispose()

    asyncio.run(erase_source())
    outside = world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) FROM user_identities t",
                             world["target"])
    result = launch(world)
    assert result.returncode == 0, result.stderr + result.stdout
    receipt = json.loads(result.stdout)
    assert receipt["cases"] == 2 and receipt["deleted_rows"] == 9
    assert world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"]).strip() == "0"
    assert world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) FROM user_identities t",
                           world["target"]) == outside
    assert launch(world).returncode == 0


def test_unresolved_history_and_restrictive_policy_do_not_hide_cases(replay_world):
    world = replay_world
    scheduled = world["owner"]("SELECT id FROM account_closure_requests WHERE state='scheduled' LIMIT 1").strip()
    for state in ("finalizing", "blocked", "unknown"):
        world["owner"](f"UPDATE account_closure_requests SET state='{state}' WHERE id='{scheduled}'")
        assert launch(world).returncode != 0
    world["owner"](f"UPDATE account_closure_requests SET state='scheduled' WHERE id='{scheduled}'")
    original = world["operator"].read_text()
    for state in ("scheduled", "canceled"):
        selector = world["owner"](f"SELECT id FROM account_closure_requests WHERE state='{state}' LIMIT 1").strip()
        extra = world["case"].replace(str(world["closure"]), selector)
        extra = extra.replace("case_synthetic", "case_other").replace("decision_synthetic", "decision_other")
        closed(world["operator"], original + extra + "\n")
        assert launch(world).returncode != 0
    closed(world["operator"], original)
    world["owner"]("CREATE POLICY synthetic_hide ON account_closure_requests AS RESTRICTIVE USING(false)")
    assert launch(world).returncode != 0
    world["owner"]("DROP POLICY synthetic_hide ON account_closure_requests")
    assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 9


def test_transaction_rollback_and_unknown_after_commit(replay_world, monkeypatch):
    from twobrain_rec_server.product_analytics import restore_replay as replay

    world = replay_world
    kwargs = {"host": world["url"].host, "port": world["url"].port,
              "password_file": world["password"], "operator_file": world["operator"],
              "ownership_file": world["ownership"], "staging": world["staging"]}
    original = replay.verify_ledger
    before = world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) "
                              "FROM product_activation_milestones t", world["target"])
    for fail_at in (1, 2):
        calls = 0

        async def fail_readback(db, expected, fail_at=fail_at):
            nonlocal calls
            calls += 1
            if calls == fail_at:
                raise replay.ReplayHold("replay_ledger_mismatch")
            await original(db, expected)

        monkeypatch.setattr(replay, "verify_ledger", fail_readback)
        with pytest.raises(replay.ReplayHold) as error:
            asyncio.run(replay.reconcile(**kwargs))
        if fail_at == 1:
            assert error.value.args == ("replay_ledger_mismatch",)
            assert world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY id)::text) "
                                   "FROM product_activation_milestones t", world["target"]) == before
        else:
            assert error.value.args == ("replay_result_unknown",)
            assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 8
    monkeypatch.setattr(replay, "verify_ledger", original)
    receipt = asyncio.run(replay.reconcile(**kwargs))
    assert receipt["quarantined_intents"] == receipt["deleted_rows"] == 0


def replay_kwargs(world):
    return {"host": world["url"].host, "port": world["url"].port,
            "password_file": world["password"], "operator_file": world["operator"],
            "ownership_file": world["ownership"], "staging": world["staging"]}


def test_lost_commit_response_is_unknown_even_when_database_applied(replay_world, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncSession

    from twobrain_rec_server.product_analytics import restore_replay as replay

    world = replay_world
    original = AsyncSession.commit

    async def commit_then_lose_response(db):
        await original(db)
        raise ConnectionError("synthetic_lost_ack")

    with monkeypatch.context() as patch:
        patch.setattr(AsyncSession, "commit", commit_then_lose_response)
        with pytest.raises(replay.ReplayHold, match="replay_result_unknown"):
            asyncio.run(replay.reconcile(**replay_kwargs(world)))
    assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 8
    receipt = asyncio.run(replay.reconcile(**replay_kwargs(world)))
    assert receipt["quarantined_intents"] == receipt["deleted_rows"] == 0


def test_deadline_is_evaluated_at_verification_time(replay_world, monkeypatch):
    from twobrain_rec_server.product_analytics import restore_replay as replay

    started = datetime.now(UTC)

    class AdvancingClock(datetime):
        calls = 0

        @classmethod
        def now(cls, tz=None):
            cls.calls += 1
            return started + (timedelta(0) if cls.calls == 1 else timedelta(days=2))

    monkeypatch.setattr(replay, "datetime", AdvancingClock)
    receipt = asyncio.run(replay.reconcile(**replay_kwargs(replay_world)))
    assert receipt["overdue_cases"] == 1
    assert receipt["readiness"] == "hold"


def test_changed_operator_rolls_back_and_cleanup_failure_never_passes(replay_world, monkeypatch):
    from twobrain_rec_server.product_analytics import restore_replay as replay

    world = replay_world
    original_verify = replay.verify_ledger
    operator = world["operator"].read_text()

    async def mutate_operator(db, expected):
        await original_verify(db, expected)
        closed(world["operator"], operator + "# changed\n")

    with monkeypatch.context() as patch:
        patch.setattr(replay, "verify_ledger", mutate_operator)
        with pytest.raises(replay.ReplayHold, match="replay_inputs_changed"):
            asyncio.run(replay.reconcile(**replay_kwargs(world)))
    closed(world["operator"], operator)
    assert int(world["owner"]("SELECT count(*) FROM product_activation_milestones", world["target"])) == 9
    original_exists = Path.exists

    def uncertain_cleanup(path):
        return True if path.parent == world["staging"] and path.name.startswith("replay-") else original_exists(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "exists", uncertain_cleanup)
        with pytest.raises(replay.ReplayHold, match="replay_result_unknown"):
            asyncio.run(replay.reconcile(**replay_kwargs(world)))
    assert not list(world["staging"].iterdir())


def test_negative_copy_epoch_cannot_replay_grant_and_all_choices_are_quarantined(replay_world, monkeypatch):
    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.public.consent import ChoiceRejected, control_choice

    world = replay_world
    closed(world["root"] / "basis", "legal_basis_state_version=1\n")
    monkeypatch.setenv("GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_FILE", str(world["root"] / "basis"))
    settings = Settings(public_analytics_enabled=True, public_analytics_validation_mode="render_only",
                        public_analytics_yandex_metrica_id="12345678")
    consent_id, copied_epoch = world["choices"][0]
    payload = {"action": "grant", "consent_id": consent_id, "expected_epoch": copied_epoch,
               "categories": ["necessary", "analytics"], "copy_version": "2026-10-22.1"}

    async def source_transitions():
        engine = create_async_engine(world["url"], poolclass=NullPool)
        try:
            sessions = async_sessionmaker(engine)
            assert (await control_choice(sessions, settings, payload))["state"] == "granted"
            assert (await control_choice(sessions, settings, {"action": "revoke", "consent_id": consent_id}))["state"] == "revoked"
        finally:
            await engine.dispose()
    asyncio.run(source_transitions())
    before = world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY consent_digest)::text) FROM public_analytics_choices t")
    result = launch(world)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["quarantined_choices"] == 2
    assert world["owner"]("SELECT md5(jsonb_agg(to_jsonb(t) ORDER BY consent_digest)::text) FROM public_analytics_choices t") == before
    assert world["owner"]("SELECT count(*) FROM public_analytics_choices WHERE categories=jsonb_build_array('necessary') AND copy_version IS NULL", world["target"]).strip() == "2"

    async def replay_old_grant():
        engine = create_async_engine(world["url"].set(database=world["target"]), poolclass=NullPool)
        try:
            with pytest.raises(ChoiceRejected) as rejected:
                await control_choice(async_sessionmaker(engine), settings, payload)
            assert rejected.value.status == 409
        finally:
            await engine.dispose()
    asyncio.run(replay_old_grant())
    assert all(reference not in result.stdout for pair in world["choices"] for reference in pair)


def test_public_control_requires_named_case_and_closed_grants_then_replays_deletion(replay_world):
    from twobrain_rec_server.db.tenant_context import apply_tenant_context
    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
        BASIS_WITHDRAWAL_STATE_FILE_ENV,
        LegalBasisLifecycleError,
        apply_basis_loss_disposition,
        plan_processing_stop,
    )
    from twobrain_rec_server.product_analytics.restore_replay import CHOICE_CONTEXT

    world = replay_world
    now = datetime.now(UTC)
    due = now + timedelta(days=1)
    category = ("disposition_case case_ref=case_control decision_ref=decision_control "
                "scope=public_consent_control selector_ref=all owner_role=operator "
                f"reason=purpose_ended decided_at={now.isoformat()} due_at={due.isoformat()} stage=accepted")
    original = world["operator"].read_text()
    closed(world["operator"], original + category + "\n")
    assert launch(world).returncode != 0, "a case without closed grants must not erase control"
    withdrawal = ("basis_withdrawal level=provider_analytics state=withdrawn "
                  f"withdrawn_at={now.date().isoformat()} reason=purpose_ended\n")
    plan = plan_processing_stop(level_key="provider_analytics", basis_lost_at=now,
                               reason="purpose_ended", affected_categories=("public_consent_control",),
                               deletion_deadlines={"public_consent_control": due})

    async def delete_source():
        url = world["url"].set(username="twobrain_rec_maintenance", password=world["password"].read_text())
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine)() as db:
                await apply_tenant_context(db, CHOICE_CONTEXT)
                return await apply_basis_loss_disposition(
                    db, plan, basis_environ={BASIS_WITHDRAWAL_STATE_FILE_ENV: str(world["operator"])})
        finally:
            await engine.dispose()

    closed(world["operator"], original + withdrawal)
    with pytest.raises(LegalBasisLifecycleError, match="public_control_deletion_case_missing"):
        asyncio.run(delete_source())
    closed(world["operator"], original + withdrawal + category + "\n")
    assert asyncio.run(delete_source())[0].rows_affected == 2
    assert world["owner"]("SELECT count(*) FROM public_analytics_choices").strip() == "0"
    result = launch(world)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["cases"] == 2 and receipt["deleted_rows"] == 3
    assert world["owner"]("SELECT count(*) FROM public_analytics_choices", world["target"]).strip() == "0"
    assert launch(world).returncode == 0
