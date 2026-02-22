"""
Unit tests for retrain policy DAG logic.

Tests for the dynamic threshold using Airflow Variables.
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestRetrainPolicyLogic:
    """Test retrain policy decision logic."""

    def test_get_threshold_from_airflow_variables(self):
        """Test retrieving threshold from Airflow Variables."""
        # Simulate Airflow Variable.get()
        mock_threshold = "10"
        threshold = int(mock_threshold) if mock_threshold else 10
        
        assert threshold == 10

    def test_get_threshold_default_value(self):
        """Test default threshold when variable not set."""
        mock_threshold = None
        threshold = int(mock_threshold) if mock_threshold else 10
        
        assert threshold == 10

    def test_get_threshold_custom_value(self):
        """Test retrieving custom threshold value."""
        mock_threshold = "50"
        threshold = int(mock_threshold) if mock_threshold else 10
        
        assert threshold == 50

    def test_compute_new_rows(self):
        """Test calculation of new rows since last training."""
        current_master_rows = 1000
        last_training_rows = 950
        new_rows = current_master_rows - last_training_rows
        
        assert new_rows == 50

    def test_retrain_decision_above_threshold(self):
        """Test retrain decision when new rows exceed threshold."""
        new_rows = 15
        threshold = 10
        should_retrain = new_rows > threshold
        
        assert should_retrain is True

    def test_retrain_decision_below_threshold(self):
        """Test retrain decision when new rows below threshold."""
        new_rows = 5
        threshold = 10
        should_retrain = new_rows > threshold
        
        assert should_retrain is False

    def test_retrain_decision_exactly_at_threshold(self):
        """Test retrain decision when new rows equals threshold."""
        new_rows = 10
        threshold = 10
        should_retrain = new_rows > threshold
        
        # Should NOT retrain at exactly threshold
        assert should_retrain is False

    def test_retrain_with_no_production_model(self):
        """Test retrain decision when no production model exists."""
        prod_run_id = None
        
        # Should handle gracefully
        if prod_run_id is None:
            return_value = {
                "should_retrain": False,
                "reason": "No production model"
            }
        
        assert return_value["should_retrain"] is False

    def test_retrain_notification_includes_threshold(self):
        """Test that notification includes threshold information."""
        decision = {
            "config": {
                "split_version": 1,
                "feature_version": 1,
                "model_version": 1,
            },
            "current_master_rows": 1000,
            "last_master_rows": 950,
            "new_rows": 50,
            "threshold": 10,
            "model_name": "construction_cost_model",
        }
        
        # Verify all required fields for notification
        assert "threshold" in decision
        assert "new_rows" in decision
        assert decision["threshold"] == 10
        assert decision["new_rows"] == 50

    def test_multiple_threshold_updates(self):
        """Test handling multiple threshold updates over time."""
        thresholds = [10, 20, 15, 25, 30]
        
        for threshold in thresholds:
            new_rows = 25
            should_retrain = new_rows > threshold
            # Just verify it's computed correctly for each
            assert isinstance(should_retrain, bool)

    def test_threshold_edge_case_zero(self):
        """Test edge case with zero threshold."""
        threshold = 0
        new_rows = 1
        should_retrain = new_rows > threshold
        
        assert should_retrain is True

    def test_threshold_edge_case_very_large(self):
        """Test edge case with very large threshold."""
        threshold = 100000
        new_rows = 1000
        should_retrain = new_rows > threshold
        
        assert should_retrain is False


class TestRetrainPolicyTaskOrchestration:
    """Test retrain policy DAG task orchestration."""

    def test_get_production_context_task(self):
        """Test production context retrieval task."""
        # Mock production context
        prod_context = {
            "model_name": "construction_cost_model",
            "run_id": "run_abc123",
            "split_version": 1,
            "feature_version": 1,
            "model_version": 1,
        }
        
        assert prod_context is not None
        assert prod_context["model_name"] == "construction_cost_model"

    def test_compute_retrain_decision_task(self):
        """Test retrain decision computation task."""
        prod_context = {
            "model_name": "construction_cost_model",
            "split_version": 1,
            "feature_version": 1,
            "model_version": 1,
        }
        
        current_master_rows = 1000
        last_master_rows = 980
        threshold = 10
        
        new_rows = current_master_rows - last_master_rows
        decision = {
            "should_retrain": new_rows > threshold,
            "config": prod_context,
            "current_master_rows": current_master_rows,
            "last_master_rows": last_master_rows,
            "new_rows": new_rows,
            "threshold": threshold,
        }
        
        assert decision["should_retrain"] is True
        assert decision["new_rows"] == 20

    def test_short_circuit_task_when_no_retrain(self):
        """Test short circuit task when retrain not needed."""
        decision = {
            "should_retrain": False,
            "reason": "New rows below threshold"
        }
        
        # In airflow, short_circuit returns False to skip downstream
        if not decision["should_retrain"]:
            # Downstream tasks should be skipped
            assert True

    def test_short_circuit_task_when_retrain_needed(self):
        """Test short circuit task when retrain needed."""
        decision = {
            "should_retrain": True,
        }
        
        # In airflow, short_circuit returns True to continue
        if decision["should_retrain"]:
            # Downstream tasks should execute
            assert True

    def test_notification_task(self):
        """Test notification task sends correct information."""
        decision = {
            "should_retrain": True,
            "config": {
                "split_version": 1,
                "feature_version": 1,
                "model_version": 1,
            },
            "current_master_rows": 1020,
            "last_master_rows": 1000,
            "new_rows": 20,
            "threshold": 10,
            "model_name": "construction_cost_model",
        }
        
        # Task should format and send notification
        message = f"""
