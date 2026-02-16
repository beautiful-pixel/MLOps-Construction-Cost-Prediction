import pandas as pd
from data.data_contract import load_data_contract


def merge_into_master(
    batch_df: pd.DataFrame,
    master_df: pd.DataFrame,
    data_contract_version: int,
) -> pd.DataFrame:
    """
    Merge batch into master dataset.
    Ensures column consistency.
    Removes duplicates if specified in data contract.
    """
    
    # Column consistency

    if set(batch_df.columns) != set(master_df.columns):
        raise ValueError(
            "Batch and master columns do not match. "
            f"Batch columns: {batch_df.columns.tolist()}, "
            f"Master columns: {master_df.columns.tolist()}"
        )


    # Merge

    merged = pd.concat([master_df, batch_df], ignore_index=True)


    # Deduplication

    data_contract = load_data_contract(data_contract_version)
    if "deduplication" in data_contract:
        params = data_contract["deduplication"]
        subset = params.get("subset", None)
        keep = params.get("keep", "last")
        merged = merged.drop_duplicates(subset=subset, keep=keep)


    return merged
