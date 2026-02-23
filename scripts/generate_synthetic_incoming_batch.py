#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import uuid4

import numpy as np
import pandas as pd
import yaml


@dataclass(frozen=True)
class Paths:
    repo_root: Path
    config_root: Path
    data_root: Path
    incoming_dir: Path


YES_NO = ["Yes", "No"]

REGION_ECONOMIC_CLASSIFICATION = [
    "Low income",
    "Lower-middle income",
    "Upper-middle income",
    "High income",
]

SEISMIC_HAZARD_ZONE = ["Very Low", "Low", "Moderate", "High", "Very High"]
WIND_RISK = ["Very Low", "Low", "Moderate", "High", "Very High"]

KOPPEN = (
    ["Af", "Am", "Aw", "As"]
    + [f"BW{x}" for x in ("h", "k")]
    + [f"BS{x}" for x in ("h", "k")]
    + [f"C{w}{t}" for w in ("f", "w", "s") for t in ("a", "b", "c")]
    + [f"D{w}{t}" for w in ("f", "w", "s") for t in ("a", "b", "c", "d")]
    + ["ET", "EF"]
)

COUNTRIES = [
    "United States",
    "France",
    "Germany",
    "Brazil",
    "India",
    "Japan",
    "Canada",
    "Australia",
    "South Africa",
    "Mexico",
]

GEOLOCATIONS = [
    "Capital District",
    "Coastal Zone",
    "Industrial Park",
    "Metro Area",
    "Rural Region",
    "Northern Province",
    "Eastern Province",
    "Southern Province",
    "Western Province",
]


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    if not data:
        raise ValueError(f"YAML file is empty or invalid: {path}")
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def _load_active_data_contract_version(config_root: Path) -> int:
    active_path = config_root / "active_config.yaml"
    active = _load_yaml(active_path)
    version = active.get("data_contract_version")
    if not isinstance(version, int):
        raise ValueError(
            f"Invalid or missing 'data_contract_version' in {active_path}"
        )
    return version


def _load_data_contract(config_root: Path, version: int) -> Dict[str, Any]:
    contract_path = config_root / "data_contracts" / f"v{version}.yaml"
    contract = _load_yaml(contract_path)
    return contract


def _pick(rng: np.random.Generator, items: List[str] | Tuple[str, ...], size: int) -> List[str]:
    return list(rng.choice(np.array(list(items), dtype=object), size=size, replace=True))


def _random_yes_no(rng: np.random.Generator, size: int, p_yes: float = 0.6) -> List[str]:
    return list(rng.choice(np.array(YES_NO, dtype=object), size=size, p=[p_yes, 1 - p_yes]))


def _make_quarter_labels(rng: np.random.Generator, years: np.ndarray) -> List[str]:
    quarters = rng.integers(1, 5, size=len(years))
    return [f"{int(y)}-Q{int(q)}" for y, q in zip(years, quarters)]


