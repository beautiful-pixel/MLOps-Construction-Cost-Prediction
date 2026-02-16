# Data Pipeline – Technical Documentation

## 1. Overview

The data pipeline transforms raw incoming data into a validated and versioned master dataset.

It follows a strict, contract-driven architecture and guarantees:

- Structural validation of tabular data  
- Strict control of external files (e.g. satellite images)  
- Deterministic canonical storage of images  
- Atomic updates of the master dataset  
- Full dataset versioning using DVC  

The pipeline is designed to be reproducible, deterministic, and robust against inconsistent data.

---

## 2. High-Level Flow

The pipeline is executed as a sequence of tasks:

incoming  
→ ingestion  
→ raw batch creation  
→ raw versioning (DVC)  
→ preprocess  
→ master update  
→ master versioning (DVC)  
→ images versioning (DVC)  
→ clean incoming  

Only one batch is processed per pipeline run.

---

## 3. Storage Structure

```
data/
    incoming/
    raw/
        batch_<timestamp>/
            tabular/
            images/
    processed/
        master.parquet
    images/
        sentinel2/
        viirs/
```

- **incoming/**: temporary landing zone  
- **raw/**: immutable ingestion archive  
- **processed/**: cumulative validated dataset  
- **images/**: canonical storage of external files  

---

## 4. Ingestion Phase

The ingestion step performs the following operations:

1. Resolve the active data contract version.  
2. Detect tabular and image files recursively in `incoming/`.  
3. Validate that:
   - No unknown files are present  
   - Images are not ingested without tabular data  
4. Create a new batch directory under `raw/`.  
5. Move recognized files into:

```
raw/<batch_id>/tabular/
raw/<batch_id>/images/
```

If no files are found, ingestion returns `None`.

If any inconsistency is detected, the pipeline fails immediately (strict mode).

---

## 5. Raw Versioning

After ingestion, the raw directory is versioned using DVC.

This ensures that each batch arrival is traceable and reproducible.

Even if preprocessing later fails, the raw batch remains archived.

---

## 6. Preprocessing Phase

The preprocess phase is responsible for:

- Validating tabular files  
- Processing linked external files  
- Merging data into the master dataset  

### Step 1 – Tabular Validation

All tabular files in the batch are loaded and validated against the data contract.

Validation includes:

- Required columns  
- Data types  
- Constraints (min, max, regex, allowed values)  
- Primary key uniqueness  

### Step 2 – Linked Image Processing

If the contract declares external image files:

- Extract referenced filenames from the dataframe  
- Ensure no referenced file is missing  
- Ensure no unreferenced image exists in batch  
- Validate technical constraints (bands, height, width)  
- Canonicalize images into `data/images/<name>/`  
- Attach derived relative path columns  

This guarantees strict consistency between tabular data and external files.

### Step 3 – Merge into Master

The validated batch dataframe is merged into the cumulative master dataset using contract-defined deduplication rules.

### Step 4 – Atomic Write

The updated master dataset is written atomically:

```
write to temporary file
replace original master file
```

This prevents corruption in case of interruption.

---

## 7. Master and Image Versioning

If preprocessing succeeds:

- `master.parquet` is versioned with DVC  
- `data/images/` is versioned with DVC  

If no images changed, DVC detects no content modification.

---

## 8. Strictness Guarantees

The pipeline enforces the following invariants:

- No unknown files in incoming  
- No images without tabular data  
- No missing referenced images  
- No unreferenced images in batch  
- No schema violations  
- No primary key violations  
- No partial master writes  

Failure at any stage stops the pipeline immediately.

---

## 9. Reproducibility

The pipeline is reproducible because:

- Raw batches are archived and versioned  
- Master dataset is versioned  
- Images are canonicalized deterministically  
- The active data contract version is resolved explicitly  

Re-running a batch with the same contract version produces identical results.

---

## 10. Design Principles

**Contract-driven validation**  
All structural and technical rules are defined in versioned YAML contracts.

**Strict mode**  
The pipeline fails on any inconsistency rather than ignoring issues.

**Separation of responsibilities**  
Ingestion, preprocessing, versioning, and cleanup are separate tasks.

**Atomic writes**  
Critical datasets are written atomically to prevent corruption.

**Deterministic storage**  
External files are canonicalized to avoid naming collisions and ambiguity.
