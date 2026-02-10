import argparse
import joblib
import mlflow
import pandas as pd

from .metrics import compute_metrics


def load_data(path, target_col):
    df = pd.read_csv(path)
    X = df.drop(columns=[target_col])
    y = df[target_col]
    return X, y


def evaluate(model_path, test_path, target_col, experiment_name):
    # On suppose qu'un run MLflow est DÉJÀ actif
    if mlflow.active_run() is None:
        raise RuntimeError(
            "No active MLflow run. evaluate() must be called inside an active run."
        )

    model = joblib.load(model_path)
    X_test, y_test = load_data(test_path, target_col)

    y_pred = model.predict(X_test)
    metrics = compute_metrics(y_test, y_pred)

    for k, v in metrics.items():
        mlflow.log_metric(f"test_{k}", v)

    mlflow.log_param("test_size", len(X_test))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--test-path", required=True)
    parser.add_argument("--target-col", default="target")
    parser.add_argument("--experiment-name", default="solafune-poc")

    args = parser.parse_args()

    # Mode CLI autonome
    mlflow.set_experiment(args.experiment_name)
    with mlflow.start_run(run_name="evaluation_cli"):
        evaluate(
            model_path=args.model_path,
            test_path=args.test_path,
            target_col=args.target_col,
            experiment_name=args.experiment_name,
        )
