from pathlib import Path

import pandas as pd

from bis_prates.report import generate_report
from bis_prates.summary import summarize_policy_rates, write_summary


def test_generate_report_writes_expected_artifacts(tmp_path: Path) -> None:
    history = pd.DataFrame(
        {
            "country_code": ["CH", "CH", "CH"],
            "country_name": ["Switzerland"] * 3,
            "frequency": ["D", "D", "D"],
            "title": ["Central bank policy rate"] * 3,
            "unit_measure": ["Per cent per year"] * 3,
            "unit_multiplier": ["Units"] * 3,
            "decimals": [2] * 3,
            "compilation": [""] * 3,
            "observation_date": pd.to_datetime(
                ["2026-06-30", "2026-07-31", "2026-08-25"]
            ),
            "observation_value": [0.25, 0.25, 0.0],
        }
    )

    data_path = tmp_path / "policy_rates.csv"
    output_dir = tmp_path / "out"

    history.to_csv(data_path, index=False)

    summary = summarize_policy_rates(
        history,
        countries=["CH"],
        start="2026-01-01",
    )
    summary_path, _ = write_summary(summary, output_dir=output_dir)

    report_path, chart_path = generate_report(
        data_path=data_path,
        summary_path=summary_path,
        output_dir=output_dir,
        start="2026-01-01",
        requested_countries=["CH"],
    )

    assert report_path == output_dir / "report.md"
    assert chart_path == output_dir / "policy_rates.png"
    assert report_path.is_file()
    assert chart_path.is_file()
    assert "![Policy rate developments](policy_rates.png)" in report_path.read_text(
        encoding="utf-8"
    )
