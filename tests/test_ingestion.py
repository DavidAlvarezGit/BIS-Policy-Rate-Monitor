from pathlib import Path
from unittest.mock import Mock

import pytest

from bis_prates import ingestion


@pytest.fixture(name="sample_html")
def sample_html_fixture() -> str:
    return """
    <h2>Locational banking statistics</h2>
    <a href="/static/bulk/WS_LBS_csv_flat.zip">LBS flat</a>

    <h2>Central bank policy rates</h2>
    <a href="/static/bulk/WS_CBPOL_csv_col.zip">Policy rates column</a>
    <a href="/static/bulk/WS_CBPOL_csv_flat.zip">Policy rates flat</a>
    """


@pytest.fixture(name="discovery_response")
def discovery_response_fixture(sample_html: str) -> Mock:
    response = Mock()
    response.text = sample_html
    response.url = "https://data.bis.org/bulkdownload"
    response.raise_for_status.return_value = None
    return response


def test_discover_bulk_downloads(
    monkeypatch: pytest.MonkeyPatch,
    discovery_response: Mock,
) -> None:
    monkeypatch.setattr(
        ingestion.requests,
        "get",
        lambda *args, **kwargs: discovery_response,
    )

    result = ingestion.discover_bulk_downloads()

    assert result == [
        {
            "code": "WS_LBS",
            "format": "flat",
            "filename": "WS_LBS_csv_flat.zip",
            "url": "https://data.bis.org/static/bulk/WS_LBS_csv_flat.zip",
        },
        {
            "code": "WS_CBPOL",
            "format": "col",
            "filename": "WS_CBPOL_csv_col.zip",
            "url": "https://data.bis.org/static/bulk/WS_CBPOL_csv_col.zip",
        },
        {
            "code": "WS_CBPOL",
            "format": "flat",
            "filename": "WS_CBPOL_csv_flat.zip",
            "url": "https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip",
        },
    ]


def test_fetch_dataset_downloads_matching_zip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    discovered = [
        {
            "code": "WS_CBPOL",
            "format": "flat",
            "filename": "WS_CBPOL_csv_flat.zip",
            "url": "https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip",
        }
    ]

    monkeypatch.setattr(
        ingestion,
        "discover_bulk_downloads",
        lambda: discovered,
    )

    response = Mock()
    response.raise_for_status.return_value = None
    response.iter_content.return_value = [
        b"first chunk",
        b"second chunk",
    ]
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)

    monkeypatch.setattr(
        ingestion.requests,
        "get",
        lambda *args, **kwargs: response,
    )

    path = ingestion.fetch_dataset(
        destination_dir=tmp_path,
    )

    assert path == tmp_path / "WS_CBPOL_csv_flat.zip"
    assert path.read_bytes() == b"first chunksecond chunk"
