import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from corridor.main import (
    ARTIFACTS_DIR,
    RECEIPTS_DIR,
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
) -> None:
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
) -> None:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corridor-cli",
        description="Red Sea corridor admissibility CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="Run the built-in demo")

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

    sub.add_parser("verify", help="Run local verifier")

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


if __name__ == "__main__":
    main()