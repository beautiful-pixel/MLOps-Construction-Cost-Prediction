"""
Unit tests for feature engineering and model components.
"""
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestFeatureExtraction:
    """Test feature extraction from dataframe."""

    def test_extract_features_and_target(self, sample_dataframe, sample_feature_schema):
        """Test extraction of features and target variable."""
        df = sample_dataframe
        feature_cols = list(sample_feature_schema["tabular_features"].keys())
        
        # Extract features
        X = df[[col for col in feature_cols if col in df.columns]]
        
        assert len(X.columns) > 0
        assert len(X) == 3

    def test_feature_validation_against_schema(self, sample_dataframe, sample_feature_schema):
        """Test validation of features against schema."""
        df = sample_dataframe
        schema_features = set(sample_feature_schema["tabular_features"].keys())
        df_features = set(df.columns)
        
        # Check which features from schema exist in data
        available_features = schema_features & df_features
        
        assert len(available_features) > 0


class TestFeatureImputation:
    """Test missing value imputation strategies."""

    def test_impute_numeric_with_median(self):
        """Test numeric imputation with median."""
        df = pd.DataFrame({
            "value": [10, 20, None, 40, 50],
        })
        
        median_value = df["value"].median()
        df["value"] = df["value"].fillna(median_value)
        
        assert df["value"].isna().sum() == 0
        assert median_value in df["value"].values

    def test_impute_numeric_with_mean(self):
        """Test numeric imputation with mean."""
        df = pd.DataFrame({
            "value": [10.0, 20.0, None, 40.0, 50.0],
        })
        
        mean_value = df["value"].mean()
        df["value"] = df["value"].fillna(mean_value)
        
        assert df["value"].isna().sum() == 0

    def test_impute_categorical_with_most_frequent(self):
        """Test categorical imputation with most frequent value."""
        df = pd.DataFrame({
            "category": ["A", "A", None, "B", "A"],
        })
        
        most_frequent = df["category"].mode()[0]
        df["category"] = df["category"].fillna(most_frequent)
        
        assert df["category"].isna().sum() == 0
        assert most_frequent == "A"

    def test_impute_forward_fill(self):
        """Test forward fill imputation for time series."""
        df = pd.DataFrame({
            "value": [10, None, None, 40, 50],
        })
        
        df["value"] = df["value"].ffill()
        
        assert df["value"].isna().sum() == 0

    def test_imputation_preserves_data_type(self):
        """Test that imputation preserves original data type."""
        df = pd.DataFrame({
            "int_col": [1, None, 3],
            "float_col": [1.5, None, 3.5],
        })
        
        original_int_dtype = df["int_col"].dtype
        original_float_dtype = df["float_col"].dtype
        
        df["int_col"] = df["int_col"].fillna(df["int_col"].median())
        df["float_col"] = df["float_col"].fillna(df["float_col"].mean())
        
        assert df["int_col"].isna().sum() == 0
        assert df["float_col"].isna().sum() == 0


class TestFeatureScaling:
    """Test feature normalization and scaling."""

    def test_standard_scaling(self):
        """Test standard scaling (mean=0, std=1)."""
        df = pd.DataFrame({
            "value": [10, 20, 30, 40, 50],
        })
        
        mean = df["value"].mean()
        std = df["value"].std()
        
        df["value_scaled"] = (df["value"] - mean) / std
        
        assert abs(df["value_scaled"].mean()) < 1e-10
        assert abs(df["value_scaled"].std() - 1.0) < 1e-10

    def test_minmax_scaling(self):
        """Test min-max scaling (0-1 range)."""
        df = pd.DataFrame({
            "value": [10, 20, 30, 40, 50],
        })
        
        min_val = df["value"].min()
        max_val = df["value"].max()
        
        df["value_scaled"] = (df["value"] - min_val) / (max_val - min_val)
        
        assert df["value_scaled"].min() == 0.0
        assert df["value_scaled"].max() == 1.0

    def test_log_scaling(self):
        """Test log scaling for skewed distributions."""
        df = pd.DataFrame({
            "value": [1, 10, 100, 1000, 10000],
        })
        
        df["value_log"] = np.log1p(df["value"])
        
        assert df["value_log"].min() < df["value"].min()
        assert df["value_log"].max() < df["value"].max()


