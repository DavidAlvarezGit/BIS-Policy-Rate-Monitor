import pandas as pd
import pytest

from bis_prates.summary import summarize_policy_rates


def test_summarize_policy_rates_calculates_changes() -> None:
    data = pd.DataFrame(
        {
            "country_code": ["CH", "CH", "CH", "CH"],
            "country_name": [
                "Switzerland",
                "Switzerland",
                "Switzerland",
                "Switzerland",
            ],
            "frequency": ["D", "D", "D", "D"],
            "title": ["Central bank policy rate"] * 4,
            "unit_measure": ["Per cent per year"] * 4,
            "unit_multiplier": ["Units"] * 4,
            "decimals": [2] * 4,
            "compilation": [""] * 4,
            "observation_date": pd.to_datetime(
                [
                    "2026-06-30",
                    "2026-07-15",
                    "2026-07-31",
                    "2026-08-25",
                ]
            ),
            "observation_value": [
                2.00,
                2.25,
                2.25,
                2.50,
            ],
        }
    )

    result = summarize_policy_rates(
        data,
        countries=["CH"],
        start="2026-01-01",
    )

    assert len(result) == 1

    row = result.iloc[0]

    assert row["country_code"] == "CH"
    assert row["latest_rate"] == pytest.approx(2.50)
    assert row["latest_date"] == pd.Timestamp("2026-08-25")

    assert row["previous_month_end_rate"] == pytest.approx(2.25)
    assert row["previous_month_end_date"] == pd.Timestamp("2026-07-31")

    assert row["change_vs_previous_month_end"] == pytest.approx(0.25)

    assert row["last_change_size"] == pytest.approx(0.25)
    assert row["last_change_date"] == pd.Timestamp("2026-08-25")
    assert row["policy_direction"] == "hike"


def test_summarize_policy_rates_prefers_daily_frequency() -> None:
    data = pd.DataFrame(
        {
            "country_code": ["CH", "CH", "CH"],
            "country_name": [
                "Switzerland",
                "Switzerland",
                "Switzerland",
            ],
            "frequency": ["M", "D", "D"],
            "title": ["Central bank policy rate"] * 3,
            "unit_measure": ["Per cent per year"] * 3,
            "unit_multiplier": ["Units"] * 3,
            "decimals": [2] * 3,
            "compilation": [""] * 3,
            "observation_date": pd.to_datetime(
                [
                    "2026-08-31",
                    "2026-07-31",
                    "2026-08-25",
                ]
            ),
            "observation_value": [
                9.99,
                1.00,
                1.25,
            ],
        }
    )

    result = summarize_policy_rates(
        data,
        countries=["CH"],
        start="2026-01-01",
    )

    row = result.iloc[0]

    assert row["frequency"] == "D"
    assert row["latest_rate"] == pytest.approx(1.25)
