from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

COUNTRY_ALIASES = {
    "EA": "XM",
}


def generate_report(
    data_path: Path | str = Path("data/processed/policy_rates.csv"),
    summary_path: Path | str = Path("out/summary.csv"),
    output_dir: Path | str = Path("out"),
    start: str | None = None,
    requested_countries: list[str] | tuple[str, ...] | None = None,
) -> tuple[Path, Path]:
    """Generate the BIS policy-rate chart and Markdown report."""
    data_path = Path(data_path)
    summary_path = Path(summary_path)
    output_dir = Path(output_dir)

    if not data_path.is_file():
        raise FileNotFoundError(f"Processed dataset not found: {data_path}")

    if not summary_path.is_file():
        raise FileNotFoundError(f"Summary dataset not found: {summary_path}")

    history = pd.read_csv(
        data_path,
        parse_dates=["observation_date"],
        low_memory=False,
    )

    summary = pd.read_csv(summary_path)

    start_date = pd.Timestamp(start) if start is not None else None

    if requested_countries is None:
        requested_codes = summary["country_code"].astype(str).tolist()
    else:
        requested_codes = _normalize_country_codes(requested_countries)

    resolved_codes = [COUNTRY_ALIASES.get(code, code) for code in requested_codes]

    coverage_issues = _find_coverage_issues(
        history=history,
        summary=summary,
        requested_codes=requested_codes,
        resolved_codes=resolved_codes,
    )

    report_history = history.loc[
        history["country_code"].isin(summary["country_code"])
        & history["observation_value"].notna()
    ].copy()

    if start_date is not None:
        report_history = report_history.loc[
            report_history["observation_date"] >= start_date
        ].copy()

    report_history = _select_reporting_frequency(report_history)

    if report_history.empty:
        raise ValueError("No policy-rate history available for the report.")

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    chart_path = output_dir / "policy_rates.png"
    report_path = output_dir / "report.md"

    create_policy_rate_timeseries_chart(
        history=report_history,
        summary=summary,
        output_path=chart_path,
    )

    write_markdown_report(
        summary=summary,
        chart_path=chart_path,
        report_path=report_path,
        start_date=start_date,
        requested_codes=requested_codes,
        resolved_codes=resolved_codes,
        coverage_issues=coverage_issues,
    )

    return report_path, chart_path


