from pathlib import Path
from typing import Any, Dict, List


EVENT_REQUIRED_FIELDS = {
    "event_type": str,
    "vessel_id": str,
    "imo": str,
    "classification": str,
    "flag": str,
    "entry_point": str,
    "exit_point": str,
    "eta_start": str,
    "eta_end": str,
    "declared_path": str,
}

RECEIPT_REQUIRED_FIELDS = {
    "vessel_id": str,
    "classification": str,
    "event_type": str,
    "location": str,
    "description": str,
}

EVENT_TYPE_VALUES = {"ENTRY", "TRANSIT", "EXIT"}
RECEIPT_EVENT_TYPE_VALUES = {"SAFE_PASSAGE", "INCIDENT", "HALT"}
CLASSIFICATION_VALUES = {"HUM", "CIV", "MIL"}
MISSION_VALUES = {"ESCORT", "DECONFLICT", "EXPANDED"}
EXECUTION_ORIGIN_VALUES = {"present_state", "carried_state"}
PROOF_SOURCE_VALUES = {"AIS", "RADAR", "EO"}


def _type_name(expected_type: type) -> str:
    return expected_type.__name__


def _require_fields(data: Dict[str, Any], required: Dict[str, type], errors: List[str]) -> None:
    for field, expected_type in required.items():
        if field not in data:
            errors.append(f"missing required field: {field}")
            continue
        if not isinstance(data[field], expected_type):
            errors.append(
                f"field {field} must be {_type_name(expected_type)}, got {type(data[field]).__name__}"
            )


def _validate_common(data: Dict[str, Any], errors: List[str]) -> None:
    classification = data.get("classification")
    if classification is not None and classification not in CLASSIFICATION_VALUES:
        errors.append(
            f"classification must be one of {sorted(CLASSIFICATION_VALUES)}, got {classification}"
        )

    mission_expected = data.get("mission_expected", "ESCORT")
    if mission_expected not in {"ESCORT", "DECONFLICT"}:
        errors.append(
            f"mission_expected must be one of ['DECONFLICT', 'ESCORT'], got {mission_expected}"
        )

    mission_actual = data.get("mission_actual", "ESCORT")
    if mission_actual not in MISSION_VALUES:
        errors.append(
            f"mission_actual must be one of {sorted(MISSION_VALUES)}, got {mission_actual}"
        )

    execution_origin = data.get("execution_origin", "present_state")
    if execution_origin not in EXECUTION_ORIGIN_VALUES:
        errors.append(
            f"execution_origin must be one of {sorted(EXECUTION_ORIGIN_VALUES)}, got {execution_origin}"
        )

    proof_sources = data.get("proof_sources", ["AIS", "RADAR", "EO"])
    if not isinstance(proof_sources, list):
        errors.append(f"proof_sources must be list, got {type(proof_sources).__name__}")
    else:
        for idx, item in enumerate(proof_sources):
            if not isinstance(item, str):
                errors.append(f"proof_sources[{idx}] must be str, got {type(item).__name__}")
                continue
            if item.upper() not in PROOF_SOURCE_VALUES:
                errors.append(
                    f"proof_sources[{idx}] must be one of {sorted(PROOF_SOURCE_VALUES)}, got {item}"
                )

    for bool_field in [
        "refusal_available",
        "civilian_class_protected",
        "classification_valid",
        "route_window_valid",
    ]:
        if bool_field in data and not isinstance(data[bool_field], bool):
            errors.append(f"{bool_field} must be bool, got {type(data[bool_field]).__name__}")


def validate_event_data(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    _require_fields(data, EVENT_REQUIRED_FIELDS, errors)
    _validate_common(data, errors)

    event_type = data.get("event_type")
    if isinstance(event_type, str) and event_type.upper() not in EVENT_TYPE_VALUES:
        errors.append(f"event_type must be one of {sorted(EVENT_TYPE_VALUES)}, got {event_type}")

    return errors


def validate_receipt_data(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    _require_fields(data, RECEIPT_REQUIRED_FIELDS, errors)
    _validate_common(data, errors)

    event_type = data.get("event_type")
    if isinstance(event_type, str) and event_type not in RECEIPT_EVENT_TYPE_VALUES:
        errors.append(
            f"event_type must be one of {sorted(RECEIPT_EVENT_TYPE_VALUES)}, got {event_type}"
        )

    return errors


def format_errors(errors: List[str]) -> str:
    return "\n".join(f" - {err}" for err in errors)


def validate_json_file(path: str, mode: str) -> List[str]:
    import json

    file_path = Path(path)
    if not file_path.exists():
        return [f"JSON file not found: {file_path}"]

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]

    if not isinstance(data, dict):
        return [f"top-level JSON must be object, got {type(data).__name__}"]

    if mode == "event":
        return validate_event_data(data)
    if mode == "receipt":
        return validate_receipt_data(data)

    return [f"unsupported validation mode: {mode}"]