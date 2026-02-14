"""CLI tests for Item 2 activities command."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from zoidberg_coach.cli import app
from zoidberg_coach.garmin_client import GarminAuthenticationError

runner = CliRunner()


class _FakeClient:
    def get_activities(self, *, days: int) -> list[dict[str, object]]:
        assert days == 30
        return [
            {
                "id": 1001,
                "name": "Tempo Run",
                "type": "running",
                "date": "2026-02-13",
                "distance": 1609.344,
                "duration": 480.0,
            }
        ]


class _FailingClient:
    def __init__(self) -> None:
        raise GarminAuthenticationError("Authentication failed")


def test_activities_command_lists_distance_and_pace(monkeypatch: pytest.MonkeyPatch) -> None:
    """activities command should include pace and distance information."""
    monkeypatch.setattr("zoidberg_coach.cli.GarminClient", _FakeClient)

    result = runner.invoke(app, ["activities", "--days", "30"])

    assert result.exit_code == 0
    assert "Tempo Run" in result.stdout
    assert "1.00 mi" in result.stdout
    assert "8:00 /mi" in result.stdout


def test_activities_command_handles_authentication_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """activities command should exit non-zero when auth fails."""
    monkeypatch.setattr("zoidberg_coach.cli.GarminClient", _FailingClient)

    result = runner.invoke(app, ["activities"])

    assert result.exit_code == 1
    assert "Authentication failed" in result.stdout
