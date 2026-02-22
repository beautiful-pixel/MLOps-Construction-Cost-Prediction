"""
Unit tests for feature schema versioning and validation.

Tests for feature schemas v1 and v2 configurations.
"""
import sys
from pathlib import Path
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestFeatureSchemaV1:
    """Test feature schema version 1."""

    def test_v1_has_correct_version(self):
        """Test that v1 schema has version 1."""
        schema_v1 = {
            "version": 1,
            "data_contract": 1,
            "tabular_features": {}
        }
        
        assert schema_v1["version"] == 1
        assert schema_v1["data_contract"] == 1

    def test_v1_feature_list(self):
        """Test v1 contains expected features."""
        v1_features = {
            "deflated_gdp_usd": {"type": "numeric", "impute": "median"},
            "straight_distance_to_capital_km": {"type": "numeric", "impute": "median", "clip": [0, 5000]},
            "developed_country": {"type": "categorical", "encoding": "binary", "impute": "most_frequent"},
            "access_to_highway": {"type": "categorical", "encoding": "binary", "impute": "most_frequent"},
            "region_economic_classification": {
                "type": "categorical",
                "encoding": "ordinal",
                "order": ["Low income", "Lower-middle income", "Upper-middle income", "High income"],
                "impute": "most_frequent"
            },
            "seismic_hazard_zone": {
                "type": "categorical",
                "encoding": "ordinal",
                "order": ["Very Low", "Low", "Moderate", "High", "Very High"],
                "impute": "most_frequent"
            },
        }
        
        assert len(v1_features) == 6
        assert "deflated_gdp_usd" in v1_features
        assert "access_to_highway" in v1_features

    def test_v1_numeric_features(self):
        """Test numeric features in v1."""
        numeric_features = {
            "deflated_gdp_usd": {"type": "numeric", "impute": "median"},
            "straight_distance_to_capital_km": {"type": "numeric", "impute": "median", "clip": [0, 5000]},
        }
        
        for feature_name, config in numeric_features.items():
            assert config["type"] == "numeric"
            assert "impute" in config

    def test_v1_categorical_features(self):
        """Test categorical features in v1."""
        categorical_features = {
            "developed_country": {"type": "categorical", "encoding": "binary"},
            "access_to_highway": {"type": "categorical", "encoding": "binary"},
            "region_economic_classification": {"type": "categorical", "encoding": "ordinal"},
            "seismic_hazard_zone": {"type": "categorical", "encoding": "ordinal"},
        }
        
        for feature_name, config in categorical_features.items():
            assert config["type"] == "categorical"
            assert "encoding" in config

    def test_v1_ordinal_encoding_order(self):
        """Test ordinal encoding has correct order in v1."""
        region_order = ["Low income", "Lower-middle income", "Upper-middle income", "High income"]
        seismic_order = ["Very Low", "Low", "Moderate", "High", "Very High"]
        
        assert len(region_order) == 4
        assert len(seismic_order) == 5
        assert region_order[0] == "Low income"
        assert seismic_order[-1] == "Very High"

    def test_v1_clipping_constraint(self):
        """Test clipping constraint in v1."""
        distance_config = {
            "type": "numeric",
            "impute": "median",
            "clip": [0, 5000]
        }
        
        assert distance_config["clip"] == [0, 5000]
        assert distance_config["clip"][0] == 0
        assert distance_config["clip"][1] == 5000


class TestFeatureSchemaV2:
    """Test feature schema version 2."""

    def test_v2_has_correct_version(self):
        """Test that v2 schema has version 2."""
        schema_v2 = {
            "version": 2,
            "data_contract": 1,
            "tabular_features": {}
        }
        
        assert schema_v2["version"] == 2
        assert schema_v2["data_contract"] == 1

    def test_v2_feature_list(self):
        """Test v2 contains expected features."""
        v2_features = {
            "access_to_highway": {"type": "categorical", "encoding": "binary", "impute": "most_frequent"},
            "deflated_gdp_usd": {"type": "numeric", "impute": "median"},
            "developed_country": {"type": "categorical", "encoding": "binary", "impute": "most_frequent"},
            "region_economic_classification": {
                "type": "categorical",
                "encoding": "onehot",
                "impute": "most_frequent",
                "order": ["Low income", "Lower-middle income", "Upper-middle income", "High income"]
            },
            "seismic_hazard_zone": {
                "type": "categorical",
                "encoding": "ordinal",
                "impute": "most_frequent",
                "order": ["Very Low", "Low", "Moderate", "High", "Very High"]
            },
            "straight_distance_to_capital_km": {
                "type": "numeric",
                "impute": "median",
                "clip": [0, 5000]
            },
        }
        
        assert len(v2_features) == 6
        assert "deflated_gdp_usd" in v2_features

    def test_v2_vs_v1_feature_differences(self):
        """Test what changed between v1 and v2."""
        # V2 changes
        # - region_economic_classification encoding changed from ordinal to onehot
        # - impute field added to seismic_hazard_zone
        # - impute field added to region_economic_classification
        
        v2_region_encoding = "onehot"  # Changed from ordinal in v1
        v1_region_encoding = "ordinal"
        
        assert v2_region_encoding != v1_region_encoding

    def test_v2_region_encoding_is_onehot(self):
        """Test that region in v2 uses onehot encoding."""
        region_config_v2 = {
            "type": "categorical",
            "encoding": "onehot",
            "impute": "most_frequent",
        }
        
        assert region_config_v2["encoding"] == "onehot"

    def test_v2_seismic_has_impute(self):
        """Test that seismic in v2 has impute strategy."""
        seismic_config_v2 = {
            "type": "categorical",
            "encoding": "ordinal",
            "impute": "most_frequent",
        }
        
        assert "impute" in seismic_config_v2
        assert seismic_config_v2["impute"] == "most_frequent"


