import json
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ARTIFACTS_DIR = Path("artifacts")
RECEIPTS_DIR = Path("receipts")
LEDGER_PATH = ARTIFACTS_DIR / "corridor_ledger.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def chained_hash(previous_hash: str, record: Dict[str, Any]) -> str:
    body = canonical_json(record)
    return sha256_text(previous_hash + body)


def ensure_dirs() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)


def load_ledger() -> List[Dict[str, Any]]:
    if not LEDGER_PATH.exists():
        return []
    entries: List[Dict[str, Any]] = []
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def last_hash(entries: List[Dict[str, Any]]) -> str:
    if not entries:
        return "GENESIS"
    return entries[-1]["current_hash"]


def append_ledger_entry(entry: Dict[str, Any]) -> None:
    with LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def validate_classification(classification: str) -> bool:
    return classification in {"HUM", "CIV", "MIL"}


def build_bind_trace(
    vessel_id: str,
    classification: str,
    mission_type_expected: str,
    mission_type_actual: str,
    route_window_valid: bool,
    classification_valid: bool,
    proof_sources: List[str],
    refusal_available: bool,
    execution_origin: str,
    civilian_class_protected: bool,
) -> Dict[str, Any]:
    violation_class: Optional[str] = None

    if classification not in {"HUM", "CIV"}:
        violation_class = "UNPROTECTED_CLASS"
    if not proof_sources:
        violation_class = "MISSING_PROOF_SOURCES"
    if not refusal_available:
        violation_class = "REFUSAL_UNAVAILABLE_AT_BIND"
    if execution_origin != "present_state":
        violation_class = "CARRIED_STATE_EXECUTION"
    if mission_type_expected != mission_type_actual:
        violation_class = "MISSION_SCOPE_EXPANSION"
    if not route_window_valid:
        violation_class = "ROUTE_WINDOW_INVALID"
    if not classification_valid:
        violation_class = "CLASSIFICATION_INVALID"
    if not civilian_class_protected:
        violation_class = "CIVILIAN_CLASS_NOT_PROTECTED"

    return {
        "bind_trace_id": str(uuid.uuid4()),
        "binding_point": "t3_transition",
        "timestamp_utc": utc_now(),
        "vessel": {
            "vessel_id": vessel_id,
            "classification": classification,
        },
        "expected_at_bind": {
            "mission_type": mission_type_expected,
            "route_window_valid": route_window_valid,
            "classification_valid": classification_valid,
        },
        "actual_at_bind": {
            "mission_type": mission_type_actual,
            "route_window_valid": route_window_valid,
            "classification_valid": classification_valid,
        },
        "proof_checked_at_bind": {
            "status": bool(proof_sources),
            "sources": proof_sources,
        },
        "refusal_available_at_bind": refusal_available,
        "execution_origin": execution_origin,
        "civilian_class_protected": civilian_class_protected,
        "violation_class": violation_class,
    }


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def record_event(
    event_type: str,
    vessel_id: str,
    imo: str,
    classification: str,
    flag: str,
    entry_point: str,
    exit_point: str,
    eta_start: str,
    eta_end: str,
    declared_path: str,
    sources: List[str],
    bind_trace: Dict[str, Any],
) -> Dict[str, Any]:
    entries = load_ledger()
    prev = last_hash(entries)

    verification = {
        "ais_confirmed": "AIS" in sources,
        "radar_confirmed": "RADAR" in sources,
        "eo_confirmed": "EO" in sources,
        "sources": sources,
        "confidence_score": 1.0 if len(sources) == 3 else 0.66 if len(sources) == 2 else 0.33,
    }

    bind_trace_hash = sha256_text(canonical_json(bind_trace))

    entry_core = {
        "ledger_id": str(uuid.uuid4()),
        "timestamp_utc": utc_now(),
        "event_type": event_type,
        "vessel": {
            "vessel_id": vessel_id,
            "imo": imo,
            "classification": classification,
            "flag": flag,
        },
        "route": {
            "entry_point": entry_point,
            "exit_point": exit_point,
            "eta_window_start": eta_start,
            "eta_window_end": eta_end,
            "declared_path": declared_path,
        },
        "verification": verification,
        "bind_trace_ref": bind_trace_hash,
        "status": (
            "FAILED"
            if bind_trace["violation_class"] is not None
            else "COMPLETE" if event_type == "EXIT" else "ACTIVE"
        ),
    }

    entry_hash = chained_hash(prev, entry_core)
    entry = {
        **entry_core,
        "previous_hash": prev,
        "current_hash": entry_hash,
    }
    append_ledger_entry(entry)
    return entry


