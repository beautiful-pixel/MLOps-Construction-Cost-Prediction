import argparse
import joblib
import mlflow
import pandas as pd
from pathlib import Path
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

from .metrics import compute_metrics


def load_data(path, target_col):
    df = pd.read_csv(path)
    X = df.drop(columns=[target_col])
    y = df[target_col]
    return X, y


def train(train_path, target_col, experiment_name, model_output):
    # On suppose qu'un run MLflow est DÉJÀ actif
    if mlflow.active_run() is None:
        raise RuntimeError(
            "No active MLflow run. train() must be called inside an active run."
        )

    X, y = load_data(train_path, target_col)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=4,
        random_state=42,
    )

    model.fit(X_train, y_train)

    # Predictions
    y_train_pred = model.predict(X_train)
    y_val_pred = model.predict(X_val)

    train_metrics = compute_metrics(y_train, y_train_pred)
    val_metrics = compute_metrics(y_val, y_val_pred)

    # --------------------
    # MLflow tracking ONLY
    # --------------------
    mlflow.log_params(
        {
            "model_type": "GradientBoostingRegressor",
            "n_estimators": 200,
            "learning_rate": 0.05,
            "max_depth": 4,
            "random_state": 42,
            "train_size": len(X_train),
            "val_size": len(X_val),
        }
    )

    for k, v in train_metrics.items():
        mlflow.log_metric(f"train_{k}", v)

    for k, v in val_metrics.items():
        mlflow.log_metric(f"val_{k}", v)

    # --------------------
    # Save model LOCALLY
    # --------------------
    model_output = Path(model_output)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_output)

    mlflow.sklearn.log_model(
        sk_model=model,
        name="model",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-path", required=True)
    parser.add_argument("--target-col", default="target")
    parser.add_argument("--experiment-name", default="solafune-poc")
    parser.add_argument("--model-output", default="models/model.joblib")

    args = parser.parse_args()

    # Mode CLI autonome
    mlflow.set_experiment(args.experiment_name)
    with mlflow.start_run(run_name="training_cli"):
        train(
            train_path=args.train_path,
            target_col=args.target_col,
            experiment_name=args.experiment_name,
            model_output=args.model_output,
        )