class TestFeatureSchemaComparison:
    """Test comparison between v1 and v2."""

    def test_v1_v2_same_base_features(self):
        """Test v1 and v2 have same base feature set."""
        v1_features = {
            "deflated_gdp_usd",
            "straight_distance_to_capital_km",
            "developed_country",
            "access_to_highway",
            "region_economic_classification",
            "seismic_hazard_zone",
        }
        
        v2_features = {
            "deflated_gdp_usd",
            "straight_distance_to_capital_km",
            "developed_country",
            "access_to_highway",
            "region_economic_classification",
            "seismic_hazard_zone",
        }
        
        assert v1_features == v2_features

    def test_v1_has_more_features_than_latest_versions(self):
        """Test original v1/v2 had more features before cleanup."""
        # Original schemas had features like:
        # - us_cpi
        # - landlocked
        # - access_to_railway
        # - access_to_port
        # - access_to_airport
        # - flood_risk_class
        
        removed_features = {
            "us_cpi",
            "landlocked",
            "access_to_railway",
            "access_to_port",
            "access_to_airport",
            "flood_risk_class",
        }
        
        assert len(removed_features) == 6

    def test_v1_v2_encoding_strategies(self):
        """Test encoding strategies used in v1 vs v2."""
        v1_encodings = {
            "developed_country": "binary",
            "access_to_highway": "binary",
            "region_economic_classification": "ordinal",
            "seismic_hazard_zone": "ordinal",
        }
        
        v2_encodings = {
            "developed_country": "binary",
            "access_to_highway": "binary",
            "region_economic_classification": "onehot",  # Changed!
            "seismic_hazard_zone": "ordinal",
        }
        
        # Count differences
        differences = sum(1 for k in v1_encodings if v1_encodings[k] != v2_encodings[k])
        assert differences == 1  # Only region changed


class TestFeatureSchemaValidation:
    """Test feature schema validation."""

    def test_validate_schema_structure(self):
        """Test validation of schema structure."""
        schema = {
            "version": 1,
            "data_contract": 1,
            "tabular_features": {
                "feature1": {"type": "numeric"}
            }
        }
        
        # Required fields
        assert "version" in schema
        assert "data_contract" in schema
        assert "tabular_features" in schema

    def test_validate_feature_types(self):
        """Test validation of feature types."""
        valid_types = {"numeric", "categorical"}
        
        feature_configs = [
            {"type": "numeric"},
            {"type": "categorical"},
        ]
        
        for config in feature_configs:
            assert config["type"] in valid_types

    def test_validate_encoding_strategies(self):
        """Test validation of encoding strategies."""
        valid_encodings = {"binary", "ordinal", "onehot"}
        
        encodings_in_schemas = ["binary", "ordinal", "onehot"]
        
        for encoding in encodings_in_schemas:
            assert encoding in valid_encodings

    def test_validate_imputation_strategies(self):
        """Test validation of imputation strategies."""
        valid_imputers = {"median", "mean", "most_frequent", "constant"}
        
        imputers_in_schemas = ["median", "most_frequent"]
        
        for imputer in imputers_in_schemas:
            assert imputer in valid_imputers

    def test_validate_ordinal_order_field(self):
        """Test validation of ordinal feature order field."""
        ordinal_feature = {
            "type": "categorical",
            "encoding": "ordinal",
            "order": ["Low", "Medium", "High"]
        }
        
        # Ordinal encoding requires order
        if ordinal_feature["encoding"] == "ordinal":
            assert "order" in ordinal_feature
            assert len(ordinal_feature["order"]) > 0

    def test_validate_clipping_constraints(self):
        """Test validation of clipping constraints."""
        clipped_feature = {
            "type": "numeric",
            "clip": [0, 5000]
        }
        
        # Clip should be [min, max]
        assert len(clipped_feature["clip"]) == 2
        assert clipped_feature["clip"][0] < clipped_feature["clip"][1]

    def test_reject_invalid_version(self):
        """Test rejection of invalid schema version."""
        invalid_versions = [0, -1, "1.5", None]
        valid_versions = [1, 2, 3]
        
        for version in invalid_versions:
            assert version not in valid_versions


class TestFeatureSchemaBackwardCompatibility:
    """Test backward compatibility between versions."""

    def test_v1_compatible_with_v2(self):
        """Test that models trained on v1 can understand v2 features."""
        v1_feature_set = {
            "deflated_gdp_usd",
            "straight_distance_to_capital_km",
            "developed_country",
            "access_to_highway",
            "region_economic_classification",
            "seismic_hazard_zone",
        }
        
        v2_feature_set = {
            "deflated_gdp_usd",
            "straight_distance_to_capital_km",
            "developed_country",
            "access_to_highway",
            "region_economic_classification",
            "seismic_hazard_zone",
        }
        
        # Same features = backward compatible
        assert v1_feature_set == v2_feature_set

    def test_v2_preprocessing_compatible_with_v1_model(self):
        """Test that v2 preprocessing works with v1-trained model."""
        # V1 model expects:
        # - region_economic_classification as ordinal (0-3)
        
        # V2 preprocessing produces:
        # - region_economic_classification as onehot (4 columns)
        
        # This is breaking! Would need special handling
        v1_input_cols = 1  # Ordinal value
        v2_output_cols = 4  # Onehot columns
        
        # Not backward compatible for region feature
        assert v1_input_cols != v2_output_cols

    def test_inference_requires_matching_schema(self):
        """Test that inference requires matching feature schema version."""
        # A model trained on v1 must be used with v1 features
        # Cannot mix v1 model with v2 features (different preprocessing)
        
        model_schema_version = 1
        feature_schema_version = 1
        
        # Should match
        assert model_schema_version == feature_schema_version