def build_receipt(
    vessel_id: str,
    classification: str,
    event_type: str,
    location: str,
    description: str,
    bind_trace: Dict[str, Any],
    sources: List[str],
) -> Dict[str, Any]:
    receipt_core = {
        "receipt_id": str(uuid.uuid4()),
        "timestamp_utc": utc_now(),
        "vessel": {
            "vessel_id": vessel_id,
            "classification": classification,
        },
        "event": {
            "type": event_type,
            "location": location,
            "description": description,
        },
        "bind_trace_hash": sha256_text(canonical_json(bind_trace)),
        "verification_summary": {
            "sources_used": sources,
            "confidence_score": 1.0 if len(sources) == 3 else 0.66 if len(sources) == 2 else 0.33,
            "independent_verification": bool(sources),
        },
        "outcome": "FAIL" if bind_trace["violation_class"] else "PASS",
        "violation_class": bind_trace["violation_class"],
    }

    receipt_path = RECEIPTS_DIR / f"{receipt_core['receipt_id']}.json"
    if receipt_path.exists():
        raise FileExistsError(f"Receipt path already exists: {receipt_path}")

    previous_hash = "GENESIS"
    existing = sorted(RECEIPTS_DIR.glob("*.json"))
    if existing:
        last_receipt = json.loads(existing[-1].read_text(encoding="utf-8"))
        previous_hash = last_receipt["current_receipt_hash"]

    current_hash = chained_hash(previous_hash, receipt_core)

    receipt = {
        **receipt_core,
        "previous_receipt_hash": previous_hash,
        "current_receipt_hash": current_hash,
    }
    write_json(receipt_path, receipt)
    return receipt


def run_demo() -> None:
    ensure_dirs()

    now = datetime.now(timezone.utc).replace(microsecond=0)
    eta_start = now.isoformat()
    eta_end = (now + timedelta(hours=6)).isoformat()

    vessel_id = "RS-HUM-001"
    imo = "IMO1234567"
    classification = "HUM"
    flag = "UN"
    entry_point = "BAB_EL_MANDEB_SOUTH"
    exit_point = "GULF_OF_ADEN_EAST"
    declared_path = "LINESTRING(43.2 12.5, 44.1 13.0)"

    bind_trace = build_bind_trace(
        vessel_id=vessel_id,
        classification=classification,
        mission_type_expected="ESCORT",
        mission_type_actual="ESCORT",
        route_window_valid=True,
        classification_valid=True,
        proof_sources=["AIS", "RADAR", "EO"],
        refusal_available=True,
        execution_origin="present_state",
        civilian_class_protected=True,
    )

    bind_path = ARTIFACTS_DIR / "bind_trace_demo.json"
    write_json(bind_path, bind_trace)

    entry_record = record_event(
        event_type="ENTRY",
        vessel_id=vessel_id,
        imo=imo,
        classification=classification,
        flag=flag,
        entry_point=entry_point,
        exit_point=exit_point,
        eta_start=eta_start,
        eta_end=eta_end,
        declared_path=declared_path,
        sources=["AIS", "RADAR", "EO"],
        bind_trace=bind_trace,
    )

    transit_record = record_event(
        event_type="TRANSIT",
        vessel_id=vessel_id,
        imo=imo,
        classification=classification,
        flag=flag,
        entry_point=entry_point,
        exit_point=exit_point,
        eta_start=eta_start,
        eta_end=eta_end,
        declared_path=declared_path,
        sources=["AIS", "RADAR", "EO"],
        bind_trace=bind_trace,
    )

    exit_record = record_event(
        event_type="EXIT",
        vessel_id=vessel_id,
        imo=imo,
        classification=classification,
        flag=flag,
        entry_point=entry_point,
        exit_point=exit_point,
        eta_start=eta_start,
        eta_end=eta_end,
        declared_path=declared_path,
        sources=["AIS", "RADAR", "EO"],
        bind_trace=bind_trace,
    )

    receipt = build_receipt(
        vessel_id=vessel_id,
        classification=classification,
        event_type="SAFE_PASSAGE",
        location="13.0000,43.8000",
        description="Humanitarian vessel completed protected passage.",
        bind_trace=bind_trace,
        sources=["AIS", "RADAR", "EO"],
    )

    summary = {
        "status": "PASS" if bind_trace["violation_class"] is None else "FAIL",
        "bind_trace": str(bind_path),
        "ledger_path": str(LEDGER_PATH),
        "entry_event": entry_record["ledger_id"],
        "transit_event": transit_record["ledger_id"],
        "exit_event": exit_record["ledger_id"],
        "receipt_id": receipt["receipt_id"],
        "violation_class": bind_trace["violation_class"],
    }
    write_json(ARTIFACTS_DIR / "run_summary.json", summary)
    print("Artifacts written:")
    print(f" - {bind_path}")
    print(f" - {LEDGER_PATH}")
    print(f" - {ARTIFACTS_DIR / 'run_summary.json'}")
    print(f" - {RECEIPTS_DIR}")


if __name__ == "__main__":
    run_demo()