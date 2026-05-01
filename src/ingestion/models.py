from dataclasses import dataclass, field
import pandas as pd


@dataclass
class DataProfile:
    df: pd.DataFrame
    file_hash: str
    filename: str
    original_columns: list[str]
    row_count: int
    col_count: int
    parse_warnings: list[str] = field(default_factory=list)
    detected_encoding: str = "utf-8"
    detected_delimiter: str = ","
