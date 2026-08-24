from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


FEATURE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = FEATURE_ROOT / "contracts/processing-analytics.schema.json"
CONTRACT_PATH = FEATURE_ROOT / "contracts/processing-analytics.md"
FIXTURES_PATH = FEATURE_ROOT / "validation/processing-analytics-fixtures.json"

FORBIDDEN_KEYS = {
    "email",
    "phone",
    "meeting_id",
    "media_revision_id",
    "processing_attempt_id",
    "provider_job_id",
    "idempotency_key",
    "request_id",
    "user_id",
    "workspace_id",
    "meeting_title",
    "filename",
    "file_path",
    "local_path",
    "transcript_text",
    "summary_text",
    "raw_payload",
    "provider_detail",
    "signed_url",
    "token",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_variants(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants: dict[str, dict[str, Any]] = {}
    for variant in schema["oneOf"]:
        event_name = variant["properties"]["event_name"]["const"]
        dimensions_ref = variant["properties"]["dimensions"]["$ref"]
        dimensions_name = dimensions_ref.rsplit("/", 1)[-1]
        variants[event_name] = {
            "dimensions": schema["$defs"][dimensions_name],
            "surface": variant["properties"]["surface"],
        }
    return variants


def _assert_no_forbidden_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_KEYS:
                raise AssertionError(f"forbidden metadata field: {key}")
            _assert_no_forbidden_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_forbidden_keys(nested)


class ProcessingAnalyticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = _load_json(SCHEMA_PATH)
        cls.fixtures = _load_json(FIXTURES_PATH)
        cls.contract = CONTRACT_PATH.read_text(encoding="utf-8")
        cls.variants = _schema_variants(cls.schema)

    def test_schema_is_strict_and_has_no_content_or_identity_fields(self) -> None:
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(self.schema["additionalProperties"])
        self.assertTrue(
            all(
                definition.get("additionalProperties") is False
                for name, definition in self.schema["$defs"].items()
                if name.endswith("Dimensions")
            )
        )
        _assert_no_forbidden_keys(self.schema)

    def test_every_fixture_matches_the_event_specific_allowlist(self) -> None:
        root_keys = set(self.schema["properties"])
        for record in self.fixtures:
            self.assertEqual(set(record), root_keys)
            self.assertEqual(record["schema_version"], 1)
            self.assertIn(record["event_name"], self.variants)
            self.assertIn(record["window"], {"hour", "day"})
            self.assertIn(record["surface"], self.schema["properties"]["surface"]["enum"])
            self.assertIsInstance(record["count"], int)
            self.assertGreater(record["count"], 0)
            self.assertIsInstance(record["dimensions"], dict)
            _assert_no_forbidden_keys(record)

            variant = self.variants[record["event_name"]]
            dimension_schema = variant["dimensions"]
            dimensions = record["dimensions"]
            self.assertEqual(set(dimensions) - set(dimension_schema["properties"]), set())
            for required in dimension_schema["required"]:
                self.assertIn(required, dimensions)
            for key, value in dimensions.items():
                field_schema = dimension_schema["properties"][key]
                if "enum" in field_schema:
                    self.assertIn(value, field_schema["enum"])
                elif field_schema.get("type") == "boolean":
                    self.assertIsInstance(value, bool)
            surface_schema = variant["surface"]
            if "const" in surface_schema:
                self.assertEqual(record["surface"], surface_schema["const"])
            else:
                self.assertIn(record["surface"], surface_schema["enum"])
            if record["event_name"] == "processing_surface_parity_observed":
                if dimensions["parity_result"] == "mismatch":
                    self.assertIn("mismatch_reason", dimensions)
                else:
                    self.assertNotIn("mismatch_reason", dimensions)

    def test_schema_variants_cover_the_documented_events(self) -> None:
        event_names = tuple(self.variants)
        for event_name in event_names:
            self.assertIn(f"`{event_name}`", self.contract)
        self.assertEqual(len(event_names), 10)

    def test_kpi_contract_covers_all_requested_measurements(self) -> None:
        required_kpis = (
            "first_usable_transcript_rate",
            "time_to_first_usable_transcript",
            "retry_recovery_rate",
            "manual_check_execution_success_rate",
            "manual_check_value_recovery_rate",
            "terminal_actionability_rate",
            "support_handoff_completion_rate",
            "surface_parity_pass_rate",
        )
        for kpi in required_kpis:
            self.assertIn(f"`{kpi}`", self.contract)
        for marker in (
            "SC-004",
            "SC-006",
            "SC-007",
            "server_aggregate_only",
            "contract_test",
            "deletion fence",
        ):
            self.assertIn(marker, self.contract)

    def test_surface_parity_fixtures_cover_all_required_surfaces(self) -> None:
        parity_surfaces = {
            record["surface"]
            for record in self.fixtures
            if record["event_name"] == "processing_surface_parity_observed"
        }
        self.assertEqual(
            parity_surfaces,
            {"web_list", "web_detail", "embedded_desktop_detail"},
        )
        parity_records = [
            record
            for record in self.fixtures
            if record["event_name"] == "processing_surface_parity_observed"
        ]
        self.assertTrue(all(record["dimensions"]["parity_result"] == "match" for record in parity_records))

    def test_forbidden_metadata_is_rejected_by_the_spec_guard(self) -> None:
        unsafe = dict(self.fixtures[0])
        unsafe["dimensions"] = dict(unsafe["dimensions"])
        unsafe["dimensions"]["meeting_id"] = "must-not-be-present"
        with self.assertRaises(AssertionError):
            _assert_no_forbidden_keys(unsafe)

    def test_unknown_dimension_is_outside_the_event_specific_allowlist(self) -> None:
        record = self.fixtures[0]
        dimension_schema = self.variants[record["event_name"]]["dimensions"]
        unknown_fields = set(record["dimensions"]) - set(dimension_schema["properties"])
        self.assertEqual(unknown_fields, set())
        self.assertNotIn("diagnostic_detail", dimension_schema["properties"])


if __name__ == "__main__":
    unittest.main()
