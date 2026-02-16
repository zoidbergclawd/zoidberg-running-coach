"""Tests for readiness scoring (Item 7) — no Garmin token needed."""

from zoidberg_coach.coaching import readiness_score, suggest_workout


class TestReadinessScore:
    def test_high_readiness(self):
        result = readiness_score(
            sleep_score=90, hrv_last_night=60, hrv_weekly_avg=50,
            body_battery=85, recent_load_miles=20, avg_weekly_miles=25,
        )
        assert result["score"] >= 70
        assert result["interpretation"] in ("Normal training", "Ready for hard effort")

    def test_low_readiness(self):
        result = readiness_score(
            sleep_score=30, hrv_last_night=20, hrv_weekly_avg=50,
            body_battery=15, recent_load_miles=35, avg_weekly_miles=20,
        )
        assert result["score"] < 50
        assert result["interpretation"] == "Rest day recommended"

    def test_medium_readiness(self):
        result = readiness_score(
            sleep_score=60, hrv_last_night=40, hrv_weekly_avg=45,
            body_battery=50, recent_load_miles=22, avg_weekly_miles=20,
        )
        assert 40 <= result["score"] <= 80

    def test_score_bounded(self):
        result = readiness_score(
            sleep_score=100, hrv_last_night=100, hrv_weekly_avg=50,
            body_battery=100, recent_load_miles=0, avg_weekly_miles=20,
        )
        assert 0 <= result["score"] <= 100

    def test_components_present(self):
        result = readiness_score(
            sleep_score=70, hrv_last_night=45, hrv_weekly_avg=45,
            body_battery=60, recent_load_miles=20, avg_weekly_miles=20,
        )
        assert "components" in result
        assert all(k in result["components"] for k in ("sleep", "hrv", "body_battery", "fatigue"))


class TestSuggestWorkout:
    def test_rest_when_low_readiness(self):
        result = suggest_workout(readiness=30, days_since_hard=1, days_until_race=None, weekly_mileage=20)
        assert result["type"] == "rest"

    def test_easy_when_moderate_readiness(self):
        result = suggest_workout(readiness=55, days_since_hard=2, days_until_race=None, weekly_mileage=20)
        assert result["type"] == "easy_run"

    def test_tempo_when_ready_and_due(self):
        result = suggest_workout(readiness=80, days_since_hard=4, days_until_race=None, weekly_mileage=20)
        assert result["type"] == "tempo"

    def test_taper_near_race(self):
        result = suggest_workout(readiness=80, days_since_hard=3, days_until_race=2, weekly_mileage=25)
        assert result["type"] == "shakeout"

    def test_taper_two_weeks_out(self):
        result = suggest_workout(readiness=75, days_since_hard=3, days_until_race=10, weekly_mileage=25)
        assert result["type"] == "easy_run"
        assert "taper" in result["description"].lower() or "easy" in result["description"].lower()
