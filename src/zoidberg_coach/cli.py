"""CLI interface for Zoidberg's Running Coach."""

import typer

from zoidberg_coach import __version__

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
