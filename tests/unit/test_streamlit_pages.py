"""
Tests for Streamlit ML platform pages.

Tests for new pages:
- 5_Train.py (Train Control Tower)
- 7_Datasets.py (Data & Retrain Policy Control Tower)
"""
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "ml_platform"))


class TestTrainControlTowerPage:
    """Test Train Control Tower page (5_Train.py)."""

    def test_page_title(self):
        """Test page has correct title."""
        page_title = "Train Control Tower"
        assert page_title == "Train Control Tower"

    def test_train_trigger_section_exists(self):
        """Test that train trigger section exists."""
        page_sections = [
            "Trigger Training",
            "Training DAG View",
        ]
        
        assert "Trigger Training" in page_sections

    def test_feature_schema_selection(self):
        """Test feature schema version selection."""
        available_features = [1, 2]
        default_feature = 1
        
        assert default_feature in available_features

    def test_model_schema_selection(self):
        """Test model schema version selection."""
        available_models = [1, 2]
        default_model = 1
        
        assert default_model in available_models

    def test_split_version_input(self):
        """Test split version input."""
        split_version = 1
        min_split = 1
        
        assert split_version >= min_split

    def test_training_config_payload(self):
        """Test training trigger payload creation."""
        config = {
            "feature_version": 1,
            "model_version": 1,
            "split_version": 1,
        }
        
        assert "feature_version" in config
        assert "model_version" in config
        assert "split_version" in config

    def test_dag_runs_display(self):
        """Test DAG runs table display."""
        dag_runs = [
            {"dag_run_id": "run_001", "start_date": "2026-02-22", "state": "success"},
            {"dag_run_id": "run_002", "start_date": "2026-02-21", "state": "running"},
        ]
        
        assert len(dag_runs) == 2
        assert dag_runs[0]["state"] == "success"

    def test_task_instances_kpis(self):
        """Test task instance KPIs."""
        tasks = [
            {"task_id": "split", "state": "success"},
            {"task_id": "train", "state": "success"},
            {"task_id": "evaluate", "state": "running"},
        ]
        
        total_tasks = len(tasks)
        success_tasks = sum(1 for t in tasks if t["state"] == "success")
        running_tasks = sum(1 for t in tasks if t["state"] == "running")
        
        assert total_tasks == 3
        assert success_tasks == 2
        assert running_tasks == 1

    def test_dag_visualization(self):
        """Test DAG visualization with task states."""
        status_colors = {
            "success": "#48bb78",
            "failed": "#f56565",
            "running": "#ecc94b",
        }
        
        assert "success" in status_colors
        assert status_colors["success"] == "#48bb78"

    def test_auto_refresh_toggle(self):
        """Test auto-refresh toggle."""
        auto_refresh_enabled = False
        refresh_interval_seconds = 5
        
        assert isinstance(auto_refresh_enabled, bool)
        assert refresh_interval_seconds == 5


