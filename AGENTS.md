# AGENTS.md - Zoidberg's Running Coach

## Project Context

This is a Python CLI tool that connects to Garmin Connect via the garth-mcp-server
to analyze training data and provide half marathon coaching suggestions.

**Target User:** Jon McBee - training for a spring half marathon
**Built by:** Zoidberg (AI assistant) using Ralph-style autonomous coding

## Technical Stack

- **Python 3.11+** with modern typing
- **garth** library for Garmin Connect API (same lib that powers garth-mcp-server)
- **Typer** for CLI (preferred over Click - better type hints integration)
- **Pandas** for data analysis
- **Rich** for beautiful terminal output

## Why garth instead of MCP?

The garth-mcp-server is built on the `garth` Python library. Using garth directly is simpler:
- No subprocess management or JSON-RPC protocol
- Direct Python API calls
- Same GARTH_TOKEN authentication
- Better error messages and debugging

## Code Quality Standards

This is a **real project** that will be used for actual training. Not a prototype.

- Type hints on ALL functions
- Docstrings on public functions  
- Graceful error handling (API failures, missing data)
- Clean separation: client → analysis → coaching → CLI layers
- No magic numbers - use named constants for HR zones, thresholds, etc.

## Garth Library Usage

Authentication:
```python
import garth
from datetime import date

# Option 1: Load saved token from ~/.garth/
garth.resume("~/.garth")

# Option 2: Use token string
garth.resume(token_string)

# Configure domain
garth.configure(domain="garmin.com")
```

Data Classes (preferred for structured data):
```python
from garth import DailySleep, DailyHRV, DailyStress, DailyBodyBattery

sleep = DailySleep.get(date.today())
hrv = DailyHRV.get(date.today())
stress = DailyStress.get(date.today())
battery = DailyBodyBattery.get(date.today())
```

Connect API (for activities and custom endpoints):
```python
# Get activities
activities = garth.connectapi(
    "/activitylist-service/activities/search/activities",
    params={"limit": 20, "start": 0}
)

# Get activity details
details = garth.connectapi(f"/activity-service/activity/{activity_id}")
splits = garth.connectapi(f"/activity-service/activity/{activity_id}/splits")
```

Helpful garth source: https://github.com/matin/garth

## Domain Knowledge

### Half Marathon Training Principles

- **Progressive overload**: Increase weekly mileage by ~10% max
- **80/20 polarized training**: 80% easy (Zone 1-2), 20% hard (Zone 3+)
- **Long run**: Should reach 10-12 miles before race, not exceeding 13.1
- **Taper**: Reduce volume 2-3 weeks before race, maintain intensity
- **Recovery**: HRV trends, sleep quality, and body battery indicate readiness

### Heart Rate Zones (typical 5-zone model)

- Zone 1: 50-60% max HR (recovery)
- Zone 2: 60-70% max HR (aerobic base)
- Zone 3: 70-80% max HR (tempo)
- Zone 4: 80-90% max HR (threshold)
- Zone 5: 90-100% max HR (VO2max)

## File Structure (target)

```
zoidberg-running-coach/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── prd.json
├── progress.txt
└── src/
    └── zoidberg_coach/
        ├── __init__.py
        ├── __main__.py
        ├── cli.py           # CLI commands
        ├── garmin_client.py # MCP connection
        ├── analysis.py      # Training metrics
        ├── coaching.py      # Workout suggestions
        └── models.py        # Data classes
```

## Working Agreement

- Make small, focused commits
- Update progress.txt after each feature
- Run type checking before committing
- If stuck, document the blocker in progress.txt
