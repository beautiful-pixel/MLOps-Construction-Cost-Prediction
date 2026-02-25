"""
Training pipeline DAG.

Flow:
1. Resolve configuration
2. Start MLflow run
3. Split dataset
4. Version splits
5. Train model
6. Evaluate model
7. Promote if better
8. Notify success
"""

import logging
import mlflow
import os
import pendulum
import json
import urllib.request
import urllib.error

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook
from airflow.exceptions import AirflowNotFoundException

from pipelines.train_pipeline.split import run_split_pipeline
from pipelines.train_pipeline.train import train_model
from pipelines.train_pipeline.evaluate import evaluate_model
from pipelines.train_pipeline.promote import promote_if_better

from utils.active_config import (
    get_default_split_version,
    get_default_feature_version,
    get_default_model_version,
    set_default_split_version,
    set_default_feature_version,
    set_default_model_version,
)

from splitting.split_schema import get_allowed_split_versions
from features.feature_schema import get_allowed_feature_versions
from models.model_schema import get_allowed_model_versions

from utils.data_versioning import (
    dvc_add_split,
    dvc_add_reference,
    get_data_lineage,
)

from utils.mlflow_config import configure_mlflow


logger = logging.getLogger(__name__)


def _reload_inference_service() -> dict:
    """Ask inference service to reload the production model (alias 'prod').

    Uses internal service-to-service token.
    Returns a small status payload; raises only on hard HTTP failures.
    """

    base_url = os.getenv("INFERENCE_API_URL", "http://inference-api:8000").rstrip("/")
    token = os.getenv("INFERENCE_INTERNAL_TOKEN")

    if not token:
        return {
            "reloaded": False,
            "reason": "INFERENCE_INTERNAL_TOKEN not configured",
        }

    url = f"{base_url}/reload"
    req = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        data=b"{}",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            payload = json.loads(body) if body else {}
            return {
                "reloaded": True,
                "status_code": resp.status,
                "payload": payload,
            }
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8") if exc.fp else ""
        raise RuntimeError(
            f"Inference reload failed (HTTP {exc.code}): {details}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Inference reload failed: {exc}") from exc


def _try_send_slack(text: str) -> None:
    try:
        hook = SlackWebhookHook(slack_webhook_conn_id="slack_webhook")
        hook.send(text=text)
    except AirflowNotFoundException as exc:
        logger.warning("Slack connection not configured: %s", exc)
    except Exception:
        logger.exception("Slack webhook send failed")


# Slack success

def send_success_notification(metrics: dict) -> None:
    message = f"""
Training pipeline completed successfully

Configuration:
- Split version: {metrics['split_version']}
- Feature version: {metrics['feature_version']}
- Model version: {metrics['model_version']}

Data:
- Master rows: {metrics.get('master_rows')}
- Train rows: {metrics.get('train_rows')}
- Reference rows: {metrics.get('reference_rows')}
- Reference created: {metrics.get('reference_created')}

Durations:
- Split: {metrics.get('split_duration')}s
- Training: {metrics.get('training_duration')}s
- Evaluation: {metrics.get('evaluation_duration')}s

Metrics:
- Train RMSLE: {metrics.get('train_rmlse')}
- Reference RMSLE: {metrics.get('reference_rmlse')}

Promotion:
- Promoted: {metrics.get('promoted')}
- Candidate score: {metrics.get('candidate_metric')}
- Production score: {metrics.get('production_metric')}
- Delta: {metrics.get('delta')}
- New model version: {metrics.get('new_model_version')}
"""

    _try_send_slack(message)


# Slack failure

def slack_alert(context):
    exception = context.get("exception")
    task_id = context["task_instance"].task_id
    dag_id = context["dag"].dag_id

    message = f"""
Training pipeline failure

DAG: {dag_id}
Task: {task_id}

Error:
{exception}
"""

    _try_send_slack(message)