def _generate_rows(contract: Dict[str, Any], rows: int, seed: int | None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    columns: Dict[str, Any] = contract.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise ValueError("Contract is missing 'columns'.")

    # Keep years in a reasonable recent range while still respecting contract bounds.
    year_min = int(columns.get("year", {}).get("min", 1950))
    year_max = int(columns.get("year", {}).get("max", 2100))
    year_low = max(year_min, 2005)
    year_high = min(year_max, datetime.now().year)
    if year_low > year_high:
        year_low, year_high = year_min, year_max

    years = rng.integers(year_low, year_high + 1, size=rows, dtype=np.int64)

    df = pd.DataFrame(
        {
            "data_id": [f"syn_{uuid4().hex}" for _ in range(rows)],
            "geolocation_name": _pick(rng, GEOLOCATIONS, rows),
            "quarter_label": _make_quarter_labels(rng, years),
            "country": _pick(rng, COUNTRIES, rows),
            "year": years,
            "deflated_gdp_usd": np.round(rng.lognormal(mean=25.0, sigma=0.6, size=rows), 2),
            "us_cpi": np.round(rng.normal(loc=250.0, scale=40.0, size=rows).clip(min=50.0), 2),
            "developed_country": _random_yes_no(rng, rows, p_yes=0.45),
            "landlocked": _random_yes_no(rng, rows, p_yes=0.25),
            "region_economic_classification": list(
                rng.choice(
                    np.array(REGION_ECONOMIC_CLASSIFICATION, dtype=object),
                    size=rows,
                    p=[0.15, 0.35, 0.3, 0.2],
                )
            ),
            "access_to_airport": _random_yes_no(rng, rows, p_yes=0.7),
            "access_to_port": _random_yes_no(rng, rows, p_yes=0.5),
            "access_to_highway": _random_yes_no(rng, rows, p_yes=0.65),
            "access_to_railway": _random_yes_no(rng, rows, p_yes=0.55),
            "straight_distance_to_capital_km": np.round(rng.gamma(shape=2.0, scale=120.0, size=rows), 2),
            "seismic_hazard_zone": _pick(rng, SEISMIC_HAZARD_ZONE, rows),
            "flood_risk_class": _random_yes_no(rng, rows, p_yes=0.4),
            "tropical_cyclone_wind_risk": _pick(rng, WIND_RISK, rows),
            "tornadoes_wind_risk": _pick(rng, WIND_RISK, rows),
            "koppen_climate_zone": _pick(rng, KOPPEN, rows),
            # By default we do NOT generate images; keep these empty so linked-file checks pass.
            "sentinel2_tiff_file_name": np.full(rows, np.nan, dtype=float),
            "viirs_tiff_file_name": np.full(rows, np.nan, dtype=float),
        }
    )

    # Target generation: simple synthetic signal + noise, clipped at 0.
    developed = (df["developed_country"] == "Yes").astype(float)
    access_score = (
        (df["access_to_airport"] == "Yes").astype(float)
        + (df["access_to_port"] == "Yes").astype(float)
        + (df["access_to_highway"] == "Yes").astype(float)
        + (df["access_to_railway"] == "Yes").astype(float)
    )

    base = 120.0
    cost = (
        base
        + 0.06 * df["us_cpi"].astype(float)
        + 0.00000008 * df["deflated_gdp_usd"].astype(float)
        + 35.0 * developed
        + 18.0 * access_score
        + rng.normal(loc=0.0, scale=25.0, size=rows)
    )

    df["construction_cost_per_m2_usd"] = np.round(np.clip(cost, 0.0, None), 2)

    # Ensure we output exactly the strict column set (and order) from the contract.
    contract_cols = list(columns.keys())
    missing = set(contract_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Generator is missing columns required by contract: {sorted(missing)}")

    df = df[contract_cols]
    return df


def _ensure_importable(paths: Paths) -> None:
    # Make in-repo modules importable and satisfy CONFIG_ROOT requirement.
    os.environ.setdefault("CONFIG_ROOT", str(paths.config_root))
    if str(paths.repo_root / "src") not in sys.path:
        sys.path.insert(0, str(paths.repo_root / "src"))


def _validate_with_contract(df: pd.DataFrame, contract_version: int) -> None:
    from data.data_contract import validate_dataframe

    validate_dataframe(df, data_contract_version=contract_version, strict_columns=True)


def _write_ready_marker(incoming_dir: Path) -> None:
    ready_path = incoming_dir / "_READY"
    ready_path.write_text("ready\n")


def _check_incoming_lock(incoming_dir: Path) -> None:
    processing = incoming_dir / "_PROCESSING"
    if processing.exists():
        raise RuntimeError(
            f"Incoming appears locked (found {processing}). "
            "Wait for the pipeline to finish or remove the marker if safe."
        )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a synthetic tabular CSV batch compatible with the active data contract "
            "and drop it into data/incoming/ (optionally creating _READY)."
        )
    )
    parser.add_argument("--batches", type=int, default=1, help="Number of CSV files to generate.")
    parser.add_argument("--rows-min", type=int, default=50, help="Minimum rows per batch.")
    parser.add_argument("--rows-max", type=int, default=200, help="Maximum rows per batch.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (base seed; batch index is added).")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root directory (defaults to $DATA_ROOT or <repo>/data).",
    )
    parser.add_argument(
        "--contract-version",
        type=int,
        default=None,
        help="Override data contract version (defaults to configs/active_config.yaml).",
    )
    parser.add_argument(
        "--no-ready",
        action="store_true",
        help="Do not create data/incoming/_READY marker.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and validate but do not write files.",
    )

    args = parser.parse_args(argv)

    if args.batches < 1:
        raise ValueError("--batches must be >= 1")
    if args.rows_min < 1 or args.rows_max < 1:
        raise ValueError("--rows-min/--rows-max must be >= 1")
    if args.rows_min > args.rows_max:
        raise ValueError("--rows-min must be <= --rows-max")

    repo_root = _resolve_repo_root()
    config_root = repo_root / "configs"

    data_root = args.data_root
    if data_root is None:
        data_root = Path(os.getenv("DATA_ROOT") or (repo_root / "data"))

    data_root = data_root.resolve()

    paths = Paths(
        repo_root=repo_root,
        config_root=config_root,
        data_root=data_root,
        incoming_dir=(data_root / "incoming"),
    )

    contract_version = args.contract_version
    if contract_version is None:
        contract_version = _load_active_data_contract_version(paths.config_root)

    contract = _load_data_contract(paths.config_root, contract_version)

    paths.incoming_dir.mkdir(parents=True, exist_ok=True)
    _check_incoming_lock(paths.incoming_dir)

    _ensure_importable(paths)

    rng = np.random.default_rng(args.seed)

    written_files: List[Path] = []

    for i in range(args.batches):
        rows = int(rng.integers(args.rows_min, args.rows_max + 1))
        batch_seed = None if args.seed is None else (args.seed + i)

        df = _generate_rows(contract=contract, rows=rows, seed=batch_seed)
        _validate_with_contract(df, contract_version=contract_version)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"synthetic_{ts}_{uuid4().hex[:6]}_{rows}rows.csv"
        out_path = paths.incoming_dir / filename

        if not args.dry_run:
            df.to_csv(out_path, index=False)
            written_files.append(out_path)

    if not args.no_ready and not args.dry_run:
        _write_ready_marker(paths.incoming_dir)

    if args.dry_run:
        print(
            f"Dry run OK: generated and validated {args.batches} batch(es) "
            f"against contract v{contract_version}."
        )
    else:
        print(
            f"Wrote {len(written_files)} file(s) to {paths.incoming_dir} "
            f"and contract-validated against v{contract_version}."
        )
        for p in written_files:
            print(f"- {p.name}")
        if not args.no_ready:
            print("Created _READY marker.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
