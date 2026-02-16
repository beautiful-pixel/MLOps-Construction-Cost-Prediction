import logging
import mlflow
from airflow.decorators import dag, task
import pendulum
from mlflow.tracking import MlflowClient


@dag(
    dag_id="mlflow_debug_dag",
    start_date=pendulum.today("UTC").add(days=-1),
    schedule=None,
    catchup=False,
    tags=["debug", "mlflow"],
)
def mlflow_debug_dag():

    @task
    def debug_mlflow():

        logging.info("=== MLflow Debug Start ===")

        # 1️⃣ Tracking URI
        tracking_uri = mlflow.get_tracking_uri()
        logging.info(f"Tracking URI: {tracking_uri}")

        # 2️⃣ Create temporary run
        with mlflow.start_run(run_name="debug_run") as run:

            run_id = run.info.run_id
            logging.info(f"Run ID: {run_id}")

            # Log simple param + metric
            mlflow.log_param("debug_param", 1)
            mlflow.log_metric("debug_metric", 0.123)

        # 3️⃣ Inspect artifact URI
        client = MlflowClient()
        run_info = client.get_run(run_id)

        logging.info(f"Artifact URI: {run_info.info.artifact_uri}")

        # 4️⃣ Try resolving model path (if exists)
        logging.info("=== MLflow Debug End ===")


    debug_mlflow()


mlflow_debug_dag()
