from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

from src.training.train import train_model
from configs import load_params


def train_task():
    params = load_params("configs/params.yaml")
    train_model(**params["training"])


with DAG(
    dag_id="model_training",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
) as dag:
    train = PythonOperator(
        task_id="train_model",
        python_callable=train_task,
    )


# A mettre en place check_split_hash avec décision sur la suite à donner à prendre !

# check_split_hash  →  train_model  →  register_model
#         │
#         └── (si différent) → abort / branch / warning
