"""Pattern detection and inference engine for training data."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

METERS_PER_MILE = 1609.344


def weekly_pattern_report(
    activities: list[dict[str, Any]],
    sleep_data: list[dict[str, Any]] | None = None,
    hrv_data: list[dict[str, Any]] | None = None,
    weeks: int = 8,
) -> list[str]:
    """Generate actionable insights from training patterns.

    Returns a list of human-readable insight strings.
    """
    insights: list[str] = []

    runs = _get_runs(activities, weeks)
    if not runs:
        return ["Not enough running data for pattern analysis."]

    insights.extend(_day_of_week_patterns(runs))
    insights.extend(_distance_pace_patterns(runs))

    if sleep_data:
        insights.extend(_sleep_performance_correlation(runs, sleep_data))

    if hrv_data:
        insights.extend(_hrv_recovery_patterns(runs, hrv_data))

    insights.extend(_detect_overtraining_signals(runs, hrv_data))

    if not insights:
        insights.append("Not enough data to detect clear patterns yet. Keep training!")

    return insights[:7]  # Cap at 7 insights


def _get_runs(activities: list[dict[str, Any]], weeks: int) -> list[dict[str, Any]]:
    """Filter to running activities within the specified weeks."""
    cutoff = date.today() - timedelta(weeks=weeks)
    runs = []
    for a in activities:
        if "run" not in str(a.get("type", "")).lower():
            continue
        try:
            d = datetime.strptime(str(a.get("date", ""))[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if d >= cutoff:
            runs.append(a)
    return runs


def _day_of_week_patterns(runs: list[dict[str, Any]]) -> list[str]:
    """Detect day-of-week training patterns."""
    insights: list[str] = []
    day_counts: dict[str, int] = {}
    day_paces: dict[str, list[float]] = {}
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for r in runs:
        try:
            d = datetime.strptime(str(r["date"])[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        day_name = day_names[d.weekday()]
        day_counts[day_name] = day_counts.get(day_name, 0) + 1

        dist = float(r.get("distance", 0))
        dur = float(r.get("duration", 0))
        if dist > 0 and dur > 0:
            pace = dur / (dist / METERS_PER_MILE)
            if day_name not in day_paces:
                day_paces[day_name] = []
            day_paces[day_name].append(pace)

    if day_counts:
        fav_day = max(day_counts, key=lambda d: day_counts[d])
        if day_counts[fav_day] >= 3:
            insights.append(f"You run most often on {fav_day}s ({day_counts[fav_day]} runs).")

    # Find fastest day
    avg_paces = {d: sum(p) / len(p) for d, p in day_paces.items() if len(p) >= 2}
    if avg_paces:
        fastest_day = min(avg_paces, key=lambda d: avg_paces[d])
        pace_mins = int(avg_paces[fastest_day] // 60)
        pace_secs = int(avg_paces[fastest_day] % 60)
        insights.append(f"Your fastest runs tend to happen on {fastest_day}s (avg {pace_mins}:{pace_secs:02d}/mi).")

    return insights


def _distance_pace_patterns(runs: list[dict[str, Any]]) -> list[str]:
    """Detect distance and pace trends."""
    insights: list[str] = []

    # Check for long run recovery pattern
    long_runs = []
    for i, r in enumerate(runs):
        dist_miles = float(r.get("distance", 0)) / METERS_PER_MILE
        if dist_miles >= 8.0:
            long_runs.append((i, r))

    if len(long_runs) >= 2:
        insights.append(
            f"You've done {len(long_runs)} long runs (8+ miles) recently — "
            f"great half marathon prep."
        )

    return insights


def _sleep_performance_correlation(
    runs: list[dict[str, Any]],
    sleep_data: list[dict[str, Any]],
) -> list[str]:
    """Correlate sleep quality with running performance."""
    insights: list[str] = []
    sleep_by_date = {s.get("date", ""): s for s in sleep_data}

    good_sleep_paces: list[float] = []
    poor_sleep_paces: list[float] = []

    for r in runs:
        run_date = str(r.get("date", ""))[:10]
        sleep = sleep_by_date.get(run_date)
        if not sleep:
            continue
        score = float(sleep.get("score", 0))
        dist = float(r.get("distance", 0))
        dur = float(r.get("duration", 0))
        if dist <= 0 or dur <= 0:
            continue
        pace = dur / (dist / METERS_PER_MILE)

        if score >= 70:
            good_sleep_paces.append(pace)
        elif score > 0:
            poor_sleep_paces.append(pace)

    if len(good_sleep_paces) >= 2 and len(poor_sleep_paces) >= 2:
        avg_good = sum(good_sleep_paces) / len(good_sleep_paces)
        avg_poor = sum(poor_sleep_paces) / len(poor_sleep_paces)
        if avg_good < avg_poor:
            diff = avg_poor - avg_good
            diff_secs = int(diff)
            insights.append(
                f"Your runs after good sleep (70+ score) are ~{diff_secs}s/mi faster."
            )

    return insights


def _hrv_recovery_patterns(
    runs: list[dict[str, Any]],
    hrv_data: list[dict[str, Any]],
) -> list[str]:
    """Detect HRV-based recovery patterns."""
    insights: list[str] = []

    if len(hrv_data) < 3:
        return insights

    avg_hrv = sum(float(h.get("last_night", 0) or h.get("weekly_avg", 0)) for h in hrv_data) / len(hrv_data)
    if avg_hrv > 0:
        low_count = sum(1 for h in hrv_data if float(h.get("last_night", 0)) < avg_hrv * 0.8)
        if low_count >= 3:
            insights.append(
                f"HRV has been below baseline on {low_count} days — monitor for overreaching."
            )

    return insights


def _detect_overtraining_signals(
    runs: list[dict[str, Any]],
    hrv_data: list[dict[str, Any]] | None,
) -> list[str]:
    """Detect potential overtraining signals."""
    insights: list[str] = []

    # Check for declining performance (pace getting slower over recent runs)
    recent_paces: list[float] = []
    for r in sorted(runs, key=lambda x: x.get("date", ""))[-10:]:
        dist = float(r.get("distance", 0))
        dur = float(r.get("duration", 0))
        if dist > 0 and dur > 0:
            recent_paces.append(dur / (dist / METERS_PER_MILE))

    if len(recent_paces) >= 6:
        first_half = sum(recent_paces[:3]) / 3
        second_half = sum(recent_paces[-3:]) / 3
        if second_half > first_half * 1.05:
            insights.append(
                "Recent pace is trending slower — could indicate fatigue accumulation."
            )

    return insights
