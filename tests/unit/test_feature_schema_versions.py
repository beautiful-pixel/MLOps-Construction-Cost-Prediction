"""
Unit tests for feature schema versioning and validation.

Tests load ACTUAL feature schema YAML files and validate their structure,
content, and cross-version consistency.
"""
import sys
import os
from pathlib import Path
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Point CONFIG_ROOT to actual configs directory
CONFIGS_DIR = str(Path(__file__).parent.parent.parent / "configs")


@pytest.fixture(autouse=True)
def set_config_root(monkeypatch):
    """Ensure CONFIG_ROOT points to the project configs directory."""
    monkeypatch.setenv("CONFIG_ROOT", CONFIGS_DIR)


@pytest.fixture
def schema_v1():
    from features.feature_schema import load_feature_schema
    return load_feature_schema(1)


@pytest.fixture
def schema_v2():
    from features.feature_schema import load_feature_schema
    return load_feature_schema(2)


class TestFeatureSchemaV1:
    """Test feature schema version 1 loaded from actual YAML."""

    def test_v1_has_correct_version(self, schema_v1):
        """Test that v1 schema has version 1."""
        assert schema_v1["version"] == 1

    def test_v1_references_data_contract_v1(self, schema_v1):
        """Test that v1 schema references data contract v1."""
        assert schema_v1["data_contract"] == 1

    def test_v1_has_tabular_features(self, schema_v1):
        """Test v1 contains tabular_features key."""
        assert "tabular_features" in schema_v1
        assert len(schema_v1["tabular_features"]) > 0

    def test_v1_feature_list(self, schema_v1):
        """Test v1 contains the expected 6 features."""
        features = set(schema_v1["tabular_features"].keys())
        expected = {
            "deflated_gdp_usd",
            "straight_distance_to_capital_km",
            "developed_country",
            "access_to_highway",
            "region_economic_classification",
            "seismic_hazard_zone",
        }
        assert features == expected

    def test_v1_numeric_features_have_correct_type(self, schema_v1):
        """Test numeric features have type='numeric'."""
        numeric_features = ["deflated_gdp_usd", "straight_distance_to_capital_km"]
        for feat in numeric_features:
            assert schema_v1["tabular_features"][feat]["type"] == "numeric"

    def test_v1_categorical_features_have_encoding(self, schema_v1):
        """Test categorical features define an encoding strategy."""
        categorical = ["developed_country", "access_to_highway",
                       "region_economic_classification", "seismic_hazard_zone"]
        for feat in categorical:
            cfg = schema_v1["tabular_features"][feat]
            assert cfg["type"] == "categorical"
            assert "encoding" in cfg

    def test_v1_ordinal_features_have_order(self, schema_v1):
        """Test ordinal features define an order list."""
        ordinal_features = ["region_economic_classification", "seismic_hazard_zone"]
        for feat in ordinal_features:
            cfg = schema_v1["tabular_features"][feat]
            assert cfg["encoding"] == "ordinal"
            assert "order" in cfg
            assert isinstance(cfg["order"], list)
            assert len(cfg["order"]) > 1

    def test_v1_region_uses_ordinal(self, schema_v1):
        """Test v1 uses ordinal encoding for region_economic_classification."""
        assert schema_v1["tabular_features"]["region_economic_classification"]["encoding"] == "ordinal"

    def test_v1_clipping_constraint_on_distance(self, schema_v1):
        """Test clipping constraint on straight_distance_to_capital_km."""
        cfg = schema_v1["tabular_features"]["straight_distance_to_capital_km"]
        assert "clip" in cfg
        assert cfg["clip"][0] == 0
        assert cfg["clip"][1] == 5000

    def test_v1_all_features_have_impute(self, schema_v1):
        """Test all v1 features define an imputation strategy."""
        for feat, cfg in schema_v1["tabular_features"].items():
            assert "impute" in cfg, f"Feature '{feat}' missing 'impute'"


class TestFeatureSchemaV2:
    """Test feature schema version 2 loaded from actual YAML."""

    def test_v2_has_correct_version(self, schema_v2):
        """Test that v2 schema has version 2."""
        assert schema_v2["version"] == 2

    def test_v2_references_data_contract_v1(self, schema_v2):
        """Test v2 still references data contract v1."""
        assert schema_v2["data_contract"] == 1

    def test_v2_has_same_feature_count_as_v1(self, schema_v1, schema_v2):
        """Test v2 has same number of tabular features as v1."""
        v1_count = len(schema_v1["tabular_features"])
        v2_count = len(schema_v2["tabular_features"])
        assert v1_count == v2_count

    def test_v2_region_encoding_is_onehot(self, schema_v2):
        """Test that v2 uses onehot encoding for region_economic_classification."""
        assert schema_v2["tabular_features"]["region_economic_classification"]["encoding"] == "onehot"

    def test_v2_seismic_still_ordinal(self, schema_v2):
        """Test seismic_hazard_zone stays ordinal in v2."""
        assert schema_v2["tabular_features"]["seismic_hazard_zone"]["encoding"] == "ordinal"

    def test_v2_all_features_have_impute(self, schema_v2):
        """Test all v2 features define an imputation strategy."""
        for feat, cfg in schema_v2["tabular_features"].items():
            assert "impute" in cfg, f"Feature '{feat}' missing 'impute'"


