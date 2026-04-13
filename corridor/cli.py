import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from corridor.schema import format_errors, validate_json_file
from corridor.main import (
    ARTIFACTS_DIR,
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


def batch_run(folder: str, mode: str) -> None:
    ensure_dirs()

    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    files = sorted(folder_path.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files found in: {folder_path}")

    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0

    for path in files:
        try:
            if mode == "events":
                result = run_event_json(str(path))
                outcome = "PASS" if not result["violation_classes"] else "FAIL"
            elif mode == "receipts":
                result = run_receipt_json(str(path))
                outcome = result["outcome"]
            else:
                raise ValueError(f"Unsupported batch mode: {mode}")

            if outcome == "PASS":
                passed += 1
            else:
                failed += 1

            results.append({
                "file": str(path),
                "outcome": outcome,
                **result,
            })

        except Exception as exc:
            failed += 1
            results.append({
                "file": str(path),
                "outcome": "ERROR",
                "error": str(exc),
            })
            print(f"ERROR in {path}: {exc}")

    summary = {
        "timestamp_utc": utc_now(),
        "mode": mode,
        "folder": str(folder_path),
        "file_count": len(files),
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    summary_path = ARTIFACTS_DIR / f"batch_{mode}_summary.json"
    write_json(summary_path, summary)

    print("BATCH complete.")
    print(f"mode = {mode}")
    print(f"files = {len(files)}")
    print(f"passed = {passed}")
    print(f"failed = {failed}")
    print(f"summary = {summary_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corridor-cli",
        description="Red Sea corridor admissibility CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="Run the built-in demo")
    sub.add_parser("verify", help="Run local verifier")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vessel-id", required=True)
    common.add_argument("--imo", required=True)
    common.add_argument("--classification", required=True, choices=["HUM", "CIV", "MIL"])
    common.add_argument("--flag", required=True)
    common.add_argument("--entry-point", required=True)
    common.add_argument("--exit-point", required=True)
    common.add_argument("--eta-start", default=utc_now())
    common.add_argument("--eta-end", default=utc_now())
    common.add_argument("--declared-path", required=True)
    common.add_argument("--mission-expected", default="ESCORT", choices=["ESCORT", "DECONFLICT"])
    common.add_argument("--mission-actual", default="ESCORT", choices=["ESCORT", "DECONFLICT", "EXPANDED"])
    common.add_argument("--proof-sources", default="AIS,RADAR,EO")
    common.add_argument("--refusal-available", action="store_true")
    common.add_argument("--execution-origin", default="present_state", choices=["present_state", "carried_state"])
    common.add_argument("--civilian-class-protected", action="store_true")
    common.add_argument("--classification-valid", action="store_true")
    common.add_argument("--route-window-valid", action="store_true")

    sub.add_parser("entry", parents=[common], help="Record ENTRY event")
    sub.add_parser("transit", parents=[common], help="Record TRANSIT event")
    sub.add_parser("exit", parents=[common], help="Record EXIT event")

    receipt = sub.add_parser("receipt", help="Create immutable receipt")
    receipt.add_argument("--vessel-id", required=True)
    receipt.add_argument("--classification", required=True, choices=["HUM", "CIV", "MIL"])
    receipt.add_argument("--event-type", required=True, choices=["SAFE_PASSAGE", "INCIDENT", "HALT"])
    receipt.add_argument("--location", required=True)
    receipt.add_argument("--description", required=True)
    receipt.add_argument("--mission-expected", default="ESCORT", choices=["ESCORT", "DECONFLICT"])
    receipt.add_argument("--mission-actual", default="ESCORT", choices=["ESCORT", "DECONFLICT", "EXPANDED"])
    receipt.add_argument("--proof-sources", default="AIS,RADAR,EO")
    receipt.add_argument("--refusal-available", action="store_true")
    receipt.add_argument("--execution-origin", default="present_state", choices=["present_state", "carried_state"])
    receipt.add_argument("--civilian-class-protected", action="store_true")
    receipt.add_argument("--classification-valid", action="store_true")
    receipt.add_argument("--route-window-valid", action="store_true")

    event_json = sub.add_parser("event-json", help="Record event from JSON file")
    event_json.add_argument("--file", required=True)

    receipt_json = sub.add_parser("receipt-json", help="Create receipt from JSON file")
    receipt_json.add_argument("--file", required=True)

    batch_events = sub.add_parser("batch-events", help="Run all event JSON files in a folder")
    batch_events.add_argument("--folder", required=True)

    batch_receipts = sub.add_parser("batch-receipts", help="Run all receipt JSON files in a folder")
    batch_receipts.add_argument("--folder", required=True)

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

    if args.command in {"entry", "transit", "exit"}:
        add_event(
            event_type=args.command.upper(),
            vessel_id=args.vessel_id,
            imo=args.imo,
            classification=args.classification,
            flag=args.flag,
            entry_point=args.entry_point,
            exit_point=args.exit_point,
            eta_start=args.eta_start,
            eta_end=args.eta_end,
            declared_path=args.declared_path,
            mission_expected=args.mission_expected,
            mission_actual=args.mission_actual,
            proof_sources=normalize_sources(args.proof_sources),
            refusal_available=args.refusal_available,
            execution_origin=args.execution_origin,
            civilian_class_protected=args.civilian_class_protected,
            classification_valid=args.classification_valid,
            route_window_valid=args.route_window_valid,
        )
        return

    if args.command == "receipt":
        add_receipt(
            vessel_id=args.vessel_id,
            classification=args.classification,
            event_type=args.event_type,
            location=args.location,
            description=args.description,
            mission_expected=args.mission_expected,
            mission_actual=args.mission_actual,
            proof_sources=normalize_sources(args.proof_sources),
            refusal_available=args.refusal_available,
            execution_origin=args.execution_origin,
            civilian_class_protected=args.civilian_class_protected,
            classification_valid=args.classification_valid,
            route_window_valid=args.route_window_valid,
        )
        return

    if args.command == "event-json":
        run_event_json(args.file)
        return

    if args.command == "receipt-json":
        run_receipt_json(args.file)
        return

    if args.command == "batch-events":
        batch_run(args.folder, mode="events")
        return

    if args.command == "batch-receipts":
        batch_run(args.folder, mode="receipts")
        return


if __name__ == "__main__":
    main()