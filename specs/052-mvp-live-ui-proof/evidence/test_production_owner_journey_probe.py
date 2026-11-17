"""Offline contract checks; every identifier and content value is artificial."""

from __future__ import annotations

import contextlib
import copy
import http.client
import importlib.util
import io
import json
import os
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT = Path(__file__).with_name("production-owner-journey-probe.py")
SPEC = importlib.util.spec_from_file_location("owner_probe", SCRIPT)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
MEETING = "11111111-aaaa-4111-8111-111111111111"
PRIVATE = "ARTIFICIAL_PRIVATE_SENTINEL"
CATEGORIES = (
    "summary",
    "key_points",
    "decisions",
    "action_items",
    "followups",
    "risks",
    "questions",
    "evidence",
)


def ready_payload():
    access = dict(
        state="owner",
        can_view=True,
        can_view_full_meeting=True,
        content_scope="full_meeting",
    )
    return {
        "meeting": {
            "meeting_id": MEETING,
            "status": "ready",
            "access": access.copy(),
            "title": PRIVATE,
        },
        "access": access,
        "transcript": {
            "available": True,
            "segments": [
                {
                    "start_seconds": 0,
                    "end_seconds": 2,
                    "seekable": True,
                    "seek_seconds": 0,
                    "text": PRIVATE,
                },
                {
                    "start_seconds": 2,
                    "end_seconds": 3,
                    "seekable": False,
                    "seek_seconds": None,
                },
            ],
        },
        "speakers": {
            "available": True,
            "speakers": [
                {
                    "label": PRIVATE,
                    "segments": [{"start_seconds": 0, "end_seconds": 2}],
                },
                {"segments": [{"start_seconds": 2, "end_seconds": 3}]},
            ],
        },
        "playback": dict(
            available=True,
            can_play=True,
            state="available",
            source_mode="stored_review_m4a",
            duration_seconds=5,
            url=PRIVATE,
        ),
        "notes_action_truth": {
            "source_basis": "stored_output",
            **{
                key: {
                    "state": "available",
                    "readiness_impact": "closes_gap",
                    "items": [{"text": PRIVATE}],
                }
                for key in CATEGORIES
            },
        },
    }


