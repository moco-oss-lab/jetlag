#!/usr/bin/env python3
"""jetlag — a tiny jet lag planner.

Given a flight (departure and arrival time zones plus local times), jetlag
works out how big the time shift is, which direction your body clock has
to move, how long the flight takes, and how many days you will need to
recover. It also prints a simple pre-travel sleep-shift schedule so you
can start adjusting before you fly.

The rule of thumb used here is the one travel-medicine guides commonly
cite: about one day of recovery per hour of shift when flying east, and
about half a day per hour when flying west. Eastward travel is harder
because you have to fall asleep earlier than your body wants to.

Standard library only (zoneinfo handles real IANA time zones, including
daylight saving). Python 3.9+.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None

# A few handy presets, keyed by short name. Any IANA zone name also works.
PRESETS = {
    "tokyo": ("Tokyo, Japan", "Asia/Tokyo"),
    "lima": ("Lima, Peru", "America/Lima"),
    "cusco": ("Cusco, Peru", "America/Lima"),
    "lapaz": ("La Paz, Bolivia", "America/La_Paz"),
    "uyuni": ("Uyuni, Bolivia", "America/La_Paz"),
    "saopaulo": ("Sao Paulo, Brazil", "America/Sao_Paulo"),
    "iguazu": ("Iguazu, Argentina", "America/Argentina/Cordoba"),
    "newyork": ("New York, USA", "America/New_York"),
    "losangeles": ("Los Angeles, USA", "America/Los_Angeles"),
    "london": ("London, UK", "Europe/London"),
    "paris": ("Paris, France", "Europe/Paris"),
    "sydney": ("Sydney, Australia", "Australia/Sydney"),
    "singapore": ("Singapore", "Asia/Singapore"),
    "bangkok": ("Bangkok, Thailand", "Asia/Bangkok"),
    "seoul": ("Seoul, South Korea", "Asia/Seoul"),
    "hongkong": ("Hong Kong", "Asia/Hong_Kong"),
    "dubai": ("Dubai, UAE", "Asia/Dubai"),
}


def resolve_zone(name):
    """Turn a preset name or IANA zone name into (display name, ZoneInfo)."""
    key = name.strip().lower()
    if key in PRESETS:
        label, zone_name = PRESETS[key]
        return label, ZoneInfo(zone_name)
    # Accept a plain IANA zone name; ZoneInfo raises ZoneInfoNotFoundError
    # for unknown names, which the caller turns into a friendly error.
    return name, ZoneInfo(name)


def parse_local(text, zone):
    """Parse 'YYYY-MM-DD HH:MM' as a wall-clock time in the given zone."""
    naive = datetime.strptime(text, "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=zone)


def shift_hours(from_dt, to_dt):
    """Signed time-zone shift in hours: arrival zone minus departure zone.

    Positive means the destination is ahead (eastward travel).
    """
    from_off = from_dt.utcoffset()
    to_off = to_dt.utcoffset()
    return (to_off - from_off).total_seconds() / 3600.0


def flight_duration_hours(depart_dt, arrive_dt):
    """Flight length in hours, from aware datetimes."""
    delta = arrive_dt.astimezone(depart_dt.tzinfo) - depart_dt
    return delta.total_seconds() / 3600.0


def recovery_days(shift):
    """Estimated recovery days from the signed shift in hours.

    Eastward (positive): ~1 day per hour. Westward: ~0.5 day per hour.
    Rounded up to whole days, minimum 0.
    """
    hours = abs(shift)
    if hours == 0:
        return 0
    per_hour = 1.0 if shift > 0 else 0.5
    days = hours * per_hour
    # Whole days, rounded up.
    return int(days) if days == int(days) else int(days) + 1


def shift_schedule(shift, depart_date, usual_bedtime="23:00"):
    """Day-by-day pre-travel sleep shifts.

    Move bedtime by up to 1 hour per day toward the destination clock,
    starting ``recovery_days`` days before departure (but at most the
    number of days needed to cover the whole shift). Returns a list of
    (date, bedtime) pairs, earliest first.
    """
    hours = abs(shift)
    if hours == 0:
        return []
    steps = int(hours) if hours == int(hours) else int(hours) + 1
    steps = min(steps, 7)  # a week of shifting is plenty for a plan
    base_h, base_m = (int(p) for p in usual_bedtime.split(":"))
    base = timedelta(hours=base_h, minutes=base_m)
    direction = 1 if shift > 0 else -1  # east: earlier bedtime
    plan = []
    for i in range(steps, 0, -1):
        day = depart_date - timedelta(days=i)
        bedtime = base - direction * timedelta(hours=steps - i + 1)
        # Wrap into a 24h clock for display.
        total_minutes = int(bedtime.total_seconds() // 60) % (24 * 60)
        hh, mm = divmod(total_minutes, 60)
        plan.append((day, "%02d:%02d" % (hh, mm)))
    return plan


def _display_time(dt):
    """'YYYY-MM-DD HH:MM ZONE', with numeric zone names shown as UTC offsets."""
    zone = dt.strftime("%Z")
    if zone.startswith(("+", "-")):
        zone = "UTC" + zone
    return dt.strftime("%Y-%m-%d %H:%M ") + zone


def plan(from_name, to_name, depart_text, arrive_text, bedtime="23:00"):
    """Build the full jet lag plan dict. Raises ValueError on bad input."""
    if ZoneInfo is None:  # pragma: no cover
        raise ValueError("zoneinfo is unavailable (needs Python 3.9+)")
    from_label, from_zone = resolve_zone(from_name)
    to_label, to_zone = resolve_zone(to_name)
    try:
        depart_dt = parse_local(depart_text, from_zone)
        arrive_dt = parse_local(arrive_text, to_zone)
    except ValueError as exc:
        raise ValueError(
            "times must look like 'YYYY-MM-DD HH:MM' (%s)" % exc
        ) from exc
    shift = shift_hours(depart_dt, arrive_dt)
    duration = flight_duration_hours(depart_dt, arrive_dt)
    if duration <= 0:
        raise ValueError("arrival must be after departure")
    days = recovery_days(shift)
    schedule = shift_schedule(shift, depart_dt.date(), bedtime)
    return {
        "from": from_label,
        "to": to_label,
        "depart_local": _display_time(depart_dt),
        "arrive_local": _display_time(arrive_dt),
        "shift_hours": shift,
        "direction": "east" if shift > 0 else ("west" if shift < 0 else "none"),
        "flight_hours": round(duration, 1),
        "recovery_days": days,
        "schedule": [
            {"date": d.isoformat(), "bedtime": b} for d, b in schedule
        ],
    }


def format_plan(result):
    """Render a plan dict as human-readable text."""
    lines = []
    lines.append("Jet lag plan: %s -> %s" % (result["from"], result["to"]))
    lines.append("  Departs: %s" % result["depart_local"])
    lines.append("  Arrives: %s" % result["arrive_local"])
    lines.append("  Flight time: %.1f hours" % result["flight_hours"])
    shift = result["shift_hours"]
    if shift == 0:
        lines.append("  Time shift: none — same time zone, no jet lag.")
    else:
        direction = "ahead (eastward)" if shift > 0 else "behind (westward)"
        lines.append(
            "  Time shift: %+.1f hours — destination is %s"
            % (shift, direction)
        )
        lines.append(
            "  Recovery: about %d day%s (rule of thumb: %s)"
            % (
                result["recovery_days"],
                "s" if result["recovery_days"] != 1 else "",
                "1 day per hour east, 0.5 day per hour west",
            )
        )
    if result["schedule"]:
        lines.append("")
        lines.append("  Pre-travel sleep shift (usual bedtime 23:00):")
        for entry in result["schedule"]:
            lines.append("    %s  bedtime %s" % (entry["date"], entry["bedtime"]))
        lines.append("")
        if result["direction"] == "east":
            lines.append("  Tip: get bright light in the morning at your")
            lines.append("  destination, and avoid bright light late at night.")
        else:
            lines.append("  Tip: get bright light in the late afternoon at")
            lines.append("  your destination, and keep mornings dim.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="jetlag",
        description="Plan around jet lag: shift size, recovery days, "
        "and a pre-travel sleep schedule.",
    )
    parser.add_argument("--from", dest="from_name", required=False,
                        help="departure zone: preset (e.g. tokyo, lima) "
                        "or IANA name (e.g. Asia/Tokyo)")
    parser.add_argument("--to", dest="to_name", required=False,
                        help="arrival zone: preset or IANA name")
    parser.add_argument("--depart", required=False,
                        help="departure local time 'YYYY-MM-DD HH:MM'")
    parser.add_argument("--arrive", required=False,
                        help="arrival local time 'YYYY-MM-DD HH:MM'")
    parser.add_argument("--bedtime", default="23:00",
                        help="usual bedtime 'HH:MM' (default 23:00)")
    parser.add_argument("--json", action="store_true",
                        help="print the plan as JSON")
    parser.add_argument("--list", action="store_true",
                        help="list preset zones and exit")
    args = parser.parse_args(argv)

    if args.list:
        for key in sorted(PRESETS):
            label, zone = PRESETS[key]
            print("%-12s %s (%s)" % (key, label, zone))
        return 0

    missing = [n for n, v in (("--from", args.from_name),
                              ("--to", args.to_name),
                              ("--depart", args.depart),
                              ("--arrive", args.arrive)) if not v]
    if missing:
        parser.error("missing required option(s): %s" % ", ".join(missing))

    try:
        result = plan(args.from_name, args.to_name,
                      args.depart, args.arrive, args.bedtime)
    except Exception as exc:  # ZoneInfoNotFoundError, ValueError, ...
        print("error: %s" % exc, file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_plan(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
