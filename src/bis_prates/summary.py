from pathlib import Path

import pandas as pd

SUMMARY_COLUMNS = [
    "country_code",
    "country_name",
    "frequency",
    "title",
    "unit_measure",
    "unit_multiplier",
    "decimals",
    "latest_date",
    "latest_rate",
    "previous_month_end_date",
    "previous_month_end_rate",
    "change_vs_previous_month_end",
    "last_change_date",
    "last_change_size",
    "policy_direction",
    "days_since_last_change",
    "min_rate",
    "min_rate_date",
    "max_rate",
    "max_rate_date",
]


def build_summary(
    data_path: Path | str = Path("data/processed/policy_rates.csv"),
    countries: list[str] | tuple[str, ...] = (
        "US",
        "XM",
        "GB",
        "JP",
        "CH",
    ),
    start: str | None = None,
) -> pd.DataFrame:
    """Load transformed BIS data and build a latest policy-rate summary."""
    data_path = Path(data_path)

    if not data_path.is_file():
        raise FileNotFoundError(f"Processed dataset not found: {data_path}")

    df = pd.read_csv(
        data_path,
        parse_dates=["observation_date"],
        low_memory=False,
    )

    return summarize_policy_rates(
        df,
        countries=countries,
        start=start,
    )


def summarize_policy_rates(
    df: pd.DataFrame,
    countries: list[str] | tuple[str, ...],
    start: str | None = None,
) -> pd.DataFrame:
    """Build a latest policy-rate snapshot for selected countries."""
    country_codes = _normalize_country_codes(countries)

    available = set(df["country_code"].dropna().astype(str).str.upper().unique())

    unknown = sorted(set(country_codes) - available)

    if unknown:
        raise ValueError(f"Unknown country code(s): {unknown}")

    selected = df.loc[
        df["country_code"].isin(country_codes) & df["observation_value"].notna()
    ].copy()

    if start is not None:
        start_date = pd.Timestamp(start)

        selected = selected.loc[selected["observation_date"] >= start_date].copy()

    if selected.empty:
        raise ValueError("No usable policy-rate observations found.")

    selected = _select_reporting_frequency(selected)

    summaries = []

    for country_code in country_codes:
        country = selected.loc[selected["country_code"].eq(country_code)].sort_values(
            "observation_date"
        )

        if country.empty:
            continue

        summaries.append(_summarize_country(country))

    return pd.DataFrame(
        summaries,
        columns=SUMMARY_COLUMNS,
    )


