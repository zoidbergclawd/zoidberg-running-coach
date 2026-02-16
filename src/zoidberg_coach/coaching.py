"""Coaching logic: readiness scoring, workout suggestions, race readiness."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

METERS_PER_MILE = 1609.344


def readiness_score(
    sleep_score: float,
    hrv_last_night: float,
    hrv_weekly_avg: float,
    body_battery: float,
    recent_load_miles: float,
    avg_weekly_miles: float,
) -> dict[str, Any]:
    """Compute a 0-100 readiness score.

    Weights: sleep quality (30%), HRV vs baseline (30%), body battery (20%), fatigue (20%).
    """
    # Sleep component (0-30): sleep_score is 0-100 from Garmin
    sleep_component = min(sleep_score, 100) * 0.30

    # HRV component (0-30): ratio of last night to weekly average
    if hrv_weekly_avg > 0:
        hrv_ratio = hrv_last_night / hrv_weekly_avg
        hrv_component = min(hrv_ratio, 1.5) / 1.5 * 100 * 0.30
    else:
        hrv_component = 15.0  # neutral if no baseline

    # Body battery component (0-20): body_battery is 0-100
    bb_component = min(body_battery, 100) * 0.20

    # Fatigue component (0-20): inverse of load ratio
    if avg_weekly_miles > 0:
        load_ratio = recent_load_miles / avg_weekly_miles
        fatigue_score = max(0, min(100, (2.0 - load_ratio) / 2.0 * 100))
    else:
        fatigue_score = 50.0
    fatigue_component = fatigue_score * 0.20

    score = sleep_component + hrv_component + bb_component + fatigue_component
    score = max(0, min(100, round(score)))

    if score < 50:
        interpretation = "Rest day recommended"
    elif score < 70:
        interpretation = "Easy effort only"
    elif score < 85:
        interpretation = "Normal training"
    else:
        interpretation = "Ready for hard effort"

    return {
        "score": score,
        "interpretation": interpretation,
        "components": {
            "sleep": round(sleep_component, 1),
            "hrv": round(hrv_component, 1),
            "body_battery": round(bb_component, 1),
            "fatigue": round(fatigue_component, 1),
        },
    }


def suggest_workout(
    readiness: int,
    days_since_hard: int,
    days_until_race: int | None,
    weekly_mileage: float,
) -> dict[str, Any]:
    """Generate a daily workout suggestion based on readiness and context."""
    if readiness < 50:
        return {
            "type": "rest",
            "description": "Rest day — your body needs recovery.",
            "duration_minutes": 0,
            "intensity": "none",
        }

    if readiness < 70:
        base_minutes = max(20, min(45, weekly_mileage * 2))
        return {
            "type": "easy_run",
            "description": "Easy recovery run. Keep heart rate in Zone 1-2.",
            "duration_minutes": round(base_minutes),
            "intensity": "easy",
        }

    # Taper logic
    if days_until_race is not None and days_until_race <= 14:
        if days_until_race <= 3:
            return {
                "type": "shakeout",
                "description": "Short shakeout run. Stay loose for race day.",
                "duration_minutes": 20,
                "intensity": "easy",
            }
        return {
            "type": "easy_run",
            "description": "Taper period — easy effort, reduced volume.",
            "duration_minutes": 30,
            "intensity": "easy",
        }

    # Ready for quality work and it's been a while
    if days_since_hard >= 3 and readiness >= 70:
        base_minutes = max(30, min(60, weekly_mileage * 2.5))
        return {
            "type": "tempo",
            "description": "Tempo run or intervals. Push into Zone 3-4 for the main set.",
            "duration_minutes": round(base_minutes),
            "intensity": "moderate-hard",
        }

    # Normal day
    base_minutes = max(30, min(50, weekly_mileage * 2))
    return {
        "type": "easy_run",
        "description": "Standard easy run. Build aerobic base.",
        "duration_minutes": round(base_minutes),
        "intensity": "easy",
    }


def race_readiness(
    activities: list[dict[str, Any]],
    target_date: date,
    goal_time_seconds: float | None = None,
) -> dict[str, Any]:
    """Assess half marathon race readiness."""
    today = date.today()
    days_until = (target_date - today).days

    # Analyze recent 8 weeks of running
    cutoff = today - timedelta(weeks=8)
    runs = [
        a for a in activities
        if "run" in str(a.get("type", "")).lower()
        and _parse_date(a["date"]) is not None
        and _parse_date(a["date"]) >= cutoff  # type: ignore[operator]
    ]

    # Longest run
    longest_miles = 0.0
    for r in runs:
        miles = float(r.get("distance", 0)) / METERS_PER_MILE
        if miles > longest_miles:
            longest_miles = miles

    # Weekly mileage (last 4 full weeks)
    weekly_miles: list[float] = []
    for w in range(4):
        week_start = today - timedelta(weeks=w + 1)
        week_end = week_start + timedelta(days=6)
        week_total = sum(
            float(r.get("distance", 0)) / METERS_PER_MILE
            for r in runs
            if _parse_date(r["date"]) is not None
            and week_start <= _parse_date(r["date"]) <= week_end  # type: ignore[operator]
        )
        weekly_miles.append(week_total)

    avg_weekly = sum(weekly_miles) / len(weekly_miles) if weekly_miles else 0

    # Find best recent pace for prediction (Riegel formula)
    best_pace_per_mile = float("inf")
    best_distance_miles = 0.0
    best_duration_seconds = 0.0
    for r in runs:
        dist_miles = float(r.get("distance", 0)) / METERS_PER_MILE
        dur = float(r.get("duration", 0))
        if dist_miles >= 3.0 and dur > 0:
            pace = dur / dist_miles
            if pace < best_pace_per_mile:
                best_pace_per_mile = pace
                best_distance_miles = dist_miles
                best_duration_seconds = dur

    # Riegel prediction for half marathon (13.1 miles)
    predicted_time_seconds = None
    if best_distance_miles >= 3.0 and best_duration_seconds > 0:
        predicted_time_seconds = best_duration_seconds * (13.1 / best_distance_miles) ** 1.06

    # Gaps analysis
    gaps: list[str] = []
    if longest_miles < 10:
        gaps.append(f"Need more long runs (longest: {longest_miles:.1f} mi, target: 10+ mi)")
    if avg_weekly < 15:
        gaps.append(f"Weekly mileage too low (avg: {avg_weekly:.1f} mi, target: 15+ mi)")
    if len(runs) < 12:
        gaps.append(f"Inconsistent training (only {len(runs)} runs in 8 weeks)")

    # Overall assessment
    score = 0
    if longest_miles >= 10:
        score += 35
    elif longest_miles >= 8:
        score += 20
    if avg_weekly >= 20:
        score += 35
    elif avg_weekly >= 15:
        score += 20
    if len(runs) >= 20:
        score += 30
    elif len(runs) >= 12:
        score += 15

    return {
        "days_until_race": days_until,
        "target_date": target_date.isoformat(),
        "longest_run_miles": round(longest_miles, 1),
        "avg_weekly_miles": round(avg_weekly, 1),
        "total_runs_8wk": len(runs),
        "predicted_finish_seconds": round(predicted_time_seconds) if predicted_time_seconds else None,
        "readiness_score": min(score, 100),
        "gaps": gaps,
        "goal_time_seconds": goal_time_seconds,
    }


def _parse_date(date_str: str) -> date | None:
    """Parse a YYYY-MM-DD date string."""
    try:
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
