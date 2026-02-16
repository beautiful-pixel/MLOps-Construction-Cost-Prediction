# Configuration Management

## 1. Overview

The project is configuration-driven.

All structural rules, feature definitions, dataset splits and model
parameters are defined in versioned YAML configuration files.

Pipeline modules do not hardcode configuration values.

Each configuration family is independently versioned and resolved
at orchestration level.

---

## 2. Active Configuration

The active configuration defines which version of each configuration
family is used during execution.

Example:

data_contract_version: 1

training_defaults:
  feature_version: 1
  split_version: 1
  model_version: 1

The active configuration:

- Does not define logic
- Does not define schema
- Does not define transformations

It only resolves versions.

Version resolution is performed at orchestration level and passed
explicitly to pipeline components.

---

## 3. Configuration Families

The project defines four configuration families:

- Data Contract
- Feature Configuration
- Split Configuration
- Model Configuration

Each family is versioned independently.

Configurations are stored under:

configs/
    data_contracts/
    features/
    splits/
    models/

Each version file is immutable once created.

# Data Contract

## 1. Purpose

The data contract defines the structural integrity of the dataset.

It acts as the single source of truth for:

- Dataset schema
- Column constraints
- External file linkage
- Primary key enforcement
- Deduplication behavior

All incoming data must strictly comply with the active data contract.

If validation fails, the pipeline stops immediately.

---

## 2. High-Level Structure

A data contract YAML file contains the following top-level fields:

version
tabular_extensions
image_extensions
columns
primary_key
deduplication

Example (simplified):

version: 1

tabular_extensions:
  - csv

image_extensions:
  - tif

columns:
  data_id:
    type: string
    non_nullable: true

primary_key:
  - data_id

deduplication:
  subset:
    - data_id
  keep: last

---

## 3. Tabular and Image Extensions

tabular_extensions

Defines which file extensions are accepted during ingestion
for tabular data.

image_extensions

Defines which file extensions are accepted for external files.

Any file with an unsupported extension will cause ingestion to fail.

---

## 4. Column Definitions

The columns section defines all allowed columns.

Each column can define:

type (required)
non_nullable (optional)
min (optional)
max (optional)
format (optional regex)
allowed_values (optional list)
external_file (optional nested definition)

Example:

year:
  type: int
  min: 1950
  max: 2100

This ensures that:

- The column exists
- The type matches
- Values fall within the allowed range

---

## 5. Column Type

Allowed types:

- string
- int
- float

Validation ensures pandas dtype compatibility.

---

## 6. Constraints

Optional constraints include:

non_nullable  
If true, null values are forbidden.

min / max  
Define numeric bounds.

allowed_values  
Restrict categorical values.

format  
Define a regex pattern that values must match exactly.

---

## 7. External File Definition

A column may reference an external file.

Example:

sentinel2_tiff_file_name:
  type: string
  format: '^sentinel_2_[\w\-]+\.tif$'
  external_file:
    type: image
    name: sentinel2
    bands: 12
    height: 1024
    width: 1024

external_file contains:

type  
Currently supported: image

name  
Defines canonical storage namespace.

bands  
Expected number of channels.

height  
Expected image height.

width  
Expected image width.

During preprocessing:

1. Referenced filenames are extracted from the dataframe.
2. Missing referenced files raise an error.
3. Unreferenced files raise an error.
4. Technical validation is performed.
5. Files are canonicalized under:

data/images/<name>/

6. A derived column <name>_relative_path is added.
The value represents a path relative to the data/ directory.

This guarantees strict consistency between tabular data and external storage.

---

## 8. Primary Key

primary_key defines row-level uniqueness.

Example:

primary_key:
  - data_id

Validation ensures:

- No null values
- No duplicates

---

## 9. Deduplication Rules

Deduplication is applied when merging batches into master.

Example:

deduplication:
  subset:
    - data_id
  keep: last

subset defines the uniqueness subset.
keep defines which duplicate is retained.

---

## 10. Design Principles

The data contract is:

- Versioned
- Immutable once released
- Strictly enforced
- Decoupled from pipeline logic

It ensures long-term structural stability of the dataset.
