from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path


@dataclass
class DatasetContext:
    filename: str
    rows: int
    columns: int
    column_names: list[str]
    prompt_context: str


def load_table(uploaded_file, filename):

    import pandas as pd

    suffix = Path(filename).suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(uploaded_file)

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(BytesIO(uploaded_file.read()))

    raise ValueError("Unsupported file type")


def build_dataset_context(df, filename):

    summary = []

    summary.append(f"File: {filename}")
    summary.append(f"Rows: {len(df)}")
    summary.append(f"Columns: {len(df.columns)}")
    summary.append(
        "Column names: "
        + ", ".join(df.columns.astype(str))
    )

    return DatasetContext(
        filename=filename,
        rows=len(df),
        columns=len(df.columns),
        column_names=list(df.columns.astype(str)),
        prompt_context="\n".join(summary),
    )