"""IO helpers for reading, cleaning, and exporting shot data."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, IO, Mapping, Union

import pandas as pd


PathLike = Union[str, Path]
FileLike = Union[IO[str], IO[bytes]]


def read_csv(path_or_file: Union[PathLike, FileLike]) -> pd.DataFrame:
    """Load a CSV into a DataFrame and raise a ValueError on failure."""

    try:
        df = pd.read_csv(path_or_file)
    except FileNotFoundError as exc:
        raise FileNotFoundError("CSV file not found.") from exc
    except Exception as exc:  # pragma: no cover - pandas composes different errors
        raise ValueError(f"Failed to read CSV: {exc}") from exc

    if df.empty:
        raise ValueError("CSV is empty. Add shot records before importing.")
    return df


def _normalise_result(value: object) -> str:
    """Convert arbitrary truthy/falsey entries into MAKE or MISS."""

    text = str(value).strip().lower()
    make_tokens = {"make", "made", "hit", "true", "t", "1", "yes", "y"}
    miss_tokens = {"miss", "missed", "false", "f", "0", "no", "n"}

    if text in make_tokens:
        return "MAKE"
    if text in miss_tokens:
        return "MISS"
    raise ValueError(f"Result value '{value}' is not recognised as make or miss.")


def normalize_columns(df: pd.DataFrame, mapping: Mapping[str, str]) -> pd.DataFrame:
    """Rename and validate required columns based on the provided mapping."""

    required = {"x", "y", "result"}
    missing_targets = required.difference(mapping.keys())
    if missing_targets:
        raise ValueError(f"Missing mappings for: {', '.join(sorted(missing_targets))}.")

    rename_map: Dict[str, str] = {}
    for target, source in mapping.items():
        if source not in df.columns:
            raise ValueError(f"Source column '{source}' not found in the imported data.")
        rename_map[source] = target

    normalized = df.rename(columns=rename_map).copy()

    for coordinate in ("x", "y"):
        normalized[coordinate] = pd.to_numeric(
            normalized[coordinate], errors="coerce"
        )
        if normalized[coordinate].isna().any():
            raise ValueError(
                f"Column '{coordinate}' contains non-numeric values after conversion."
            )

    normalized["result"] = normalized["result"].apply(_normalise_result)
    return normalized


def write_csv(df: pd.DataFrame) -> bytes:
    """Serialise the DataFrame into UTF-8 encoded CSV bytes."""

    return df.to_csv(index=False).encode("utf-8")
