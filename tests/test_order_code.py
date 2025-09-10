import os
import sys
import pathlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar  # noqa: E402
from main import generate_public_order_code  # noqa: E402


def setup_function(function):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_order_code_sequence_and_reset():
    db = SessionLocal()
    bar = Bar(name="Test Bar", slug="test-bar")
    db.add(bar)
    db.commit()
    db.refresh(bar)

    tz = ZoneInfo("Europe/Zurich")
    now = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    d1, seq1, code1 = generate_public_order_code(db, bar.id, now)
    assert seq1 == 1
    assert code1 == f"{bar.id:03d}-{now.astimezone(tz).strftime('%d%m%y')}-001"

    now2 = now + timedelta(minutes=5)
    d2, seq2, code2 = generate_public_order_code(db, bar.id, now2)
    assert seq2 == 2
    assert code2.endswith("-002")
    assert d1 == d2

    next_day = now + timedelta(days=1)
    d3, seq3, code3 = generate_public_order_code(db, bar.id, next_day)
    assert seq3 == 1
    assert code3.endswith("-001")
    assert d3 != d1
    db.close()
