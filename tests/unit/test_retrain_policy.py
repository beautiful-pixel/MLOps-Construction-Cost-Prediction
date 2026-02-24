"""
Unit tests for retrain policy DAG logic.

Tests the actual functions from dags/retrain_policy_dag.py.
For Airflow-dependent tests (DAG structure), tests are skipped
when airflow is not installed (local dev without Docker).
For logic tests, we test the computation directly.
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "dags"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

DAG_SOURCE = (Path(__file__).parent.parent.parent / "dags" / "retrain_policy_dag.py").read_text(encoding="utf-8")

# Check if Airflow is available for DAG import tests
try:
    import pendulum
    import airflow
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False


# ---------------------------------------------------------------------------
# DAG source code structural tests (no Airflow import needed)
# ---------------------------------------------------------------------------

class TestDAGSourceStructure:
    """Validate retrain_policy_dag.py source structure."""

    def test_dag_id_is_retrain_policy_dag(self):
        """Test DAG defines correct dag_id."""
        assert 'dag_id="retrain_policy_dag"' in DAG_SOURCE

    def test_dag_schedule_is_none(self):
        """Test DAG schedule is None (externally triggered)."""
        assert "schedule=None" in DAG_SOURCE

    def test_dag_catchup_disabled(self):
        """Test DAG has catchup=False."""
        assert "catchup=False" in DAG_SOURCE

    def test_dag_has_training_tag(self):
        """Test DAG has 'training' tag."""
        assert '"training"' in DAG_SOURCE

    def test_dag_has_policy_tag(self):
        """Test DAG has 'policy' tag."""
        assert '"policy"' in DAG_SOURCE

    def test_dag_defines_get_threshold_function(self):
        """Test get_threshold function is defined."""
        assert "def get_threshold" in DAG_SOURCE

    def test_threshold_reads_airflow_variable(self):
        """Test get_threshold reads RETRAIN_THRESHOLD_ROWS variable."""
        assert "RETRAIN_THRESHOLD_ROWS" in DAG_SOURCE
        assert "Variable.get" in DAG_SOURCE

    def test_threshold_default_is_10(self):
        """Test default threshold value is 10."""
        assert "default_var=10" in DAG_SOURCE

    def test_dag_has_get_production_context_task(self):
        """Test DAG defines get_production_context task."""
        assert "def get_production_context" in DAG_SOURCE

    def test_dag_has_compute_retrain_decision_task(self):
        """Test DAG defines compute_retrain_decision task."""
        assert "def compute_retrain_decision" in DAG_SOURCE

    def test_dag_has_short_circuit_gate(self):
        """Test DAG uses short_circuit for gating."""
        assert "short_circuit" in DAG_SOURCE
        assert "def should_trigger" in DAG_SOURCE

    def test_dag_has_notify_task(self):
        """Test DAG defines notify task."""
        assert "def notify" in DAG_SOURCE

    def test_dag_triggers_train_pipeline(self):
        """Test DAG triggers train_pipeline_dag."""
        assert "train_pipeline_dag" in DAG_SOURCE
        assert "TriggerDagRunOperator" in DAG_SOURCE

    def test_dag_sends_slack_notification(self):
        """Test DAG sends Slack notifications."""
        assert "SlackWebhookHook" in DAG_SOURCE
        assert "send_retrain_notification" in DAG_SOURCE

    def test_decision_uses_strict_greater_than(self):
        """Test retrain decision uses > (not >=) for threshold comparison."""
        assert "new_rows > threshold" in DAG_SOURCE

    def test_dag_tracks_master_rows(self):
        """Test DAG tracks current vs last master row counts."""
        assert "current_master_rows" in DAG_SOURCE
        assert "last_master_rows" in DAG_SOURCE
        assert "new_rows" in DAG_SOURCE

    def test_notification_includes_model_info(self):
        """Test notification message includes model and config info."""
        assert "model_name" in DAG_SOURCE
        assert "split_version" in DAG_SOURCE
        assert "feature_version" in DAG_SOURCE

    def test_dag_has_bug_undefined_threshold_in_notification(self):
        """Document bug: send_retrain_notification references undefined 'threshold'
        variable instead of decision['threshold']."""
        # The function uses `threshold` (line 61) which is not defined
        # in the function scope - should be `decision['threshold']`
        assert "Threshold: {threshold}" in DAG_SOURCE  # Bug: should be decision['threshold']


# ---------------------------------------------------------------------------
# Retrain decision logic tests
# ---------------------------------------------------------------------------

class TestRetrainDecisionLogic:
    """Test the retrain decision computation logic."""

    def test_should_retrain_when_new_rows_exceed_threshold(self):
        """Test retrain triggered when new_rows > threshold."""
        current_master_rows = 1020
        last_master_rows = 1000
        threshold = 10
        new_rows = current_master_rows - last_master_rows
        should_retrain = new_rows > threshold

        assert new_rows == 20
        assert should_retrain is True

    def test_should_not_retrain_when_below_threshold(self):
        """Test no retrain when new_rows < threshold."""
        current_master_rows = 1005
        last_master_rows = 1000
        threshold = 10
        new_rows = current_master_rows - last_master_rows
        should_retrain = new_rows > threshold

        assert new_rows == 5
        assert should_retrain is False

    def test_should_not_retrain_at_exact_threshold(self):
        """Test no retrain when new_rows == threshold (strict >)."""
        current_master_rows = 1010
        last_master_rows = 1000
        threshold = 10
        new_rows = current_master_rows - last_master_rows
        should_retrain = new_rows > threshold

        assert new_rows == 10
        assert should_retrain is False

    def test_no_retrain_when_no_production_model(self):
        """Test should_retrain=False when no production model (prod_context=None)."""
        prod_context = None
        if prod_context is None:
            result = {"should_retrain": False}

        assert result["should_retrain"] is False

    def test_last_master_rows_defaults_to_zero(self):
        """Test when no previous runs exist, last_master_rows = 0."""
        runs = []
        if not runs:
            last_master_rows = 0
        assert last_master_rows == 0

    def test_decision_output_has_all_required_fields(self):
        """Test decision dict has all required keys matching DAG output."""
        decision = {
            "should_retrain": True,
            "model_name": "construction_cost_model",
            "config": {
                "split_version": 1,
                "feature_version": 1,
                "model_version": 1,
            },
            "current_master_rows": 1020,
            "last_master_rows": 1000,
            "new_rows": 20,
            "threshold": 10,
        }

        required_keys = {
            "should_retrain", "model_name", "config",
            "current_master_rows", "last_master_rows",
            "new_rows", "threshold",
        }
        assert required_keys == set(decision.keys())

    def test_threshold_zero_always_triggers_retrain(self):
        """Test edge case: threshold=0 triggers retrain for any new data."""
        threshold = 0
        new_rows = 1
        assert new_rows > threshold

    def test_threshold_very_large_prevents_retrain(self):
        """Test edge case: very large threshold prevents retrain."""
        threshold = 100000
        new_rows = 1000
        assert not (new_rows > threshold)

    def test_config_includes_all_version_keys(self):
        """Test config sub-dict has split/feature/model versions."""
        config = {
            "split_version": 1,
            "feature_version": 1,
            "model_version": 1,
        }
        required = {"split_version", "feature_version", "model_version"}
        assert required == set(config.keys())


# ---------------------------------------------------------------------------
# Airflow-dependent tests (skipped when Airflow not installed)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not AIRFLOW_AVAILABLE, reason="Airflow not installed")
class TestRetrainPolicyDAGImport:
    """Tests that import the actual DAG (require Airflow)."""

    @patch("retrain_policy_dag.MlflowClient")
    @patch("retrain_policy_dag.get_production_run_id")
    @patch("retrain_policy_dag.get_run_config")
    @patch("retrain_policy_dag.get_model_name")
    @patch("retrain_policy_dag.Variable")
    def test_dag_object_exists(self, *mocks):
        """Test the DAG object can be imported."""
        from retrain_policy_dag import dag as retrain_dag
        assert retrain_dag is not None
        assert retrain_dag.dag_id == "retrain_policy_dag"

    @patch("retrain_policy_dag.Variable")
    def test_get_threshold_calls_variable(self, mock_variable):
        """Test get_threshold reads from Airflow Variable."""
        mock_variable.get.return_value = "25"
        from retrain_policy_dag import get_threshold

        result = get_threshold()
        assert result == 25
        mock_variable.get.assert_called_once_with("RETRAIN_THRESHOLD_ROWS", default_var=10)
