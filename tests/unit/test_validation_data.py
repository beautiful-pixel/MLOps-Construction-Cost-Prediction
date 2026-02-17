import pytest
import pandas as pd

from data.data_contract import validate_dataframe

# Mock du data contract

@pytest.fixture
def mock_contract(monkeypatch):

    contract = {
        "columns": {
            "id": {
                "type": "int",
                "non_nullable": True,
            },
            "value": {
                "type": "float",
                "min": 0.0,
                "max": 10.0,
            },
            "category": {
                "type": "string",
                "allowed_values": ["A", "B"],
            },
        },
        "primary_key": ["id"],
    }

    monkeypatch.setattr(
        "data.data_contract.load_data_contract",
        lambda version: contract
    )

    return contract

# tests

def test_validate_dataframe_success(mock_contract):

    df = pd.DataFrame({
        "id": [1, 2],
        "value": [5.0, 7.5],
        "category": ["A", "B"],
    })

    validate_dataframe(df, data_contract_version=1)


def test_missing_column_raises(mock_contract):

    df = pd.DataFrame({
        "id": [1, 2],
        "value": [5.0, 7.5],
    })

    with pytest.raises(ValueError):
        validate_dataframe(df, 1)


def test_invalid_type_raises(mock_contract):

    df = pd.DataFrame({
        "id": ["1", "2"],  # should be int
        "value": [5.0, 7.5],
        "category": ["A", "B"],
    })

    with pytest.raises(TypeError):
        validate_dataframe(df, 1)


def test_value_below_min_raises(mock_contract):

    df = pd.DataFrame({
        "id": [1],
        "value": [-1.0],
        "category": ["A"],
    })

    with pytest.raises(ValueError):
        validate_dataframe(df, 1)


def test_duplicate_primary_key_raises(mock_contract):

    df = pd.DataFrame({
        "id": [1, 1],
        "value": [5.0, 6.0],
        "category": ["A", "B"],
    })

    with pytest.raises(ValueError):
        validate_dataframe(df, 1)

def test_empty_dataframe_raises(mock_contract):
    df = pd.DataFrame()
    with pytest.raises(ValueError):
        validate_dataframe(df, 1)