class TestFeatureSchemaComparison:
    """Test comparison between v1 and v2 using actual loaded schemas."""

    def test_v1_v2_same_feature_set(self, schema_v1, schema_v2):
        """Test v1 and v2 share exactly the same feature names."""
        v1_features = set(schema_v1["tabular_features"].keys())
        v2_features = set(schema_v2["tabular_features"].keys())
        assert v1_features == v2_features

    def test_v1_v2_encoding_difference_only_in_region(self, schema_v1, schema_v2):
        """Test that v1 and v2 differ only in region_economic_classification encoding."""
        differences = []
        for feat in schema_v1["tabular_features"]:
            v1_enc = schema_v1["tabular_features"][feat].get("encoding")
            v2_enc = schema_v2["tabular_features"][feat].get("encoding")
            if v1_enc != v2_enc:
                differences.append(feat)

        assert differences == ["region_economic_classification"]

    def test_v1_v2_same_data_contract(self, schema_v1, schema_v2):
        """Test both versions reference the same data contract."""
        assert schema_v1["data_contract"] == schema_v2["data_contract"]


class TestFeatureSchemaValidation:
    """Test feature schema validation using actual project functions."""

    def test_validate_schema_structure_requires_keys(self):
        """Test that schema validation rejects missing required keys."""
        from features.feature_schema import validate_feature_schema_definition

        incomplete_schema = {"version": 1}

        with pytest.raises(ValueError, match="Missing required keys"):
            validate_feature_schema_definition(incomplete_schema)

    def test_validate_rejects_unknown_feature_type(self):
        """Test validation rejects invalid feature types."""
        from features.feature_schema import validate_feature_schema_definition

        schema = {
            "version": 99,
            "data_contract": 1,
            "tabular_features": {
                "deflated_gdp_usd": {
                    "type": "unknown_type",
                    "impute": "median",
                }
            },
        }

        with pytest.raises(ValueError, match="invalid type"):
            validate_feature_schema_definition(schema)

    def test_validate_rejects_ordinal_without_order(self):
        """Test validation rejects ordinal encoding without order list."""
        from features.feature_schema import validate_feature_schema_definition

        schema = {
            "version": 99,
            "data_contract": 1,
            "tabular_features": {
                "region_economic_classification": {
                    "type": "categorical",
                    "encoding": "ordinal",
                    "impute": "most_frequent",
                    # missing 'order'
                }
            },
        }

        with pytest.raises(ValueError, match="must define 'order'"):
            validate_feature_schema_definition(schema)

    def test_validate_rejects_categorical_without_encoding(self):
        """Test validation rejects categorical features without encoding."""
        from features.feature_schema import validate_feature_schema_definition

        schema = {
            "version": 99,
            "data_contract": 1,
            "tabular_features": {
                "developed_country": {
                    "type": "categorical",
                    "impute": "most_frequent",
                    # missing 'encoding'
                }
            },
        }

        with pytest.raises(ValueError, match="invalid encoding"):
            validate_feature_schema_definition(schema)

    def test_validate_rejects_target_in_schema(self):
        """Test validation rejects target column in feature schema."""
        from features.feature_schema import validate_feature_schema_definition

        schema = {
            "version": 99,
            "data_contract": 1,
            "tabular_features": {
                "deflated_gdp_usd": {"type": "numeric", "impute": "median"},
            },
            "target": "construction_cost_per_m2_usd",
        }

        with pytest.raises(ValueError, match="must not define 'target'"):
            validate_feature_schema_definition(schema)

    def test_validate_rejects_empty_features(self):
        """Test validation rejects schema with no features."""
        from features.feature_schema import validate_feature_schema_definition

        schema = {
            "version": 99,
            "data_contract": 1,
            "tabular_features": {},
        }

        with pytest.raises(ValueError, match="at least one tabular feature"):
            validate_feature_schema_definition(schema)


class TestFeatureSchemaFunctions:
    """Test feature_schema module utility functions."""

    def test_get_allowed_feature_versions(self):
        """Test listing available feature versions."""
        from features.feature_schema import get_allowed_feature_versions

        versions = get_allowed_feature_versions()
        assert isinstance(versions, list)
        assert 1 in versions
        assert 2 in versions

    def test_get_feature_columns_returns_list(self, schema_v1):
        """Test get_feature_columns returns feature names as list."""
        from features.feature_schema import get_feature_columns

        cols = get_feature_columns(schema_v1)
        assert isinstance(cols, list)
        assert len(cols) == 6
        assert "deflated_gdp_usd" in cols

    def test_get_feature_versions_for_contract(self):
        """Test filtering feature versions by contract version."""
        from features.feature_schema import get_feature_versions_for_contract

        versions = get_feature_versions_for_contract(1)
        assert 1 in versions
        assert 2 in versions

    def test_load_nonexistent_version_raises(self):
        """Test loading nonexistent version raises error."""
        from features.feature_schema import load_feature_schema

        with pytest.raises(ValueError, match="Unknown version"):
            load_feature_schema(9999)
