# AGENTS.md - Zoidberg's Running Coach

## Project Context

This is a Python CLI tool that connects to Garmin Connect via the garth-mcp-server
to analyze training data and provide half marathon coaching suggestions.

**Target User:** Jon McBee - training for a spring half marathon
**Built by:** Zoidberg (AI assistant) using Ralph-style autonomous coding

## Technical Stack

- **Python 3.11+** with modern typing
- **MCP client** for connecting to garth-mcp-server
- **Click** or **Typer** for CLI
- **Pandas** for data analysis
- **Rich** for beautiful terminal output

## Code Quality Standards

This is a **real project** that will be used for actual training. Not a prototype.

- Type hints on ALL functions
- Docstrings on public functions  
- Graceful error handling (API failures, missing data)
- Clean separation: client → analysis → coaching → CLI layers
- No magic numbers - use named constants for HR zones, thresholds, etc.

## MCP Integration Notes

The garth-mcp-server is an external MCP server. Connection requires:
- GARTH_TOKEN environment variable (from `uvx garth login`)
- MCP client library to call tools

Available tools include:
- get_activities, get_activity_details, get_activity_splits
- nightly_sleep, daily_hrv, daily_body_battery
- user_profile, user_settings

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
