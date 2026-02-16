"""Tests for analysis module (Items 5-6) — no Garmin token needed."""

from datetime import date, timedelta

from zoidberg_coach.analysis import (
    METERS_PER_MILE,
    polarization_analysis,
    training_load_trend,
    weekly_summary,
)


def _make_run(days_ago: int, distance_miles: float, duration_min: float, avg_hr: float = 140) -> dict:
    d = date.today() - timedelta(days=days_ago)
    return {
        "id": days_ago,
        "name": "Test Run",
        "type": "running",
        "date": d.isoformat(),
        "distance": distance_miles * METERS_PER_MILE,
        "duration": duration_min * 60,
        "avg_hr": avg_hr,
    }


class TestWeeklySummary:
    def test_empty_activities(self):
        result = weekly_summary([], weeks=4)
        assert len(result) == 4
        assert all(s["run_count"] == 0 for s in result)

    def test_counts_runs(self):
        activities = [_make_run(1, 3.0, 30), _make_run(2, 4.0, 40)]
        result = weekly_summary(activities, weeks=1)
        assert result[0]["run_count"] >= 1
        assert result[0]["total_miles"] > 0


class TestTrainingLoadTrend:
    def test_flags_overload(self):
        summaries = [
            {"week_start": "2026-02-10", "total_miles": 25, "total_time_seconds": 0, "run_count": 4},
            {"week_start": "2026-02-03", "total_miles": 15, "total_time_seconds": 0, "run_count": 3},
        ]
        result = training_load_trend(summaries)
        assert result[0]["overload_flag"] is True
        assert result[0]["mileage_increase_pct"] > 10

    def test_no_overload(self):
        summaries = [
            {"week_start": "2026-02-10", "total_miles": 21, "total_time_seconds": 0, "run_count": 3},
            {"week_start": "2026-02-03", "total_miles": 20, "total_time_seconds": 0, "run_count": 3},
        ]
        result = training_load_trend(summaries)
        assert result[0]["overload_flag"] is False


class TestPolarization:
    def test_all_easy(self):
        activities = [_make_run(i, 5.0, 50, avg_hr=130) for i in range(1, 8)]
        result = polarization_analysis(activities, weeks=2, zone_boundary_hr=150)
        assert result["easy_pct"] == 100.0

    def test_mixed(self):
        easy = [_make_run(i, 5.0, 50, avg_hr=130) for i in range(1, 5)]
        hard = [_make_run(i, 3.0, 25, avg_hr=165) for i in range(5, 7)]
        result = polarization_analysis(easy + hard, weeks=2, zone_boundary_hr=150)
        assert result["easy_pct"] > 0
        assert result["hard_pct"] > 0

    def test_no_hr_data(self):
        activities = [_make_run(1, 5.0, 50, avg_hr=0)]
        result = polarization_analysis(activities, weeks=2)
        assert "No heart rate data" in result["recommendation"]
