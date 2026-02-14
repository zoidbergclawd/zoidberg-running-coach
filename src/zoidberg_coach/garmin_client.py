"""Garmin Connect client wrapper using the garth library."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

import garth

DEFAULT_TOKEN_PATH = "~/.garth"
DEFAULT_DOMAIN = "garmin.com"
ACTIVITY_SEARCH_ENDPOINT = "/activitylist-service/activities/search/activities"
ACTIVITY_PAGE_LIMIT = 200


class GarminClientError(RuntimeError):
    """Base error for Garmin client failures."""


class GarminAuthenticationError(GarminClientError):
    """Raised when authentication to Garmin Connect cannot be established."""


class GarminClient:
    """Client for fetching Garmin Connect data."""

    def __init__(self, token_path: str = DEFAULT_TOKEN_PATH, domain: str = DEFAULT_DOMAIN) -> None:
        """Initialize and authenticate the Garmin client."""
        self._token_path = token_path
        self._domain = domain
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate using GARTH_TOKEN or a saved garth token path."""
        garth.configure(domain=self._domain)
        token = os.getenv("GARTH_TOKEN")
        try:
            if token:
                garth.resume(token)
            else:
                garth.resume(self._token_path)
        except Exception as exc:  # pragma: no cover - garth raises varying exception types
            raise GarminAuthenticationError(
                "Unable to authenticate with Garmin Connect. "
                "Run `uvx garth login` or set GARTH_TOKEN. "
                f"Details: {exc}"
            ) from exc

    def get_activities(self, days: int = 30) -> list[dict[str, Any]]:
        """Fetch and normalize recent activities from Garmin Connect."""
        if days <= 0:
            raise ValueError("days must be a positive integer")

        try:
            response = garth.connectapi(
                ACTIVITY_SEARCH_ENDPOINT,
                params={"limit": ACTIVITY_PAGE_LIMIT, "start": 0},
            )
        except Exception as exc:  # pragma: no cover - garth raises varying exception types
            raise GarminClientError(f"Failed to fetch activities: {exc}") from exc

        if not isinstance(response, list):
            raise GarminClientError("Garmin activity response was not a list.")

        cutoff = date.today() - timedelta(days=days)
        activities: list[dict[str, Any]] = []

        for activity in response:
            if not isinstance(activity, dict):
                continue
            normalized = self._normalize_activity(activity)
            if normalized is None:
                continue
            if datetime.strptime(normalized["date"], "%Y-%m-%d").date() >= cutoff:
                activities.append(normalized)

        return activities

    def _normalize_activity(self, activity: dict[str, Any]) -> dict[str, Any] | None:
        """Normalize an activity payload to a consistent dictionary."""
        start_time = activity.get("startTimeLocal")
        if not isinstance(start_time, str) or len(start_time) < 10:
            return None

        activity_type = activity.get("activityType")
        if isinstance(activity_type, dict):
            type_name = str(activity_type.get("typeKey", "unknown"))
        else:
            type_name = "unknown"

        return {
            "id": int(activity.get("activityId", 0)),
            "name": str(activity.get("activityName", "Unnamed Activity")),
            "type": type_name,
            "date": start_time[:10],
            "distance": float(activity.get("distance", 0.0)),
            "duration": float(activity.get("duration", 0.0)),
        }
