"""
Retrain policy DAG.

Triggered manually or by data_pipeline after successful ingestion.

Responsibilities:
- Retrieve production model configuration
- Find latest training run using same config
- Compare master_rows
- Notify if retrain triggered
- Trigger train_pipeline_dag if threshold exceeded
"""

import os
import logging
from typing import Dict, Optional

import pendulum
from airflow.decorators import dag, task
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook
from airflow.models import Variable
from airflow.exceptions import AirflowNotFoundException

from mlflow.tracking import MlflowClient

from registry.model_registry import get_production_run_id
from registry.run_metadata import get_run_config
from utils.mlflow_config import get_model_name



logger = logging.getLogger(__name__)


def get_threshold():
    return int(
        Variable.get("RETRAIN_THRESHOLD_ROWS", default_var=10)
    )

# Slack notification


def _try_send_slack(text: str) -> None:
    try:
        hook = SlackWebhookHook(slack_webhook_conn_id="slack_webhook")
        hook.send(text=text)
    except AirflowNotFoundException as exc:
        logger.warning("Slack connection not configured: %s", exc)
    except Exception:
        logger.exception("Slack webhook send failed")

def send_retrain_notification(decision: Dict) -> None:
    config = decision["config"]
    threshold = decision.get("threshold")

    message = f"""
Automatic retraining triggered

Model: {decision["model_name"]}

Config:
- Split version: {config["split_version"]}
- Feature version: {config["feature_version"]}
- Model version: {config["model_version"]}

Master rows: {decision["current_master_rows"]}
Last training master rows: {decision["last_master_rows"]}
New rows since last training: {decision["new_rows"]}
Threshold: {threshold}

Training pipeline launched.
"""

    _try_send_slack(message)


@dag(
    dag_id="retrain_policy_dag",
    start_date=pendulum.today("UTC").add(days=-1),
    schedule=None,
    catchup=False,
    tags=["training", "policy"],
)
def retrain_policy():

    # 1. Retrieve production configuration

    @task
    def get_production_context() -> Optional[Dict]:

        #model_name = os.getenv("MLFLOW_MODEL_NAME")
        model_name = get_model_name()

        prod_run_id = get_production_run_id(model_name)

        if prod_run_id is None:
            logger.info("No production model found.")
            return None

        prod_config = get_run_config(prod_run_id)

        return {
            "model_name": model_name,
            **prod_config,
        }

    # 2. Compute retrain decision

    @task
    def compute_retrain_decision(prod_context: Optional[Dict]) -> Dict:

        if prod_context is None:
            return {"should_retrain": False}

        client = MlflowClient()

        split_version = prod_context["split_version"]
        feature_version = prod_context["feature_version"]
        model_version = prod_context["model_version"]

        filter_string = (
            f"params.split_version = '{split_version}' and "
            f"params.feature_version = '{feature_version}' and "
            f"params.model_version = '{model_version}'"
        )

        runs = client.search_runs(
            experiment_ids=["0"],
            filter_string=filter_string,
            order_by=["attributes.start_time DESC"],
            max_results=1,
        )

        if not runs:
            last_master_rows = 0
        else:
            last_run = runs[0]
            last_master_rows = int(
                last_run.data.metrics.get("master_rows")
            )

        current_master_rows = int(Variable.get("CURRENT_MASTER_ROWS", default_var="0"))

        new_rows = current_master_rows - last_master_rows

        logger.info(
            f"Current master rows: {current_master_rows} | "
            f"Last training rows: {last_master_rows} | "
            f"New rows: {new_rows}"
        )

        threshold = get_threshold()
        should_retrain = new_rows > threshold

        return {
            "should_retrain": should_retrain,
            "model_name": prod_context["model_name"],
            "config": {
                "split_version": split_version,
                "feature_version": feature_version,
                "model_version": model_version,
            },
            "current_master_rows": current_master_rows,
            "last_master_rows": last_master_rows,
            "new_rows": new_rows,
            "threshold": threshold,
        }

    # 3. Boolean gate (ShortCircuit behavior)

    @task.short_circuit
    def should_trigger(decision: Dict) -> bool:
        return decision.get("should_retrain", False)

    # 4. Notify

    @task
    def notify(decision: Dict) -> Dict:
        send_retrain_notification(decision)
        return decision

    # 5. Trigger training DAG

    trigger_train = TriggerDagRunOperator(
        task_id="trigger_train_pipeline",
        trigger_dag_id="train_pipeline_dag",
        conf="{{ ti.xcom_pull(task_ids='compute_retrain_decision')['config'] | tojson }}",
        wait_for_completion=False,
    )

    prod_context = get_production_context()
    decision = compute_retrain_decision(prod_context)
    gate = should_trigger(decision)
    notified = notify(decision)

    prod_context >> decision >> gate >> notified >> trigger_train


dag = retrain_policy()