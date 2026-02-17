"""
Data Pipeline DAG.

Flow:
1. Ingest CSV files from data/incoming/
2. Create raw batch folders
3. Preprocess batches
4. Update cumulative master dataset

This DAG is event-triggered or manual (schedule=None).
"""

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from datetime import timedelta

from pipelines.data_pipeline.ingestion import ingest_incoming_files
from pipelines.data_pipeline.preprocess import preprocess_batch
from pipelines.data_pipeline.clean_incoming import clean_incoming
from utils.data_versioning import dvc_add_raw, dvc_add_master, dvc_add_images

from airflow.decorators import task



DEFAULT_ARGS = {
    "owner": "mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


@dag(
    dag_id="data_pipeline_dag",
    default_args=DEFAULT_ARGS,
    description="Ingestion + preprocessing pipeline",
    start_date=days_ago(1),
    schedule=None,   # event-driven or manual
    catchup=False,
    tags=["data", "pipeline"],
)

def data_pipeline():

    @task
    def ingestion() -> str | None:
        """
        Ingest incoming files and return created batch ID.
        """
        return ingest_incoming_files()

    @task
    def version_raw(batch_id: str | None) -> str | None:
        """
        Snapshot raw dataset with DVC.
        """
        if batch_id:
            dvc_add_raw()
        return batch_id

    @task
    def preprocess(batch_id: str | None) -> bool:
        """
        Preprocess each batch and update master dataset.
        """
        if batch_id is None:
            return False

        preprocess_batch(batch_id)

        return True

    @task
    def version_master(preprocess_success: bool) -> bool:
        """
        Snapshot master dataset if it was updated.
        """
        if preprocess_success:
            dvc_add_master()
            return True

        return False

    @task
    def version_images(preprocess_success: bool) -> bool:
        """
        Snapshot images if preprocess was successful.
        """
        if preprocess_success:
            dvc_add_images()
            return True

        return False

    @task
    def validate_and_clean_incoming(preprocess_success: bool) -> None:
        """
        Remove empty incoming folders if preprocessing was successful.
        """
        if not preprocess_success:
            return

        clean_incoming()

        


    batch_id = ingestion()
    batch_id = version_raw(batch_id)

    preprocess_success = preprocess(batch_id)

    version_master(preprocess_success)
    version_images(preprocess_success)

    validate_and_clean_incoming(preprocess_success)


data_pipeline()






