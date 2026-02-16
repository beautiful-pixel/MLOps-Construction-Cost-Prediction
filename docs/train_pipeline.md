# Training Pipeline – Technical Documentation

## 1. Overview

The training pipeline builds, evaluates, and conditionally promotes a machine learning model using fully versioned components.

It guarantees:

- Explicit configuration resolution  
- Deterministic dataset splitting  
- Controlled dataset versioning via DVC  
- Versioned feature and model definitions  
- Single MLflow run per pipeline execution  
- Reproducible training and evaluation  
- Safe production promotion logic  

The pipeline is designed for strict reproducibility and clear experiment lineage.

---

## 2. High-Level Flow

The pipeline executes sequentially:

resolve_config  
→ start_mlflow_run  
→ split_data  
→ version_split_data (DVC)  
→ train_model  
→ evaluate_model  
→ promote_model  

Each pipeline execution corresponds to exactly one MLflow run.

---

## 3. Configuration Resolution

Runtime configuration is resolved from:

- DAG runtime parameters (if provided)  
- Active default configuration  

Validated parameters:

- split_version  
- feature_version  
- model_version  

Strict validation ensures:

- The version exists  
- The version is allowed  
- No implicit fallback to unknown configuration  

If validation fails, the pipeline stops immediately.

---

## 4. MLflow Run Initialization

A single MLflow run is created at the beginning of the pipeline.

The run logs:

- split_version  
- feature_version  
- model_version  

All subsequent tasks attach to this same run using its run_id.

This ensures:

- Unified experiment traceability  
- No nested runs  
- Clear lineage across tasks  

---

## 5. Split Phase

The split phase:

- Loads the master dataset  
- Applies the versioned split schema  
- Enforces reference test immutability  
- Persists split artifacts  

### 5.1 Reference Test Handling

If the reference test already exists:

- It is loaded  
- It is never overwritten  

If it does not exist:

- It is created  
- It becomes frozen  
- It is stored permanently  

This guarantees a stable evaluation benchmark across experiments.

---

## 6. Atomic Split Persistence

Train and optional test datasets are written atomically.

Instead of:

```python
train_df.to_parquet(train_path)
```

The process is:

```python
tmp_path = train_path.with_suffix(".tmp")
train_df.to_parquet(tmp_path, index=False)
tmp_path.replace(train_path)
```

This prevents corruption in case of interruption.

Split directory structure:

    data/splits/v<split_version>/
        train.parquet
        optional_tests/

Reference tests:

    data/reference/tests/v<split_version>/
        test_reference.parquet

---

## 7. Split Versioning (DVC)

After split creation:

- The train split directory is versioned with DVC  
- The reference test is versioned only if newly created  

The MLflow run logs:

- Data lineage metadata  
- Version information  

This guarantees reproducibility of training inputs.

---

## 8. Training Phase

The training phase performs:

1. Feature schema loading (versioned YAML)  
2. Model schema loading (versioned YAML)  
3. Dataset validation  
4. Construction of full sklearn pipeline  
5. Model fitting  
6. Training metric logging  

Pipeline structure:

```python
Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        ("model", model),
    ]
)
```

The entire pipeline is logged to MLflow as a single artifact.

---

## 9. Evaluation Phase

The trained pipeline is reloaded from MLflow using:

```python
model_uri = f"runs:/{run_id}/model"
pipeline = mlflow.sklearn.load_model(model_uri)
```

Evaluation is performed on:

- Frozen reference test dataset  
- Optional test datasets  

Metrics are logged with prefixes:

- reference_<metric_name>  
- <optional_name>_<metric_name>  

The reference metric is used for promotion decisions.

---

## 10. Promotion Logic

The candidate model is compared against the current production model.

If:

- No production model exists → promote directly  
- Candidate metric is better → promote  
- Otherwise → keep current production  

Promotion steps:

```python
result = mlflow.register_model(model_uri, MODEL_NAME)

client.transition_model_version_stage(
    name=MODEL_NAME,
    version=result.version,
    stage="Production",
)
```

Promotion is deterministic and metric-driven.

---

## 11. Reproducibility Guarantees

The training pipeline is reproducible because:

- split_version is fixed  
- feature_version is fixed  
- model_version is fixed  
- Master dataset is versioned  
- Splits are versioned  
- Images are versioned  
- MLflow logs full lineage  

Re-running the pipeline with identical versions produces identical results.

---

## 12. Strictness Guarantees

The pipeline enforces:

- No unknown split version  
- No unknown feature version  
- No unknown model version  
- No empty training dataset  
- No modification of reference benchmark  
- No partial artifact logging  
- No silent promotion  

Any violation results in immediate failure.

---

## 13. Design Principles

Version-driven architecture  
All structural definitions are versioned.

Single-run experiment model  
One pipeline execution equals one MLflow run.

Immutable reference benchmark  
Ensures long-term evaluation consistency.

Deterministic promotion policy  
Production transition is rule-based and automatic.

Atomic persistence  
Critical artifacts are written atomically.

Separation of responsibilities  
Split, versioning, training, evaluation, and promotion are isolated tasks.
