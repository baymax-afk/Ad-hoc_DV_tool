import hashlib
import io
import re

import chardet
import pandas as pd

from src.core.config import settings
from src.core.exceptions import IngestionError
from src.ingestion.models import DataProfile


class DataIngestor:
    SAMPLE_BYTES = 10_000
    CANDIDATE_DELIMITERS = [",", ";", "\t", "|"]

    def ingest(self, raw_bytes: bytes, filename: str) -> DataProfile:
        if not raw_bytes:
            raise IngestionError("Uploaded file is empty.")

        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(raw_bytes) > max_bytes:
            raise IngestionError(
                f"File exceeds {settings.max_upload_mb} MB limit ({len(raw_bytes) // 1024 // 1024} MB received)."
            )

        file_hash = hashlib.sha256(raw_bytes).hexdigest()
        encoding = self._detect_encoding(raw_bytes)
        delimiter = self._detect_delimiter(raw_bytes, encoding)

        warnings: list[str] = []
        try:
            df = pd.read_csv(
                io.BytesIO(raw_bytes),
                encoding=encoding,
                sep=delimiter,
                nrows=settings.max_rows,
                on_bad_lines="warn",
                low_memory=False,
            )
        except Exception as exc:
            raise IngestionError(f"Failed to parse CSV: {exc}") from exc

        if len(df) == 0:
            raise IngestionError("CSV file parsed to zero rows. Check the file format.")

        if len(df) == settings.max_rows:
            warnings.append(
                f"File truncated to {settings.max_rows:,} rows. "
                "Results reflect a sample of the full dataset."
            )

        df = self._sanitize(df, warnings)

        return DataProfile(
            df=df,
            file_hash=file_hash,
            filename=filename,
            original_columns=list(df.columns),
            row_count=len(df),
            col_count=len(df.columns),
            parse_warnings=warnings,
            detected_encoding=encoding,
            detected_delimiter=delimiter,
        )

    # ------------------------------------------------------------------
    def _detect_encoding(self, raw: bytes) -> str:
        sample = raw[: self.SAMPLE_BYTES]
        # Strip UTF-8 BOM if present
        if sample.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        result = chardet.detect(sample)
        detected = result.get("encoding") or "utf-8"
        # chardet sometimes returns None confidence; fall back safely
        confidence = result.get("confidence") or 0
        return detected if confidence > 0.5 else "utf-8"

    def _detect_delimiter(self, raw: bytes, encoding: str) -> str:
        try:
            sample = raw[: self.SAMPLE_BYTES].decode(encoding, errors="replace")
        except Exception:
            sample = raw[: self.SAMPLE_BYTES].decode("utf-8", errors="replace")

        counts = {d: sample.count(d) for d in self.CANDIDATE_DELIMITERS}
        return max(counts, key=counts.get)

    def _sanitize(self, df: pd.DataFrame, warnings: list[str]) -> pd.DataFrame:
        # Normalize column names
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.lower()
            .str.replace(r"[^\w]", "_", regex=True)
            .str.replace(r"_+", "_", regex=True)
            .str.strip("_")
        )

        # Deduplicate column names (col, col_1, col_2 …)
        seen: dict[str, int] = {}
        new_cols = []
        for col in df.columns:
            if col in seen:
                seen[col] += 1
                new_cols.append(f"{col}_{seen[col]}")
                warnings.append(f"Duplicate column '{col}' renamed to '{col}_{seen[col]}'.")
            else:
                seen[col] = 0
                new_cols.append(col)
        df.columns = new_cols

        # Drop fully-empty rows and columns
        df = df.dropna(how="all").reset_index(drop=True)
        empty_cols = df.columns[df.isna().all()].tolist()
        if empty_cols:
            df = df.drop(columns=empty_cols)
            warnings.append(f"Dropped all-null columns: {empty_cols}")

        return df
