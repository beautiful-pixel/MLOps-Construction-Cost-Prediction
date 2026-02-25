"""
Overview page - Project structure, pipeline architecture,
and deployment topology for the MLOps platform.
"""

import streamlit as st


st.set_page_config(page_title="Overview", layout="wide")
st.title("MLOps Platform Overview")

st.markdown(
    """
    End-to-end machine learning operations platform for
    **Construction Cost Prediction** (USD per m2).
    Built with versioned pipelines, experiment tracking,
    and automated model promotion.
    """
)

# ── Section 1: Project Structure ──────────────────────────────

with st.expander("1. Project Structure", expanded=False):
    st.code(
        r"""
mlops-project/
|
|-- api/                           # FastAPI microservices
|   |-- gateway_api/               #   Gateway API (port 8080)
|   |   |-- Dockerfile             #     Container build
|   |   |-- main.py                #     App entrypoint (router registration)
|   |   |-- core/config.py         #     JWT / auth settings
|   |   |-- routers/               #     Endpoint modules
|   |   |   |-- system.py          #       Health, info, status
|   |   |   |-- auth.py            #       Login / token management
|   |   |   |-- inference.py       #       Predict proxy
|   |   |   |-- experiments.py     #       MLflow experiments
|   |   |   |-- models.py          #       MLflow model registry
|   |   |   |-- training.py        #       Training triggers
|   |   |   |-- pipeline.py        #       Airflow DAG management
|   |   |   |-- features.py        #       Feature schema CRUD
|   |   |   |-- model_schemas.py   #       Model schema CRUD
|   |   |   |-- data_contract.py   #       Data contract viewer
|   |   |   +-- datasets.py        #       Dataset management
|   |   +-- services/              #     Business-logic layer
|   |       |-- airflow_client.py  #       Airflow REST wrapper
|   |       |-- mlflow_client.py   #       MLflow REST wrapper
|   |       |-- inference_client.py#       Inference REST wrapper
|   |       |-- config_service.py  #       YAML config loader
|   |       |-- dataset_service.py #       Dataset ops
|   |       |-- security.py        #       JWT + user auth
|   |       +-- system_service.py  #       Platform info
|   +-- inference_api/             #   Inference API (port 8000)
|       |-- Dockerfile
|       +-- main.py                #     Dynamic schema, predict, metrics
|
|-- src/                           #  Core ML library (installed as package)
|   |-- data/                      #    Data ingestion & validation
|   |   |-- data_contract.py       #      Schema validation engine
|   |   |-- merge.py               #      Master dataset builder
|   |   +-- linked_files.py        #      Satellite image linker
|   |-- features/                  #    Feature engineering
|   |   |-- feature_schema.py      #      Versioned feature definitions
|   |   +-- model_preprocessor.py  #      sklearn preprocessing pipeline
|   |-- models/                    #    Model management
|   |   |-- model_schema.py        #      Model config & factory
|   |   +-- loader.py              #      MLflow model loader
|   |-- inference/
|   |   +-- schema_builder.py      #      Dynamic Pydantic model builder
|   |-- registry/
|   |   |-- model_registry.py      #      MLflow registry utilities
|   |   +-- run_metadata.py        #      Run metrics / params reader
|   |-- splitting/
|   |   |-- split_schema.py        #      Split orchestration
|   |   +-- split_strategies.py    #      Geographic split logic
|   |-- pipelines/
|   |   |-- data_pipeline/
|   |   |   |-- check_incoming.py  #      Lock & ready detection
|   |   |   |-- ingestion.py       #      File ingestion & batching
|   |   |   |-- preprocess.py      #      Validation & preprocessing
|   |   |   +-- clean_incoming.py  #      Post-processing cleanup
|   |   +-- train_pipeline/
|   |       |-- split.py           #      Data splitting
|   |       |-- train.py           #      Model training
|   |       |-- evaluate.py        #      Model evaluation
|   |       +-- promote.py         #      Production promotion
|   |-- training/
|   |   +-- metrics.py             #      RMSLE, MAE, R2
|   +-- utils/                     #    Shared utilities
|       |-- active_config.py       #      Config loader
|       |-- mlflow_config.py       #      MLflow helpers
|       |-- data_versioning.py     #      DVC integration
|       |-- versioned_config.py    #      Version resolver
|       |-- io.py                  #      File I/O
|       +-- logger.py              #      Logging setup
|
|-- dags/                          #  Airflow DAGs
|   |-- data_pipeline_dag.py       #    Data ingestion pipeline
|   |-- train_pipeline_dag.py      #    Training pipeline
|   +-- retrain_policy_dag.py      #    Auto-retrain policy
|
|-- configs/                       #  Versioned YAML configs
|   |-- active_config.yaml         #    Active version selector
|   |-- data_contracts/v1.yaml     #    Column schema + rules
|   |-- features/v1.yaml, v2.yaml  #    Feature engineering configs
|   |-- models/v1.yaml, v2.yaml    #    Model hyperparameters
|   +-- splits/v1.yaml             #    Geographic split strategy
|
|-- frontend/                      #  Streamlit dashboard
|   |-- app.py                     #    Multi-page entrypoint
|   |-- streamlit_auth.py          #    Cookie-based auth
|   +-- pages/                     #    8 interactive pages
|
|-- deployments/                   #  Infrastructure
|   |-- k8s/                       #    Kubernetes manifests (14 files)
|   |-- airflow/Dockerfile.airflow
|   |-- mlflow/Dockerfile.mlflow
|   +-- streamlit/Dockerfile.streamlit
|
|-- data/                          #  Data storage (DVC versioned)
|   |-- incoming/                  #    New data landing zone
|   |-- raw/                       #    Archived raw batches
|   |-- processed/master.parquet   #    Cumulative validated dataset
|   |-- splits/v1/                 #    Train / test splits
|   +-- reference/tests/v1/        #    Frozen reference test set
|
|-- scripts/                       #  Standalone runners
|-- tests/                         #  Unit + integration tests
+-- mlflow_server/                 #  MLflow DB + artifacts
""",
        language=None,
    )