@dag(
    dag_id="train_pipeline_dag",
    start_date=pendulum.today("UTC").add(days=-1),
    schedule=None,
    catchup=False,
    tags=["training", "ml"],
    default_args={"on_failure_callback": slack_alert},
)
def train_pipeline():

    # Resolve config

    @task
    def resolve_runtime_config():

        context = get_current_context()
        conf = context["dag_run"].conf or {}

        split_version = conf.get("split_version") or get_default_split_version()
        feature_version = conf.get("feature_version") or get_default_feature_version()
        model_version = conf.get("model_version") or get_default_model_version()

        if split_version not in get_allowed_split_versions():
            raise ValueError(f"Invalid split_version: {split_version}")

        if feature_version not in get_allowed_feature_versions():
            raise ValueError(f"Invalid feature_version: {feature_version}")

        if model_version not in get_allowed_model_versions():
            raise ValueError(f"Invalid model_version: {model_version}")

        logger.info(
            f"Resolved config → split={split_version}, "
            f"feature={feature_version}, model={model_version}"
        )

        return {
            "split_version": split_version,
            "feature_version": feature_version,
            "model_version": model_version,
        }

    # Start MLflow run

    @task
    def start_experiment_run(config: dict):

        configure_mlflow()

        with mlflow.start_run() as run:
            run_id = run.info.run_id
            mlflow.log_params(config)

        logger.info(f"Started MLflow run {run_id}")

        return {"run_id": run_id}

    # Split

    @task
    def split_task(config: dict, run_info: dict):

        split_output = run_split_pipeline(
            split_version=config["split_version"]
        )

        run_id = run_info["run_id"]

        configure_mlflow()

        with mlflow.start_run(run_id=run_id):
            mlflow.log_metrics(split_output["metrics"])
            mlflow.log_params(split_output["params"])

        return {
            **config,
            **split_output["metrics"],
            **split_output["params"],
        }

    # Version splits

    @task
    def version_splits(training_context: dict, run_info: dict):

        run_id = run_info["run_id"]
        split_version = training_context["split_version"]
        reference_created = training_context["reference_created"]

        configure_mlflow()

        with mlflow.start_run(run_id=run_id):

            dvc_add_split(split_version)

            if reference_created:
                dvc_add_reference(split_version)

            lineage = {
                k: v
                for k, v in get_data_lineage(split_version).items()
                if v is not None
            }

            if lineage:
                mlflow.log_params(lineage)

        return training_context

    # Train

    @task
    def train_task(training_context: dict, run_info: dict):

        train_metrics = train_model(
            run_id=run_info["run_id"],
            split_version=training_context["split_version"],
            feature_version=training_context["feature_version"],
            model_version=training_context["model_version"],
        )

        return {**training_context, **train_metrics}

    # Evaluate

    @task
    def evaluate_task(training_context: dict, run_info: dict):

        eval_metrics = evaluate_model(
            run_id=run_info["run_id"],
            split_version=training_context["split_version"],
            feature_version=training_context["feature_version"],
        )

        return {**training_context, **eval_metrics}

    # Promote

    @task
    def promote_task(training_context: dict, run_info: dict):

        run_id = run_info["run_id"]

        configure_mlflow()

        promotion_info = promote_if_better(run_id)

        with mlflow.start_run(run_id=run_id):
            mlflow.set_tag("pipeline_status", "completed")
            mlflow.set_tag("model_promoted", promotion_info["promoted"])

        return {**training_context, **promotion_info}

    # Persist promoted config as defaults

    @task
    def persist_promoted_defaults_task(training_context: dict) -> dict:
        """
        If the candidate model is promoted, persist the training config
        (split/feature/model versions) into configs/active_config.yaml
        so future runs without overrides use the promoted strategy.
        """

        if not training_context.get("promoted", False):
            return training_context

        split_version = int(training_context["split_version"])
        feature_version = int(training_context["feature_version"])
        model_version = int(training_context["model_version"])

        set_default_split_version(split_version)
        set_default_feature_version(feature_version)
        set_default_model_version(model_version)

        logger.info(
            "Active config defaults updated after promotion → split=%s, feature=%s, model=%s",
            split_version,
            feature_version,
            model_version,
        )

        return training_context


    @task
    def reload_inference_on_promotion_task(training_context: dict) -> dict:
        """Reload inference service only when a model has been promoted.

        This ensures the online API serves the new MLflow alias 'prod' without
        requiring a container restart.
        """

        if not training_context.get("promoted", False):
            return training_context

        try:
            result = _reload_inference_service()
            logger.info("Inference reload result: %s", result)
        except Exception:
            # Do not fail the training DAG on reload issues; promotion is already done.
            logger.exception("Inference reload after promotion failed")

        return training_context

    # Notify

    @task
    def notify_success_task(training_context: dict):
        send_success_notification(training_context)

    # DAG flow

    config = resolve_runtime_config()
    run_info = start_experiment_run(config)

    split_context = split_task(config, run_info)
    versioned_context = version_splits(split_context, run_info)

    trained_context = train_task(versioned_context, run_info)
    evaluated_context = evaluate_task(trained_context, run_info)

    promoted_context = promote_task(evaluated_context, run_info)

    persisted = persist_promoted_defaults_task(promoted_context)
    reloaded = reload_inference_on_promotion_task(persisted)
    notify = notify_success_task(reloaded)

    config >> run_info >> split_context >> versioned_context >> trained_context >> evaluated_context >> promoted_context >> persisted >> reloaded >> notify


train_pipeline()