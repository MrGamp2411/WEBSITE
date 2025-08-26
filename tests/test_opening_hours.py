import os
import pathlib
import sys

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datetime import datetime
from zoneinfo import ZoneInfo

import main


def test_is_open_now_respects_timezone(monkeypatch):
    hours = {"0": {"open": "14:00", "close": "15:30"}}
    monkeypatch.setenv("BAR_TIMEZONE", "Europe/Rome")
    tz = ZoneInfo("Europe/Rome")

    class FakeDatetime(datetime):
        tz_used = None

        @classmethod
        def now(cls, tz=None):
            cls.tz_used = tz
            return cls(2024, 1, 1, 14, 30, tzinfo=tz)

    monkeypatch.setattr(main, "datetime", FakeDatetime)
    assert main.is_open_now_from_hours(hours)
    assert FakeDatetime.tz_used == tz

    class FakeDatetimeClosed(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 1, 1, 16, 0, tzinfo=tz)

    monkeypatch.setattr(main, "datetime", FakeDatetimeClosed)
    assert not main.is_open_now_from_hours(hours)
