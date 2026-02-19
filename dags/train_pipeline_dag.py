import logging
import mlflow

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

import pendulum

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


@dag(
    dag_id="train_pipeline_dag",
    start_date=pendulum.today("UTC").add(days=-1),
    schedule=None,
    catchup=False,
    tags=["training", "ml"],
)
def train_pipeline():

    # Resolve runtime configuration

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

        logging.info(
            f"Resolved config → "
            f"split={split_version}, "
            f"feature={feature_version}, "
            f"model={model_version}"
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

        logging.info(f"Started MLflow run {run_id}")

        return {
            "run_id": run_id
        }

    # Data splitting

    @task
    def split_task(config: dict):

        reference_created = run_split_pipeline(
            split_version=config["split_version"]
        )

        return {
            "reference_created": reference_created
        }

    # Version splits and log lineage

    @task
    def version_splits(config: dict, run_info: dict, split_info: dict):

        run_id = run_info["run_id"]
        reference_created = split_info["reference_created"]

        configure_mlflow()

        with mlflow.start_run(run_id=run_id):

            dvc_add_split(config["split_version"])

            if reference_created:
                dvc_add_reference(config["split_version"])

            lineage = {
                k: v for k, v in get_data_lineage(config["split_version"]).items()
                if v is not None
            }
            if lineage:
                mlflow.log_params(lineage)

    # Train model

    @task
    def train_task(config: dict, run_info: dict):

        train_model(
            run_id=run_info["run_id"],
            **config,
        )

    # Evaluate model

    @task
    def evaluate_task(config: dict, run_info: dict):

        evaluate_model(
            run_id=run_info["run_id"],
            split_version=config["split_version"],
            feature_version=config["feature_version"],
        )

    # Promote model

    @task
    def promote_task(run_info: dict):

        run_id = run_info["run_id"]

        configure_mlflow()

        promote_if_better(run_id)

        with mlflow.start_run(run_id=run_id):
            mlflow.set_tag("pipeline_status", "completed")

    # DAG flow

    resolve_config = resolve_runtime_config()
    initialize_run = start_experiment_run(resolve_config)
    split_data = split_task(resolve_config)

    version_data = version_splits(resolve_config, initialize_run, split_data)

    train = train_task(resolve_config, initialize_run)
    evaluate = evaluate_task(resolve_config, initialize_run)
    promote_model = promote_task(initialize_run)

    resolve_config >> initialize_run >> split_data >> version_data >> train >> evaluate >> promote_model


train_pipeline()