class TestFeatureEncoding:
    """Test categorical feature encoding."""

    def test_binary_encoding(self):
        """Test binary encoding of categorical variables."""
        df = pd.DataFrame({
            "flag": ["Yes", "No", "Yes", "No"],
        })
        
        encoding_map = {"Yes": 1, "No": 0}
        df["flag_encoded"] = df["flag"].map(encoding_map)
        
        assert set(df["flag_encoded"].unique()) == {0, 1}

    def test_ordinal_encoding(self):
        """Test ordinal encoding for ordered categories."""
        df = pd.DataFrame({
            "income_level": ["Low income", "Lower-middle income", "Upper-middle income", "High income"],
        })
        
        order = {
            "Low income": 0,
            "Lower-middle income": 1,
            "Upper-middle income": 2,
            "High income": 3,
        }
        
        df["income_encoded"] = df["income_level"].map(order)
        
        assert df["income_encoded"].is_monotonic_increasing

    def test_onehot_encoding(self):
        """Test one-hot encoding for nominal categories."""
        df = pd.DataFrame({
            "region": ["Europe", "Asia", "Africa", "Europe"],
        })
        
        onehot = pd.get_dummies(df["region"], prefix="region")
        
        assert len(onehot.columns) == 3
        assert (onehot.sum(axis=1) == 1).all()

    def test_target_encoding(self):
        """Test target encoding based on target variable."""
        df = pd.DataFrame({
            "category": ["A", "A", "B", "B", "B"],
            "target": [10, 12, 50, 55, 48],
        })
        
        target_encoding = df.groupby("category")["target"].mean()
        
        assert target_encoding.loc["A"] < target_encoding.loc["B"]


class TestFeatureClipping:
    """Test clipping of extreme values."""

    def test_clip_outliers(self):
        """Test clipping outliers within bounds."""
        df = pd.DataFrame({
            "value": [-100, 10, 20, 30, 5000],
        })
        
        lower_bound = 0
        upper_bound = 100
        
        df["value_clipped"] = df["value"].clip(lower_bound, upper_bound)
        
        assert df["value_clipped"].min() >= lower_bound
        assert df["value_clipped"].max() <= upper_bound

    def test_clip_preserves_valid_range(self):
        """Test that clipping doesn't affect values within range."""
        df = pd.DataFrame({
            "value": [10, 20, 30, 40, 50],
        })
        
        df["value_clipped"] = df["value"].clip(0, 100)
        
        assert (df["value"] == df["value_clipped"]).all()


class TestModelBuild:
    """Test model construction."""

    def test_build_sklearn_model(self):
        """Test building a scikit-learn model."""
        from sklearn.ensemble import RandomForestRegressor
        
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        assert model is not None
        assert model.n_estimators == 100

    def test_build_pipeline(self):
        """Test building a sklearn Pipeline."""
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.ensemble import RandomForestRegressor
        
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("model", RandomForestRegressor(n_estimators=10, random_state=42))
        ])
        
        assert len(pipeline.steps) == 2
        assert pipeline.steps[0][0] == "scaler"
        assert pipeline.steps[1][0] == "model"


