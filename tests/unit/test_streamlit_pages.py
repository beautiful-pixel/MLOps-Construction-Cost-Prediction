"""
Tests for Streamlit ML platform pages.

Validates page source code structure and shared utilities
(streamlit_auth module) by reading actual source files
and testing utility functions directly.

Note: Streamlit pages run as top-level scripts and are hard
to import directly. We test:
1. Source file structure (DAG IDs, API endpoints, required sections)
2. streamlit_auth utility functions (cookie encoding, auth headers)
"""
import sys
import os
from pathlib import Path
import pytest
import json
import base64
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "ml_platform"))

PAGES_DIR = Path(__file__).parent.parent.parent / "apps" / "ml_platform" / "pages"


# ---------------------------------------------------------------------------
# Source code structural validation
# ---------------------------------------------------------------------------

class TestTrainPageStructure:
    """Validate 6_Train.py source structure against requirements."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        self.source = (PAGES_DIR / "6_Train.py").read_text(encoding="utf-8")

    def test_page_imports_streamlit_auth(self):
        """Train page must use streamlit_auth for authentication."""
        assert "from streamlit_auth import" in self.source

    def test_page_calls_require_auth(self):
        """Train page must enforce authentication."""
        assert "require_auth()" in self.source

    def test_page_has_correct_title(self):
        """Train page must set the correct title."""
        assert 'st.title("Train Control Tower")' in self.source

    def test_page_uses_train_pipeline_dag(self):
        """Train page must reference the correct DAG ID."""
        assert '"train_pipeline_dag"' in self.source

    def test_page_has_feature_schema_selector(self):
        """Train page must have feature schema version selector."""
        assert "feature-schemas" in self.source
        assert "feature_version" in self.source

    def test_page_has_model_schema_selector(self):
        """Train page must have model schema version selector."""
        assert "model-schemas" in self.source
        assert "model_version" in self.source

    def test_page_has_split_version_input(self):
        """Train page must have split version input."""
        assert "split_version" in self.source
        assert "st.number_input" in self.source

    def test_page_has_trigger_button(self):
        """Train page must have a trigger training button."""
        assert "Trigger Training" in self.source
        assert "/pipeline/trigger" in self.source

    def test_page_displays_dag_runs(self):
        """Train page must fetch and display DAG runs."""
        assert "dag_runs" in self.source

    def test_page_shows_task_kpis(self):
        """Train page must show task success/running/failed KPIs."""
        assert 'state"] == "success"' in self.source or "success" in self.source
        assert "running" in self.source
        assert "failed" in self.source

    def test_page_has_dag_visualization(self):
        """Train page must render a graphviz DAG chart."""
        assert "graphviz" in self.source
        assert "st.graphviz_chart" in self.source

    def test_page_has_auto_refresh(self):
        """Train page must have auto-refresh toggle."""
        assert "auto_refresh" in self.source or "Auto refresh" in self.source

    def test_page_uses_status_colors(self):
        """Train page must define status-to-color mapping."""
        assert "#48bb78" in self.source  # success green
        assert "#f56565" in self.source  # failed red
        assert "#ecc94b" in self.source  # running yellow

    def test_page_sends_conf_with_trigger(self):
        """Train page must send config (feature/model/split versions) when triggering."""
        assert '"feature_version"' in self.source
        assert '"model_version"' in self.source
        assert '"split_version"' in self.source


class TestDatasetPageStructure:
    """Validate 3_Datasets.py source structure against requirements."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        self.source = (PAGES_DIR / "3_Datasets.py").read_text(encoding="utf-8")

    def test_page_imports_streamlit_auth(self):
        """Dataset page must use streamlit_auth for authentication."""
        assert "from streamlit_auth import" in self.source

    def test_page_calls_require_auth(self):
        """Dataset page must enforce authentication."""
        assert "require_auth()" in self.source

    def test_page_has_correct_title(self):
        """Dataset page must set the correct title."""
        assert "Data & Retrain Policy Control Tower" in self.source

    def test_page_references_both_dags(self):
        """Dataset page must reference both data_pipeline and retrain_policy DAGs."""
        assert '"data_pipeline_dag"' in self.source
        assert '"retrain_policy_dag"' in self.source

    def test_page_fetches_dataset_overview(self):
        """Dataset page must fetch dataset overview from API."""
        assert "/datasets/overview" in self.source

    def test_page_shows_master_rows_metric(self):
        """Dataset page must display master rows count."""
        assert "master_rows" in self.source

    def test_page_shows_new_rows_metric(self):
        """Dataset page must display new rows count."""
        assert "new_rows" in self.source

    def test_page_shows_threshold_metric(self):
        """Dataset page must display retrain threshold."""
        assert "threshold" in self.source

    def test_page_shows_retrain_indicator(self):
        """Dataset page must display retrain-required indicator."""
        assert "should_retrain" in self.source

    def test_page_has_threshold_update(self):
        """Dataset page must support updating the threshold."""
        assert "/datasets/threshold" in self.source
        assert "Update Threshold" in self.source

    def test_page_has_global_orchestration_diagram(self):
        """Dataset page must show global DAG orchestration."""
        assert "Global Orchestration" in self.source
        assert "Data Pipeline" in self.source
        assert "Retrain Policy" in self.source
        assert "Train Pipeline" in self.source

    def test_page_has_dag_visualization(self):
        """Dataset page must render graphviz charts."""
        assert "graphviz" in self.source
        assert "st.graphviz_chart" in self.source

    def test_page_has_auto_refresh(self):
        """Dataset page must have auto-refresh toggle."""
        assert "auto_refresh" in self.source or "Auto refresh" in self.source

    def test_page_uses_status_colors(self):
        """Dataset page must define status-to-color mapping."""
        assert "#48bb78" in self.source  # success
        assert "#f56565" in self.source  # failed
        assert "#ecc94b" in self.source  # running


