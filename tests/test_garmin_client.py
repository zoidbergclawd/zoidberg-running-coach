"""Tests for Item 2: Garmin Client & activities fetching."""

from __future__ import annotations

from datetime import date

import pytest

from zoidberg_coach.garmin_client import GarminClient


class _FakeDate(date):
    @classmethod
    def today(cls) -> "_FakeDate":
        return cls(2026, 2, 14)


def test_garmin_client_uses_env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Client should prioritize GARTH_TOKEN when present."""
    calls: list[str] = []

    def fake_configure(*, domain: str) -> None:
        assert domain == "garmin.com"

    def fake_resume(value: str) -> None:
        calls.append(value)

    monkeypatch.setenv("GARTH_TOKEN", "token-from-env")
    monkeypatch.setattr("zoidberg_coach.garmin_client.garth.configure", fake_configure)
    monkeypatch.setattr("zoidberg_coach.garmin_client.garth.resume", fake_resume)

    GarminClient(token_path="/tmp/should-not-be-used")

    assert calls == ["token-from-env"]


def test_get_activities_maps_fields_and_filters_by_days(monkeypatch: pytest.MonkeyPatch) -> None:
    """Activities should be normalized to expected fields and old activities dropped."""
    api_calls: list[tuple[str, dict[str, int]]] = []

    def fake_configure(*, domain: str) -> None:
        assert domain == "garmin.com"

    def fake_resume(value: str) -> None:
        assert value

    def fake_connectapi(endpoint: str, params: dict[str, int]) -> list[dict[str, object]]:
        api_calls.append((endpoint, params))
        return [
            {
                "activityId": 123,
                "activityName": "Morning Run",
                "activityType": {"typeKey": "running"},
                "startTimeLocal": "2026-02-12 06:30:00",
                "distance": 5000.0,
                "duration": 1500.0,
            },
            {
                "activityId": 456,
                "activityName": "Old Run",
                "activityType": {"typeKey": "running"},
                "startTimeLocal": "2026-01-01 06:30:00",
                "distance": 10000.0,
                "duration": 3600.0,
            },
        ]

    monkeypatch.setenv("GARTH_TOKEN", "test-token")
    monkeypatch.setattr("zoidberg_coach.garmin_client.garth.configure", fake_configure)
    monkeypatch.setattr("zoidberg_coach.garmin_client.garth.resume", fake_resume)
    monkeypatch.setattr("zoidberg_coach.garmin_client.garth.connectapi", fake_connectapi)
    monkeypatch.setattr("zoidberg_coach.garmin_client.date", _FakeDate)

    client = GarminClient()
    activities = client.get_activities(days=14)

    assert api_calls == [
        (
            "/activitylist-service/activities/search/activities",
            {"limit": 200, "start": 0},
        )
    ]
    assert activities == [
        {
            "id": 123,
            "name": "Morning Run",
            "type": "running",
            "date": "2026-02-12",
            "distance": 5000.0,
            "duration": 1500.0,
        }
    ]


def test_get_activities_rejects_non_positive_days(monkeypatch: pytest.MonkeyPatch) -> None:
    """Days must be a positive integer."""

    def fake_configure(*, domain: str) -> None:
        assert domain == "garmin.com"

    def fake_resume(value: str) -> None:
        assert value

    monkeypatch.setenv("GARTH_TOKEN", "test-token")
    monkeypatch.setattr("zoidberg_coach.garmin_client.garth.configure", fake_configure)
    monkeypatch.setattr("zoidberg_coach.garmin_client.garth.resume", fake_resume)

    client = GarminClient()

    with pytest.raises(ValueError):
        client.get_activities(days=0)
