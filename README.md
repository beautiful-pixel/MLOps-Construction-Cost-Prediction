# MLOps – Construction Cost Prediction  
### Multimodal Learning with Structured Data & Satellite Imagery (Solafune)

This project implements an end-to-end MLOps pipeline for the Construction Cost Prediction challenge (Solafune), combining structured tabular data and satellite imagery to predict construction costs.

The focus of this repository is not only on model performance, but on building a reproducible, scalable, and production-oriented machine learning system, covering the full lifecycle from data ingestion to monitoring in production.

---

## Project Objectives

### Machine Learning Objectives
- Predict construction costs using:
  - structured tabular features
  - satellite images
- Build a robust baseline model for multimodal learning
- Track and compare experiments reproducibly

### MLOps Objectives
- Design a modular and maintainable architecture
- Version data, models, and configurations
- Orchestrate workflows using Airflow
- Deploy models through a FastAPI inference service
- Monitor model performance and data drift
- Automate testing and CI pipelines

---

## Evaluation Metrics

The primary evaluation metric for this project is the **Root Mean Squared Logarithmic Error (RMSLE)**, which is the official metric of the Solafune Construction Cost Prediction challenge.

RMSLE is well suited for this task as it focuses on relative errors and is robust to large variations in construction costs.

In addition, the following complementary metrics are reported:

- **MAE (Mean Absolute Error)**  
  Used for interpretability and business relevance, as it represents the average absolute error in the original target scale.

- **R² (Coefficient of Determination)**  
  Reported as a complementary diagnostic metric to measure the proportion of variance explained by the model.

All metrics are logged and tracked using MLflow.

---

## Project Structure

    mlops_project/
    ├── dags/
    │   ├── ingestion_dag.py
    │   ├── preprocess_dag.py
    │   └── training_dag.py
    │
    ├── src/
    │   ├── data/
    │   │   ├── ingest.py
    │   │   ├── validate.py
    │   │   └── preprocess.py
    │   │
    │   ├── models/
    │   │   ├── train.py
    │   │   └── evaluate.py
    │   │
    │   └── inference/
    │       └── predict.py
    │
    ├── api/
    │   ├── inference_api/
    │   │   ├── Dockerfile
    │   │   ├── main.py
    │   │   └── requirements.txt
    │   │
    │   └── ensemble_api/
    │       ├── Dockerfile
    │       ├── main.py
    │       └── requirements.txt
    │
    ├── tests/
    │   ├── data/
    │   ├── models/
    │   ├── inference/
    │   └── api/
    │
    ├── monitoring/
    │   ├── prometheus/
    │   │   └── prometheus.yml
    │   ├── grafana/
    │   │   └── dashboards.json
    │   └── evidently/
    │       └── drift_report.py
    │
    ├── scripts/
    │   ├── run_ingestion.py
    │   ├── run_training.py
    │   └── run_evaluation.py
    │
    ├── data/
    │   ├── raw/
    │   │   ├── tabular/
    │   │   └── images/
    │   └── processed/
    │
    ├── models/
    ├── mlruns/
    │
    ├── docker/
    │   ├── Dockerfile.airflow
    │   ├── Dockerfile.mlflow
    │   └── docker-compose.yml
    │
    ├── configs/
    │   └── params.yaml
    │
    ├── .github/workflows/ci.yml
    ├── .env.example
    ├── requirements-base.txt
    ├── README.md
    └── .gitignore

---

## MLOps Pipeline Overview

### 1. Data Ingestion
- Detection of new datasets (structured + satellite images)
- Schema validation and integrity checks
- Raw data versioning using DVC

### 2. Preprocessing & Feature Engineering
- Cleaning and encoding of structured features
- Image preprocessing (resizing, normalization)
- Creation of multimodal training datasets

### 3. Model Training
- Train / validation / test split
- Multimodal model combining tabular and image features
- Experiment tracking with MLflow (metrics, parameters, artifacts)

### 4. Deployment
- FastAPI inference service
- Dockerized microservices
- Central orchestration API for inference and training triggers

### 5. Monitoring & Maintenance
- API and model monitoring with Prometheus and Grafana
- Data and prediction drift detection using Evidently
- Support for automated retraining pipelines

---

## Testing Strategy

The project includes unit tests covering:
- data validation and preprocessing,
- multimodal training and evaluation,
- inference logic,
- FastAPI endpoints.

Tests are automatically executed in the CI pipeline.

---

## Running the Project

### 1. Clone the repository
    git clone <repository_url>
    cd mlops_project

### 2. Configure environment variables
    cp .env.example .env

### 3. Start the services
    docker-compose up --build

Available services:
- Airflow (orchestration)
- MLflow (experiment tracking)
- FastAPI inference API
- Prometheus and Grafana (monitoring)

---

## Tech Stack

- Python
- scikit-learn / PyTorch
- Airflow
- MLflow
- FastAPI
- Docker and Docker Compose
- Prometheus and Grafana
- Evidently
- DVC
- GitHub Actions

---

## Notes

This project is designed with a strong focus on real-world MLOps practices, reproducibility, and maintainability.

The goal is not to maximize leaderboard performance, but to demonstrate a production-ready MLOps architecture for multimodal machine learning.

---

## License
This project is for educational and demonstration purposes.
