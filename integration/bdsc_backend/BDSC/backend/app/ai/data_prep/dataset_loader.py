"""Dataset loader and data provenance manager for DispatchGrid AI."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Literal

import pandas as pd

from app.ai.config import BACKEND_ROOT_DIR, DATA_DIR

logger = logging.getLogger("dispatchgrid.ai.data")

ProvenanceType = Literal["SYNTHETIC_BENCHMARK", "OPERATIONAL_DB", "SYNTHETIC_AUGMENTED"]


class DatasetBundle:
    """Container for loaded datasets with provenance metadata."""

    def __init__(
        self,
        jobs_df: pd.DataFrame,
        electricians_df: pd.DataFrame,
        travel_times_df: pd.DataFrame,
        provenance: ProvenanceType,
    ) -> None:
        self.jobs_df = jobs_df
        self.electricians_df = electricians_df
        self.travel_times_df = travel_times_df
        self.provenance = provenance

    def summary(self) -> dict[str, int]:
        return {
            "jobs_count": len(self.jobs_df),
            "electricians_count": len(self.electricians_df),
            "travel_pairs_count": len(self.travel_times_df),
        }


def load_raw_benchmark_csvs() -> DatasetBundle:
    """Load the original benchmark CSV files from backend/data."""
    jobs_path = DATA_DIR / "electrical_jobs.csv"
    elec_path = DATA_DIR / "electricians.csv"
    travel_path = DATA_DIR / "travel_times.csv"

    if not jobs_path.exists():
        raise FileNotFoundError(f"Missing required benchmark data file: {jobs_path}")

    jobs_df = pd.read_csv(jobs_path)
    elec_df = pd.read_csv(elec_path) if elec_path.exists() else pd.DataFrame()
    travel_df = pd.read_csv(travel_path) if travel_path.exists() else pd.DataFrame()

    jobs_df["data_provenance"] = "SYNTHETIC_BENCHMARK"
    return DatasetBundle(
        jobs_df=jobs_df,
        electricians_df=elec_df,
        travel_times_df=travel_df,
        provenance="SYNTHETIC_BENCHMARK",
    )


def load_operational_db_records(db_path: Path | str | None = None) -> pd.DataFrame:
    """Load operational job records from the SQLite database."""
    if db_path is None:
        db_path = BACKEND_ROOT_DIR / "dispatchgrid.db"

    if not Path(db_path).exists():
        logger.warning(f"Database at {db_path} not found. Returning empty DataFrame.")
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)
    try:
        query = """
            SELECT 
                id as job_id,
                job_type,
                priority,
                service_zone as zone,
                status,
                estimated_duration_minutes as duration_min,
                appointment_window_start,
                appointment_window_end,
                sla_deadline,
                actual_start_time,
                actual_completion_time,
                assigned_technician_id,
                created_at
            FROM jobs
        """
        df = pd.read_sql_query(query, conn)
        df["data_provenance"] = "OPERATIONAL_DB"
        return df
    finally:
        conn.close()