def create_policy_rate_timeseries_chart(
    history: pd.DataFrame,
    summary: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    """Plot policy-rate histories for the selected countries."""
    output_path = Path(output_path)

    fig, ax = plt.subplots(figsize=(8, 5))

    for country_code in summary["country_code"]:
        country = history.loc[history["country_code"].eq(country_code)].sort_values(
            "observation_date"
        )

        if country.empty:
            continue

        country_name = country["country_name"].iloc[-1]

        ax.plot(
            country["observation_date"],
            country["observation_value"],
            label=f"{country_name} ({country_code})",
            linewidth=1.7,
        )

    ax.set_title("Central Bank Policy Rates Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Policy rate (%)")
    ax.grid(alpha=0.25)
    ax.legend(
        frameon=False,
        ncol=2,
    )

    fig.tight_layout()

    fig.savefig(
        output_path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return output_path


def write_markdown_report(
    summary: pd.DataFrame,
    chart_path: Path | str,
    report_path: Path | str,
    start_date: pd.Timestamp | None = None,
    requested_codes: list[str] | None = None,
    resolved_codes: list[str] | None = None,
    coverage_issues: list[dict] | None = None,
) -> Path:
    """Write the BIS Policy Rate Monitor report as Markdown."""
    chart_path = Path(chart_path)
    report_path = Path(report_path)

    requested_codes = requested_codes or []
    resolved_codes = resolved_codes or []
    coverage_issues = coverage_issues or []

    table = summary.copy()

    for column in [
        "latest_date",
        "last_change_date",
    ]:
        table[column] = (
            pd.to_datetime(
                table[column],
                errors="coerce",
            )
            .dt.strftime("%Y-%m-%d")
            .fillna("")
        )

    table["latest_rate"] = table["latest_rate"].map(
        lambda value: f"{value:.4f}%" if pd.notna(value) else ""
    )

    table["change_vs_previous_month_end"] = table["change_vs_previous_month_end"].map(
        lambda value: "—" if pd.isna(value) or value == 0 else f"{value:+.4f} pp"
    )

    table["last_move"] = table.apply(
        _format_last_move,
        axis=1,
    )

    table["days_since_last_change"] = table["days_since_last_change"].map(
        lambda value: str(int(value)) if pd.notna(value) else ""
    )

    snapshot = table[
        [
            "country_name",
            "latest_rate",
            "latest_date",
            "change_vs_previous_month_end",
            "last_move",
            "last_change_date",
            "days_since_last_change",
        ]
    ].rename(
        columns={
            "country_name": "Country / Area",
            "latest_rate": "Rate",
            "latest_date": "Latest Date",
            "change_vs_previous_month_end": "Monthly Δ",
            "last_move": "Last Move",
            "last_change_date": "Last Change",
            "days_since_last_change": "Days Since Last Change",
        }
    )

    generated_at = pd.Timestamp.now(tz="UTC")

    lines = [
        "# BIS Policy Rate Monitor",
        "",
        (
            "> Latest central-bank policy rates and recent developments "
            "from the Bank for International Settlements."
        ),
        "",
        f"**Generated:** {generated_at:%Y-%m-%d %H:%M UTC}  ",
    ]

    if start_date is not None:
        lines.append(
            f"**Period:** {start_date:%Y-%m-%d} → latest available observation  "
        )

    lines.append(f"**Coverage:** {', '.join(summary['country_name'].astype(str))}  ")

    if requested_codes:
        lines.append(f"**Requested:** {', '.join(requested_codes)}  ")

    if resolved_codes != requested_codes:
        lines.append(f"**BIS codes:** {', '.join(resolved_codes)}  ")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Latest Policy Rate Snapshot",
            "",
            snapshot.to_markdown(
                index=False,
                colalign=(
                    "left",
                    "right",
                    "left",
                    "right",
                    "left",
                    "left",
                    "right",
                ),
            ),
            "",
            (
                "*Monthly Δ compares the latest observation with "
                "the final available observation before the current "
                "month. ↑ indicates a hike, ↓ a cut, and — no change.*"
            ),
            "",
        ]
    )

    if coverage_issues:
        lines.extend(
            _coverage_warning(
                coverage_issues,
                start_date,
            )
        )

    lines.extend(
        [
            "---",
            "",
            "## Policy Rate Developments",
            "",
            (
                "Policy-rate developments across the selected economies "
                "over the reporting period."
            ),
            "",
            f"![Policy rate developments]({chart_path.name})",
            "",
            (
                "*Figure 1. Central-bank policy rates over time. "
                "Daily observations are shown where available, with "
                "monthly observations used as a fallback.*"
            ),
            "",
            "---",
            "",
            "## Methodology",
            "",
            (
                "Daily observations are used when available, with monthly "
                "observations used as a fallback. Monthly change compares "
                "the latest policy rate with the final available observation "
                "before the current month."
            ),
            "",
            (
                "The last change is the most recent non-zero policy-rate "
                "move within the selected reporting period. Days since "
                "change is measured from that observation to the latest "
                "available observation. Missing BIS observations are "
                "retained during transformation but excluded from "
                "calculations."
            ),
            "",
            "## Data Source",
            "",
            "**Bank for International Settlements (BIS)**  ",
            "Central bank policy rates — bulk-download dataset.",
            "",
        ]
    )

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return report_path


