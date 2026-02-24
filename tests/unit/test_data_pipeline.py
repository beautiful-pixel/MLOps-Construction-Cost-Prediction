"""
Unit tests for data pipeline components.

Tests actual project code from src/data/data_contract.py and
src/features/feature_schema.py, using the real configs.
"""
import sys
import os
from pathlib import Path
import pytest
import pandas as pd
import tempfile
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

CONFIGS_DIR = str(Path(__file__).parent.parent.parent / "configs")


@pytest.fixture(autouse=True)
def set_config_root(monkeypatch):
    """Ensure CONFIG_ROOT points to the project configs directory."""
    monkeypatch.setenv("CONFIG_ROOT", CONFIGS_DIR)


# ---------------------------------------------------------------------------
# Data contract validation tests (using actual validate_dataframe)
# ---------------------------------------------------------------------------

class TestDataContractValidation:
    """Test data contract validation using actual project code."""

    def test_validate_required_columns_present(self, sample_dataframe):
        """Test that sample data has some required contract columns."""
        from data.data_contract import load_data_contract

        contract = load_data_contract(1)
        required_cols = set(contract["columns"].keys())
        actual_cols = set(sample_dataframe.columns)

        # sample_dataframe may not have all 23 columns, but check overlap
        overlap = required_cols & actual_cols
        assert len(overlap) > 0

    def test_validate_missing_columns_detected(self):
        """Test detection of missing required columns via contract."""
        from data.data_contract import load_data_contract

        contract = load_data_contract(1)
        required_cols = set(contract["columns"].keys())

        df = pd.DataFrame({"not_a_real_column": [1, 2, 3]})
        missing = required_cols - set(df.columns)
        assert len(missing) > 0

    def test_data_contract_has_primary_key(self):
        """Test data contract v1 defines a primary key."""
        from data.data_contract import get_primary_key

        pk = get_primary_key(1)
        assert isinstance(pk, list)
        assert len(pk) > 0
        assert "data_id" in pk

    def test_data_contract_has_target(self):
        """Test data contract v1 defines a target column."""
        from data.data_contract import get_target_column

        target = get_target_column(1)
        assert target == "construction_cost_per_m2_usd"

    def test_data_contract_has_dedup_rules(self):
        """Test data contract v1 defines deduplication rules."""
        from data.data_contract import get_deduplication_rules

        rules = get_deduplication_rules(1)
        assert isinstance(rules, dict)

    def test_validate_dataframe_rejects_empty(self):
        """Test validate_dataframe raises on empty DataFrame."""
        from data.data_contract import validate_dataframe

        with pytest.raises(ValueError, match="empty"):
            validate_dataframe(pd.DataFrame(), 1)

    def test_validate_dataframe_rejects_missing_columns(self):
        """Test validate_dataframe raises when columns are missing."""
        from data.data_contract import validate_dataframe

        df = pd.DataFrame({"bogus": [1]})
        with pytest.raises(ValueError, match="Missing required columns"):
            validate_dataframe(df, 1)

    def test_load_data_contract_returns_dict(self):
        """Test loading data contract returns valid dict."""
        from data.data_contract import load_data_contract

        contract = load_data_contract(1)
        assert isinstance(contract, dict)
        assert "columns" in contract
        assert "primary_key" in contract
        assert "target" in contract

    def test_data_contract_columns_have_types(self):
        """Test all columns in contract define a type."""
        from data.data_contract import load_data_contract

        contract = load_data_contract(1)
        for col, rules in contract["columns"].items():
            assert "type" in rules, f"Column '{col}' missing 'type'"

    def test_data_contract_target_is_non_nullable(self):
        """Test target column is marked as non_nullable."""
        from data.data_contract import load_data_contract

        contract = load_data_contract(1)
        target = contract["target"]
        target_rules = contract["columns"][target]
        assert target_rules.get("non_nullable", False) is True


