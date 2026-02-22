"""
Data Pipeline DAG.

Flow:
1. Check _READY
2. Ingest files
3. Preprocess batch
4. Update master
5. Notify success
6. Clean incoming
"""

from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
from datetime import timedelta
from pathlib import Path

from pipelines.data_pipeline.check_incoming import check_and_lock_ready
from pipelines.data_pipeline.ingestion import ingest_incoming_files
from pipelines.data_pipeline.preprocess import preprocess_batch
from pipelines.data_pipeline.clean_incoming import clean_incoming
from utils.data_versioning import dvc_add_raw, dvc_add_master
from utils.io import load_master_dataframe

from airflow.providers.slack.hooks.slack_webhook import SlackWebhookHook
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.models import Variable


def send_success_notification(metrics: dict) -> None:
    hook = SlackWebhookHook(slack_webhook_conn_id="slack_webhook")

    message = f"""
Data batch processed successfully

Batch ID: {metrics['batch_id']}

Data:
- Tabular files: {metrics['tabular_files']}
- Images moved (ingestion): {metrics['image_files']}
- Rows in batch: {metrics['rows_batch']}
- Rows added to master: {metrics['rows_added']}
- Images processed: {metrics['images_processed']}

Durations:
- Ingestion: {metrics['ingestion_duration']}s
- Preprocess: {metrics['preprocess_duration']}s
"""

    hook.send(text=message)



def slack_alert(context):
    hook = SlackWebhookHook(slack_webhook_conn_id="slack_webhook")

    exception = context.get("exception")
    task_id = context["task_instance"].task_id
    dag_id = context["dag"].dag_id

    message = f"""
Data pipeline failure

DAG: {dag_id}
Task: {task_id}

Error:
{exception}
"""

    hook.send(text=message)


DEFAULT_ARGS = {
    "owner": "mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "on_failure_callback": slack_alert,
}

@dag(
    dag_id="data_pipeline_dag",
    default_args=DEFAULT_ARGS,
    description="Ingestion + preprocessing pipeline",
    start_date=days_ago(1),
    schedule="*/5 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["data", "pipeline"],
)

def data_pipeline():

    @task.short_circuit
    def check_ready_task():
        ready = check_and_lock_ready()
        return ready

    @task
    def ingestion_task() -> dict:
        return ingest_incoming_files()

    @task
    def version_raw_task(ingestion_metrics: dict) -> dict:
        batch_id = ingestion_metrics["batch_id"]
        dvc_add_raw(batch_id)
        return ingestion_metrics

    @task
    def preprocess_task(ingestion_metrics: dict) -> dict:
        batch_id = ingestion_metrics["batch_id"]
        preprocess_metrics = preprocess_batch(batch_id)
        return {
            **ingestion_metrics,
            **preprocess_metrics,
        }

@task
def version_master_task(metrics: dict) -> dict:
    dvc_add_master()
    master_df = load_master_dataframe()
    current_master_rows = len(master_df)
    Variable.set(
        "CURRENT_MASTER_ROWS",
        str(current_master_rows),
    )
    return {
        **metrics,
        "current_master_rows": current_master_rows,
    }

    @task
    def validate_and_clean_incoming_task(metrics: dict):
        
        clean_incoming()

        processing_file = (
            Path(__file__).resolve().parents[3]
            / "data"
            / "incoming"
            / "_PROCESSING"
        )

        if processing_file.exists():
            processing_file.unlink()

        return metrics


    @task
    def notify_success_task(metrics: dict):

        send_success_notification(metrics)


    trigger_retrain = TriggerDagRunOperator(
        task_id="trigger_retrain_policy",
        trigger_dag_id="retrain_policy_dag",
        wait_for_completion=False,
    )

    # Task chain
    check = check_ready_task()

    ingested = ingestion_task()
    versioned_raw = version_raw_task(ingested)
    processed = preprocess_task(versioned_raw)
    versioned_master = version_master_task(processed)
    cleaned = validate_and_clean_incoming_task(versioned_master)
    notified = notify_success_task(cleaned)

    check >> ingested >> versioned_raw >> processed >> versioned_master >> cleaned >> notified >> trigger_retrain


dag = data_pipeline()