def response(payload, status=200):
    return dict(ok=True, http_status=status, payload=payload)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "PUBLIC_URL": "https://example.invalid",
                    "OWNER_JOURNEY_PROBE_TIMEOUT": "1",
                    "OWNER_SESSION_COOKIE": PRIVATE,
                    "OWNER_MEETING_ID": MEETING,
                },
                clear=True,
            )
        )
        self.enterContext(
            patch(
                "urllib.request.OpenerDirector.open",
                side_effect=AssertionError("network forbidden"),
            )
        )

    def owner(self, payload):
        with patch.object(probe, "_get_json", return_value=response(payload)):
            return probe._owner_review()

    def assert_classification(self, payload, status, reason):
        result = self.owner(payload)
        self.assertEqual((result["status"], result["reason"]), (status, reason))
        output = json.dumps(result)
        self.assertNotIn(PRIVATE, output)
        self.assertNotIn(MEETING, output)
        return result

    def test_complete_subset_and_counts(self):
        result = self.assert_classification(
            ready_payload(), "pass", "review_metadata_available"
        )
        for key, count in dict(
            transcript_segment_count=2,
            speaker_count=2,
            speaker_interval_count=2,
            seek_target_count=1,
        ).items():
            self.assertEqual(result[key], count)
        self.assertEqual(result["meeting_status"], "ready")
        self.assertEqual(result["outcome_item_counts"], dict.fromkeys(CATEGORIES, 1))

    def test_empty_and_wrong_top_level_never_pass(self):
        for payload in (
            {},
            None,
            [],
            True,
            1,
            PRIVATE,
            {"status": "ready"},
            {"meeting": {"status": "ready"}},
        ):
            with self.subTest(payload_type=type(payload).__name__):
                self.assert_classification(payload, "fail", "schema_mismatch")

    def test_candidate_identity(self):
        for value in (None, 1, {}, PRIVATE, "22222222-bbbb-4222-8222-222222222222"):
            data = ready_payload()
            data["meeting"]["meeting_id"] = value
            with self.subTest(value_type=type(value).__name__):
                self.assert_classification(
                    data,
                    "fail",
                    "candidate_mismatch"
                    if isinstance(value, str) and value != PRIVATE
                    else "schema_mismatch",
                )
        data = ready_payload()
        del data["meeting"]["meeting_id"]
        self.assert_classification(data, "fail", "schema_mismatch")
        data = ready_payload()
        data["meeting"]["meeting_id"] = MEETING.upper().replace("-", "")
        self.assert_classification(data, "pass", "review_metadata_available")

    def test_every_projected_meeting_state(self):
        for state in (
            "local_only",
            "uploading",
            "submitted",
            "processing",
            "partial",
            "blocked",
            "failed",
            "unavailable",
            "deleted_future",
        ):
            data = ready_payload()
            data["meeting"]["status"] = state
            with self.subTest(state=state):
                self.assert_classification(data, "blocked", "meeting_not_ready")

    def test_access_and_priority(self):
        for key, value in (
            ("state", "team"),
            ("state", "shared"),
            ("state", "denied"),
            ("state", "unavailable"),
            ("state", "deleted"),
            ("content_scope", "summary_only"),
            ("can_view", False),
            ("can_view_full_meeting", False),
        ):
            for location in ("access", "nested"):
                data = ready_payload()
                data["meeting"]["status"] = "processing"
                access = (
                    data["access"]
                    if location == "access"
                    else data["meeting"]["access"]
                )
                access[key] = value
                with self.subTest(key=key, value=value, location=location):
                    self.assert_classification(data, "blocked", "owner_access_unproven")
        for nested in (None, "absent"):
            data = ready_payload()
            if nested is None:
                data["meeting"]["access"] = None
            else:
                del data["meeting"]["access"]
            self.assert_classification(data, "pass", "review_metadata_available")

    def test_required_fields_and_strict_types(self):
        paths = [
            ("access",),
            ("meeting",),
            ("transcript",),
            ("speakers",),
            ("playback",),
            ("notes_action_truth",),
            ("access", "state"),
            ("access", "can_view"),
            ("access", "can_view_full_meeting"),
            ("access", "content_scope"),
            ("meeting", "status"),
            ("transcript", "available"),
            ("transcript", "segments"),
            ("speakers", "available"),
            ("speakers", "speakers"),
            ("playback", "available"),
            ("playback", "can_play"),
            ("playback", "state"),
            ("playback", "source_mode"),
            ("playback", "duration_seconds"),
            ("notes_action_truth", "source_basis"),
        ]
        for path in paths:
            for value in (None, PRIVATE, 1, [], "absent"):
                if value == [] and path in (
                    ("transcript", "segments"),
                    ("speakers", "speakers"),
                ):
                    continue
                if value == 1 and path == ("playback", "duration_seconds"):
                    continue
                data = ready_payload()
                node = data
                for key in path[:-1]:
                    node = node[key]
                if value == "absent":
                    del node[path[-1]]
                else:
                    node[path[-1]] = value
                with self.subTest(path=path, type=type(value).__name__):
                    self.assert_classification(data, "fail", "schema_mismatch")
        data = ready_payload()
        data["access"]["state"] = "denied"
        del data["transcript"]["segments"]
        self.assert_classification(data, "fail", "schema_mismatch")

    def test_intervals_and_seek_types(self):
        for location in ("transcript", "speaker"):
            for key in ("start_seconds", "end_seconds"):
                for value in (None, True, "0", -1, float("inf"), float("nan")):
                    data = ready_payload()
                    segment = (
                        data["transcript"]["segments"][0]
                        if location == "transcript"
                        else data["speakers"]["speakers"][0]["segments"][0]
                    )
                    segment[key] = value
                    with self.subTest(
                        location=location, key=key, value_type=type(value).__name__
                    ):
                        self.assert_classification(data, "fail", "schema_mismatch")
            data = ready_payload()
            segment = (
                data["transcript"]["segments"][0]
                if location == "transcript"
                else data["speakers"]["speakers"][0]["segments"][0]
            )
            segment.update(start_seconds=3, end_seconds=2)
            self.assert_classification(data, "fail", "schema_mismatch")
        for key, values in (
            ("seekable", (None, 1, "true")),
            ("seek_seconds", (True, -1, "0", float("inf"), float("nan"))),
        ):
            for value in values:
                data = ready_payload()
                data["transcript"]["segments"][0][key] = value
                self.assert_classification(data, "fail", "schema_mismatch")

    def test_required_arrays_contain_objects(self):
        for path in (
            ("transcript", "segments"),
            ("speakers", "speakers"),
            ("notes_action_truth", "summary", "items"),
        ):
            data = ready_payload()
            node = data
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = [PRIVATE]
            self.assert_classification(data, "fail", "schema_mismatch")
        for lane in ({}, {"segments": None}, {"segments": [PRIVATE]}):
            data = ready_payload()
            data["speakers"]["speakers"] = [lane]
            self.assert_classification(data, "fail", "schema_mismatch")

    def test_missing_availability_and_zero_counts_block(self):
        for section in ("transcript", "speakers", "playback"):
            data = ready_payload()
            data[section]["available"] = False
            self.assert_classification(data, "blocked", "review_metadata_incomplete")
        for section, key in (("transcript", "segments"), ("speakers", "speakers")):
            data = ready_payload()
            data[section][key] = []
            result = self.assert_classification(
                data, "blocked", "review_metadata_incomplete"
            )
            self.assertEqual(
                result[
                    "transcript_segment_count"
                    if section == "transcript"
                    else "speaker_count"
                ],
                0,
            )
        for segments in ([], [{"start_seconds": 0, "end_seconds": 0}]):
            data = ready_payload()
            for lane in data["speakers"]["speakers"]:
                lane["segments"] = copy.deepcopy(segments)
            self.assert_classification(data, "blocked", "review_metadata_incomplete")
        for seek in (None, 6):
            data = ready_payload()
            data["transcript"]["segments"][0]["seek_seconds"] = seek
            result = self.assert_classification(
                data, "blocked", "review_metadata_incomplete"
            )
            self.assertEqual(result["seek_target_count"], 0)

    def test_playback(self):
        for key, value in (
            ("can_play", False),
            ("state", "preparing"),
            ("state", "unavailable"),
            ("state", "deleting"),
            ("state", "deleted"),
            ("source_mode", "none"),
        ):
            data = ready_payload()
            data["playback"][key] = value
            self.assert_classification(data, "blocked", "review_metadata_incomplete")
        for duration in (0, -1, True, 1.5, float("inf")):
            data = ready_payload()
            data["playback"]["duration_seconds"] = duration
            self.assert_classification(data, "fail", "schema_mismatch")

    def test_outcome_matrix_for_every_category(self):
        for category in CATEGORIES:
            for state in (
                "available",
                "not_found",
                "not_inferable",
                "processing",
                "blocked",
                "unavailable",
                "deferred",
                "unsafe",
            ):
                for impact in ("closes_gap", "keeps_gap_open", "non_blocking"):
                    for populated in (False, True):
                        data = ready_payload()
                        item = data["notes_action_truth"][category]
                        item.update(
                            state=state,
                            readiness_impact=impact,
                            items=[{}] if populated else [],
                        )
                        positive = impact == "closes_gap" and (
                            (state == "available" and populated)
                            or (
                                state in ("not_found", "not_inferable")
                                and not populated
                            )
                        )
                        with self.subTest(
                            category=category,
                            state=state,
                            impact=impact,
                            populated=populated,
                        ):
                            self.assert_classification(
                                data,
                                "pass" if positive else "blocked",
                                "review_metadata_available"
                                if positive
                                else "review_metadata_incomplete",
                            )

    def test_protocol_exception_is_bounded(self):
        for category in CATEGORIES:
            data = ready_payload()
            data["notes_action_truth"]["protocol"] = {"private": PRIVATE}
            data["notes_action_truth"][category].update(
                state="unavailable",
                readiness_impact="non_blocking",
                items=[],
            )
            self.assert_classification(
                data,
                "pass" if category == "risks" else "blocked",
                "review_metadata_available"
                if category == "risks"
                else "review_metadata_incomplete",
            )
        for protocol in (None, PRIVATE, [], 1):
            data = ready_payload()
            data["notes_action_truth"]["protocol"] = protocol
            data["notes_action_truth"]["risks"].update(
                state="unavailable",
                readiness_impact="non_blocking",
                items=[],
            )
            self.assert_classification(
                data,
                "blocked" if protocol is None else "fail",
                "review_metadata_incomplete" if protocol is None else "schema_mismatch",
            )

    def test_protocol_optional_type_and_wrong_nesting(self):
        for protocol in (None, {}, {"private": PRIVATE}, PRIVATE, [], True, 1):
            data = ready_payload()
            data["notes_action_truth"]["protocol"] = protocol
            valid = protocol is None or isinstance(protocol, dict)
            self.assert_classification(
                data,
                "pass" if valid else "fail",
                "review_metadata_available" if valid else "schema_mismatch",
            )
        for protocol in ({}, {"private": PRIVATE}, PRIVATE):
            data = ready_payload()
            data["notes_action_truth"]["risks"]["protocol"] = protocol
            self.assert_classification(data, "pass", "review_metadata_available")
            data["notes_action_truth"]["risks"].update(
                state="unavailable", readiness_impact="non_blocking", items=[]
            )
            self.assert_classification(data, "blocked", "review_metadata_incomplete")
        data = ready_payload()
        data["notes_action_truth"]["risks"].update(
            state="unavailable", readiness_impact="non_blocking", items=[]
        )
        self.assert_classification(data, "blocked", "review_metadata_incomplete")
        data["notes_action_truth"]["protocol"] = {}
        self.assert_classification(data, "pass", "review_metadata_available")
        data["notes_action_truth"]["source_basis"] = "blocked"
        self.assert_classification(data, "blocked", "review_metadata_incomplete")

    def test_category_schema_and_source_basis(self):
        for category in CATEGORIES:
            for key in ("state", "readiness_impact", "items"):
                for value in (None, PRIVATE, True, "absent"):
                    data = ready_payload()
                    item = data["notes_action_truth"][category]
                    if value == "absent":
                        del item[key]
                    else:
                        item[key] = value
                    self.assert_classification(data, "fail", "schema_mismatch")
        for source in (
            "processing_status",
            "transcript_only",
            "policy_deferral",
            "not_supported",
            "blocked",
        ):
            data = ready_payload()
            data["notes_action_truth"]["source_basis"] = source
            self.assert_classification(data, "blocked", "review_metadata_incomplete")

    def test_configuration_and_absent_context(self):
        for key in ("OWNER_MEETING_ID", "OWNER_SESSION_COOKIE"):
            with (
                patch.dict(os.environ, {key: ""}),
                patch.object(probe, "_get_json") as request,
            ):
                result = probe._owner_review()
                self.assertEqual(
                    (result["status"], result["reason"]),
                    ("blocked", "owner_context_missing"),
                )
                request.assert_not_called()
        for key, values in (
            ("OWNER_MEETING_ID", (PRIVATE, "../invalid")),
            (
                "PUBLIC_URL",
                (
                    "http://example.invalid",
                    "https://user@example.invalid",
                    "https://example.invalid/path",
                    "https://example.invalid?x",
                    "https://example.invalid#x",
                    "https://example.invalid:bad",
                    "https://example.invalid///",
                    "https://example.invalid?",
                    "https://example.invalid#",
                ),
            ),
            ("OWNER_JOURNEY_PROBE_TIMEOUT", (PRIVATE, "0", "-1", "inf", "nan")),
        ):
            for value in values:
                with (
                    patch.dict(os.environ, {key: value}),
                    patch.object(probe, "_get_json") as request,
                ):
                    result = probe._owner_review()
                    self.assertEqual(
                        (result["status"], result["reason"]),
                        ("fail", "invalid_configuration"),
                    )
                    request.assert_not_called()

    def test_health_and_aggregate_exit_are_scoped(self):
        for health in ("ok", PRIVATE, None, True, {}, []):
            for owner_status in ("ready", "processing", PRIVATE):
                data = ready_payload()
                data["meeting"]["status"] = owner_status
                with (
                    patch.object(
                        probe,
                        "_get_json",
                        side_effect=[
                            response({"status": health}),
                            response({"status": "ready"}),
                            response(data),
                        ],
                    ),
                    contextlib.redirect_stdout(io.StringIO()) as output,
                ):
                    code = probe.main()
                result = json.loads(output.getvalue())
                expected = (
                    "fail"
                    if health != "ok" or owner_status == PRIVATE
                    else "pass"
                    if owner_status == "ready"
                    else "blocked"
                )
                self.assertEqual(result["overall_status"], expected)
                self.assertEqual(code, 0 if expected == "pass" else 1)
                self.assertEqual(result["proof_scope"], "owner_review_api_metadata")
                self.assertEqual(result["owner_journey_status"], "unproven")
                self.assertNotIn(PRIVATE, output.getvalue())
                self.assertNotIn(MEETING, output.getvalue())
                self.assertNotIn("example.invalid", output.getvalue())
        with (
            patch.dict(os.environ, {"OWNER_SESSION_COOKIE": ""}),
            patch.object(
                probe,
                "_get_json",
                side_effect=[response({"status": "ok"}), response({"status": "ready"})],
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(probe.main(), 1)

    def test_http_and_health_failures(self):
        for status in (301, 302, 401, 403, 404, 500):
            with patch.object(
                probe, "_get_json", return_value=response(ready_payload(), status)
            ):
                self.assertEqual(probe._owner_review()["reason"], "request_failed")
            with patch.object(
                probe, "_get_json", return_value=response({"status": "ok"}, status)
            ):
                self.assertFalse(probe._health()["live"]["ok"])
        with patch.object(
            probe,
            "_get_json",
            return_value={"ok": False, "http_status": 200, "payload": {"status": "ok"}},
        ):
            self.assertFalse(probe._health()["live"]["ok"])
        for value in (None, [], PRIVATE, {"status": PRIVATE}):
            with patch.object(probe, "_get_json", return_value=response(value)):
                health = probe._health()
                self.assertFalse(health["live"]["ok"])
                self.assertNotIn(PRIVATE, json.dumps(health))

    def test_import_does_not_parse_runtime_configuration_or_run_main(self):
        with (
            patch.dict(os.environ, {"OWNER_JOURNEY_PROBE_TIMEOUT": PRIVATE}),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            module = importlib.util.module_from_spec(SPEC)
            SPEC.loader.exec_module(module)
        self.assertEqual(output.getvalue(), "")

    def test_transport_errors_never_expose_exceptions(self):
        for error in (
            urllib.error.HTTPError("https://example.invalid", 403, PRIVATE, {}, None),
            urllib.error.URLError(PRIVATE),
            TimeoutError(PRIVATE),
            OSError(PRIVATE),
            ValueError(PRIVATE),
            http.client.BadStatusLine(PRIVATE),
            RecursionError(PRIVATE),
        ):
            with patch("urllib.request.build_opener") as factory:
                factory.return_value.open.side_effect = error
                result = probe._get_json("/api/v1/health/live")
                self.assertFalse(result["ok"])
                self.assertNotIn(PRIVATE, json.dumps(result))

    def test_transport_decode_errors_and_get_only(self):
        for raw in (b"", b"{", b"\xff"):
            with patch("urllib.request.build_opener") as factory:
                reply = MagicMock(status=200)
                reply.read.return_value = raw
                factory.return_value.open.return_value.__enter__.return_value = reply
                self.assertFalse(probe._get_json("/api/v1/health/live")["ok"])
        for raw in (b"null", b"[]", b"true"):
            with patch("urllib.request.build_opener") as factory:
                reply = MagicMock(status=200)
                reply.read.return_value = raw
                factory.return_value.open.return_value.__enter__.return_value = reply
                self.assertEqual(probe._owner_review()["reason"], "schema_mismatch")
                self.assertFalse(probe._health()["live"]["ok"])
        with patch("urllib.request.build_opener") as factory:
            reply = MagicMock(status=200)
            reply.read.return_value = b'{"status":"ok"}'
            factory.return_value.open.return_value.__enter__.return_value = reply
            self.assertTrue(probe._get_json("/api/v1/health/live")["ok"])
            request = factory.return_value.open.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            handlers = factory.call_args.args
            redirect = next(
                item
                for item in handlers
                if isinstance(item, probe.urllib.request.HTTPRedirectHandler)
            )
            self.assertIsNone(
                redirect.redirect_request(
                    request, None, 302, PRIVATE, {}, "https://elsewhere.invalid"
                )
            )


if __name__ == "__main__":
    unittest.main()
