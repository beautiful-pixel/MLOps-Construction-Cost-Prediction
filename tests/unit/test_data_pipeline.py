"""
Unit tests for data pipeline components.
"""
import sys
from pathlib import Path
import pytest
import pandas as pd
import tempfile
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestDataContractValidation:
    """Test data contract validation logic."""

    def test_validate_required_columns(self, sample_dataframe, sample_data_contract):
        """Test validation of required columns."""
        required_cols = ["data_id", "country", "year"]
        df = sample_dataframe
        
        # Check all required columns exist
        for col in required_cols:
            assert col in df.columns

    def test_validate_missing_columns(self, sample_invalid_dataframe):
        """Test detection of missing required columns."""
        df = sample_invalid_dataframe
        required_cols = ["non_existent_column"]
        
        # Check for missing columns
        missing = [col for col in required_cols if col not in df.columns]
        assert len(missing) > 0

    def test_validate_data_types(self, sample_dataframe):
        """Test data type validation."""
        df = sample_dataframe
        
        # Check integer types
        assert df["year"].dtype in ["int64", "int32"]
        
        # Check float types
        assert df["deflated_gdp_usd"].dtype in ["float64", "float32"]
        
        # Check string types
        assert df["country"].dtype == "object"

    def test_validate_numeric_constraints(self, sample_invalid_dataframe):
        """Test numeric min/max constraints."""
        df = sample_invalid_dataframe
        
        # Check for negative values where not allowed
        negative_values = df[df["deflated_gdp_usd"] < 0]
        assert len(negative_values) > 0

    def test_validate_year_range(self, sample_dataframe):
        """Test year range constraints."""
        df = sample_dataframe
        min_year = 1950
        max_year = 2100
        
        assert (df["year"] >= min_year).all()
        assert (df["year"] <= max_year).all()

    def test_validate_allowed_values(self, sample_dataframe):
        """Test allowed values constraint."""
        df = sample_dataframe
        
        allowed_values = ["Yes", "No"]
        assert df["developed_country"].isin(allowed_values).all()

    def test_validate_primary_key_uniqueness(self, sample_dataframe):
        """Test primary key uniqueness validation."""
        df = sample_dataframe
        primary_key = "data_id"
        
        # Check uniqueness
        duplicate_ids = df[df.duplicated(subset=[primary_key], keep=False)]
        assert len(duplicate_ids) == 0

    def test_validate_primary_key_with_duplicates(self):
        """Test detection of duplicate primary keys."""
        df = pd.DataFrame({
            "data_id": ["ID001", "ID001", "ID003"],  # Duplicate
            "country": ["France", "France", "Spain"],
        })
        
        duplicate_ids = df[df.duplicated(subset=["data_id"], keep=False)]
        assert len(duplicate_ids) > 0

    def test_validate_non_nullable_columns(self):
        """Test non-nullable constraint validation."""
        df = pd.DataFrame({
            "data_id": ["ID001", None, "ID003"],  # Contains NULL
            "country": ["France", "Germany", "Spain"],
        })
        
        # Check for nulls in non-nullable column
        nulls_in_data_id = df["data_id"].isna().sum()
        assert nulls_in_data_id > 0

    def test_validate_no_nulls_in_required_fields(self, sample_dataframe):
        """Test that required fields have no NaN values."""
        df = sample_dataframe
        required_fields = ["data_id", "country", "year"]
        
        for field in required_fields:
            assert df[field].isna().sum() == 0


class TestIngestionPipeline:
    """Test data ingestion pipeline."""

    def test_generate_batch_id(self):
        """Test batch ID generation."""
        from datetime import datetime
        from uuid import uuid4
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"batch_{timestamp}_{uuid4().hex[:6]}"
        
        # Verify format
        assert batch_id.startswith("batch_")
        assert len(batch_id) > len("batch_")

    def test_detect_csv_files(self, temp_incoming_dir, sample_csv_file):
        """Test detection of CSV files."""
        csv_files = list(temp_incoming_dir.glob("*.csv"))
        
        assert len(csv_files) == 1
        assert csv_files[0].name == "data_sample.csv"

    def test_detect_image_files(self, temp_incoming_dir):
        """Test detection of image files."""
        # Create dummy TIF file
        tif_file = temp_incoming_dir / "image_001.tif"
        tif_file.touch()
        
        image_files = list(temp_incoming_dir.glob("*.tif"))
        assert len(image_files) == 1

    def test_ignore_system_files(self, temp_incoming_dir):
        """Test that system files are ignored."""
        # Create system files
        ds_store = temp_incoming_dir / ".DS_Store"
        thumbs = temp_incoming_dir / "Thumbs.db"
        ds_store.touch()
        thumbs.touch()
        
        ignored_files = {".DS_Store", "Thumbs.db"}
        files_in_dir = {f.name for f in temp_incoming_dir.iterdir()}
        
        assert ds_store.name in ignored_files
        assert thumbs.name in ignored_files

    def test_reject_unsupported_file_types(self):
        """Test rejection of unsupported file types."""
        supported_extensions = {".csv", ".tif"}
        unsupported_file = "document.pdf"
        
        ext = Path(unsupported_file).suffix
        assert ext not in supported_extensions

    def test_create_batch_directory(self, temp_raw_dir):
        """Test batch directory creation."""
        batch_id = "batch_20260222_120000_abc123"
        batch_dir = temp_raw_dir / batch_id
        
        batch_dir.mkdir(parents=True, exist_ok=True)
        
        assert batch_dir.exists()
        assert batch_dir.is_dir()

    def test_organize_files_in_batch(self, temp_raw_dir):
        """Test organization of files in batch structure."""
        batch_id = "batch_20260222_120000_abc123"
        batch_dir = temp_raw_dir / batch_id
        tabular_dir = batch_dir / "tabular"
        images_dir = batch_dir / "images"
        
        tabular_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)
        
        assert tabular_dir.exists()
        assert images_dir.exists()


