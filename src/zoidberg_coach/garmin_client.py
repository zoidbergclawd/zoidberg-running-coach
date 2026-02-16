"""Garmin Connect client wrapper using the garth library."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

import garth

DEFAULT_TOKEN_PATH = "~/.garth"
DEFAULT_DOMAIN = "garmin.com"
ACTIVITY_SEARCH_ENDPOINT = "/activitylist-service/activities/search/activities"
ACTIVITY_SPLITS_ENDPOINT = "/activity-service/activity/{id}/splits"
ACTIVITY_DETAIL_ENDPOINT = "/activity-service/activity/{id}"
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

    def get_activity_details(self, activity_id: int) -> dict[str, Any]:
        """Fetch detailed activity data including splits and heart rate."""
        try:
            splits_resp = garth.connectapi(
                ACTIVITY_SPLITS_ENDPOINT.format(id=activity_id),
            )
        except Exception as exc:
            raise GarminClientError(f"Failed to fetch splits for activity {activity_id}: {exc}") from exc

        splits: list[dict[str, Any]] = []
        if isinstance(splits_resp, dict):
            raw_splits = splits_resp.get("lapDTOs", [])
            if not isinstance(raw_splits, list):
                raw_splits = []
            for i, lap in enumerate(raw_splits):
                if not isinstance(lap, dict):
                    continue
                splits.append({
                    "lap": i + 1,
                    "distance": float(lap.get("distance", 0.0)),
                    "duration": float(lap.get("duration", 0.0)),
                    "avg_hr": float(lap.get("averageHR", 0.0)),
                    "max_hr": float(lap.get("maxHR", 0.0)),
                    "avg_speed": float(lap.get("averageSpeed", 0.0)),
                })

        # Also fetch the activity summary for overall HR data
        try:
            detail_resp = garth.connectapi(
                ACTIVITY_DETAIL_ENDPOINT.format(id=activity_id),
            )
        except Exception:
            detail_resp = {}

        summary: dict[str, Any] = {}
        if isinstance(detail_resp, dict):
            summary = {
                "activity_id": activity_id,
                "name": str(detail_resp.get("activityName", "")),
                "avg_hr": float(detail_resp.get("averageHR", 0.0)),
                "max_hr": float(detail_resp.get("maxHR", 0.0)),
                "distance": float(detail_resp.get("distance", 0.0)),
                "duration": float(detail_resp.get("duration", 0.0)),
                "calories": float(detail_resp.get("calories", 0.0)),
            }

        return {"summary": summary, "splits": splits}

    def get_sleep(self, target_date: date | None = None) -> dict[str, Any]:
        """Fetch sleep data for a given date using garth data classes."""
        target_date = target_date or date.today()
        try:
            sleep = garth.DailySleep.get(target_date)
            if sleep is None:
                return {"date": target_date.isoformat(), "score": 0, "duration_seconds": 0}
            # garth DailySleep has .score, .start, .end, etc.
            return {
                "date": target_date.isoformat(),
                "score": getattr(sleep, "score", 0) or 0,
                "duration_seconds": getattr(sleep, "sleep_time_seconds", 0) or 0,
            }
        except Exception:
            return {"date": target_date.isoformat(), "score": 0, "duration_seconds": 0}

    def get_hrv(self, target_date: date | None = None) -> dict[str, Any]:
        """Fetch HRV data for a given date."""
        target_date = target_date or date.today()
        try:
            hrv = garth.HRVData.get(target_date)
            if hrv is None:
                return {"date": target_date.isoformat(), "weekly_avg": 0, "last_night": 0, "status": "unknown"}
            return {
                "date": target_date.isoformat(),
                "weekly_avg": getattr(hrv, "weekly_avg", 0) or 0,
                "last_night": getattr(hrv, "last_night", 0) or 0,
                "status": getattr(hrv, "status", "unknown") or "unknown",
            }
        except Exception:
            return {"date": target_date.isoformat(), "weekly_avg": 0, "last_night": 0, "status": "unknown"}

    def get_body_battery(self, target_date: date | None = None) -> dict[str, Any]:
        """Fetch body battery data for a given date."""
        target_date = target_date or date.today()
        try:
            bb = garth.DailyBodyBattery.get(target_date)
            if bb is None:
                return {"date": target_date.isoformat(), "highest": 0, "lowest": 0, "current": 0}
            body_battery_list = getattr(bb, "body_battery", []) or []
            values = [v for v in body_battery_list if isinstance(v, (int, float))]
            return {
                "date": target_date.isoformat(),
                "highest": max(values) if values else 0,
                "lowest": min(values) if values else 0,
                "current": values[-1] if values else 0,
            }
        except Exception:
            return {"date": target_date.isoformat(), "highest": 0, "lowest": 0, "current": 0}

    def get_stress(self, target_date: date | None = None) -> dict[str, Any]:
        """Fetch stress data for a given date."""
        target_date = target_date or date.today()
        try:
            stress = garth.DailyStress.get(target_date)
            if stress is None:
                return {"date": target_date.isoformat(), "avg_stress": 0, "max_stress": 0}
            return {
                "date": target_date.isoformat(),
                "avg_stress": getattr(stress, "avg_stress_level", 0) or 0,
                "max_stress": getattr(stress, "max_stress_level", 0) or 0,
            }
        except Exception:
            return {"date": target_date.isoformat(), "avg_stress": 0, "max_stress": 0}

    def get_user_hr_zones(self) -> list[dict[str, Any]]:
        """Fetch user heart rate zones from Garmin settings."""
        try:
            settings = garth.UserSettings.get()
            if settings is None:
                return []
            zones = getattr(settings, "heart_rate_zones", None)
            if zones and isinstance(zones, list):
                return [{"zone": i + 1, "low": z.get("low", 0), "high": z.get("high", 0)}
                        for i, z in enumerate(zones) if isinstance(z, dict)]
        except Exception:
            pass
        return []

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
            "avg_hr": float(activity.get("averageHR", 0.0)),
            "max_hr": float(activity.get("maxHR", 0.0)),
        }
