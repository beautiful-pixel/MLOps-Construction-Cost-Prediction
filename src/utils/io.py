from pathlib import Path
import pandas as pd
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
MASTER_PATH = PROCESSED_ROOT / "master.parquet"


def load_tabular_file(path: Path) -> pd.DataFrame:
    """
    Load a tabular file according to its extension.

    Currently supports CSV.
    """

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    else:
        raise ValueError(f"Unsupported tabular format: {suffix}")


def atomic_write_parquet(df, path: Path, **kwargs) -> None:
    """
    Atomically write a parquet file.

    The file is first written to a temporary file
    in the same directory, then atomically replaced.
    """

    tmp_path = path.with_suffix(path.suffix + ".tmp")

    df.to_parquet(tmp_path, **kwargs)

    tmp_path.replace(path)


def load_master_dataframe() -> pd.DataFrame:
    """
    Load the current master dataset.

    """

    if not MASTER_PATH.exists():
        raise FileNotFoundError(
            f"Master dataset not found at {MASTER_PATH}"
        )

    df = pd.read_parquet(MASTER_PATH)

    if df.empty:
        raise ValueError("Master dataset is empty.")


    return df


