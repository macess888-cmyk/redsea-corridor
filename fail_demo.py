from corridor.main import (
    ensure_dirs,
    build_bind_trace,
    record_event,
    build_receipt,
)

def main() -> None:
    ensure_dirs()

    bind_trace = build_bind_trace(
        vessel_id="RS-CIV-FAIL-001",
        classification="CIV",
        mission_type_expected="ESCORT",
        mission_type_actual="EXPANDED",
        route_window_valid=True,
        classification_valid=True,
        proof_sources=["AIS", "RADAR"],
        refusal_available=False,
        execution_origin="carried_state",
        civilian_class_protected=True,
    )

    record_event(
        event_type="ENTRY",
        vessel_id="RS-CIV-FAIL-001",
        imo="IMO7654321",
        classification="CIV",
        flag="PA",
        entry_point="BAB_EL_MANDEB_SOUTH",
        exit_point="GULF_OF_ADEN_EAST",
        eta_start="2026-04-12T00:00:00+00:00",
        eta_end="2026-04-12T06:00:00+00:00",
        declared_path="LINESTRING(43.2 12.5, 44.1 13.0)",
        sources=["AIS", "RADAR"],
        bind_trace=bind_trace,
    )

    receipt = build_receipt(
        vessel_id="RS-CIV-FAIL-001",
        classification="CIV",
        event_type="HALT",
        location="12.9000,43.7000",
        description="Execution halted due to bind condition breach.",
        bind_trace=bind_trace,
        sources=["AIS", "RADAR"],
    )

    print("FAIL demo complete.")
    print(f"violation_class = {bind_trace['violation_class']}")
    print(f"receipt_id = {receipt['receipt_id']}")

if __name__ == "__main__":
    main()