"""Extract: read the raw CSV files exactly as delivered (everything as text)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from summitbase.config import RAW_DIR, TABLES


def read_raw_table(name: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Read one raw CSV as strings so that typing is an explicit transform step."""
    path = raw_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Raw file not found: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def extract_all(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    return {name: read_raw_table(name, raw_dir) for name in TABLES}
