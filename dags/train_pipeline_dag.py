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
import pendulum

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook

from pipelines.train_pipeline.split import run_split_pipeline
from pipelines.train_pipeline.train import train_model
from pipelines.train_pipeline.evaluate import evaluate_model
from pipelines.train_pipeline.promote import promote_if_better

from utils.active_config import (
    get_default_split_version,
    get_default_feature_version,
    get_default_model_version,
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


# Slack success

def send_success_notification(metrics: dict) -> None:

    hook = SlackWebhookHook(slack_webhook_conn_id="slack_webhook")

    message = f"""
*Training pipeline completed successfully*

*Split version:* {metrics['split_version']}
*Feature version:* {metrics['feature_version']}
*Model version:* {metrics['model_version']}

*Master rows:* {metrics.get('master_rows')}
*Train rows:* {metrics.get('train_rows')}
*Reference rows:* {metrics.get('reference_rows')}
*Reference created:* {metrics.get('reference_created')}

*Split duration:* {metrics.get('split_duration')}s
*Training duration:* {metrics.get('training_duration')}s
*Evaluation duration:* {metrics.get('evaluation_duration')}s

*Train RMSE:* {metrics.get('train_rmse')}
*Reference RMSE:* {metrics.get('reference_rmse')}

*Promoted:* {metrics.get('promoted')}
*Candidate score:* {metrics.get('candidate_metric')}
*Production score:* {metrics.get('production_metric')}
*Delta:* {metrics.get('delta')}
*New model version:* {metrics.get('new_model_version')}
"""

    hook.send(text=message)


# Slack failure

def slack_alert(context):

    hook = SlackWebhookHook(slack_webhook_conn_id="slack_webhook")

    exception = context.get("exception")
    task_id = context["task_instance"].task_id
    dag_id = context["dag"].dag_id

    hook.send(
        text=f"""
*Training Pipeline Failure*

*DAG:* {dag_id}
*Task:* {task_id}

*Error:*
{exception}
"""
    )


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
    notify = notify_success_task(promoted_context)

    config >> run_info >> split_context >> versioned_context >> trained_context >> evaluated_context >> promoted_context >> notify


train_pipeline()