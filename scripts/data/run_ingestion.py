"""
Ingestion step:
- Each CSV in incoming/ becomes its own batch
- Creates raw/<batch_id>/
- Moves file into batch folder
"""

from pipelines.data_pipeline.ingestion import ingest_incoming_files
from utils.logger import setup_logging

def main():
    batch_ids = ingest_incoming_files()
    print(f"Ingested batches: {batch_ids}")

if __name__ == "__main__":
    setup_logging("ingestion")
    main()
