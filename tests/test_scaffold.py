"""Tests for Item 1: Project Scaffold."""

import importlib
import subprocess
import sys


def test_package_importable():
    """zoidberg_coach package can be imported."""
    import zoidberg_coach

    assert zoidberg_coach is not None


def test_version_defined():
    """Package has a __version__ string."""
    from zoidberg_coach import __version__

    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_cli_app_exists():
    """CLI app object exists and is a Typer instance."""
    from zoidberg_coach.cli import app

    import typer

    assert isinstance(app, typer.Typer)


def test_main_module_structure():
    """__main__.py imports app from cli module."""
    # Verify __main__ module can be imported and has the right structure
    import zoidberg_coach.__main__ as main_mod

    assert hasattr(main_mod, "app")


def test_cli_help_runs():
    """zoidberg-coach --help exits 0 and shows usage info."""
    result = subprocess.run(
        [sys.executable, "-m", "zoidberg_coach", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "options" in result.stdout.lower()


def test_cli_version_flag():
    """zoidberg-coach --version shows version string."""
    result = subprocess.run(
        [sys.executable, "-m", "zoidberg_coach", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_no_args_shows_help():
    """Running with no args shows help text (no_args_is_help=True)."""
    result = subprocess.run(
        [sys.executable, "-m", "zoidberg_coach"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # Typer's no_args_is_help shows usage info; exit code may be 0 or 2
    assert "usage" in result.stdout.lower() or "options" in result.stdout.lower()
