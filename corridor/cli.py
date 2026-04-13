import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from corridor.schema import format_errors, validate_json_file
from corridor.main import (
    ARTIFACTS_DIR,
    RECEIPTS_DIR,
    LEDGER_PATH,
    RECEIPT_INDEX_PATH,
    build_bind_trace,
    build_receipt,
    ensure_dirs,
    record_event,
    run_demo,
    write_json,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_sources(raw: str) -> List[str]:
    parts = [p.strip().upper() for p in raw.split(",") if p.strip()]
    return parts


def load_json(path: str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def reset_runtime() -> None:
    if ARTIFACTS_DIR.exists():
        shutil.rmtree(ARTIFACTS_DIR)
    if RECEIPTS_DIR.exists():
        shutil.rmtree(RECEIPTS_DIR)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Runtime reset complete.")
    print(f" - {ARTIFACTS_DIR}")
    print(f" - {RECEIPTS_DIR}")


def runtime_status() -> None:
    artifacts_exists = ARTIFACTS_DIR.exists()
    receipts_exists = RECEIPTS_DIR.exists()
    ledger_exists = LEDGER_PATH.exists()
    receipt_index_exists = RECEIPT_INDEX_PATH.exists()

    receipt_files = []
    if receipts_exists:
        receipt_files = [
            p for p in RECEIPTS_DIR.glob("*.json")
            if p.name != "receipt_index.jsonl"
        ]

    ledger_entries = 0
    if ledger_exists:
        with LEDGER_PATH.open("r", encoding="utf-8") as f:
            ledger_entries = sum(1 for line in f if line.strip())

    receipt_index_entries = 0
    if receipt_index_exists:
        with RECEIPT_INDEX_PATH.open("r", encoding="utf-8") as f:
            receipt_index_entries = sum(1 for line in f if line.strip())

    if ledger_exists and receipt_index_exists and ledger_entries > 0 and receipt_index_entries > 0:
        state = "READY"
    else:
        state = "HOLD"

    print("Runtime status:")
    print(f" - artifacts_dir: {'present' if artifacts_exists else 'missing'}")
    print(f" - receipts_dir: {'present' if receipts_exists else 'missing'}")
    print(f" - ledger: {'present' if ledger_exists else 'missing'}")
    print(f" - ledger_entries: {ledger_entries}")
    print(f" - receipt_index: {'present' if receipt_index_exists else 'missing'}")
    print(f" - receipt_index_entries: {receipt_index_entries}")
    print(f" - receipt_files: {len(receipt_files)}")
    print(f" - state: {state}")

    if state == "HOLD":
        print("Guidance:")
        print(" - run: python -m corridor.cli event-json --file examples\\event_pass.json")
        print(" - then: python -m corridor.cli receipt-json --file examples\\receipt_pass.json")
        print(" - or: run_all.bat")


def add_event(
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
    mission_expected: str,
    mission_actual: str,
    proof_sources: List[str],
    refusal_available: bool,
    execution_origin: str,
    civilian_class_protected: bool,
    classification_valid: bool,
    route_window_valid: bool,
) -> Dict[str, Any]:
    ensure_dirs()

    bind_trace = build_bind_trace(
        vessel_id=vessel_id,
        classification=classification,
        mission_type_expected=mission_expected,
        mission_type_actual=mission_actual,
        route_window_valid=route_window_valid,
        classification_valid=classification_valid,
        proof_sources=proof_sources,
        refusal_available=refusal_available,
        execution_origin=execution_origin,
        civilian_class_protected=civilian_class_protected,
    )

    bind_path = ARTIFACTS_DIR / f"bind_trace_{vessel_id}_{event_type.lower()}.json"
    write_json(bind_path, bind_trace)

    entry = record_event(
        event_type=event_type,
        vessel_id=vessel_id,
        imo=imo,
        classification=classification,
        flag=flag,
        entry_point=entry_point,
        exit_point=exit_point,
        eta_start=eta_start,
        eta_end=eta_end,
        declared_path=declared_path,
        sources=proof_sources,
        bind_trace=bind_trace,
    )

    print(f"{event_type} recorded.")
    print(f"ledger_id = {entry['ledger_id']}")
    print(f"status = {entry['status']}")
    print(f"bind_trace = {bind_path}")
    print(f"violation_class = {bind_trace['violation_class']}")
    print(f"violation_classes = {bind_trace['violation_classes']}")

    return {
        "ledger_id": entry["ledger_id"],
        "status": entry["status"],
        "bind_trace_path": str(bind_path),
        "violation_class": bind_trace["violation_class"],
        "violation_classes": bind_trace["violation_classes"],
    }


def add_receipt(
    vessel_id: str,
    classification: str,
    event_type: str,
    location: str,
    description: str,
    mission_expected: str,
    mission_actual: str,
    proof_sources: List[str],
    refusal_available: bool,
    execution_origin: str,
    civilian_class_protected: bool,
    classification_valid: bool,
    route_window_valid: bool,
) -> Dict[str, Any]:
    ensure_dirs()

    bind_trace = build_bind_trace(
        vessel_id=vessel_id,
        classification=classification,
        mission_type_expected=mission_expected,
        mission_type_actual=mission_actual,
        route_window_valid=route_window_valid,
        classification_valid=classification_valid,
        proof_sources=proof_sources,
        refusal_available=refusal_available,
        execution_origin=execution_origin,
        civilian_class_protected=civilian_class_protected,
    )

    bind_path = ARTIFACTS_DIR / f"bind_trace_{vessel_id}_receipt.json"
    write_json(bind_path, bind_trace)

    receipt = build_receipt(
        vessel_id=vessel_id,
        classification=classification,
        event_type=event_type,
        location=location,
        description=description,
        bind_trace=bind_trace,
        sources=proof_sources,
    )

    print("RECEIPT recorded.")
    print(f"receipt_id = {receipt['receipt_id']}")
    print(f"outcome = {receipt['outcome']}")
    print(f"bind_trace = {bind_path}")
    print(f"violation_class = {bind_trace['violation_class']}")
    print(f"violation_classes = {bind_trace['violation_classes']}")

    return {
        "receipt_id": receipt["receipt_id"],
        "outcome": receipt["outcome"],
        "bind_trace_path": str(bind_path),
        "violation_class": bind_trace["violation_class"],
        "violation_classes": bind_trace["violation_classes"],
    }


def run_event_json(path: str) -> Dict[str, Any]:
    errors = validate_json_file(path, mode="event")
    if errors:
        raise ValueError("Event JSON validation failed:\n" + format_errors(errors))

    data = load_json(path)
    return add_event(
        event_type=str(data["event_type"]).upper(),
        vessel_id=data["vessel_id"],
        imo=data["imo"],
        classification=data["classification"],
        flag=data["flag"],
        entry_point=data["entry_point"],
        exit_point=data["exit_point"],
        eta_start=data["eta_start"],
        eta_end=data["eta_end"],
        declared_path=data["declared_path"],
        mission_expected=data.get("mission_expected", "ESCORT"),
        mission_actual=data.get("mission_actual", "ESCORT"),
        proof_sources=data.get("proof_sources", ["AIS", "RADAR", "EO"]),
        refusal_available=data.get("refusal_available", False),
        execution_origin=data.get("execution_origin", "present_state"),
        civilian_class_protected=data.get("civilian_class_protected", False),
        classification_valid=data.get("classification_valid", False),
        route_window_valid=data.get("route_window_valid", False),
    )


def run_receipt_json(path: str) -> Dict[str, Any]:
    errors = validate_json_file(path, mode="receipt")
    if errors:
        raise ValueError("Receipt JSON validation failed:\n" + format_errors(errors))

    data = load_json(path)
    return add_receipt(
        vessel_id=data["vessel_id"],
        classification=data["classification"],
        event_type=data["event_type"],
        location=data["location"],
        description=data["description"],
        mission_expected=data.get("mission_expected", "ESCORT"),
        mission_actual=data.get("mission_actual", "ESCORT"),
        proof_sources=data.get("proof_sources", ["AIS", "RADAR", "EO"]),
        refusal_available=data.get("refusal_available", False),
        execution_origin=data.get("execution_origin", "present_state"),
        civilian_class_protected=data.get("civilian_class_protected", False),
        classification_valid=data.get("classification_valid", False),
        route_window_valid=data.get("route_window_valid", False),
    )


def run_all() -> None:
    reset_runtime()

    event_files = [
        "examples\\event_pass.json",
        "examples\\event_fail.json",
    ]
    receipt_files = [
        "examples\\receipt_pass.json",
        "examples\\receipt_fail.json",
    ]

    event_results = []
    receipt_results = []

    print("Running events...")
    for path in event_files:
        result = run_event_json(path)
        event_results.append({"file": path, **result})

    print("Running receipts...")
    for path in receipt_files:
        result = run_receipt_json(path)
        receipt_results.append({"file": path, **result})

    import verify_corridor
    verify_corridor.main()

    summary = {
        "timestamp_utc": utc_now(),
        "command": "run-all",
        "events": event_results,
        "receipts": receipt_results,
        "verify": "PASS",
    }
    summary_path = ARTIFACTS_DIR / "run_all_summary.json"
    write_json(summary_path, summary)

    print("RUN-ALL complete.")
    print(f"summary = {summary_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="corridor-cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo")
    sub.add_parser("verify")
    sub.add_parser("reset-runtime")
    sub.add_parser("run-all")
    sub.add_parser("status")

    event_json = sub.add_parser("event-json")
    event_json.add_argument("--file", required=True)

    receipt_json = sub.add_parser("receipt-json")
    receipt_json.add_argument("--file", required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "demo":
        run_demo()
        return

    if args.command == "verify":
        import verify_corridor
        verify_corridor.main()
        return

    if args.command == "reset-runtime":
        reset_runtime()
        return

    if args.command == "run-all":
        run_all()
        return

    if args.command == "status":
        runtime_status()
        return

    if args.command == "event-json":
        run_event_json(args.file)
        return

    if args.command == "receipt-json":
        run_receipt_json(args.file)
        return


if __name__ == "__main__":
    main()