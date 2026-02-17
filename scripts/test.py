from mlflow.tracking import MlflowClient
import mlflow
import time
from utils.mlflow_config import configure_mlflow

configure_mlflow()



run_id = "1b992cb54f994014b80bd6764884a88c"  # mets le vrai run_id

client = MlflowClient()

start = time.time()
run = client.get_run(run_id)
print("get_run:", time.time() - start)

artifact_uri = run.info.artifact_uri
print("Artifact URI:", artifact_uri)

# start = time.time()
# mlflow.artifacts.download_artifacts(f"runs:/{run_id}/model")
# print("download:", time.time() - start)
