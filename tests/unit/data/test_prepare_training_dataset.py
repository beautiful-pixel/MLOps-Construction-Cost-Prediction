import pandas as pd
import pytest
from pathlib import Path

from data.prepare import prepare_training_dataset


def _create_batch(path: Path, year: int, n_rows: int = 3):
    """
    Helper to create a fake batch CSV.
    """
    df = pd.DataFrame({
        "year": [year] * n_rows,
        "value": range(n_rows),
    })
    df.to_csv(path, index=False)


def test_use_all_batches(tmp_path):
    """
    If k_last_batches=None, all batches should be used.
    """
    _create_batch(tmp_path / "2018.csv", 2018)
    _create_batch(tmp_path / "2019.csv", 2019)
    _create_batch(tmp_path / "2020.csv", 2020)

    df = prepare_training_dataset(
        processed_dir=tmp_path,
        k_last_batches=None,
    )

    assert len(df) == 9
    assert set(df["year"].unique()) == {2018, 2019, 2020}


def test_use_k_last_batches(tmp_path):
    """
    Should only use the k most recent batches.
    """
    _create_batch(tmp_path / "2018.csv", 2018)
    _create_batch(tmp_path / "2019.csv", 2019)
    _create_batch(tmp_path / "2020.csv", 2020)

    df = prepare_training_dataset(
        processed_dir=tmp_path,
        k_last_batches=2,
    )

    assert len(df) == 6
    assert set(df["year"].unique()) == {2019, 2020}


def test_k_larger_than_available_raises(tmp_path):
    """
    Should raise if k_last_batches > available batches.
    """
    _create_batch(tmp_path / "2019.csv", 2019)

    with pytest.raises(ValueError):
        prepare_training_dataset(
            processed_dir=tmp_path,
            k_last_batches=5,
        )


def test_k_zero_or_negative_raises(tmp_path):
    """
    k_last_batches must be positive.
    """
    _create_batch(tmp_path / "2019.csv", 2019)

    with pytest.raises(ValueError):
        prepare_training_dataset(
            processed_dir=tmp_path,
            k_last_batches=0,
        )

    with pytest.raises(ValueError):
        prepare_training_dataset(
            processed_dir=tmp_path,
            k_last_batches=-1,
        )


def test_no_batches_found_raises(tmp_path):
    """test_prepare_training_dataset.py
    Should raise if directory contains no CSV files.
    """
    with pytest.raises(ValueError):
        prepare_training_dataset(
            processed_dir=tmp_path,
            k_last_batches=None,
        )


def test_duplicates_are_removed(tmp_path):
    """
    Duplicate rows across batches should be removed.
    """
    df = pd.DataFrame({
        "year": [2020, 2020],
        "value": [1, 1],  # duplicate row
    })

    df.to_csv(tmp_path / "2020.csv", index=False)

    result = prepare_training_dataset(
        processed_dir=tmp_path,
        k_last_batches=None,
    )

    assert len(result) == 1