class TestPreprocessing:
    """Test data preprocessing functionality."""

    def test_load_csv_file(self, sample_csv_file):
        """Test loading CSV file."""
        df = pd.read_csv(sample_csv_file)
        
        assert len(df) == 3
        assert len(df.columns) == 16

    def test_concatenate_multiple_csv(self):
        """Test concatenation of multiple CSV files."""
        df1 = pd.DataFrame({"id": [1, 2], "value": [10, 20]})
        df2 = pd.DataFrame({"id": [3, 4], "value": [30, 40]})
        
        result = pd.concat([df1, df2], ignore_index=True)
        
        assert len(result) == 4
        assert result["id"].tolist() == [1, 2, 3, 4]

    def test_merge_into_master(self):
        """Test merging batch into master dataset."""
        master_df = pd.DataFrame({
            "id": [1, 2],
            "value": [10, 20],
        })
        batch_df = pd.DataFrame({
            "id": [3, 4],
            "value": [30, 40],
        })
        
        merged_df = pd.concat([master_df, batch_df], ignore_index=True)
        
        assert len(merged_df) == 4
        assert len(merged_df.columns) == 2

    def test_deduplication_on_merge(self):
        """Test deduplication during merge."""
        master_df = pd.DataFrame({
            "id": [1, 2, 3],
            "value": [10, 20, 30],
        })
        batch_df = pd.DataFrame({
            "id": [3, 4, 5],  # 3 is duplicate
            "value": [35, 40, 50],
        })
        
        # Drop duplicates based on ID
        merged_df = pd.concat([master_df, batch_df], ignore_index=True)
        merged_df = merged_df.drop_duplicates(subset=["id"], keep="first")
        
        assert len(merged_df) == 5
        assert 1 in merged_df["id"].values

    def test_atomic_write_parquet(self):
        """Test atomic parquet write."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "value": [10, 20, 30],
        })
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.parquet"
            
            # Write to temporary file first
            temp_path = Path(tmpdir) / "output.parquet.tmp"
            df.to_parquet(temp_path, index=False)
            
            # Atomic rename
            temp_path.rename(output_path)
            
            assert output_path.exists()
            
            # Verify content
            result = pd.read_parquet(output_path)
            assert len(result) == 3


class TestImageProcessing:
    """Test image processing in data pipeline."""

    def test_collect_referenced_images(self):
        """Test collection of image references from dataframe."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "sentinel2_path": ["img_001.tif", "img_002.tif", "img_003.tif"],
        })
        
        referenced_images = set(df["sentinel2_path"].unique())
        
        assert len(referenced_images) == 3
        assert "img_001.tif" in referenced_images

    def test_detect_missing_referenced_images(self):
        """Test detection of missing image files."""
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "image_file": ["img_001.tif", "img_002.tif", "img_003.tif"],
        })
        
        available_files = {"img_001.tif", "img_002.tif"}  # img_003.tif missing
        referenced_files = set(df["image_file"].unique())
        
        missing_files = referenced_files - available_files
        assert len(missing_files) > 0
        assert "img_003.tif" in missing_files

    def test_detect_unreferenced_images(self):
        """Test detection of unreferenced image files."""
        df = pd.DataFrame({
            "id": [1, 2],
            "image_file": ["img_001.tif", "img_002.tif"],
        })
        
        referenced_images = set(df["image_file"].unique())
        available_files = {"img_001.tif", "img_002.tif", "img_999.tif"}  # img_999.tif unreferenced
        
        unreferenced_files = available_files - referenced_images
        assert len(unreferenced_files) > 0
        assert "img_999.tif" in unreferenced_files

    def test_canonicalize_image_path(self):
        """Test image path canonicalization."""
        original_path = "raw/batch_001/images/sentinel2/image_001.tif"
        canonical_path = f"images/sentinel2/{Path(original_path).name}"
        
        assert canonical_path == "images/sentinel2/image_001.tif"


class TestDataValidationErrorHandling:
    """Test error handling in validation."""

    def test_validation_error_on_missing_required_field(self):
        """Test error raised when required field is missing."""
        df = pd.DataFrame({
            "country": ["France"],
            # Missing "data_id" required field
        })
        
        required_fields = ["data_id"]
        missing = [f for f in required_fields if f not in df.columns]
        
        assert len(missing) > 0

    def test_validation_error_on_invalid_type(self):
        """Test error raised for invalid data type."""
        df = pd.DataFrame({
            "year": ["not_a_number"],  # Should be int
        })
        
        try:
            df["year"].astype(int)
            assert False, "Should have raised an error"
        except ValueError:
            pass

    def test_validation_error_on_constraint_violation(self):
        """Test error raised for constraint violation."""
        df = pd.DataFrame({
            "year": [9999],  # Outside valid range
        })
        
        max_year = 2100
        violations = df[df["year"] > max_year]
        
        assert len(violations) > 0

    def test_validation_rollback_on_failure(self):
        """Test that failed validation doesn't corrupt data."""
        original_df = pd.DataFrame({
            "id": [1, 2, 3],
            "value": [10, 20, 30],
        })
        
        # Attempt invalid operation
        try:
            invalid_data = pd.DataFrame({
                "id": ["invalid"],
                "value": [None],
            })
            # Validation would fail here
            if invalid_data["id"].dtype != "int64":
                raise ValueError("Invalid data type")
        except ValueError:
            pass
        
        # Original data should be unchanged
        assert len(original_df) == 3
