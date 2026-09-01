from pathlib import Path

import pandas as pd

COLUMN_RENAMES = {
    "FREQ:Frequency": "frequency",
    "REF_AREA:Reference area": "reference_area",
    "TIME_PERIOD:Time period or range": "time_period_raw",
    "OBS_VALUE:Observation Value": "observation_value",
    "TITLE:Title": "title",
    "UNIT_MEASURE:Unit of measure": "unit_measure",
    "UNIT_MULT:Unit Multiplier": "unit_multiplier",
    "DECIMALS:Decimals": "decimals",
    "COMPILATION:Compilation": "compilation",
    "SOURCE_REF:Publication Source": "source_ref",
    "SUPP_INFO_BREAKS:Supplemental information and breaks": "supp_info_breaks",
    "OBS_STATUS:Observation Status": "obs_status",
    "OBS_CONF:Observation confidentiality": "obs_conf",
    "OBS_PRE_BREAK:Pre-Break Observation": "obs_pre_break",
}

FINAL_COLUMNS = [
    "country_code",
    "country_name",
    "frequency",
    "observation_date",
    "observation_value",
    "time_period_raw",
    "title",
    "unit_measure",
    "unit_multiplier",
    "decimals",
    "compilation",
    "source_ref",
    "supp_info_breaks",
    "obs_status",
    "obs_conf",
    "obs_pre_break",
]

SERIES_KEY = ["country_code", "frequency", "observation_date"]


def transform_policy_rates(
    zip_path: Path | str = Path("data/raw/WS_CBPOL_csv_flat.zip"),
    out_path: Path | str = Path("data/processed/policy_rates.csv"),
) -> Path:
    """Transform the BIS policy-rate bulk download into a tidy CSV."""
    zip_path = Path(zip_path)
    out_path = Path(out_path)

    if not zip_path.is_file():
        raise FileNotFoundError(f"BIS dataset not found: {zip_path}")

    raw = pd.read_csv(zip_path, compression="zip", low_memory=False)

    tidy = clean_policy_rates(raw)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    tidy.to_csv(
        out_path,
        index=False,
        encoding="utf-8",
        date_format="%Y-%m-%d",
    )

    return out_path


def clean_policy_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the BIS central-bank policy-rate dataset."""
    missing = set(COLUMN_RENAMES) - set(df.columns)

    if missing:
        raise ValueError(f"Missing expected BIS columns: {sorted(missing)}")

    tidy = df.rename(columns=COLUMN_RENAMES).copy()

    # Drop SDMX transport-level metadata.
    tidy = tidy.drop(
        columns=["STRUCTURE", "STRUCTURE_ID", "ACTION"],
        errors="ignore",
    )

    # "M: Monthly" -> "M"
    tidy["frequency"] = tidy["frequency"].str.split(":", n=1).str[0].str.strip()

    # "CH: Switzerland" -> "CH" and "Switzerland"
    area = tidy["reference_area"].str.split(":", n=1, expand=True)

    tidy["country_code"] = area[0].str.strip()
    tidy["country_name"] = area[1].str.strip()

    # Preserve legitimate BIS missing observations as NaN.
    tidy["observation_value"] = pd.to_numeric(
        tidy["observation_value"],
        errors="coerce",
    )

    tidy["decimals"] = pd.to_numeric(
        tidy["decimals"].str.split(":", n=1).str[0].str.strip(),
        errors="coerce",
    ).astype("Int64")

    tidy["observation_date"] = convert_period_to_date(
        tidy["time_period_raw"],
        tidy["frequency"],
    )

    tidy = tidy.drop(columns="reference_area")

    # Exact duplicate rows can safely be collapsed.
    tidy = tidy.drop_duplicates()

    if tidy.duplicated(SERIES_KEY).any():
        raise ValueError(
            "Multiple different observations found for the same "
            "country, frequency, and date."
        )

    tidy = tidy[FINAL_COLUMNS]

    return tidy.sort_values(SERIES_KEY).reset_index(drop=True)


def convert_period_to_date(
    time_period: pd.Series,
    frequency: pd.Series,
) -> pd.Series:
    """Convert BIS daily and monthly periods to timestamps."""
    dates = pd.Series(
        pd.NaT,
        index=time_period.index,
        dtype="datetime64[ns]",
    )

    daily = frequency.eq("D")
    monthly = frequency.eq("M")

    dates.loc[daily] = pd.to_datetime(
        time_period.loc[daily],
        format="%Y-%m-%d",
        errors="coerce",
    )

    dates.loc[monthly] = pd.to_datetime(
        time_period.loc[monthly],
        format="%Y-%m",
        errors="coerce",
    ) + pd.offsets.MonthEnd(0)

    invalid = time_period.notna() & dates.isna()

    if invalid.any():
        raise ValueError("Could not parse some BIS observation dates.")

    return dates
