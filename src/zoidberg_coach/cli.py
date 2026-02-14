"""CLI interface for Zoidberg's Running Coach."""

import typer

from zoidberg_coach import __version__
from zoidberg_coach.garmin_client import GarminAuthenticationError, GarminClient, GarminClientError

METERS_PER_MILE = 1609.344

app = typer.Typer(
    name="zoidberg-coach",
    help="Analyze Garmin training data and get half marathon coaching suggestions.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"zoidberg-coach {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit.", callback=version_callback, is_eager=True
    ),
) -> None:
    """Zoidberg's Running Coach - your AI half marathon training companion."""


def _format_pace(duration_seconds: float, distance_meters: float) -> str:
    """Format pace as min:sec per mile."""
    if duration_seconds <= 0 or distance_meters <= 0:
        return "N/A"

    miles = distance_meters / METERS_PER_MILE
    seconds_per_mile = duration_seconds / miles
    minutes = int(seconds_per_mile // 60)
    seconds = int(round(seconds_per_mile % 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d} /mi"


@app.command()
def activities(
    days: int = typer.Option(30, "--days", "-d", min=1, help="Number of trailing days to fetch."),
) -> None:
    """List recent Garmin activities with distance and pace."""
    try:
        client = GarminClient()
        recent_activities = client.get_activities(days=days)
    except GarminAuthenticationError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    except GarminClientError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)

    if not recent_activities:
        typer.echo("No activities found for the selected period.")
        return

    typer.echo("Date | Type | Name | Distance | Pace")
    for activity in recent_activities:
        distance_meters = float(activity["distance"])
        duration_seconds = float(activity["duration"])
        miles = distance_meters / METERS_PER_MILE
        pace = _format_pace(duration_seconds, distance_meters)
        typer.echo(
            f"{activity['date']} | {activity['type']} | {activity['name']} | "
            f"{miles:.2f} mi | {pace}"
        )
