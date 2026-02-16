"""CLI interface for Zoidberg's Running Coach."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zoidberg_coach import __version__
from zoidberg_coach.analysis import (
    polarization_analysis,
    training_load_trend,
    weekly_summary,
)
from zoidberg_coach.coaching import (
    race_readiness,
    readiness_score,
    suggest_workout,
)
from zoidberg_coach.garmin_client import (
    GarminAuthenticationError,
    GarminClient,
    GarminClientError,
)
from zoidberg_coach.patterns import weekly_pattern_report

METERS_PER_MILE = 1609.344

app = typer.Typer(
    name="zoidberg-coach",
    help="Analyze Garmin training data and get half marathon coaching suggestions.",
    no_args_is_help=True,
)

console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"zoidberg-coach {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit.", callback=version_callback, is_eager=True
    ),
) -> None:
    """Zoidberg's Running Coach - your AI half marathon training companion."""


def _format_pace(duration_seconds: float, distance_meters: float) -> str:
    """Format pace as min:sec per mile."""
    if duration_seconds <= 0 or distance_meters <= 0:
        return "N/A"

    miles = distance_meters / METERS_PER_MILE
    seconds_per_mile = duration_seconds / miles
    minutes = int(seconds_per_mile // 60)
    seconds = int(round(seconds_per_mile % 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d} /mi"


def _format_duration(seconds: float) -> str:
    """Format seconds as H:MM:SS or M:SS."""
    if seconds <= 0:
        return "0:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _get_client() -> GarminClient:
    """Create a Garmin client with error handling."""
    try:
        return GarminClient()
    except GarminAuthenticationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


def _color_for_value(value: float, good: float, warn: float) -> str:
    """Return color based on value thresholds (higher is better)."""
    if value >= good:
        return "green"
    if value >= warn:
        return "yellow"
    return "red"


# --- Item 2: Activities ---
@app.command()
def activities(
    days: int = typer.Option(30, "--days", "-d", min=1, help="Number of trailing days to fetch."),
) -> None:
    """List recent Garmin activities with distance and pace."""
    client = _get_client()
    try:
        recent_activities = client.get_activities(days=days)
    except GarminClientError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    if not recent_activities:
        console.print("No activities found for the selected period.")
        return

    table = Table(title=f"Activities (last {days} days)")
    table.add_column("Date", style="cyan")
    table.add_column("Type")
    table.add_column("Name")
    table.add_column("Distance", justify="right")
    table.add_column("Pace", justify="right")

    for a in recent_activities:
        dist = float(a["distance"])
        dur = float(a["duration"])
        miles = dist / METERS_PER_MILE
        pace = _format_pace(dur, dist)
        table.add_row(a["date"], a["type"], a["name"], f"{miles:.2f} mi", pace)

    console.print(table)


# --- Item 3: Activity Details ---
@app.command()
def activity(
    activity_id: int = typer.Argument(..., help="Garmin activity ID"),
) -> None:
    """Show lap-by-lap breakdown with pace and HR for an activity."""
    client = _get_client()
    try:
        details = client.get_activity_details(activity_id)
    except GarminClientError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    summary = details.get("summary", {})
    splits = details.get("splits", [])

    if summary:
        panel_text = (
            f"[bold]{summary.get('name', 'Activity')}[/bold]\n"
            f"Distance: {summary.get('distance', 0) / METERS_PER_MILE:.2f} mi\n"
            f"Duration: {_format_duration(summary.get('duration', 0))}\n"
            f"Avg HR: {summary.get('avg_hr', 0):.0f} bpm | Max HR: {summary.get('max_hr', 0):.0f} bpm"
        )
        console.print(Panel(panel_text, title=f"Activity {activity_id}"))

    if splits:
        table = Table(title="Splits")
        table.add_column("Lap", justify="center")
        table.add_column("Distance", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Pace", justify="right")
        table.add_column("Avg HR", justify="right")
        table.add_column("Max HR", justify="right")

        for s in splits:
            dist = float(s["distance"])
            dur = float(s["duration"])
            table.add_row(
                str(s["lap"]),
                f"{dist / METERS_PER_MILE:.2f} mi",
                _format_duration(dur),
                _format_pace(dur, dist),
                f"{s['avg_hr']:.0f}",
                f"{s['max_hr']:.0f}",
            )
        console.print(table)
    else:
        console.print("No split data available for this activity.")


# --- Item 4: Recovery Metrics ---
@app.command()
def recovery(
    target_date: str = typer.Option(None, "--date", help="Date (YYYY-MM-DD), defaults to today."),
) -> None:
    """Show sleep score, HRV, body battery, and stress for a date."""
    client = _get_client()
    d = _parse_date_arg(target_date)

    sleep = client.get_sleep(d)
    hrv = client.get_hrv(d)
    bb = client.get_body_battery(d)
    stress = client.get_stress(d)

    table = Table(title=f"Recovery Metrics — {d.isoformat()}")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    sleep_score = float(sleep.get("score", 0))
    table.add_row("Sleep Score", f"[{_color_for_value(sleep_score, 70, 50)}]{sleep_score:.0f}[/]")
    table.add_row("Sleep Duration", _format_duration(float(sleep.get("duration_seconds", 0))))

    hrv_val = float(hrv.get("last_night", 0))
    hrv_avg = float(hrv.get("weekly_avg", 0))
    table.add_row("HRV (last night)", f"{hrv_val:.0f} ms")
    table.add_row("HRV (weekly avg)", f"{hrv_avg:.0f} ms")
    table.add_row("HRV Status", str(hrv.get("status", "unknown")))

    bb_current = float(bb.get("current", 0))
    table.add_row(
        "Body Battery",
        f"[{_color_for_value(bb_current, 60, 30)}]{bb_current:.0f}[/] "
        f"(low: {bb.get('lowest', 0)}, high: {bb.get('highest', 0)})"
    )

    avg_stress = float(stress.get("avg_stress", 0))
    stress_color = "green" if avg_stress < 30 else ("yellow" if avg_stress < 50 else "red")
    table.add_row("Avg Stress", f"[{stress_color}]{avg_stress:.0f}[/]")
    table.add_row("Max Stress", f"{stress.get('max_stress', 0)}")

    console.print(table)


# --- Item 5: Weekly Summary ---
@app.command()
def summary(
    weeks: int = typer.Option(8, "--weeks", "-w", min=1, help="Number of weeks to summarize."),
) -> None:
    """Show weekly mileage progression with trend indicators."""
    client = _get_client()
    all_activities = client.get_activities(days=weeks * 7 + 7)
    summaries = weekly_summary(all_activities, weeks=weeks)
    annotated = training_load_trend(summaries)

    table = Table(title=f"Weekly Summary (last {weeks} weeks)")
    table.add_column("Week", style="cyan")
    table.add_column("Runs", justify="center")
    table.add_column("Miles", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Status")

    for w in annotated:
        change = w["mileage_increase_pct"]
        if w["overload_flag"]:
            status = "[red]OVERLOAD[/red]"
            change_str = f"[red]+{change:.0f}%[/red]"
        elif change > 0:
            status = "[green]OK[/green]"
            change_str = f"[green]+{change:.0f}%[/green]"
        elif change < 0:
            status = "[yellow]down[/yellow]"
            change_str = f"[yellow]{change:.0f}%[/yellow]"
        else:
            status = ""
            change_str = "--"

        table.add_row(
            w["week_start"],
            str(w["run_count"]),
            f"{w['total_miles']:.1f}",
            _format_duration(w["total_time_seconds"]),
            change_str,
            status,
        )

    console.print(table)


# --- Item 6: Polarization Analysis ---
@app.command()
def polarization(
    weeks: int = typer.Option(4, "--weeks", "-w", min=1, help="Weeks to analyze."),
) -> None:
    """Show % easy vs % hard with recommendation if ratio is off."""
    client = _get_client()
    all_activities = client.get_activities(days=weeks * 7 + 7)
    result = polarization_analysis(all_activities, weeks=weeks)

    easy = result["easy_pct"]
    hard = result["hard_pct"]
    easy_color = "green" if easy >= 75 else ("yellow" if easy >= 60 else "red")

    panel_text = (
        f"[bold]Polarization Analysis ({result['weeks_analyzed']} weeks)[/bold]\n\n"
        f"Easy (Zone 1-2): [{easy_color}]{easy:.0f}%[/]\n"
        f"Hard (Zone 3+):  {hard:.0f}%\n\n"
        f"Target: 80% easy / 20% hard\n\n"
        f"[italic]{result['recommendation']}[/italic]"
    )
    console.print(Panel(panel_text, title="80/20 Training"))


# --- Item 8: Today's Workout ---
@app.command()
def today(
    race_date: str = typer.Option(None, "--race-date", help="Race date (YYYY-MM-DD)"),
) -> None:
    """Show today's readiness and workout suggestion."""
    client = _get_client()

    sleep = client.get_sleep()
    hrv = client.get_hrv()
    bb = client.get_body_battery()

    all_activities = client.get_activities(days=56)
    summaries = weekly_summary(all_activities, weeks=4)
    current_miles = summaries[0]["total_miles"] if summaries else 0
    avg_miles = (sum(s["total_miles"] for s in summaries) / len(summaries)) if summaries else 0

    rs = readiness_score(
        sleep_score=float(sleep.get("score", 0)),
        hrv_last_night=float(hrv.get("last_night", 0)),
        hrv_weekly_avg=float(hrv.get("weekly_avg", 0)),
        body_battery=float(bb.get("current", 0)),
        recent_load_miles=current_miles,
        avg_weekly_miles=avg_miles,
    )

    # Determine days since last hard effort (avg_hr > zone boundary)
    days_since_hard = _days_since_hard_effort(all_activities)

    days_until_race = None
    if race_date:
        rd = _parse_date_arg(race_date)
        days_until_race = (rd - date.today()).days

    workout = suggest_workout(
        readiness=rs["score"],
        days_since_hard=days_since_hard,
        days_until_race=days_until_race,
        weekly_mileage=current_miles,
    )

    score_color = _color_for_value(rs["score"], 70, 50)
    panel_text = (
        f"[bold]Readiness: [{score_color}]{rs['score']}[/] / 100[/bold]\n"
        f"{rs['interpretation']}\n\n"
        f"Components: Sleep {rs['components']['sleep']:.0f} | "
        f"HRV {rs['components']['hrv']:.0f} | "
        f"Battery {rs['components']['body_battery']:.0f} | "
        f"Fatigue {rs['components']['fatigue']:.0f}\n\n"
        f"[bold]Today's Workout:[/bold] {workout['type'].replace('_', ' ').title()}\n"
        f"{workout['description']}\n"
        f"Duration: {workout['duration_minutes']} min | Intensity: {workout['intensity']}"
    )

    if days_until_race is not None:
        panel_text += f"\n\n[dim]Race in {days_until_race} days[/dim]"

    console.print(Panel(panel_text, title="Today"))


# --- Item 9: Race Readiness ---
@app.command(name="race-prep")
def race_prep(
    race_date_str: str = typer.Option(..., "--date", help="Race date (YYYY-MM-DD)"),
    goal: str = typer.Option(None, "--goal", help="Goal time (HH:MM:SS)"),
) -> None:
    """Show race readiness assessment with recommendations."""
    client = _get_client()
    target = _parse_date_arg(race_date_str)
    goal_seconds = _parse_time(goal) if goal else None

    all_activities = client.get_activities(days=60)
    result = race_readiness(all_activities, target_date=target, goal_time_seconds=goal_seconds)

    score = result["readiness_score"]
    score_color = _color_for_value(score, 70, 40)

    lines = [
        f"[bold]Race Readiness: [{score_color}]{score}[/] / 100[/bold]",
        f"Days until race: {result['days_until_race']}",
        f"",
        f"Longest run: {result['longest_run_miles']:.1f} mi",
        f"Avg weekly mileage: {result['avg_weekly_miles']:.1f} mi",
        f"Total runs (8 wk): {result['total_runs_8wk']}",
    ]

    if result["predicted_finish_seconds"]:
        lines.append(f"Predicted finish: {_format_duration(result['predicted_finish_seconds'])}")

    if goal_seconds:
        lines.append(f"Goal time: {_format_duration(goal_seconds)}")

    if result["gaps"]:
        lines.append("")
        lines.append("[bold yellow]Gaps to address:[/bold yellow]")
        for gap in result["gaps"]:
            lines.append(f"  - {gap}")

    console.print(Panel("\n".join(lines), title="Half Marathon Readiness"))


# --- Item 11: Patterns ---
@app.command()
def patterns(
    weeks: int = typer.Option(8, "--weeks", "-w", min=1, help="Weeks to analyze."),
) -> None:
    """Show actionable insights based on historical data."""
    client = _get_client()
    all_activities = client.get_activities(days=weeks * 7 + 7)

    # Gather sleep/hrv data for correlation
    sleep_data: list[dict[str, Any]] = []
    hrv_data: list[dict[str, Any]] = []
    for i in range(min(14, weeks * 7)):
        d = date.today() - timedelta(days=i)
        sleep_data.append(client.get_sleep(d))
        hrv_data.append(client.get_hrv(d))

    insights = weekly_pattern_report(all_activities, sleep_data, hrv_data, weeks=weeks)

    panel_lines = [f"[bold]Training Patterns ({weeks} weeks)[/bold]", ""]
    for insight in insights:
        panel_lines.append(f"  - {insight}")

    console.print(Panel("\n".join(panel_lines), title="Patterns & Insights"))


# --- Item 12: Daily Report ---
@app.command(name="daily-report")
def daily_report(
    race_date: str = typer.Option(None, "--race-date", help="Race date (YYYY-MM-DD)"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Generate a complete daily coaching report."""
    client = _get_client()

    # Gather all data
    sleep = client.get_sleep()
    hrv = client.get_hrv()
    bb = client.get_body_battery()
    stress = client.get_stress()

    all_activities = client.get_activities(days=60)
    summaries = weekly_summary(all_activities, weeks=8)
    current_miles = summaries[0]["total_miles"] if summaries else 0
    avg_miles = (sum(s["total_miles"] for s in summaries) / len(summaries)) if summaries else 0

    rs = readiness_score(
        sleep_score=float(sleep.get("score", 0)),
        hrv_last_night=float(hrv.get("last_night", 0)),
        hrv_weekly_avg=float(hrv.get("weekly_avg", 0)),
        body_battery=float(bb.get("current", 0)),
        recent_load_miles=current_miles,
        avg_weekly_miles=avg_miles,
    )

    days_since_hard = _days_since_hard_effort(all_activities)

    days_until_race = None
    race_data = None
    if race_date:
        rd = _parse_date_arg(race_date)
        days_until_race = (rd - date.today()).days
        race_data = race_readiness(all_activities, target_date=rd)

    workout = suggest_workout(
        readiness=rs["score"],
        days_since_hard=days_since_hard,
        days_until_race=days_until_race,
        weekly_mileage=current_miles,
    )

    load_trend = training_load_trend(summaries[:4])
    polar = polarization_analysis(all_activities, weeks=4)

    # Gather pattern insights (limited date range to reduce API calls)
    sleep_data = [client.get_sleep(date.today() - timedelta(days=i)) for i in range(7)]
    hrv_data_list = [client.get_hrv(date.today() - timedelta(days=i)) for i in range(7)]
    insights = weekly_pattern_report(all_activities, sleep_data, hrv_data_list, weeks=4)

    report: dict[str, Any] = {
        "date": date.today().isoformat(),
        "readiness": rs,
        "todays_suggestion": workout,
        "recovery": {
            "sleep": sleep,
            "hrv": hrv,
            "body_battery": bb,
            "stress": stress,
        },
        "recent_load_summary": {
            "current_week_miles": round(current_miles, 1),
            "avg_weekly_miles": round(avg_miles, 1),
            "trend": load_trend[:4] if load_trend else [],
            "polarization": polar,
        },
        "pattern_insights": insights,
    }

    if race_data:
        report["race_countdown"] = race_data

    if output_json:
        typer.echo(json.dumps(report, indent=2, default=str))
        return

    # Rich output
    score_color = _color_for_value(rs["score"], 70, 50)
    lines = [
        f"[bold]Daily Coaching Report — {date.today().isoformat()}[/bold]",
        "",
        f"Readiness: [{score_color}]{rs['score']}[/] / 100 — {rs['interpretation']}",
        f"Sleep: {sleep.get('score', 0)} | HRV: {hrv.get('last_night', 0)} ms | "
        f"Battery: {bb.get('current', 0)} | Stress: {stress.get('avg_stress', 0)}",
        "",
        f"[bold]Workout:[/bold] {workout['type'].replace('_', ' ').title()}",
        f"  {workout['description']}",
        f"  Duration: {workout['duration_minutes']} min | Intensity: {workout['intensity']}",
        "",
        f"[bold]This Week:[/bold] {current_miles:.1f} mi (avg: {avg_miles:.1f} mi/wk)",
        f"Polarization: {polar['easy_pct']:.0f}% easy / {polar['hard_pct']:.0f}% hard",
    ]

    if race_data:
        lines.extend([
            "",
            f"[bold]Race in {race_data['days_until_race']} days[/bold]",
            f"  Readiness: {race_data['readiness_score']}/100 | "
            f"Longest: {race_data['longest_run_miles']:.1f} mi | "
            f"Predicted: {_format_duration(race_data['predicted_finish_seconds'] or 0)}",
        ])
        if race_data["gaps"]:
            for gap in race_data["gaps"]:
                lines.append(f"  [yellow]- {gap}[/yellow]")

    if insights:
        lines.extend(["", "[bold]Insights:[/bold]"])
        for ins in insights[:5]:
            lines.append(f"  - {ins}")

    console.print(Panel("\n".join(lines), title="Zoidberg's Running Coach"))


# --- Helpers ---

def _parse_date_arg(date_str: str | None) -> date:
    """Parse a YYYY-MM-DD date string or return today."""
    if not date_str:
        return date.today()
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        console.print(f"[red]Invalid date format: {date_str}. Use YYYY-MM-DD.[/red]")
        raise typer.Exit(code=1)


def _parse_time(time_str: str) -> float:
    """Parse HH:MM:SS to seconds."""
    parts = time_str.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return float(time_str)


def _days_since_hard_effort(activities: list[dict[str, Any]], hr_threshold: float = 152) -> int:
    """Calculate days since last hard effort based on avg HR."""
    today = date.today()
    for a in sorted(activities, key=lambda x: x.get("date", ""), reverse=True):
        if "run" not in str(a.get("type", "")).lower():
            continue
        avg_hr = float(a.get("avg_hr", 0))
        if avg_hr >= hr_threshold:
            try:
                d = datetime.strptime(str(a["date"])[:10], "%Y-%m-%d").date()
                return (today - d).days
            except (ValueError, TypeError):
                continue
    return 7  # Default if no hard effort found