# ── Platform Services Topology ───────────────────────────────

st.subheader("Platform Services (High-Level)")

st.graphviz_chart(
    r"""
    digraph services_topology {
        rankdir=LR
        node [shape=box style="rounded,filled"
              fontname="Helvetica" fontsize=11]
        edge [fontname="Helvetica" fontsize=9]

        nginx      [label="Nginx\n(HTTPS Entry Point)" fillcolor="#e0e0e0"]
        streamlit  [label="Streamlit UI" fillcolor="#e8f4fd"]
        gateway    [label="Gateway API" fillcolor="#e8f0fe"]
        inference  [label="Inference API" fillcolor="#c8e6c9"]
        airflow    [label="Airflow" fillcolor="#bbdefb"]
        mlflow     [label="MLflow Registry" fillcolor="#fce4ec"]
        postgres   [label="PostgreSQL" fillcolor="#dcedc8"]
        prometheus [label="Prometheus" fillcolor="#c8e6c9"]
        grafana    [label="Grafana" fillcolor="#bbdefb"]

        nginx -> streamlit [label="/"]
        nginx -> gateway   [label="/api"]
        nginx -> grafana   [label="/grafana"]

        streamlit -> gateway

        gateway -> mlflow    [label="List runs"]
        gateway -> airflow   [label="Trigger training"]
        gateway -> inference [label="Predict"]

        inference -> mlflow [label="Load prod model" style=dashed]
        airflow -> mlflow   [label="Log \& register model"]
        airflow -> inference [label="Reload after promote" style=dashed]

        mlflow -> postgres

        prometheus -> gateway   [label="Scrape" style=dashed]
        prometheus -> inference [label="Scrape" style=dashed]
        grafana -> prometheus
    }
    """,
    use_container_width=False,
)


# ── Section 2: Pipeline Architecture ─────────────────────────

