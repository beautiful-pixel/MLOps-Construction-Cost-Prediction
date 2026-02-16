import subprocess
from pathlib import Path
import shutil


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_check_incoming.py"
INCOMING_DIR = PROJECT_ROOT / "data" / "incoming"


def setup_incoming():
    """
    Ensure clean incoming directory.
    """
    if INCOMING_DIR.exists():
        shutil.rmtree(INCOMING_DIR)
    INCOMING_DIR.mkdir(parents=True)


def teardown_incoming():
    """
    Clean after test.
    """
    if INCOMING_DIR.exists():
        shutil.rmtree(INCOMING_DIR)


def test_check_incoming_empty_cli():
    """
    Integration test:
    - incoming exists
    - no csv files
    - exit code = 0
    """
    setup_incoming()

    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
    )

    teardown_incoming()

    assert result.returncode == 0


def test_check_incoming_with_files_cli():
    """
    Integration test:
    - incoming exists
    - csv files present
    - exit code = 0
    """
    setup_incoming()

    # Create dummy file
    (INCOMING_DIR / "batch_2020.csv").write_text("a,b\n1,2")

    result = subprocess.run(
        ["python", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
    )

    teardown_incoming()

    assert result.returncode == 0


def test_check_incoming_missing_directory_cli():
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