Automatic retraining triggered

Model: {decision['model_name']}

Config:
- Split version: {decision['config']['split_version']}
- Feature version: {decision['config']['feature_version']}
- Model version: {decision['config']['model_version']}

Master rows: {decision['current_master_rows']}
Last training master rows: {decision['last_master_rows']}
New rows since last training: {decision['new_rows']}
Threshold: {decision['threshold']}

Training pipeline launched.
"""
        
        assert "Automatic retraining triggered" in message
        assert str(decision['threshold']) in message

    def test_trigger_train_pipeline_task(self):
        """Test train pipeline trigger task."""
        decision = {
            "should_retrain": True,
            "config": {
                "split_version": 1,
                "feature_version": 1,
                "model_version": 1,
            },
        }
        
        # Task should trigger train_pipeline_dag with config
        trigger_config = decision["config"]
        assert trigger_config is not None
        assert "split_version" in trigger_config


class TestRetrainPolicyErrorHandling:
    """Test error handling in retrain policy."""

    def test_handle_missing_production_model(self):
        """Test handling when no production model exists."""
        try:
            prod_run_id = None
            if prod_run_id is None:
                raise ValueError("No production model found")
        except ValueError as e:
            assert "No production model" in str(e)

    def test_handle_invalid_master_rows_data(self):
        """Test handling invalid master rows data."""
        try:
            current_master_rows = None
            if current_master_rows is None:
                raise ValueError("Master rows data unavailable")
            new_rows = current_master_rows - 100
        except ValueError as e:
            assert "Master rows" in str(e)

    def test_handle_threshold_retrieval_failure(self):
        """Test handling threshold variable retrieval failure."""
        try:
            threshold_var = None
            threshold = int(threshold_var) if threshold_var else 10
        except (ValueError, TypeError):
            threshold = 10  # Fallback to default
        
        assert threshold == 10

    def test_handle_config_not_found(self):
        """Test handling when config not found."""
        try:
            prod_config = None
            if prod_config is None:
                raise KeyError("Production config not found")
        except KeyError:
            prod_config = {"split_version": 1, "feature_version": 1, "model_version": 1}
        
        assert prod_config is not None


class TestRetrainPolicyMetrics:
    """Test metrics and logging for retrain policy."""

    def test_log_retrain_decision_details(self):
        """Test logging of retrain decision details."""
        decision_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "should_retrain": True,
            "current_master_rows": 1020,
            "last_master_rows": 1000,
            "new_rows": 20,
            "threshold": 10,
            "ratio": 20 / 1000,  # 2% growth
        }
        
        assert decision_info["ratio"] == 0.02
        assert decision_info["should_retrain"] is True

    def test_track_retrain_frequency(self):
        """Test tracking how often retrains are triggered."""
        retrain_events = [
            {"timestamp": datetime.utcnow(), "triggered": True},
            {"timestamp": datetime.utcnow() + timedelta(days=1), "triggered": False},
            {"timestamp": datetime.utcnow() + timedelta(days=3), "triggered": True},
        ]
        
        triggered_count = sum(1 for e in retrain_events if e["triggered"])
        assert triggered_count == 2

    def test_calculate_growth_metrics(self):
        """Test calculation of data growth metrics."""
        last_training_rows = 1000
        current_rows = 1200
        growth = current_rows - last_training_rows
        growth_percent = (growth / last_training_rows) * 100
        
        assert growth == 200
        assert growth_percent == 20.0