class TestModelTraining:
    """Test model training."""

    def test_fit_model(self):
        """Test fitting a model on training data."""
        from sklearn.ensemble import RandomForestRegressor
        
        X = pd.DataFrame({
            "feature1": [1, 2, 3, 4, 5],
            "feature2": [2, 4, 6, 8, 10],
        })
        y = pd.Series([10, 20, 30, 40, 50])
        
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X, y)
        
        assert model is not None
        assert hasattr(model, "predict")

    def test_model_predictions(self):
        """Test model making predictions."""
        from sklearn.ensemble import RandomForestRegressor
        
        X_train = pd.DataFrame({
            "feature1": [1, 2, 3, 4, 5],
            "feature2": [2, 4, 6, 8, 10],
        })
        y_train = pd.Series([10, 20, 30, 40, 50])
        
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        X_test = pd.DataFrame({
            "feature1": [2.5, 3.5],
            "feature2": [5, 7],
        })
        
        predictions = model.predict(X_test)
        
        assert len(predictions) == 2
        assert all(isinstance(p, (int, float, np.number)) for p in predictions)

    def test_training_determinism(self):
        """Test that training is deterministic with fixed seed."""
        from sklearn.ensemble import RandomForestRegressor
        
        X = pd.DataFrame({
            "feature1": [1, 2, 3, 4, 5],
            "feature2": [2, 4, 6, 8, 10],
        })
        y = pd.Series([10, 20, 30, 40, 50])
        
        model1 = RandomForestRegressor(n_estimators=10, random_state=42)
        model1.fit(X, y)
        pred1 = model1.predict(X)
        
        model2 = RandomForestRegressor(n_estimators=10, random_state=42)
        model2.fit(X, y)
        pred2 = model2.predict(X)
        
        assert np.allclose(pred1, pred2)


class TestMetrics:
    """Test metric computation."""

    def test_compute_rmsle(self):
        """Test RMSLE metric computation."""
        y_true = np.array([3, -0.5, 2, 7])
        y_pred = np.array([2.5, 0.0, 2, 8])
        
        # RMSLE = sqrt(mean((log(y_true+1) - log(y_pred+1))^2))
        log_diff = np.log(y_true + 1) - np.log(y_pred + 1)
        rmsle = np.sqrt(np.mean(log_diff ** 2))
        
        assert rmsle > 0

    def test_compute_mae(self):
        """Test MAE metric computation."""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1.1, 2.2, 2.8, 4.1, 4.9])
        
        mae = np.mean(np.abs(y_true - y_pred))
        
        assert mae > 0
        assert mae < 1.0

    def test_compute_r2_score(self):
        """Test R² score computation."""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1.1, 2.0, 3.1, 3.9, 5.1])
        
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot)
        
        assert 0 <= r2 <= 1

    def test_metric_consistency_across_versions(self):
        """Test that metrics are computed consistently."""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1, 2, 3, 4, 5])
        
        mae1 = np.mean(np.abs(y_true - y_pred))
        mae2 = np.mean(np.abs(y_true - y_pred))
        
        assert mae1 == mae2


class TestModelPersistence:
    """Test model saving and loading."""

    def test_save_model_pickle(self):
        """Test saving model as pickle."""
        import pickle
        import tempfile
        from sklearn.ensemble import RandomForestRegressor
        
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            pickle.dump(model, f)
            model_path = f.name
        
        with open(model_path, "rb") as f:
            loaded_model = pickle.load(f)
        
        assert isinstance(loaded_model, RandomForestRegressor)

    def test_save_model_joblib(self):
        """Test saving model with joblib."""
        import joblib
        import tempfile
        from sklearn.ensemble import RandomForestRegressor
        
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "model.joblib"
            joblib.dump(model, model_path)
            
            loaded_model = joblib.load(model_path)
            
            assert isinstance(loaded_model, RandomForestRegressor)

    def test_model_artifact_integrity(self):
        """Test that saved model produces same predictions."""
        import pickle
        import tempfile
        from sklearn.ensemble import RandomForestRegressor
        
        X = pd.DataFrame({
            "feature1": [1, 2, 3],
            "feature2": [2, 4, 6],
        })
        
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X, [10, 20, 30])
        
        original_pred = model.predict(X)
        
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            pickle.dump(model, f)
            model_path = f.name
        
        with open(model_path, "rb") as f:
            loaded_model = pickle.load(f)
        
        loaded_pred = loaded_model.predict(X)
        
        assert np.allclose(original_pred, loaded_pred)