with st.expander("2. Pipeline Architecture", expanded=False):

    st.subheader("Data Pipeline DAG")
    st.caption("Triggered when new CSV / GeoTIFF files arrive in `data/incoming/`")
    st.graphviz_chart(
        """
        digraph data_pipeline {
            rankdir=LR
            node [shape=box style="rounded,filled" fillcolor="#e8f4fd"
                  fontname="Helvetica" fontsize=11]
            edge [fontname="Helvetica" fontsize=9]

            subgraph cluster_pipeline {
                label="Data Pipeline DAG"
                style=dashed
                color="#4a90d9"
                fontname="Helvetica"
                fontsize=12

                check  [label="check_incoming\\n(lock & ready gate)"]
                ingest [label="ingestion\\n(detect files, create batch)"]
                ver_raw [label="version_raw\\n(DVC snapshot)"]
                preprocess [label="preprocess\\n(contract validation\\ndeduplicate & merge)"]
                ver_master [label="version_master\\n(DVC snapshot)"]
                ver_images [label="version_images\\n(DVC snapshot)"]
                notify [label="notify\\n(Slack summary)"]
                clean  [label="clean_incoming\\n(remove processed files)"]

                check -> ingest
                ingest -> ver_raw
                ver_raw -> preprocess
                preprocess -> ver_master
                preprocess -> ver_images
                ver_master -> notify
                ver_images -> notify
                notify -> clean
            }

            incoming [shape=folder label="data/incoming/\\n(CSV + GeoTIFF)"
                      fillcolor="#fff3cd"]
            master   [shape=cylinder label="master.parquet"
                      fillcolor="#d4edda"]

            incoming -> check [style=dashed label="new files"]
            preprocess -> master [style=dashed label="append"]
        }
        """,
        use_container_width=True,
    )

    st.divider()

    st.subheader("Training Pipeline DAG")
    st.caption("Triggered manually or by the retrain policy")
    st.graphviz_chart(
        """
        digraph train_pipeline {
            rankdir=LR
            node [shape=box style="rounded,filled" fillcolor="#e8f0fe"
                  fontname="Helvetica" fontsize=11]
            edge [fontname="Helvetica" fontsize=9]

            subgraph cluster_pipeline {
                label="Training Pipeline DAG"
                style=dashed
                color="#4a90d9"
                fontname="Helvetica"
                fontsize=12

                resolve [label="resolve_config\\n(version selection)"]
                mlflow_run [label="start_mlflow_run\\n(create experiment)"]
                split [label="split_data\\n(geographic strategy)"]
                ver_splits [label="version_splits\\n(DVC snapshot)"]
                train [label="train_model\\n(sklearn Pipeline)"]
                evaluate [label="evaluate_model\\n(RMSLE / MAE / R2)"]
                promote [label="promote_model\\n(auto if better)"]

                resolve -> mlflow_run
                mlflow_run -> split
                split -> ver_splits
                ver_splits -> train
                train -> evaluate
                evaluate -> promote
            }

            master [shape=cylinder label="master.parquet"
                    fillcolor="#d4edda"]
            mlflow [shape=component label="MLflow\\n(registry)"
                    fillcolor="#fce4ec"]
            prod   [shape=box label="Production\\nModel"
                    fillcolor="#fff9c4" style="rounded,filled"]

            master -> split [style=dashed label="load"]
            train -> mlflow [style=dashed label="log metrics"]
            promote -> mlflow [style=dashed label="set alias"]
            promote -> prod [style=dashed label="if improved"]
        }
        """,
        use_container_width=True,
    )

    st.divider()

    st.subheader("Retrain Policy DAG")
    st.caption("Scheduled check for data growth; auto-triggers training")
    st.graphviz_chart(
        """
        digraph retrain_policy {
            rankdir=LR
            node [shape=box style="rounded,filled" fillcolor="#f3e5f5"
                  fontname="Helvetica" fontsize=11]
            edge [fontname="Helvetica" fontsize=9]

            subgraph cluster_policy {
                label="Retrain Policy DAG"
                style=dashed
                color="#7b1fa2"
                fontname="Helvetica"
                fontsize=12

                ctx    [label="get_production_context\\n(current model config)"]
                decide [label="compute_retrain_decision\\n(compare master rows\\nvs last training rows)"]
                gate   [label="should_trigger\\n(new_rows > threshold?)"]
                ntfy   [label="notify\\n(Slack notification)"]
                trig   [label="trigger train_pipeline\\n(pass config)"]

                ctx -> decide
                decide -> gate
                gate -> ntfy [label="yes"]
                gate -> skip [label="no"]
                ntfy -> trig
            }

            skip [shape=plaintext label="skip\\n(no action)"
                  fillcolor=white]
            train_dag [shape=component
                       label="Training\\nPipeline DAG"
                       fillcolor="#e8f0fe"]

            trig -> train_dag [style=dashed]
        }
        """,
        use_container_width=True,
    )


# ── Section 3: Inference Flow ────────────────────────────────

with st.expander("3. Inference Flow", expanded=False):
    st.graphviz_chart(
        """
        digraph inference_flow {
            rankdir=LR
            node [shape=box style="rounded,filled"
                  fontname="Helvetica" fontsize=11]
            edge [fontname="Helvetica" fontsize=9]

            browser [label="Browser" shape=ellipse fillcolor="#fff9c4"]
            nginx   [label="Nginx\\n(HTTPS)" fillcolor="#e0e0e0"]
            sl      [label="Streamlit\\n(form UI)" fillcolor="#e8f4fd"]
            gw      [label="Gateway API\\n(auth + proxy)" fillcolor="#e8f0fe"]
            inf     [label="Inference API\\n(model predict)" fillcolor="#c8e6c9"]
            mlflow  [label="MLflow\\n(load prod model)" fillcolor="#fce4ec"]
            result  [label="Prediction\\n(USD / m2)" shape=ellipse fillcolor="#fff9c4"]

            browser -> nginx [label="HTTPS"]
            nginx -> sl [label="port 8501"]
            sl -> gw [label="POST /predict"]
            gw -> inf [label="internal token"]
            inf -> mlflow [label="load model\\n(startup)" style=dashed]
            inf -> result [label="return"]
            result -> browser [style=dashed]
        }
        """,
        use_container_width=True,
    )


# ── Section 4: Deployment Architecture ───────────────────────

with st.expander("4. Deployment Architecture", expanded=False):
    st.subheader("K3s Cluster Topology (Single Node)")

    st.graphviz_chart(
        """
        digraph deployment {
            rankdir=LR
            compound=true
            node [shape=box style="rounded,filled"
                  fontname="Helvetica" fontsize=10]
            edge [fontname="Helvetica" fontsize=9]

            subgraph cluster_nginx {
                label="Nginx Reverse Proxy (HTTPS)"
                style=filled
                color="#e0e0e0"
                fillcolor="#f5f5f5"
                fontname="Helvetica"

                nginx [label="engineerai.space\\n(Let's Encrypt SSL)"
                       fillcolor="#e0e0e0"]
            }

            subgraph cluster_k3s {
                label="K3s Cluster  |  namespace: mlops"
                style=filled
                color="#1565c0"
                fillcolor="#e3f2fd"
                fontname="Helvetica"
                fontsize=12

                subgraph cluster_nodeport {
                    label="NodePort Services (external)"
                    style=dashed
                    color="#1976d2"

                    gw   [label="Gateway API\\n:8080 -> :30080"
                          fillcolor="#bbdefb"]
                    sl_k [label="Streamlit\\n:8501 -> :30501"
                          fillcolor="#bbdefb"]
                    gf   [label="Grafana\\n:3000 -> :30300"
                          fillcolor="#bbdefb"]
                }

                subgraph cluster_clusterip {
                    label="ClusterIP Services (internal)"
                    style=dashed
                    color="#42a5f5"

                    mlf  [label="MLflow\\n:5000"   fillcolor="#c8e6c9"]
                    af_w [label="Airflow Web\\n:8080" fillcolor="#c8e6c9"]
                    af_s [label="Airflow Sched"    fillcolor="#c8e6c9"]
                    inf  [label="Inference API\\n:8000" fillcolor="#c8e6c9"]
                    pg   [label="PostgreSQL\\n:5432" fillcolor="#c8e6c9"]
                    prom [label="Prometheus\\n:9090" fillcolor="#c8e6c9"]
                }

                subgraph cluster_storage {
                    label="Persistent Volumes"
                    style=dashed
                    color="#66bb6a"

                    pv_proj [label="project-pv  5Gi RWX\\n(shared data/configs)"
                             shape=folder fillcolor="#dcedc8"]
                    pv_pg   [label="postgres-pv  2Gi"
                             shape=folder fillcolor="#dcedc8"]
                    pv_mlf  [label="mlflow-pv  2Gi"
                             shape=folder fillcolor="#dcedc8"]
                    pv_af   [label="airflow-pv  2Gi"
                             shape=folder fillcolor="#dcedc8"]
                    pv_prom [label="prometheus-pv  2Gi"
                             shape=folder fillcolor="#dcedc8"]
                    pv_gf   [label="grafana-pv  1Gi"
                             shape=folder fillcolor="#dcedc8"]
                }
            }


            // Nginx routing
            nginx -> sl_k  [label="/  (port 30501)"]
            nginx -> gw     [label="/api/*  (port 30080)"]
            nginx -> gf     [label="/grafana/*  (port 30300)"]

            // Internal communication
            gw -> mlf  [label="experiments"]
            gw -> af_w [label="DAG mgmt"]
            gw -> inf  [label="predict"]
            af_s -> pg [label="metadata"]
            inf -> mlf [label="load model" style=dashed]
            prom -> gw [label="scrape /metrics" style=dashed]
            prom -> inf [label="scrape /metrics" style=dashed]
            gf -> prom [label="query"]

            // Storage bindings
            pg -> pv_pg [style=dotted arrowhead=none]
            mlf -> pv_mlf [style=dotted arrowhead=none]
            af_s -> pv_af [style=dotted arrowhead=none]
            af_w -> pv_af [style=dotted arrowhead=none]
            gw -> pv_proj [style=dotted arrowhead=none label="configs"]
            prom -> pv_prom [style=dotted arrowhead=none]
            gf -> pv_gf [style=dotted arrowhead=none]
        }
        """,
        use_container_width=True,
    )


