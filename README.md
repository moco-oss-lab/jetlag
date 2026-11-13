# jetlag

Tiny jet lag planner — a CLI that tells you how big the time shift of a
flight is, how long you will need to recover, and how to shift your sleep
before you fly.

Give it a departure zone, an arrival zone and the local departure/arrival
times. It works out the signed time-zone shift (east or west), the flight
length, the recovery time (rule of thumb: about 1 day per hour of shift
flying east, about 0.5 day per hour flying west), and a day-by-day
pre-travel sleep-shift schedule — move bedtime by up to 1 hour a day
toward the destination clock.

Zones can be short presets (`tokyo`, `lima`, `cusco`, `saopaulo`, ...)
or any IANA zone name (`Asia/Tokyo`, `America/New_York`). Real time
zones are used, so daylight saving is handled correctly.

Standard library only. No dependencies to install. Python 3.9+.

## Install

```sh
git clone https://github.com/moco-oss-lab/jetlag.git
cd jetlag
python3 jetlag.py --help
```

## Usage

```sh
# Tokyo -> Lima: how bad is the jet lag?
python3 jetlag.py --from tokyo --to lima \
  --depart "2026-12-01 18:00" --arrive "2026-12-01 17:00"

# Same trip, with a different usual bedtime
python3 jetlag.py --from tokyo --to lima \
  --depart "2026-12-01 18:00" --arrive "2026-12-01 17:00" --bedtime 22:30

# Machine-readable output
python3 jetlag.py --from newyork --to london \
  --depart "2026-07-15 10:00" --arrive "2026-07-15 22:00" --json

# List every preset zone
python3 jetlag.py --list
```

Example output:

```
Jet lag plan: Tokyo, Japan -> Lima, Peru
  Departs: 2026-12-01 18:00 JST
  Arrives: 2026-12-01 17:00 UTC-05
  Flight time: 13.0 hours
  Time shift: -14.0 hours — destination is behind (westward)
  Recovery: about 7 days (rule of thumb: 1 day per hour east, 0.5 day per hour west)

  Pre-travel sleep shift (usual bedtime 23:00):
    2026-11-24  bedtime 00:00
    ...
    2026-11-30  bedtime 06:00

  Tip: get bright light in the late afternoon at
  your destination, and keep mornings dim.
```

## Notes

The recovery estimate and sleep schedule are planning rules of thumb,
not medical advice. The sleep-shift plan is capped at 7 days — for very
large shifts, keep shifting gradually and use light exposure at your
destination.

## Tests

```sh
python3 -m unittest test_jetlag -v
```

## License

MIT — see [LICENSE](LICENSE).