def _select_reporting_frequency(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Prefer daily observations, with monthly as a fallback."""
    daily_countries = set(
        df.loc[
            df["frequency"].eq("D"),
            "country_code",
        ]
    )

    keep_daily = df["country_code"].isin(daily_countries) & df["frequency"].eq("D")

    keep_monthly = ~df["country_code"].isin(daily_countries) & df["frequency"].eq("M")

    return df.loc[keep_daily | keep_monthly].copy()


def _summarize_country(
    country: pd.DataFrame,
) -> dict:
    """Compute latest, month-end, and rate-change statistics for one country."""
    latest = country.iloc[-1]

    previous_month_end = _previous_month_end(
        country,
        latest_date=latest["observation_date"],
    )

    minimum = country.loc[country["observation_value"].idxmin()]

    maximum = country.loc[country["observation_value"].idxmax()]

    latest_rate = latest["observation_value"]

    rate_changes = country["observation_value"].diff()
    changed = rate_changes.ne(0) & rate_changes.notna()

    if changed.any():
        last_change_index = rate_changes[changed].index[-1]
        last_change = country.loc[last_change_index]
        last_change_size = rate_changes.loc[last_change_index]

        policy_direction = "hike" if last_change_size > 0 else "cut"

        days_since_last_change = (
            latest["observation_date"] - last_change["observation_date"]
        ).days
    else:
        last_change = None
        last_change_size = pd.NA
        policy_direction = "unchanged"
        days_since_last_change = pd.NA

    return {
        "country_code": latest["country_code"],
        "country_name": latest["country_name"],
        "frequency": latest["frequency"],
        "title": latest["title"],
        "unit_measure": latest["unit_measure"],
        "unit_multiplier": latest["unit_multiplier"],
        "decimals": latest["decimals"],
        "latest_date": latest["observation_date"],
        "latest_rate": latest_rate,
        "previous_month_end_date": (
            previous_month_end["observation_date"]
            if previous_month_end is not None
            else pd.NaT
        ),
        "previous_month_end_rate": (
            previous_month_end["observation_value"]
            if previous_month_end is not None
            else pd.NA
        ),
        "change_vs_previous_month_end": (
            latest_rate - previous_month_end["observation_value"]
            if previous_month_end is not None
            else pd.NA
        ),
        "last_change_date": (
            last_change["observation_date"] if last_change is not None else pd.NaT
        ),
        "last_change_size": last_change_size,
        "policy_direction": policy_direction,
        "days_since_last_change": days_since_last_change,
        "min_rate": minimum["observation_value"],
        "min_rate_date": minimum["observation_date"],
        "max_rate": maximum["observation_value"],
        "max_rate_date": maximum["observation_date"],
    }


def _previous_month_end(
    country: pd.DataFrame,
    latest_date: pd.Timestamp,
) -> pd.Series | None:
    """Return the last available observation before the current month."""
    current_month_start = latest_date.to_period("M").start_time

    previous = country.loc[country["observation_date"] < current_month_start]

    if previous.empty:
        return None

    return previous.iloc[-1]


def _normalize_country_codes(
    countries: list[str] | tuple[str, ...],
) -> list[str]:
    """Normalize country codes while preserving input order."""
    country_codes = []

    for country in countries:
        code = country.strip().upper()

        if code and code not in country_codes:
            country_codes.append(code)

    if not country_codes:
        raise ValueError("At least one country code must be provided.")

    return country_codes


def write_summary(
    summary: pd.DataFrame,
    output_dir: Path | str = Path("out"),
    start: str | None = None,
    requested_countries: list[str] | None = None,
    resolved_countries: list[str] | None = None,
) -> tuple[Path, Path]:
    """Write the policy-rate summary to CSV and JSON."""
    output_dir = Path(output_dir)
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = output_dir / "summary.csv"
    json_path = output_dir / "summary.json"

    summary.to_csv(
        csv_path,
        index=False,
        date_format="%Y-%m-%d",
    )

    json_summary = summary.copy()

    for column in [
        "latest_date",
        "previous_month_end_date",
        "last_change_date",
        "min_rate_date",
        "max_rate_date",
    ]:
        json_summary[column] = pd.to_datetime(
            json_summary[column],
            errors="coerce",
        ).dt.strftime("%Y-%m-%d")

    countries = []

    for _, row in json_summary.iterrows():
        countries.append(
            {
                "country_code": row["country_code"],
                "country_name": row["country_name"],
                "latest_snapshot": {
                    "latest_rate_pct": row["latest_rate"],
                    "latest_date": row["latest_date"],
                    "last_month_end_rate_pct": row["previous_month_end_rate"],
                    "last_month_end_date": row["previous_month_end_date"],
                    "change_vs_last_month_end_pp": row["change_vs_previous_month_end"],
                    "last_change_date": row["last_change_date"],
                    "last_change_size_pp": row["last_change_size"],
                    "policy_direction": row["policy_direction"],
                    "days_since_last_change": row["days_since_last_change"],
                    "min_since_start_pct": row["min_rate"],
                    "min_date": row["min_rate_date"],
                    "max_since_start_pct": row["max_rate"],
                    "max_date": row["max_rate_date"],
                },
                "series_metadata": {
                    "frequency": row["frequency"],
                    "title": row["title"],
                    "unit_measure": row["unit_measure"],
                    "unit_multiplier": row["unit_multiplier"],
                    "decimals": row["decimals"],
                },
            }
        )

    report = {
        "run_date": pd.Timestamp.now(tz="UTC").date().isoformat(),
        "start_date": start,
        "dataflow_id": "WS_CBPOL",
        "dataset_file": "WS_CBPOL_csv_flat.zip",
        "source": "BIS Data Portal bulk download",
        "requested_countries": requested_countries or [],
        "resolved_countries": resolved_countries or [],
        "countries": countries,
    }

    pd.Series(report).to_json(
        json_path,
        indent=2,
        force_ascii=False,
    )

    return csv_path, json_path
