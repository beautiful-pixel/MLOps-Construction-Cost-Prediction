from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"


def clean_incoming() -> None:
    if not INCOMING_DIR.exists():
        raise RuntimeError("Incoming directory does not exist.")

    for path in INCOMING_DIR.rglob("*"):
        if path.is_file():
            raise RuntimeError(
                f"Incoming directory is not empty. File still present: {path}"
            )

    for path in sorted(INCOMING_DIR.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass