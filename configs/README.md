# Configuration-Driven Strategy

This project uses a configuration-driven architecture to control
data validation, feature engineering, data splitting, and modeling strategies.

All strategies are defined via versioned YAML files.

This ensures:

- Reproducibility
- Clear experiment traceability
- Strategy evolution without modifying core code
- Compatibility with DVC and MLflow versioning

---

# Folder Structure

    configs/
    ├── active_config.yaml
    ├── data_contracts/
    ├── features/
    ├── models/
    └── splits/

Each configuration type is versioned independently.

---

# Active Configuration

active_config.yaml defines which versions are currently used by the pipeline.

    data_contract_version: 1
    default_feature_version: 1
    default_split_version: 1
    default_model_version: 1

Changing this file switches strategy versions without touching code.

---

# 1. Data Contracts

Data contracts define the expected dataset schema and validation rules.

They ensure:

- Schema validation
- Type safety
- Constraint enforcement
- Prevention of silent data drift

Example structure:

    version: 1

    columns:
      column_name:
        type: string | int | float
        non_nullable: true | false
        min: <number>
        max: <number>
        format: <regex>
        allowed_values: [...]

    primary_key:
      - column_name

    deduplication:
      subset:
        - column_name
      keep: last | first

Required fields:

- version
- columns
- type (for every column)

Optional constraints:

- non_nullable
- min
- max
- format
- allowed_values

Data contracts act as a formal agreement between data producers and the ML pipeline.

---

# 2. Feature Configuration

Feature configs define:

- Target variable
- Feature list
- Feature types
- Preprocessing strategy

Example structure:

    version: 1
    data_contract: 1
    target: target_column

    features:
      feature_name:
        type: numeric | categorical
        impute: median | mean | most_frequent
        encoding: binary | ordinal | onehot
        order: [...]
        clip: [min, max]

Required fields:

- version
- data_contract
- target
- features
- type (for each feature)

Numeric features may include:

- impute
- clip

Categorical features may include:

- encoding
- impute
- order (mandatory for ordinal encoding)

The structure is evolutive.
New preprocessing blocks (e.g., scaling, log transform) can be added
by extending the preprocessing module in src/.

---

# 3. Split Configuration

Split configs define how data is separated into train and test sets.

Example:

    version: 1
    data_contract: 1

    split_strategy: geographic

    geographic_column:
      - geolocation_name

    periodic_column:
      - year

    test_localities:
      - Example A
      - Example B

    reference_test_period:
      min: 2019
      max: 2020

    moving_test_period:
      durations: [1]

Supported strategy in v1:

- geographic

Future strategies could include:

- temporal
- random
- stratified

New strategies require adding a handler in src/ without changing the configuration philosophy.

---

# 4. Model Configuration

Model configs define:

- Model type
- Hyperparameters

Example:

    version: v1

    model:
      type: gradient_boosting

      params:
        n_estimators: 200
        learning_rate: 0.05
        max_depth: 4
        random_state: 42

Required:

- version
- model.type
- model.params

This ensures reproducibility and experiment traceability.

---

# Versioning Philosophy

Each config:

- Is versioned independently
- Is tracked in Git
- Is linked to DVC data version
- Is logged in MLflow during training

This guarantees full reproducibility of:

- Dataset version
- Feature engineering strategy
- Split strategy
- Model hyperparameters

---

# Future Improvement: Config Validation

A validation layer should ensure:

- Required fields exist
- Types are valid
- Referenced versions exist
- Feature columns exist in data contract

This can run:

- At pipeline start
- In CI
- Before training execution

---

# Architectural Philosophy

This project follows a Strategy-as-Configuration architecture.

All modeling logic is externalized into versioned YAML files.

This enables:

- Clean separation of concerns
- Experiment flexibility
- Safe strategy evolution
- Scalable MLOps workflows


# CI Proposal: Configuration Validation

## Objective

Prevent invalid configuration files from reaching:

- Training pipelines
- Production deployments
- MLflow experiment runs

---

## When Should Validation Run?

Validation should trigger when:

- A PR modifies files in configs/
- active_config.yaml changes
- A new version file is added

---

## Validation Layers

### 1. YAML Structure Validation

Ensure:

- Required fields exist
- Field types are correct
- Unsupported keys are rejected

Implementation options:

- Pydantic models
- jsonschema
- Custom validation functions

---

### 2. Cross-Reference Validation

Ensure:

- features.data_contract exists
- split.data_contract exists
- active_config references existing versions
- Feature columns exist in data contract

---

### 3. Logical Validation

Examples:

- Ordinal encoding requires order
- clip only allowed for numeric
- allowed_values only for categorical/string columns
- primary_key columns must exist

---

## Example GitHub Actions Workflow

    name: Validate Configurations

    on:
      pull_request:
        paths:
          - "configs/**"

    jobs:
      validate-config:
        runs-on: ubuntu-latest

        steps:
          - uses: actions/checkout@v3

          - name: Install dependencies
            run: pip install -r requirements.txt

          - name: Run config validation
            run: python -m src.validation.validate_configs

---

## Recommended Structure

    src/validation/
      ├── validate_data_contract.py
      ├── validate_features.py
      ├── validate_split.py
      ├── validate_model.py
      └── validate_configs.py

validate_configs.py orchestrates the full validation process.
