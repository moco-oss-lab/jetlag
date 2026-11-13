#!/usr/bin/env python3
"""Tests for jetlag.py. Run: python3 -m unittest test_jetlag -v"""

import unittest

import jetlag


class TestShiftAndDirection(unittest.TestCase):
    def test_eastward_shift_tokyo_to_lima(self):
        # Tokyo (UTC+9) -> Lima (UTC-5): 14 hours behind, westward.
        result = jetlag.plan("tokyo", "lima",
                             "2026-12-01 18:00", "2026-12-01 17:00")
        self.assertEqual(result["shift_hours"], -14)
        self.assertEqual(result["direction"], "west")

    def test_westward_shift_lima_to_tokyo(self):
        result = jetlag.plan("lima", "tokyo",
                             "2026-12-01 10:00", "2026-12-03 05:00")
        self.assertEqual(result["shift_hours"], 14)
        self.assertEqual(result["direction"], "east")

    def test_no_shift_same_zone(self):
        result = jetlag.plan("tokyo", "Asia/Tokyo",
                             "2026-12-01 10:00", "2026-12-01 12:00")
        self.assertEqual(result["shift_hours"], 0)
        self.assertEqual(result["direction"], "none")
        self.assertEqual(result["recovery_days"], 0)
        self.assertEqual(result["schedule"], [])

    def test_iana_zone_names_work(self):
        result = jetlag.plan("Europe/London", "America/New_York",
                             "2026-06-01 10:00", "2026-06-01 13:00")
        # London BST (UTC+1) vs New York EDT (UTC-4): -5 hours.
        self.assertEqual(result["shift_hours"], -5)

    def test_daylight_saving_is_handled(self):
        # Lima stays at UTC-5 all year; New York is EST (UTC-5) in
        # January and EDT (UTC-4) in July, so the shift changes.
        winter = jetlag.plan("newyork", "lima",
                             "2026-01-15 10:00", "2026-01-15 12:00")
        summer = jetlag.plan("newyork", "lima",
                             "2026-07-15 10:00", "2026-07-15 12:00")
        self.assertEqual(winter["shift_hours"], 0)
        self.assertEqual(summer["shift_hours"], -1)


class TestFlightDuration(unittest.TestCase):
    def test_duration_across_date_line(self):
        # Tokyo 18:00 Dec 1 (09:00 UTC) -> Lima 17:00 Dec 1 (22:00 UTC):
        # 13 hours of flight.
        result = jetlag.plan("tokyo", "lima",
                             "2026-12-01 18:00", "2026-12-01 17:00")
        self.assertAlmostEqual(result["flight_hours"], 13.0)

    def test_arrival_before_departure_is_rejected(self):
        # Lima 03:00 Dec 1 is 08:00 UTC, before the 09:00 UTC departure.
        with self.assertRaises(ValueError):
            jetlag.plan("tokyo", "lima",
                        "2026-12-01 18:00", "2026-12-01 03:00")


class TestRecoveryDays(unittest.TestCase):
    def test_eastward_one_day_per_hour(self):
        self.assertEqual(jetlag.recovery_days(5), 5)
        self.assertEqual(jetlag.recovery_days(14), 14)

    def test_westward_half_day_per_hour(self):
        self.assertEqual(jetlag.recovery_days(-6), 3)
        self.assertEqual(jetlag.recovery_days(-5), 3)  # 2.5 rounds up

    def test_zero_shift_zero_days(self):
        self.assertEqual(jetlag.recovery_days(0), 0)


class TestSchedule(unittest.TestCase):
    def test_eastward_shifts_bedtime_earlier(self):
        from datetime import date
        plan = jetlag.shift_schedule(3, date(2026, 12, 10))
        self.assertEqual(len(plan), 3)
        # 3 days out: 1h earlier, 2 days out: 2h, day before: 3h.
        self.assertEqual([b for _, b in plan], ["22:00", "21:00", "20:00"])
        self.assertEqual(plan[0][0], date(2026, 12, 7))

    def test_westward_shifts_bedtime_later(self):
        from datetime import date
        plan = jetlag.shift_schedule(-2, date(2026, 12, 10))
        self.assertEqual([b for _, b in plan], ["00:00", "01:00"])

    def test_schedule_capped_at_a_week(self):
        from datetime import date
        plan = jetlag.shift_schedule(14, date(2026, 12, 10))
        self.assertEqual(len(plan), 7)

    def test_no_schedule_without_shift(self):
        from datetime import date
        self.assertEqual(jetlag.shift_schedule(0, date(2026, 12, 10)), [])


class TestFormatting(unittest.TestCase):
    def test_text_output_mentions_key_facts(self):
        result = jetlag.plan("tokyo", "lima",
                             "2026-12-01 18:00", "2026-12-01 17:00")
        text = jetlag.format_plan(result)
        self.assertIn("Tokyo, Japan", text)
        self.assertIn("Lima, Peru", text)
        self.assertIn("-14.0 hours", text)
        self.assertIn("7 day", text)  # westward: 14h * 0.5 = 7 days

    def test_bad_time_format_is_rejected(self):
        with self.assertRaises(ValueError):
            jetlag.plan("tokyo", "lima", "Dec 1", "2026-12-01 17:00")

    def test_unknown_zone_is_rejected(self):
        with self.assertRaises(Exception):
            jetlag.plan("nowhere", "lima",
                        "2026-12-01 18:00", "2026-12-01 17:00")


if __name__ == "__main__":
    unittest.main()
