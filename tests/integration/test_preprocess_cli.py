import subprocess
from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_preprocess.py"

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
BATCH_MARKER = DATA_DIR / "current_batch.txt"


def clean_environment():
    """
    Clean data folders to ensure deterministic tests.
    """
    if RAW_DIR.exists():
        shutil.rmtree(RAW_DIR)

    if PROCESSED_DIR.exists():
        shutil.rmtree(PROCESSED_DIR)

    if BATCH_MARKER.exists():
        BATCH_MARKER.unlink()


def test_preprocess_missing_batch_marker_cli():
    """
    Integration test:
    - No current_batch.txt
    - exit code = 1
    """

    clean_environment()

    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 1


def test_preprocess_missing_raw_batch_cli():
    """
    Integration test:
    - current_batch.txt exists
    - raw/<batch_id> does NOT exist
    - exit code = 1
    """

    clean_environment()

    BATCH_MARKER.write_text("batch_test")

    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 1


def test_preprocess_valid_batch_cli():
    """
    Integration test:
    - current_batch.txt exists
    - raw/<batch_id> exists with valid CSV
    - processed/<batch_id> created
    - exit code = 0
    """

    clean_environment()

    batch_id = "batch_test"
    raw_batch_dir = RAW_DIR / batch_id
    raw_batch_dir.mkdir(parents=True)

    BATCH_MARKER.write_text(batch_id)

    # ⚠️ IMPORTANT :
    # Ce CSV doit correspondre EXACTEMENT au schéma attendu
    # sinon validate_dataframe va échouer.
    csv_file = raw_batch_dir / "test.csv"

    csv_file.write_text(
        "feature1,feature2,target\n"
        "1,2,100\n"
        "3,4,200\n"
    )

    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0

    processed_batch_dir = PROCESSED_DIR / batch_id
    assert processed_batch_dir.exists()

    processed_files = list(processed_batch_dir.glob("*.csv"))
    assert len(processed_files) == 1