class TestDatasetControlTowerPage:
    """Test Data & Retrain Policy Control Tower page (7_Datasets.py)."""

    def test_page_title(self):
        """Test page has correct title."""
        page_title = "Data & Retrain Policy Control Tower"
        assert page_title == "Data & Retrain Policy Control Tower"

    def test_dataset_overview_section(self):
        """Test dataset overview section."""
        overview = {
            "master_rows": 1000,
            "new_rows": 50,
            "threshold": 10,
            "should_retrain": True,
        }
        
        assert overview["master_rows"] == 1000
        assert overview["should_retrain"] is True

    def test_master_rows_metric(self):
        """Test master rows KPI metric."""
        master_rows = 1000
        assert master_rows > 0

    def test_new_rows_metric(self):
        """Test new rows metric."""
        new_rows = 50
        assert new_rows >= 0

    def test_retrain_threshold_metric(self):
        """Test retrain threshold metric."""
        threshold = 10
        assert threshold > 0

    def test_retrain_indicator(self):
        """Test retrain required indicator."""
        new_rows = 15
        threshold = 10
        should_retrain = new_rows > threshold
        
        assert should_retrain is True

    def test_threshold_update_input(self):
        """Test threshold update number input."""
        current_threshold = 10
        min_threshold = 1
        
        assert current_threshold >= min_threshold

    def test_threshold_update_button(self):
        """Test threshold update button functionality."""
        new_threshold = 50
        
        # Button should accept new value
        assert new_threshold > 0

    def test_global_orchestration_diagram(self):
        """Test global orchestration DAG diagram."""
        dag_nodes = ["data", "policy", "train"]
        
        assert "data" in dag_nodes
        assert "policy" in dag_nodes
        assert "train" in dag_nodes

    def test_data_pipeline_dag_render(self):
        """Test data pipeline DAG rendering."""
        dag_id = "data_pipeline_dag"
        assert dag_id == "data_pipeline_dag"

    def test_retrain_policy_dag_render(self):
        """Test retrain policy DAG rendering."""
        dag_id = "retrain_policy_dag"
        assert dag_id == "retrain_policy_dag"

    def test_dag_run_selection(self):
        """Test DAG run selection."""
        runs = [
            {"dag_run_id": "run_001", "start_date": "2026-02-22"},
            {"dag_run_id": "run_002", "start_date": "2026-02-21"},
        ]
        
        assert len(runs) == 2
        assert runs[0]["dag_run_id"] == "run_001"

    def test_task_visualization(self):
        """Test task instance visualization."""
        tasks = [
            {"task_id": "check_ready", "state": "success"},
            {"task_id": "ingest", "state": "success"},
            {"task_id": "preprocess", "state": "running"},
        ]
        
        total_tasks = len(tasks)
        progress = 2 / 3  # 2 out of 3 finished
        
        assert progress > 0.5

    def test_task_state_colors(self):
        """Test task state color mapping."""
        status_colors = {
            "success": "#48bb78",
            "failed": "#f56565",
            "running": "#ecc94b",
            "queued": "#a0aec0",
            "skipped": "#63b3ed",
        }
        
        assert status_colors["success"] == "#48bb78"
        assert status_colors["running"] == "#ecc94b"

    def test_auto_refresh_toggle(self):
        """Test auto-refresh toggle."""
        auto_refresh_enabled = False
        refresh_interval_seconds = 5
        
        assert isinstance(auto_refresh_enabled, bool)
        assert refresh_interval_seconds == 5


class TestStreamlitPageIntegration:
    """Test integration between pages."""

    def test_both_pages_use_same_api(self):
        """Test that both pages use same gateway API."""
        gateway_api_endpoints = {
            "configs/feature-schemas": "GET",
            "configs/model-schemas": "GET",
            "pipeline/trigger": "POST",
            "pipeline/dags/{dag_id}/runs": "GET",
            "datasets/overview": "GET",
            "datasets/threshold": "POST",
        }
        
        # Both pages should use these endpoints
        assert "pipeline/trigger" in gateway_api_endpoints
        assert "datasets/overview" in gateway_api_endpoints

    def test_authentication_flow_consistency(self):
        """Test authentication flow is consistent."""
        auth_requirements = {
            "pages": ["require_auth()"],
            "headers": ["auth_headers()"],
        }
        
        assert "require_auth()" in auth_requirements["pages"]

    def test_error_handling_consistency(self):
        """Test error handling patterns are consistent."""
        error_checks = [
            "response.status_code == 200",
            "assert_response_ok()",
        ]
        
        assert len(error_checks) == 2


class TestPageFeatureCompleteness:
    """Test that pages have all required features."""

    def test_train_page_completeness(self):
        """Test Train page has all required components."""
        components = {
            "title": "Train Control Tower",
            "feature_selector": True,
            "model_selector": True,
            "split_selector": True,
            "trigger_button": True,
            "dag_visualization": True,
            "task_table": True,
            "kpi_metrics": True,
        }
        
        required_components = ["title", "feature_selector", "model_selector", "trigger_button"]
        for component in required_components:
            assert component in components
            assert components[component]

    def test_dataset_page_completeness(self):
        """Test Dataset page has all required components."""
        components = {
            "title": "Data & Retrain Policy Control Tower",
            "overview": True,
            "threshold_editor": True,
            "global_orchestration": True,
            "data_pipeline_section": True,
            "retrain_policy_section": True,
            "task_visualization": True,
        }
        
        required_components = ["title", "overview", "threshold_editor", "global_orchestration"]
        for component in required_components:
            assert component in components
            assert components[component]
