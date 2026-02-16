"""
Utilities for handling external files declared in the data contract.

This module manages:

- Detection of columns referencing external files
- Validation of referenced files
- Technical validation of images (bands, dimensions)
- Canonicalization into stable storage
- Attachment of canonical relative paths to dataframes

All operations are strictly contract-driven.
"""


from pathlib import Path
from typing import Dict, List
import shutil
import uuid

import pandas as pd

from data.data_contract import load_data_contract



def extract_external_file_columns(
    data_contract_version: int,
    file_type: str = "image",
) -> Dict[str, Dict]:
    """
    Return columns declaring external files of a given type.
    """

    contract = load_data_contract(data_contract_version)

    return {
        col: spec["external_file"]
        for col, spec in contract["columns"].items()
        if "external_file" in spec
        and spec["external_file"].get("type") == file_type
    }


def collect_linked_files_by_name(
    df: pd.DataFrame,
    available_files: List[str],
    data_contract_version: int,
) -> Dict[str, List[str]]:
    """
    Collect unique external filenames referenced in a dataframe.

    Raises an error if any referenced file is missing from the batch.
    """

    external_columns = extract_external_file_columns(
        data_contract_version,
        file_type="image",
    )

    available_set = set(available_files)
    result: Dict[str, set] = {}

    for col, rules in external_columns.items():

        if col not in df.columns:
            continue

        name = rules["name"]

        referenced_files = df[col].dropna().astype(str).unique()

        for filename in referenced_files:

            if filename not in available_set:
                raise ValueError(
                    f"Referenced file '{filename}' not found in batch."
                )

            result.setdefault(name, set()).add(filename)

    return {
        name: sorted(files)
        for name, files in result.items()
    }


def validate_image_files_technical(
    images_dir: Path,
    files_by_name: Dict[str, List[str]],
    data_contract_version: int,
) -> None:
    """
    Validate image technical constraints defined in the contract
    (bands, height, width).
    """

    import rasterio

    external_columns = extract_external_file_columns(
        data_contract_version,
        file_type="image",
    )

    rules_by_name = {
        rules["name"]: rules
        for rules in external_columns.values()
    }

    for name, filenames in files_by_name.items():

        rules = rules_by_name.get(name, {})

        expected_bands = rules.get("bands")
        expected_height = rules.get("height")
        expected_width = rules.get("width")

        for filename in filenames:

            path = images_dir / filename

            with rasterio.open(path) as src:

                if expected_bands is not None and src.count != expected_bands:
                    raise ValueError(
                        f"{filename}: invalid band count "
                        f"(expected {expected_bands}, got {src.count})"
                    )

                if expected_height is not None and src.height != expected_height:
                    raise ValueError(
                        f"{filename}: invalid height "
                        f"(expected {expected_height}, got {src.height})"
                    )

                if expected_width is not None and src.width != expected_width:
                    raise ValueError(
                        f"{filename}: invalid width "
                        f"(expected {expected_width}, got {src.width})"
                    )


def canonicalize_linked_images(
    images_dir: Path,
    images_root: Path,
    files_by_name: Dict[str, List[str]],
    use_hardlink: bool = True,
) -> Dict[str, Dict[str, str]]:
    """
    Canonicalize images into stable storage under images_root.

    Files are renamed using UUIDs to prevent collisions.
    Returns a mapping from original filename to canonical path.
    """

    mapping: Dict[str, Dict[str, str]] = {}

    for name, filenames in files_by_name.items():

        dest_dir = images_root / name
        dest_dir.mkdir(parents=True, exist_ok=True)

        mapping[name] = {}

        for filename in filenames:

            src_path = images_dir / filename

            new_name = f"{uuid.uuid4().hex}.tif"
            dest_path = dest_dir / new_name

            if use_hardlink:
                try:
                    dest_path.hardlink_to(src_path)
                except Exception:
                    shutil.copy2(src_path, dest_path)
            else:
                shutil.copy2(src_path, dest_path)

            relative_path = str(Path("images") / name / new_name)

            mapping[name][filename] = relative_path

    return mapping


def attach_canonical_paths(
    df: pd.DataFrame,
    mapping: Dict[str, Dict[str, str]],
    data_contract_version: int,
) -> pd.DataFrame:
    """
    Add canonical relative path columns to the dataframe.
    """


    external_columns = extract_external_file_columns(
        data_contract_version,
        file_type="image",
    )

    df = df.copy()

    for col, rules in external_columns.items():

        if col not in df.columns:
            continue

        name = rules["name"]
        output_column = f"{name}_relative_path"

        if name in mapping:
            df[output_column] = df[col].map(mapping[name])

    return df