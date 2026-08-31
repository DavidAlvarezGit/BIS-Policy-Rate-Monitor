import typer

from bis_prates.ingestion import fetch_dataset, fetch_reference_area
from bis_prates.metadata import load_reference_areas, resolve_country_codes
from bis_prates.report import generate_report
from bis_prates.summary import build_summary, write_summary
from bis_prates.transform import transform as transform_dataset

app = typer.Typer(
    name="bis-prates",
    help="Download, transform, and report BIS central bank policy rates.",
    no_args_is_help=True,
)


@app.command()
def fetch(
    refresh: bool = False,
) -> None:
    """Download and cache BIS policy-rate data and reference metadata."""
    data_path = fetch_dataset(refresh=refresh)
    metadata_path = fetch_reference_area(refresh=refresh)

    typer.echo(f"Dataset:   {data_path}")
    typer.echo(f"Metadata:  {metadata_path}")


@app.command()
def transform() -> None:
    """Transform the raw BIS dataset into a tidy CSV."""
    path = transform_dataset()

    typer.echo(f"Transformed: {path}")


@app.command()
def report(
    countries: str = "US,EA,GB,JP,CH",
    start: str | None = None,
) -> None:
    """Generate the summary, chart, and Markdown report."""
    requested_codes = [
        code.strip().upper() for code in countries.split(",") if code.strip()
    ]

    if not requested_codes:
        raise typer.BadParameter("Provide at least one country code.")

    reference_areas = load_reference_areas()

    try:
        country_codes = resolve_country_codes(
            requested_codes,
            reference_areas,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    summary = build_summary(
        countries=country_codes,
        start=start,
    )

    csv_path, json_path = write_summary(
        summary,
        start=start,
        requested_countries=requested_codes,
        resolved_countries=country_codes,
    )

    report_path, chart_path = generate_report(
        summary_path=csv_path,
        start=start,
        requested_countries=requested_codes,
    )

    typer.echo(f"Summary CSV:  {csv_path}")
    typer.echo(f"Summary JSON: {json_path}")
    typer.echo(f"Chart:        {chart_path}")
    typer.echo(f"Report:       {report_path}")


if __name__ == "__main__":
    app()
