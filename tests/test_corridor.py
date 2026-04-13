import json
import shutil
import tempfile
import unittest
from pathlib import Path

from corridor.main import build_bind_trace, build_receipt, record_event
from corridor.schema import validate_event_data, validate_receipt_data
import corridor.main as main_mod


class CorridorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="redsea_corridor_test_"))
        self.artifacts_dir = self.temp_dir / "artifacts"
        self.receipts_dir = self.temp_dir / "receipts"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)

        self.original_artifacts = main_mod.ARTIFACTS_DIR
        self.original_receipts = main_mod.RECEIPTS_DIR
        self.original_ledger = main_mod.LEDGER_PATH
        self.original_index = main_mod.RECEIPT_INDEX_PATH

        main_mod.ARTIFACTS_DIR = self.artifacts_dir
        main_mod.RECEIPTS_DIR = self.receipts_dir
        main_mod.LEDGER_PATH = self.artifacts_dir / "corridor_ledger.jsonl"
        main_mod.RECEIPT_INDEX_PATH = self.receipts_dir / "receipt_index.jsonl"

    def tearDown(self) -> None:
        main_mod.ARTIFACTS_DIR = self.original_artifacts
        main_mod.RECEIPTS_DIR = self.original_receipts
        main_mod.LEDGER_PATH = self.original_ledger
        main_mod.RECEIPT_INDEX_PATH = self.original_index
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_event_data_pass(self) -> None:
        data = {
            "event_type": "ENTRY",
            "vessel_id": "RS-HUM-T-001",
            "imo": "IMO1234567",
            "classification": "HUM",
            "flag": "UN",
            "entry_point": "BAB_EL_MANDEB_SOUTH",
            "exit_point": "GULF_OF_ADEN_EAST",
            "eta_start": "2026-04-12T00:00:00+00:00",
            "eta_end": "2026-04-12T06:00:00+00:00",
            "declared_path": "LINESTRING(43.2 12.5, 44.1 13.0)",
            "mission_expected": "ESCORT",
            "mission_actual": "ESCORT",
            "proof_sources": ["AIS", "RADAR", "EO"],
            "refusal_available": True,
            "execution_origin": "present_state",
            "civilian_class_protected": True,
            "classification_valid": True,
            "route_window_valid": True,
        }
        errors = validate_event_data(data)
        self.assertEqual(errors, [])

    def test_validate_event_data_fail(self) -> None:
        data = {
            "event_type": "LAUNCH",
            "vessel_id": 123,
            "imo": "IMO1234567",
            "classification": "XYZ",
            "flag": "UN",
            "entry_point": "BAB_EL_MANDEB_SOUTH",
            "declared_path": "LINESTRING(43.2 12.5, 44.1 13.0)",
            "mission_expected": "ATTACK",
            "mission_actual": "EXPANDED",
            "proof_sources": "AIS,RADAR",
            "refusal_available": "yes",
            "execution_origin": "future_state",
            "civilian_class_protected": "true",
            "classification_valid": 1,
            "route_window_valid": None,
        }
        errors = validate_event_data(data)
        self.assertTrue(any("missing required field: exit_point" in e for e in errors))
        self.assertTrue(any("field vessel_id must be str" in e for e in errors))
        self.assertTrue(any("classification must be one of" in e for e in errors))
        self.assertTrue(any("proof_sources must be list" in e for e in errors))

    def test_validate_receipt_data_fail(self) -> None:
        data = {
            "vessel_id": "RS-BAD-001",
            "classification": "BOGUS",
            "event_type": "BROKEN",
            "location": 12345,
            "description": False,
            "mission_expected": "ATTACK",
            "mission_actual": "UNKNOWN",
            "proof_sources": ["AIS", 99, "NOPE"],
            "refusal_available": "no",
            "execution_origin": "future_state",
            "civilian_class_protected": "false",
            "classification_valid": "false",
            "route_window_valid": "false",
        }
        errors = validate_receipt_data(data)
        self.assertTrue(any("classification must be one of" in e for e in errors))
        self.assertTrue(any("field location must be str" in e for e in errors))
        self.assertTrue(any("proof_sources[1] must be str" in e for e in errors))

    def test_bind_trace_multi_violation(self) -> None:
        bind_trace = build_bind_trace(
            vessel_id="RS-CIV-MULTI-TEST",
            classification="CIV",
            mission_type_expected="ESCORT",
            mission_type_actual="EXPANDED",
            route_window_valid=False,
            classification_valid=False,
            proof_sources=["AIS", "RADAR"],
            refusal_available=False,
            execution_origin="carried_state",
            civilian_class_protected=False,
        )
        self.assertEqual(bind_trace["violation_class"], "REFUSAL_UNAVAILABLE_AT_BIND")
        self.assertIn("CARRIED_STATE_EXECUTION", bind_trace["violation_classes"])
        self.assertIn("MISSION_SCOPE_EXPANSION", bind_trace["violation_classes"])
        self.assertIn("ROUTE_WINDOW_INVALID", bind_trace["violation_classes"])
        self.assertIn("CLASSIFICATION_INVALID", bind_trace["violation_classes"])
        self.assertIn("CIVILIAN_CLASS_NOT_PROTECTED", bind_trace["violation_classes"])

    def test_primary_violation_proof_fail(self) -> None:
        bind_trace = build_bind_trace(
            vessel_id="RS-ADV-PROOF-001",
            classification="CIV",
            mission_type_expected="ESCORT",
            mission_type_actual="ESCORT",
            route_window_valid=True,
            classification_valid=True,
            proof_sources=[],
            refusal_available=True,
            execution_origin="present_state",
            civilian_class_protected=True,
        )
        self.assertEqual(bind_trace["violation_class"], "MISSING_PROOF_SOURCES")
        self.assertEqual(bind_trace["violation_classes"], ["MISSING_PROOF_SOURCES"])

    def test_primary_violation_refusal_fail(self) -> None:
        bind_trace = build_bind_trace(
            vessel_id="RS-ADV-REFUSAL-001",
            classification="CIV",
            mission_type_expected="ESCORT",
            mission_type_actual="ESCORT",
            route_window_valid=True,
            classification_valid=True,
            proof_sources=["AIS", "RADAR", "EO"],
            refusal_available=False,
            execution_origin="present_state",
            civilian_class_protected=True,
        )
        self.assertEqual(bind_trace["violation_class"], "REFUSAL_UNAVAILABLE_AT_BIND")
        self.assertEqual(bind_trace["violation_classes"], ["REFUSAL_UNAVAILABLE_AT_BIND"])

    def test_primary_violation_scope_fail(self) -> None:
        bind_trace = build_bind_trace(
            vessel_id="RS-ADV-SCOPE-001",
            classification="CIV",
            mission_type_expected="ESCORT",
            mission_type_actual="EXPANDED",
            route_window_valid=True,
            classification_valid=True,
            proof_sources=["AIS", "RADAR", "EO"],
            refusal_available=True,
            execution_origin="present_state",
            civilian_class_protected=True,
        )
        self.assertEqual(bind_trace["violation_class"], "MISSION_SCOPE_EXPANSION")
        self.assertEqual(bind_trace["violation_classes"], ["MISSION_SCOPE_EXPANSION"])

    def test_record_event_status_active_and_failed(self) -> None:
        pass_trace = build_bind_trace(
            vessel_id="RS-HUM-PASS",
            classification="HUM",
            mission_type_expected="ESCORT",
            mission_type_actual="ESCORT",
            route_window_valid=True,
            classification_valid=True,
            proof_sources=["AIS", "RADAR", "EO"],
            refusal_available=True,
            execution_origin="present_state",
            civilian_class_protected=True,
        )
        pass_entry = record_event(
            event_type="ENTRY",
            vessel_id="RS-HUM-PASS",
            imo="IMO1111111",
            classification="HUM",
            flag="UN",
            entry_point="BAB_EL_MANDEB_SOUTH",
            exit_point="GULF_OF_ADEN_EAST",
            eta_start="2026-04-12T00:00:00+00:00",
            eta_end="2026-04-12T06:00:00+00:00",
            declared_path="LINESTRING(43.2 12.5, 44.1 13.0)",
            sources=["AIS", "RADAR", "EO"],
            bind_trace=pass_trace,
        )
        self.assertEqual(pass_entry["status"], "ACTIVE")

        fail_trace = build_bind_trace(
            vessel_id="RS-CIV-FAIL",
            classification="CIV",
            mission_type_expected="ESCORT",
            mission_type_actual="EXPANDED",
            route_window_valid=False,
            classification_valid=False,
            proof_sources=["AIS"],
            refusal_available=False,
            execution_origin="carried_state",
            civilian_class_protected=False,
        )
        fail_entry = record_event(
            event_type="ENTRY",
            vessel_id="RS-CIV-FAIL",
            imo="IMO2222222",
            classification="CIV",
            flag="PA",
            entry_point="BAB_EL_MANDEB_SOUTH",
            exit_point="GULF_OF_ADEN_EAST",
            eta_start="2026-04-12T00:00:00+00:00",
            eta_end="2026-04-12T06:00:00+00:00",
            declared_path="LINESTRING(43.2 12.5, 44.1 13.0)",
            sources=["AIS"],
            bind_trace=fail_trace,
        )
        self.assertEqual(fail_entry["status"], "FAILED")

    def test_receipt_chain_with_index(self) -> None:
        pass_trace = build_bind_trace(
            vessel_id="RS-HUM-R1",
            classification="HUM",
            mission_type_expected="ESCORT",
            mission_type_actual="ESCORT",
            route_window_valid=True,
            classification_valid=True,
            proof_sources=["AIS", "RADAR", "EO"],
            refusal_available=True,
            execution_origin="present_state",
            civilian_class_protected=True,
        )
        r1 = build_receipt(
            vessel_id="RS-HUM-R1",
            classification="HUM",
            event_type="SAFE_PASSAGE",
            location="13.0000,43.8000",
            description="First receipt",
            bind_trace=pass_trace,
            sources=["AIS", "RADAR", "EO"],
        )

        fail_trace = build_bind_trace(
            vessel_id="RS-CIV-R2",
            classification="CIV",
            mission_type_expected="ESCORT",
            mission_type_actual="EXPANDED",
            route_window_valid=False,
            classification_valid=False,
            proof_sources=["AIS", "RADAR"],
            refusal_available=False,
            execution_origin="carried_state",
            civilian_class_protected=False,
        )
        r2 = build_receipt(
            vessel_id="RS-CIV-R2",
            classification="CIV",
            event_type="HALT",
            location="12.9000,43.7000",
            description="Second receipt",
            bind_trace=fail_trace,
            sources=["AIS", "RADAR"],
        )

        index_path = self.receipts_dir / "receipt_index.jsonl"
        self.assertTrue(index_path.exists())

        rows = []
        with index_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))

        self.assertEqual(len(rows), 2)

        first_receipt = json.loads(Path(rows[0]["path"]).read_text(encoding="utf-8"))
        second_receipt = json.loads(Path(rows[1]["path"]).read_text(encoding="utf-8"))

        self.assertEqual(second_receipt["previous_receipt_hash"], first_receipt["current_receipt_hash"])
        self.assertEqual(r2["outcome"], "FAIL")


if __name__ == "__main__":
    unittest.main()