# ── Section 5: Service Status Table ──────────────────────────

with st.expander("5. Service Summary", expanded=False):
    st.markdown(
        """
| Service | Port | Type | Role |
|---------|------|------|------|
| **Gateway API** | 8080 / 30080 | NodePort | Unified API gateway (auth, proxy) |
| **Inference API** | 8000 | ClusterIP | Model serving (dynamic schema) |
| **MLflow** | 5000 | ClusterIP | Experiment tracking & model registry |
| **Airflow Webserver** | 8080 | ClusterIP | DAG visualization |
| **Airflow Scheduler** | -- | ClusterIP | DAG execution |
| **PostgreSQL** | 5432 | ClusterIP | Airflow metadata store |
| **Prometheus** | 9090 | ClusterIP | Metrics collection |
| **Grafana** | 3000 / 30300 | NodePort | Monitoring dashboards |
| **Streamlit** | 8501 / 30501 | NodePort | Frontend dashboard |
        """
    )


# ── Section 6: Technology Stack ──────────────────────────────

with st.expander("6. Technology Stack", expanded=False):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            **ML & Data**
            - scikit-learn (GradientBoosting)
            - pandas / numpy
            - DVC (data versioning)
            - Parquet (storage format)
            """
        )

    with col2:
        st.markdown(
            """
            **Platform**
            - MLflow (tracking + registry)
            - Apache Airflow (orchestration)
            - FastAPI (microservices)
            - Streamlit (dashboard)
            """
        )

    with col3:
        st.markdown(
            """
            **Infrastructure**
            - K3s (Kubernetes)
            - Docker (containers)
            - PostgreSQL (metadata)
            - Prometheus + Grafana
            - Nginx (reverse proxy + SSL)
            """
        )


# ── Section 7: Configuration Strategy ────────────────────────

with st.expander("7. Configuration Strategy", expanded=False):
    st.markdown(
        """
        All ML strategies are managed through **versioned YAML files**
        under `configs/`. The active version is selected in
        `active_config.yaml` and can be overridden at training time.
        """
    )

    st.graphviz_chart(
        """
        digraph config_strategy {
            rankdir=LR
            node [shape=note style=filled fillcolor="#fff9c4"
                  fontname="Helvetica" fontsize=10]
            edge [fontname="Helvetica" fontsize=9]

            active [label="active_config.yaml\\n(version selector)"
                    fillcolor="#ffe0b2"]
            feat [label="features/\\nv1.yaml  v2.yaml"]
            model [label="models/\\nv1.yaml  v2.yaml"]
            split [label="splits/\\nv1.yaml"]
            contract [label="data_contracts/\\nv1.yaml"]

            active -> feat [label="feature_version"]
            active -> model [label="model_version"]
            active -> split [label="split_version"]
            active -> contract [label="data_contract_version"]
        }
        """,
        use_container_width=True,
    )

    st.markdown(
        """
        | Config | Current | Description |
        |--------|---------|-------------|
        | **Features** | v1 (12 tabular features), v2 (6 features, one-hot encoding) | Feature selection and encoding |
        | **Models** | v1 (GB 200 trees), v2 (GB 300 trees) | Algorithm and hyperparameters |
        | **Splits** | v1 (geographic: Japan + Philippines test) | Train/test split strategy |
        | **Data Contract** | v1 (30+ columns, types, ranges, regex) | Schema validation rules |
        """
    )
