# Configuration Management

## 1. Overview

The project is fully configuration-driven.

All structural rules, feature definitions, dataset splitting strategies, and model hyperparameters are defined in immutable, versioned YAML files.

Configuration families are stored under:

    configs/
        data_contracts/
        features/
        splits/
        models/

Each configuration family:

- Is independently versioned
- Is immutable once released
- Is strictly validated by dedicated Python modules
- Contains no filesystem paths
- Is fully decoupled from environment variables
- Is resolved at orchestration level

The active configuration only resolves version numbers:

```yaml
data_contract_version: 1
training_defaults:
  feature_version: 2
  model_version: 1
  split_version: 1
```

The active configuration:
- Does not define logic
- Does not define schema
- Does not define transformations
- Only resolves which versions are used during execution

---

# 2. Data Contract

## 2.1 Purpose

The Data Contract defines the structural integrity of the master dataset.

It is the single source of truth for:

- Dataset schema
- Column constraints
- Primary key enforcement
- Deduplication rules
- External file linkage
- Target definition

All incoming data must strictly comply with the active data contract.  
If validation fails, the pipeline stops immediately.

---

## 2.2 High-Level Structure

Example:

```yaml
version: 1

tabular_extensions: ['csv']
image_extensions: ['tif']

columns:
  data_id:
    type: string
    non_nullable: true

  year:
    type: int
    min: 1950
    max: 2100

  developed_country:
    type: string
    allowed_values: ['Yes', 'No']

  sentinel2_tiff_file_name:
    type: string
    format: '^sentinel_2_[\w\-]+\.tif$'
    external_file:
      type: image
      name: sentinel2
      bands: 12
      height: 1024
      width: 1024

  construction_cost_per_m2_usd:
    type: float
    non_nullable: true
    min: 0

primary_key:
  - data_id

target: construction_cost_per_m2_usd

deduplication:
  subset:
    - data_id
  keep: last
```

---

## 2.3 Core Rules

### Structural Validation

- All declared columns must exist
- No unexpected columns if strict mode is enabled
- Type enforcement: `int`, `float`, `string`
- `min` / `max` validation
- `allowed_values` validation
- Regex format validation

### Target

- Mandatory
- Must exist in `columns`
- Must be `non_nullable`
- Cannot be part of the primary key
- Defined only in the data contract

### Primary Key

- No null values allowed
- No duplicates allowed
- Strict enforcement

### Deduplication

Used when merging batch data into master:

```yaml
deduplication:
  subset:
    - data_id
  keep: last
```

### External Files (Images)

Declared via `external_file`.

Enforced rules:

- Referenced files must exist
- Unreferenced files are rejected
- Technical validation (bands, height, width)
- Canonicalization under stable storage
- Automatic addition of `<name>_relative_path` column

All behavior is fully contract-driven.

---

# 3. Feature Configuration

## 3.1 Purpose

The Feature Schema defines:

- Which columns are used as model features
- Their ML type
- Imputation strategy
- Encoding strategy
- Optional clipping and scaling

It:

- Must reference a data contract
- Never defines the target
- Is strictly validated against the data contract
- Contains only transformation metadata (at the moment; may later include declarative feature engineering such as derived features from image bands).

---

## 3.2 Example

```yaml
version: 1
data_contract: 1

tabular_features:

  deflated_gdp_usd:
    type: numeric
    impute: median

  developed_country:
    type: categorical
    encoding: binary
    impute: most_frequent

  region_economic_classification:
    type: categorical
    encoding: ordinal
    order:
      - Low income
      - Lower-middle income
      - Upper-middle income
      - High income
    impute: most_frequent
```

---

## 3.3 Core Rules

### Contract Consistency

- All features must exist in the referenced data contract
- If a column is nullable in the contract → imputation is mandatory
- Target must not appear in the feature schema

### Supported Feature Types

- `numeric`
- `categorical`

Supported encodings:

- `binary`
- `ordinal`
- `onehot`

### Numeric Features

Support:

- imputation
- clipping
- scaling (`standard`, `minmax`)

### Categorical Features

- `binary` → ordinal encoding
- `ordinal` → ordered encoding with explicit category order
- `onehot` → one-hot encoding

Strict validation of allowed ordinal values is enforced.

---

# 4. Model Configuration

## 4.1 Purpose

The Model Schema defines:

- Model type
- Hyperparameters

It does not define:
- Features
- Preprocessing
- Data logic

---

## 4.2 Example

```yaml
version: 1

model:
  type: gradient_boosting
  params:
    n_estimators: 200
    learning_rate: 0.05
    max_depth: 4
    random_state: 42
```

---

## 4.3 Supported Models

- gradient_boosting
- random_forest
- ridge

Validation guarantees:

- Model type is supported
- Only valid parameters are allowed
- No extra keys are permitted
- Instantiation is deterministic

---

# 5. Split Configuration

## 5.1 Purpose

The Split Schema defines the evaluation strategy.

It guarantees:

- Reproducible dataset splitting
- Explicit evaluation protocol
- Frozen reference test sets
- Clean separation between configuration and split logic

---

## 5.2 Example

```yaml
version: 1
data_contract: 1

split_strategy: geographic

geographic_column: geolocation_name
periodic_column: year

test_localities:
  - 10000 Gunma
  - 20000 Nagano

reference_test_period:
  min: 2019
  max: 2020

moving_test_period:
  durations: [1]
```

---

## 5.3 Geographic Strategy

Implements:

- Train set = data outside `test_localities`
- Reference test set = selected localities within fixed period
- Additional moving test sets = recent rolling windows

---

# 6. Design Principles

### Strict Separation of Responsibilities

- Data Contract → dataset structure and target
- Feature Schema → feature definition and preprocessing metadata
- Split Schema → evaluation strategy
- Model Schema → model type and hyperparameters

### Immutability

Once a version is released:
- It never changes
- Full reproducibility is guaranteed

### Orchestration-Level Resolution

All version selection is centralized in the active configuration.

Pipeline components only receive resolved version numbers.

---

# 7. End-to-End Execution Flow

1. Validate dataset against Data Contract
2. Validate Feature Schema consistency
3. Generate dataset splits
4. Build preprocessing pipeline
5. Instantiate model
6. Train under fully versioned configuration

Each training run is fully reproducible and traceable
to an explicit set of configuration versions.