# ---------------------------------------------------------------------------
# streamlit_auth utility function tests
# ---------------------------------------------------------------------------

class TestStreamlitAuthCookieEncoding:
    """Test cookie encoding/decoding functions from streamlit_auth."""

    def test_encode_cookie_payload(self):
        """Test cookie payload encoding produces valid base64."""
        from streamlit_auth import _encode_cookie_payload

        result = _encode_cookie_payload("test_token_123", "admin")
        # Should be valid base64
        decoded_bytes = base64.urlsafe_b64decode(result.encode("utf-8"))
        payload = json.loads(decoded_bytes)
        assert payload["token"] == "test_token_123"
        assert payload["username"] == "admin"

    def test_decode_cookie_payload_roundtrip(self):
        """Test encode -> decode produces original values."""
        from streamlit_auth import _encode_cookie_payload, _decode_cookie_payload

        encoded = _encode_cookie_payload("my_token", "my_user")
        decoded = _decode_cookie_payload(encoded)

        assert decoded is not None
        assert decoded["token"] == "my_token"
        assert decoded["username"] == "my_user"

    def test_decode_invalid_cookie_returns_none(self):
        """Test decoding invalid data returns None."""
        from streamlit_auth import _decode_cookie_payload

        assert _decode_cookie_payload("not_valid_base64!!!") is None

    def test_decode_empty_token_returns_none(self):
        """Test cookie with empty token returns None."""
        from streamlit_auth import _decode_cookie_payload

        # Create a cookie with empty token
        payload = json.dumps({"token": "", "username": "user"}).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("utf-8")
        assert _decode_cookie_payload(encoded) is None

    def test_encode_handles_none_username(self):
        """Test encoding with None username."""
        from streamlit_auth import _encode_cookie_payload, _decode_cookie_payload

        encoded = _encode_cookie_payload("token123", None)
        decoded = _decode_cookie_payload(encoded)
        assert decoded["token"] == "token123"
        assert decoded["username"] == ""


class TestAssertResponseOk:
    """Test the assert_response_ok utility."""

    @patch("streamlit_auth.st")
    def test_401_stops_with_auth_error(self, mock_st):
        """Test 401 response triggers auth error message."""
        from streamlit_auth import assert_response_ok

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_st.stop.side_effect = SystemExit
        with pytest.raises(SystemExit):
            assert_response_ok(mock_response)

        mock_st.error.assert_called_once()

    @patch("streamlit_auth.st")
    def test_403_admin_shows_admin_message(self, mock_st):
        """Test 403 with admin_only shows admin-specific message."""
        from streamlit_auth import assert_response_ok

        mock_response = MagicMock()
        mock_response.status_code = 403

        mock_st.stop.side_effect = SystemExit
        with pytest.raises(SystemExit):
            assert_response_ok(mock_response, admin_only=True)

        error_msg = mock_st.error.call_args[0][0]
        assert "Admin" in error_msg or "admin" in error_msg

    @patch("streamlit_auth.st")
    def test_200_does_not_stop(self, mock_st):
        """Test 200 response passes without error."""
        from streamlit_auth import assert_response_ok

        mock_response = MagicMock()
        mock_response.status_code = 200

        assert_response_ok(mock_response)
        mock_st.stop.assert_not_called()


class TestPageConsistency:
    """Cross-page consistency checks."""

    def test_both_pages_use_auth_headers(self):
        """Both pages must use auth_headers() for API calls."""
        train_src = (PAGES_DIR / "6_Train.py").read_text(encoding="utf-8")
        dataset_src = (PAGES_DIR / "3_Datasets.py").read_text(encoding="utf-8")

        assert "auth_headers()" in train_src
        assert "auth_headers()" in dataset_src

    def test_both_pages_use_assert_response_ok(self):
        """Both pages must validate API responses."""
        train_src = (PAGES_DIR / "6_Train.py").read_text(encoding="utf-8")
        dataset_src = (PAGES_DIR / "3_Datasets.py").read_text(encoding="utf-8")

        assert "assert_response_ok" in train_src
        assert "assert_response_ok" in dataset_src

    def test_both_pages_use_same_gateway_url(self):
        """Both pages must use get_gateway_api_url()."""
        train_src = (PAGES_DIR / "6_Train.py").read_text(encoding="utf-8")
        dataset_src = (PAGES_DIR / "3_Datasets.py").read_text(encoding="utf-8")

        assert "get_gateway_api_url()" in train_src
        assert "get_gateway_api_url()" in dataset_src

    def test_both_pages_consistent_status_colors(self):
        """Both pages must use same status color mapping."""
        train_src = (PAGES_DIR / "6_Train.py").read_text(encoding="utf-8")
        dataset_src = (PAGES_DIR / "3_Datasets.py").read_text(encoding="utf-8")

        # Both should define the same success/failed/running colors
        for color in ["#48bb78", "#f56565", "#ecc94b"]:
            assert color in train_src
            assert color in dataset_src
