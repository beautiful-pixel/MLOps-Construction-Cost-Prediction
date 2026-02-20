"""
Preprocess current batch only.

Steps:
1. Load raw CSV files for a given batch
2. Validate schema strictly (data contract)
3. Merge into cumulative master dataset
4. Save updated master
"""

import argparse
from pipelines.data_pipeline.preprocess import preprocess_batch
from utils.logger import setup_logging

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch-id",
        required=True,
        help="Batch ID to preprocess (folder name inside data/raw/)",
    )
    parser.add_argument(
        "--version",
        type=int,
        default=None,
        help="Data contract version to use (e.g. 1). If not specified, active version is used.",
    )

    args = parser.parse_args()

    preprocess_batch(
        batch_id=args.batch_id,
        data_contract_version=args.version,
    )


if __name__ == "__main__":
    setup_logging("preprocess")
    main()
