import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import msgspec
import requests
from bs4 import BeautifulSoup
from pysdmx.api.qb import (
    ApiVersion,
    RestService,
    StructureQuery,
    StructureType,
)
from pysdmx.io.json.sdmxjson2.messages.code import JsonCodelistMessage

BIS_BULK_DOWNLOADS_URL = "https://data.bis.org/bulkdownload"
BIS_SDMX_API_URL = "https://stats.bis.org/api/v2"

BULK_FILENAME_PATTERN = re.compile(
    r"(?P<code>.+?)_csv_(?P<fmt>.+?)\.zip",
    re.IGNORECASE,
)


def discover_bulk_downloads(
    page_url: str = BIS_BULK_DOWNLOADS_URL,
) -> list[dict[str, str]]:
    """Discover BIS CSV bulk-download ZIP files."""
    response = requests.get(page_url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    downloads: list[dict[str, str]] = []

    for link in soup.find_all("a", href=True):
        url = urljoin(response.url, link["href"])
        filename = urlsplit(url).path.rsplit("/", 1)[-1]

        match = BULK_FILENAME_PATTERN.fullmatch(filename)

        if match is None:
            continue

        downloads.append(
            {
                "code": match.group("code"),
                "format": match.group("fmt"),
                "filename": filename,
                "url": url,
            }
        )
    if not downloads:
        raise RuntimeError(
            f"No BIS CSV bulk-download ZIP links found at {response.url}. "
            "The page content or filename convention may have changed."
        )

    return downloads


def fetch_dataset(
    dataset_code: str = "WS_CBPOL",
    fmt: str = "flat",
    destination_dir: Path | str = Path("data/raw"),
    refresh: bool = False,
) -> Path:
    """Download and cache a BIS bulk dataset."""
    matches = [
        dataset
        for dataset in discover_bulk_downloads()
        if dataset["code"].casefold() == dataset_code.casefold()
        and dataset["format"].casefold() == fmt.casefold()
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one BIS dataset for "
            f"code={dataset_code!r}, format={fmt!r}; "
            f"found {len(matches)}."
        )

    dataset = matches[0]

    destination = Path(destination_dir) / dataset["filename"]
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.is_file() and not refresh:
        return destination

    with requests.get(
        dataset["url"],
        timeout=30,
        stream=True,
    ) as response:
        response.raise_for_status()
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=4 * 1024 * 1024):
                file.write(chunk)

    return destination


def fetch_reference_area(
    destination: Path | str = Path("data/raw/reference_areas.json"),
    refresh: bool = False,
) -> Path:
    """Fetch and cache the BIS reference-area codelist."""
    destination = Path(destination)

    if destination.is_file() and not refresh:
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)

    service = RestService(
        "https://stats.bis.org/api/v2",
        ApiVersion.V2_0_0,
    )

    response = service.structure(
        StructureQuery(
            StructureType.CODELIST,
            "BIS",
            "CL_BIS_GL_REF_AREA",
            "latest",
        )
    )

    codelist = msgspec.json.Decoder(JsonCodelistMessage).decode(response).to_model()

    reference_areas = {code.id: code.name for code in codelist.codes}

    destination.write_text(
        json.dumps(reference_areas, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return destination
