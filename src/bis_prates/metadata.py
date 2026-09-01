import json
from pathlib import Path

from rapidfuzz import process

BIS_COUNTRY_CODE_MAP = {
    "EA": "XM",
}


def load_reference_areas(
    path: Path | str = Path("data/raw/reference_areas.json"),
) -> dict[str, str]:
    """Load BIS reference-area codes and names."""
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Reference-area codelist not found: {path}. Run 'bis-prates fetch' first."
        )

    return json.loads(path.read_text(encoding="utf-8"))


def resolve_country_codes(
    codes: list[str],
    reference_areas: dict[str, str],
) -> list[str]:
    """Resolve aliases and validate BIS country/area codes."""
    resolved: list[str] = []

    for code in codes:
        normalized = code.strip().upper()
        bis_code = BIS_COUNTRY_CODE_MAP.get(normalized, normalized)

        if bis_code not in reference_areas:
            suggestion = process.extractOne(
                bis_code,
                reference_areas.keys(),
                score_cutoff=60,
            )

            if suggestion is not None:
                suggested_code = suggestion[0]
                suggested_name = reference_areas[suggested_code]

                raise ValueError(
                    f"Unknown BIS country/area code: {normalized}. "
                    f"Did you mean {suggested_code} "
                    f"({suggested_name})?"
                )

            raise ValueError(f"Unknown BIS country/area code: {normalized}.")

        if bis_code not in resolved:
            resolved.append(bis_code)

    return resolved