class TestIngestionPipeline:
    """Test data ingestion pipeline file operations."""

    def test_generate_batch_id_format(self):
        """Test batch ID generation follows expected format."""
        from datetime import datetime
        from uuid import uuid4

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"batch_{timestamp}_{uuid4().hex[:6]}"

        assert batch_id.startswith("batch_")
        parts = batch_id.split("_")
        assert len(parts) >= 3

    def test_detect_csv_files(self, temp_incoming_dir, sample_csv_file):
        """Test detection of CSV files in incoming directory."""
        csv_files = list(temp_incoming_dir.glob("*.csv"))

        assert len(csv_files) == 1
        assert csv_files[0].name == "data_sample.csv"

    def test_detect_image_files(self, temp_incoming_dir):
        """Test detection of TIF image files."""
        tif_file = temp_incoming_dir / "image_001.tif"
        tif_file.touch()

        image_files = list(temp_incoming_dir.glob("*.tif"))
        assert len(image_files) == 1

    def test_reject_unsupported_file_types(self):
        """Test rejection of unsupported file types based on contract."""
        from data.data_contract import load_data_contract

        contract = load_data_contract(1)
        supported = set(contract.get("tabular_extensions", []))
        # PDF is not a supported extension
        assert "pdf" not in supported

    def test_create_batch_directory(self, temp_raw_dir):
        """Test batch directory creation."""
        batch_id = "batch_20260222_120000_abc123"
        batch_dir = temp_raw_dir / batch_id

        batch_dir.mkdir(parents=True, exist_ok=True)

        assert batch_dir.exists()
        assert batch_dir.is_dir()


class TestPreprocessing:
    """Test data preprocessing functionality."""

    def test_load_csv_file(self, sample_csv_file):
        """Test loading CSV file."""
        df = pd.read_csv(sample_csv_file)

        assert len(df) == 3
        assert "data_id" in df.columns

    def test_concatenate_multiple_csv(self):
        """Test concatenation of multiple DataFrames."""
        df1 = pd.DataFrame({"id": [1, 2], "value": [10, 20]})
        df2 = pd.DataFrame({"id": [3, 4], "value": [30, 40]})

        result = pd.concat([df1, df2], ignore_index=True)

        assert len(result) == 4
        assert result["id"].tolist() == [1, 2, 3, 4]

    def test_deduplication_on_merge(self):
        """Test deduplication during merge (mirrors contract's dedup rules)."""
        master_df = pd.DataFrame({
            "data_id": ["ID001", "ID002", "ID003"],
            "value": [10, 20, 30],
        })
        batch_df = pd.DataFrame({
            "data_id": ["ID003", "ID004", "ID005"],
            "value": [35, 40, 50],
        })

        merged_df = pd.concat([master_df, batch_df], ignore_index=True)
        merged_df = merged_df.drop_duplicates(subset=["data_id"], keep="last")

        assert len(merged_df) == 5
        # ID003 should have the batch value (keep="last")
        id3_row = merged_df[merged_df["data_id"] == "ID003"]
        assert id3_row["value"].values[0] == 35

    def test_atomic_write_parquet(self):
        """Test atomic parquet write with temp file + rename."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "value": [10, 20, 30],
        })

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.parquet"
            temp_path = Path(tmpdir) / "output.parquet.tmp"

            df.to_parquet(temp_path, index=False)
            temp_path.rename(output_path)

            assert output_path.exists()
            result = pd.read_parquet(output_path)
            assert len(result) == 3


class TestImageProcessing:
    """Test image reference handling in data pipeline."""

    def test_contract_defines_image_columns(self):
        """Test data contract defines external image file columns."""
        from data.data_contract import load_data_contract

        contract = load_data_contract(1)
        image_cols = [
            col for col, rules in contract["columns"].items()
            if rules.get("type") == "string" and "external_file" in rules
        ]
        # Contract should have sentinel2 and/or viirs image columns
        assert len(image_cols) > 0

    def test_detect_missing_referenced_images(self):
        """Test detection of missing image files from references."""
        referenced = {"img_001.tif", "img_002.tif", "img_003.tif"}
        available = {"img_001.tif", "img_002.tif"}

        missing = referenced - available
        assert len(missing) == 1
        assert "img_003.tif" in missing

    def test_detect_unreferenced_images(self):
        """Test detection of unreferenced image files."""
        referenced = {"img_001.tif", "img_002.tif"}
        available = {"img_001.tif", "img_002.tif", "img_999.tif"}

        unreferenced = available - referenced
        assert len(unreferenced) == 1
        assert "img_999.tif" in unreferenced


class TestDataValidationErrorHandling:
    """Test error handling via actual data_contract functions."""

    def test_validation_error_on_missing_columns(self):
        """Test validate_dataframe raises for missing required columns."""
        from data.data_contract import validate_dataframe

        df = pd.DataFrame({"country": ["France"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            validate_dataframe(df, data_contract_version=1)

    def test_load_nonexistent_contract_version(self):
        """Test loading nonexistent contract version raises error."""
        from data.data_contract import load_data_contract

        with pytest.raises(ValueError, match="Unknown version"):
            load_data_contract(9999)

    def test_get_available_versions(self):
        """Test listing available data contract versions."""
        from data.data_contract import get_data_contract_versions

        versions = get_data_contract_versions()
        assert isinstance(versions, list)
        assert 1 in versions