def _find_coverage_issues(
    history: pd.DataFrame,
    summary: pd.DataFrame,
    requested_codes: list[str],
    resolved_codes: list[str],
) -> list[dict]:
    """Find requested countries absent from the summary."""
    reported_codes = set(summary["country_code"].astype(str))

    issues = []

    for requested_code, country_code in zip(
        requested_codes,
        resolved_codes,
    ):
        if country_code in reported_codes:
            continue

        country = history.loc[history["country_code"].eq(country_code)]

        if country.empty:
            issues.append(
                {
                    "requested_code": requested_code,
                    "country_code": country_code,
                    "country_name": country_code,
                    "latest_date": pd.NaT,
                    "latest_rate": pd.NA,
                    "compilation": "",
                }
            )
            continue

        valid = country.loc[
            country["observation_date"].notna() & country["observation_value"].notna()
        ].sort_values("observation_date")

        names = country["country_name"].dropna()

        country_name = names.iloc[-1] if not names.empty else country_code

        if valid.empty:
            issues.append(
                {
                    "requested_code": requested_code,
                    "country_code": country_code,
                    "country_name": country_name,
                    "latest_date": pd.NaT,
                    "latest_rate": pd.NA,
                    "compilation": "",
                }
            )
            continue

        latest = valid.iloc[-1]
        compilation = latest.get("compilation", "")

        issues.append(
            {
                "requested_code": requested_code,
                "country_code": country_code,
                "country_name": country_name,
                "latest_date": latest["observation_date"],
                "latest_rate": latest["observation_value"],
                "compilation": (
                    "" if pd.isna(compilation) else str(compilation).strip()
                ),
            }
        )

    return issues


def _coverage_warning(
    issues: list[dict],
    start_date: pd.Timestamp | None,
) -> list[str]:
    """Build the report coverage warning."""
    missing = ", ".join(issue["country_name"] for issue in issues)

    lines = [
        "> [!WARNING]",
        (
            f"> **Incomplete coverage:** {missing} could not be "
            "included in the current policy-rate snapshot."
        ),
        ">",
    ]

    for issue in issues:
        name = issue["country_name"]
        requested = issue["requested_code"]
        code = issue["country_code"]

        if requested == code:
            lines.append(f"> ### {name} ({code})")
        else:
            lines.append(f"> ### {name} ({requested} → {code})")

        lines.append(">")

        latest_date = issue["latest_date"]
        latest_rate = issue["latest_rate"]

        if pd.isna(latest_date) or pd.isna(latest_rate):
            lines.extend(
                [
                    (
                        "> No usable policy-rate observations were found "
                        "for this series in the processed BIS dataset."
                    ),
                    ">",
                ]
            )
            continue

        latest_date = pd.Timestamp(latest_date)

        if start_date is not None and latest_date < start_date:
            lines.extend(
                [
                    (
                        f"> No policy-rate observations are available "
                        f"for {name} on or after "
                        f"**{start_date:%Y-%m-%d}**."
                    ),
                    ">",
                ]
            )

        lines.append(
            f"> The most recent available BIS observation is "
            f"**{float(latest_rate):.4f}%** on "
            f"**{latest_date:%Y-%m-%d}**."
        )

        compilation = issue["compilation"]

        if compilation:
            lines.extend(
                [
                    ">",
                    "> **BIS metadata**",
                    ">",
                ]
            )

            lines.extend(
                f"> {line}" for line in compilation.splitlines() if line.strip()
            )

        lines.append(">")

    lines.append("")

    return lines


def _format_last_move(
    row: pd.Series,
) -> str:
    """Format the most recent rate move."""
    value = row["last_change_size"]

    if pd.isna(value):
        return ""

    if row["policy_direction"] == "cut":
        return f"↓ {abs(value):.4f} pp"

    if row["policy_direction"] == "hike":
        return f"↑ {abs(value):.4f} pp"

    return "—"


def _normalize_country_codes(
    countries: list[str] | tuple[str, ...],
) -> list[str]:
    """Normalize country codes while preserving input order."""
    codes = []

    for country in countries:
        code = country.strip().upper()

        if code and code not in codes:
            codes.append(code)

    return codes


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
