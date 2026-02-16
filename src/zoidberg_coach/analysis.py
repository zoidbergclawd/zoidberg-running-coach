"""Training analysis: weekly summaries and polarization."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

METERS_PER_MILE = 1609.344
# Default HR zones if Garmin zones unavailable (% of max HR ~190)
DEFAULT_ZONE_BOUNDARY = 152  # ~80% of 190 — Zone 1-2 vs Zone 3+


def weekly_summary(activities: list[dict[str, Any]], weeks: int = 8) -> list[dict[str, Any]]:
    """Group running activities into weekly summaries.

    Returns one dict per week with total_miles, total_time, run_count,
    ordered most-recent first.
    """
    today = date.today()
    # Monday-based weeks
    current_monday = today - timedelta(days=today.weekday())

    summaries: list[dict[str, Any]] = []
    for w in range(weeks):
        week_start = current_monday - timedelta(weeks=w)
        week_end = week_start + timedelta(days=6)

        week_activities = [
            a for a in activities
            if _is_running(a) and _in_range(a["date"], week_start, week_end)
        ]

        total_meters = sum(float(a.get("distance", 0)) for a in week_activities)
        total_seconds = sum(float(a.get("duration", 0)) for a in week_activities)

        summaries.append({
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "total_miles": total_meters / METERS_PER_MILE,
            "total_time_seconds": total_seconds,
            "run_count": len(week_activities),
        })

    return summaries


def training_load_trend(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate weekly summaries with 10% rule flags.

    Returns the same summaries with added 'mileage_increase_pct' and 'overload_flag'.
    """
    annotated = []
    for i, week in enumerate(summaries):
        entry = dict(week)
        if i + 1 < len(summaries) and summaries[i + 1]["total_miles"] > 0:
            prev_miles = summaries[i + 1]["total_miles"]
            increase = ((week["total_miles"] - prev_miles) / prev_miles) * 100
            entry["mileage_increase_pct"] = round(increase, 1)
            entry["overload_flag"] = increase > 10
        else:
            entry["mileage_increase_pct"] = 0.0
            entry["overload_flag"] = False
        annotated.append(entry)

    return annotated


def polarization_analysis(
    activities: list[dict[str, Any]],
    weeks: int = 4,
    zone_boundary_hr: float = DEFAULT_ZONE_BOUNDARY,
) -> dict[str, Any]:
    """Analyze 80/20 polarized training distribution.

    Uses avg_hr on each activity to classify easy (Zone 1-2) vs hard (Zone 3+).
    Returns percentages and a recommendation.
    """
    today = date.today()
    cutoff = today - timedelta(weeks=weeks)

    easy_time = 0.0
    hard_time = 0.0

    for a in activities:
        if not _is_running(a):
            continue
        if not _in_range(a["date"], cutoff, today):
            continue
        duration = float(a.get("duration", 0))
        avg_hr = float(a.get("avg_hr", 0))
        if avg_hr <= 0 or duration <= 0:
            continue
        if avg_hr < zone_boundary_hr:
            easy_time += duration
        else:
            hard_time += duration

    total = easy_time + hard_time
    if total == 0:
        return {
            "weeks_analyzed": weeks,
            "easy_pct": 0.0,
            "hard_pct": 0.0,
            "recommendation": "No heart rate data available for analysis.",
        }

    easy_pct = round((easy_time / total) * 100, 1)
    hard_pct = round((hard_time / total) * 100, 1)

    if easy_pct >= 75:
        rec = "Good polarization! Keep maintaining ~80% easy effort."
    elif easy_pct >= 60:
        rec = "Slightly too much intensity. Try slowing down on easy days."
    else:
        rec = "Too much hard running. Risk of overtraining — add more easy miles."

    return {
        "weeks_analyzed": weeks,
        "easy_pct": easy_pct,
        "hard_pct": hard_pct,
        "recommendation": rec,
    }


def _is_running(activity: dict[str, Any]) -> bool:
    """Check if activity is a run."""
    t = str(activity.get("type", "")).lower()
    return "run" in t


def _in_range(date_str: str, start: date, end: date) -> bool:
    """Check if a date string falls within [start, end]."""
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
        return start <= d <= end
    except (ValueError, TypeError):
        return False
