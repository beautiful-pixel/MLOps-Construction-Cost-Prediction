import pytest
from unittest.mock import patch

# 1 Fixture MLflow mock

@pytest.fixture
def mock_mlflow():
    with patch("mlflow.start_run"), \
         patch("mlflow.log_param"), \
         patch("mlflow.log_metric"), \
         patch("mlflow.sklearn.log_model"):
        yield


# 2 Test : un run MLflow est créé

from src.training.train import train_model

def test_training_logs_mlflow(mock_mlflow, tmp_path):
    df = create_dummy_dataset(tmp_path)

    model = train_model(
        data_path=df,
        feature_set="S0",
        model_name="dummy",
        params={},
        target_col="y",
        location_col="loc",
        year_col="year",
        train_years=[2020],
        test_locations=["A"],
    )

    assert model is not None


# 3 Test : split hash loggué

@patch("mlflow.log_param")
def test_split_hash_logged(mock_log_param, mock_mlflow):
    train_model(...)

    keys = [call.args[0] for call in mock_log_param.call_args_list]
    assert "split_fingerprint" in keys
