import subprocess
from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_ingestion.py"

DATA_DIR = PROJECT_ROOT / "data"
INCOMING_DIR = DATA_DIR / "incoming"
RAW_DIR = DATA_DIR / "raw"
BATCH_MARKER = DATA_DIR / "current_batch.txt"


def clean_environment():
    """
    Ensure clean state before each test.
    """
    if INCOMING_DIR.exists():
        shutil.rmtree(INCOMING_DIR)

    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)

    if BATCH_MARKER.exists():
        BATCH_MARKER.unlink()

    INCOMING_DIR.mkdir(parents=True)


def test_ingestion_no_files_cli():
    """
    Integration test:
    - incoming exists
    - no files
    - exit code = 0
    - raw not created
    """

    clean_environment()

    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0
    assert not RAW_DIR.exists()
    assert not BATCH_MARKER.exists()


def test_ingestion_with_one_file_cli():
    """
    Integration test:
    - one csv in incoming
    - file moved to raw/<batch_id>/
    - batch marker created
    """

    clean_environment()

    # Create dummy file
    csv_path = INCOMING_DIR / "test_batch.csv"
    csv_path.write_text("a,b\n1,2")

    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0

    # incoming should now be empty
    assert not any(INCOMING_DIR.glob("*.csv"))

    # raw directory must exist
    assert RAW_DIR.exists()

    # exactly one batch folder
    batch_dirs = list(RAW_DIR.iterdir())
    assert len(batch_dirs) == 1

    batch_dir = batch_dirs[0]

    # file must have been moved
    moved_file = batch_dir / "test_batch.csv"
    assert moved_file.exists()

    # batch marker must exist
    assert BATCH_MARKER.exists()

    batch_id = BATCH_MARKER.read_text().strip()
    assert batch_id == batch_dir.name


def test_ingestion_missing_incoming_cli():
    """
    Integration test:
    - incoming directory missing
    - exit code = 1
    """

    if INCOMING_DIR.exists():
        shutil.rmtree(INCOMING_DIR)

    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 1
