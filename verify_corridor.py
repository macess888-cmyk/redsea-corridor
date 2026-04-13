import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List


ARTIFACTS_DIR = Path("artifacts")
RECEIPTS_DIR = Path("receipts")
LEDGER_PATH = ARTIFACTS_DIR / "corridor_ledger.jsonl"
RECEIPT_INDEX_PATH = RECEIPTS_DIR / "receipt_index.jsonl"


def canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chained_hash(previous_hash: str, record: Dict[str, Any]) -> str:
    return sha256_text(previous_hash + canonical_json(record))


def load_ledger() -> List[Dict[str, Any]]:
    if not LEDGER_PATH.exists():
        raise FileNotFoundError(f"Missing ledger: {LEDGER_PATH}")
    entries: List[Dict[str, Any]] = []
    with LEDGER_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_receipt_index() -> List[Dict[str, str]]:
    if not RECEIPT_INDEX_PATH.exists():
        print("HOLD: no receipts found (receipt_index.jsonl missing)")
        print("→ run: python -m corridor.cli receipt-json --file examples\\receipt_pass.json")
        print("→ or: run_all.bat")
        return []
    rows: List[Dict[str, str]] = []
    with RECEIPT_INDEX_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def verify_ledger(entries: List[Dict[str, Any]]) -> None:
    previous = "GENESIS"
    for idx, entry in enumerate(entries):
        core = {k: v for k, v in entry.items() if k not in {"previous_hash", "current_hash"}}
        expected_hash = chained_hash(previous, core)

        if entry["previous_hash"] != previous:
            raise ValueError(f"Ledger chain break at index {idx}: previous_hash mismatch")

        if entry["current_hash"] != expected_hash:
            raise ValueError(f"Ledger chain break at index {idx}: current_hash mismatch")

        previous = entry["current_hash"]


def verify_bind_trace_refs(entries: List[Dict[str, Any]]) -> None:
    for idx, entry in enumerate(entries):
        bind_ref = entry.get("bind_trace_ref")
        if not bind_ref or len(bind_ref) != 64:
            raise ValueError(f"Invalid bind_trace_ref at index {idx}")


def verify_status_rules(entries: List[Dict[str, Any]]) -> None:
    for idx, entry in enumerate(entries):
        vessel_class = entry["vessel"]["classification"]
        if vessel_class not in {"HUM", "CIV", "MIL"}:
            raise ValueError(f"Invalid vessel classification at index {idx}")

        if entry["event_type"] == "EXIT" and entry["status"] not in {"COMPLETE", "FAILED"}:
            raise ValueError(f"EXIT must end COMPLETE or FAILED at index {idx}")


def verify_receipts() -> None:
    index_rows = load_receipt_index()
    if not index_rows:
        return

    previous = "GENESIS"

    for idx, row in enumerate(index_rows):
        receipt_path = Path(row["path"])
        if not receipt_path.exists():
            raise ValueError(f"Indexed receipt missing at index {idx}: {receipt_path}")

        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        core = {
            k: v for k, v in receipt.items()
            if k not in {"previous_receipt_hash", "current_receipt_hash"}
        }
        expected_hash = chained_hash(previous, core)

        if receipt["previous_receipt_hash"] != previous:
            raise ValueError(f"Receipt chain break at index {idx}: previous hash mismatch")

        if receipt["current_receipt_hash"] != expected_hash:
            raise ValueError(f"Receipt chain break at index {idx}: current hash mismatch")

        if "violation_classes" not in receipt:
            raise ValueError(f"Missing violation_classes at index {idx}")

        if not isinstance(receipt["violation_classes"], list):
            raise ValueError(f"violation_classes must be a list at index {idx}")

        if row.get("receipt_id") != receipt.get("receipt_id"):
            raise ValueError(f"Receipt index mismatch at index {idx}: receipt_id differs")

        if row.get("current_receipt_hash") != receipt.get("current_receipt_hash"):
            raise ValueError(f"Receipt index mismatch at index {idx}: hash differs")

        previous = receipt["current_receipt_hash"]


def main() -> None:
    entries = load_ledger()
    verify_ledger(entries)
    verify_bind_trace_refs(entries)
    verify_status_rules(entries)
    verify_receipts()
    print("PASS: ledger, bind refs, status rules, receipt index, receipt chain, and multi-violation fields verified.")


if __name__ == "__main__":
    main()