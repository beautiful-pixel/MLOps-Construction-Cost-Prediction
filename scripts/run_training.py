import argparse
import subprocess
import logging
import mlflow
from pathlib import Path
import sys

# --- Project root & imports ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.training.train import train
from src.training.evaluate import evaluate
from src.logging.logging_config import setup_logging
from src.models.register import promote_if_better


# --- Paths ---
DATA_PREPROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

TRAIN_PATH = DATA_PREPROCESSED_DIR / "batch_1.csv"
TEST_PATH = DATA_PREPROCESSED_DIR / "batch_5.csv"
MODEL_PATH = MODELS_DIR / "model.joblib"


# --- Config ---
EXPERIMENT_NAME = "solafune-poc"
TARGET_COL = "construction_cost_per_m2_usd"
MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"


# def get_dvc_rev(path: str) -> str:
#     """
#     Retourne la révision DVC (hash) associée à un dossier ou fichier tracké.
#     """
#     result = subprocess.run(
#         ["dvc", "status", "-c", path],
#         capture_output=True,
#         text=True,
#         check=True,
#     )
#     return result.stdout.strip() or "clean"

import hashlib


def get_dvc_rev(dvc_file: str = "data/processed.dvc") -> str:
    """
    Retourne un hash stable du fichier .dvc représentant
    la version exacte des données utilisées.
    """
    path = Path(dvc_file)

    if not path.exists():
        logging.warning("DVC file not found: %s", dvc_file)
        return "no_dvc_file"

    if path.is_dir():
        raise ValueError(
            f"DVC path must be a file, got directory: {dvc_file}"
        )

    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:12]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dataset", required=True)
    parser.add_argument("--test-dataset", required=True)
    args = parser.parse_args()

    setup_logging("training")
    logging.info("=== Training pipeline started ===")

    train_path = DATA_PREPROCESSED_DIR / args.train_dataset
    test_path = DATA_PREPROCESSED_DIR / args.test_dataset

    if not train_path.exists():
        raise FileNotFoundError(train_path)
    if not test_path.exists():
        raise FileNotFoundError(test_path)

    try:
        MODELS_DIR.mkdir(exist_ok=True)

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)

        run_name = f"training_{args.train_dataset}_vs_{args.test_dataset}"

        with mlflow.start_run(run_name=run_name) as run:
            logging.info("MLflow run started | run_id=%s", run.info.run_id)
            logging.info(
                "Datasets | train=%s | test=%s",
                args.train_dataset,
                args.test_dataset,
            )

            mlflow.log_param("train_dataset", args.train_dataset)
            mlflow.log_param("test_dataset", args.test_dataset)

            dvc_rev = get_dvc_rev()
            mlflow.log_param("data_dvc_rev", dvc_rev)

            # Training
            train(
                train_path=train_path,
                target_col=TARGET_COL,
                experiment_name=EXPERIMENT_NAME,
                model_output=MODEL_PATH,
            )

            # Evaluation
            evaluate(
                model_path=MODEL_PATH,
                test_path=test_path,
                target_col=TARGET_COL,
                experiment_name=EXPERIMENT_NAME,
            )

            # Registry
            promote_if_better(
                run_id=run.info.run_id,
                train_dataset=args.train_dataset,
                test_dataset=args.test_dataset,
                data_dvc_rev=dvc_rev,
            )

    except Exception:
        logging.exception("Training pipeline failed")
        raise

    finally:
        logging.info("=== Training pipeline finished ===")


if __name__ == "__main__":
    main()