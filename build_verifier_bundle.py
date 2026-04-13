import hashlib
import json
import shutil
import zipfile
from pathlib import Path


ROOT = Path(".")
DIST_DIR = ROOT / "dist"
BUNDLE_DIR = DIST_DIR / "verifier_bundle_v0.1.0"
ZIP_PATH = DIST_DIR / "redsea-corridor-verifier-bundle-v0.1.0.zip"


FILES_TO_COPY = [
    "corridor/__init__.py",
    "corridor/main.py",
    "corridor/schema.py",
    "corridor/cli.py",
    "verify_corridor.py",
    "run_all.bat",
    "run_tests.bat",
    "README.md",
    ".github/workflows/ci.yml",
    "examples/event_pass.json",
    "examples/event_fail.json",
    "examples/receipt_pass.json",
    "examples/receipt_fail.json",
    "examples/bad_event.json",
    "examples/bad_receipt.json",
    "tests/test_corridor.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(rel_path: str) -> dict:
    src = ROOT / rel_path
    if not src.exists():
        raise FileNotFoundError(f"Missing required file: {src}")

    dst = BUNDLE_DIR / rel_path
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    return {
        "path": rel_path.replace("\\", "/"),
        "sha256": sha256_file(dst),
    }


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_manifest(copied_files: list[dict]) -> dict:
    return {
        "bundle_name": "redsea-corridor-verifier-bundle-v0.1.0",
        "version": "v0.1.0",
        "purpose": "Offline replay and verification bundle for Red Sea Corridor execution-bound admissibility baseline.",
        "files": copied_files,
    }


def create_zip(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir.parent))


def main() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    copied_files = []
    for rel_path in FILES_TO_COPY:
        copied_files.append(copy_file(rel_path))

    verify_bat = """@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\\Scripts\\python.exe" (
    echo Creating local virtual environment...
    python -m venv .venv
)

echo Running verifier suite...
call ".venv\\Scripts\\python.exe" -m unittest discover -s tests -v
if errorlevel 1 (
    echo.
    echo TEST SUITE FAILED
    exit /b 1
)

call ".venv\\Scripts\\python.exe" -m corridor.cli run-all
if errorlevel 1 (
    echo.
    echo RUN-ALL FAILED
    exit /b 1
)

echo.
echo VERIFIER BUNDLE PASS
exit /b 0
"""
    write_text(BUNDLE_DIR / "verify_bundle.bat", verify_bat)

    manifest = build_manifest(copied_files + [{
        "path": "verify_bundle.bat",
        "sha256": sha256_file(BUNDLE_DIR / "verify_bundle.bat"),
    }])
    write_text(BUNDLE_DIR / "MANIFEST.json", json.dumps(manifest, indent=2))

    create_zip(BUNDLE_DIR, ZIP_PATH)

    zip_hash = sha256_file(ZIP_PATH)
    write_text(DIST_DIR / "redsea-corridor-verifier-bundle-v0.1.0.zip.sha256", zip_hash + "\n")

    print("Bundle written:")
    print(f" - {BUNDLE_DIR}")
    print(f" - {ZIP_PATH}")
    print(f" - {DIST_DIR / 'redsea-corridor-verifier-bundle-v0.1.0.zip.sha256'}")


if __name__ == "__main__":
    main()