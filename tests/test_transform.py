import pandas as pd
import pytest

from bis_prates.transform import tidy_policy_rates


def make_raw_row(
    *,
    frequency: str = "D: Daily",
    reference_area: str = "CH: Switzerland",
    time_period: str = "2026-08-25",
    observation_value: str = "0.00",
) -> dict[str, object]:
    """Create one minimal BIS policy-rate observation for testing."""
    return {
        "FREQ:Frequency": frequency,
        "REF_AREA:Reference area": reference_area,
        "TIME_PERIOD:Time period or range": time_period,
        "OBS_VALUE:Observation Value": observation_value,
        "TITLE:Title": "Central bank policy rate",
        "UNIT_MEASURE:Unit of measure": "Percent",
        "UNIT_MULT:Unit Multiplier": "Units",
        "TIME_FORMAT:Time Format": "P1D",
        "COMPILATION:Compilation": "Test compilation",
        "DECIMALS:Decimals": "2: Two",
        "SOURCE_REF:Publication Source": "Test source",
        "SUPP_INFO_BREAKS:Supplemental information and breaks": None,
        "OBS_STATUS:Observation Status": "A",
        "OBS_CONF:Observation confidentiality": None,
        "OBS_PRE_BREAK:Pre-Break Observation": None,
    }


def test_tidy_policy_rates_parses_bis_fields() -> None:
    raw = pd.DataFrame([make_raw_row()])

    result = tidy_policy_rates(raw)

    assert len(result) == 1

    row = result.iloc[0]

    assert row["frequency"] == "D"
    assert row["country_code"] == "CH"
    assert row["country_name"] == "Switzerland"
    assert row["observation_value"] == pytest.approx(0.0)
    assert row["observation_date"] == pd.Timestamp("2026-08-25")
    assert row["decimals"] == 2


def test_tidy_policy_rates_parses_monthly_date_as_month_end() -> None:
    raw = pd.DataFrame(
        [
            make_raw_row(
                frequency="M: Monthly",
                time_period="2026-07",
            )
        ]
    )

    result = tidy_policy_rates(raw)

    assert result.loc[0, "frequency"] == "M"
    assert result.loc[0, "observation_date"] == pd.Timestamp("2026-07-31")


def test_tidy_policy_rates_drops_exact_duplicates() -> None:
    row = make_raw_row()

    raw = pd.DataFrame(
        [
            row,
            row.copy(),
        ]
    )

    result = tidy_policy_rates(raw)

    assert len(result) == 1


def test_tidy_policy_rates_rejects_conflicting_duplicates() -> None:
    raw = pd.DataFrame(
        [
            make_raw_row(observation_value="1.00"),
            make_raw_row(observation_value="1.25"),
        ]
    )

    with pytest.raises(
        ValueError,
        match="Conflicting observations",
    ):
        tidy_policy_rates(raw)
