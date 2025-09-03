import os
import sys
import pathlib
import json
from datetime import datetime

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, Order, BarClosing  # noqa: E402
from main import auto_close_bars_once  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_auto_close_bars_once():
    setup_db()
    db = SessionLocal()
    now = datetime.utcnow().replace(hour=0, minute=2, second=0, microsecond=0)
    hours = {str(now.weekday()): {"open": "00:00", "close": "00:01"}}
    bar = Bar(name="Test Bar", slug="test-bar", opening_hours=json.dumps(hours))
    order = Order(bar=bar, status="COMPLETED", subtotal=10, vat_total=2)
    db.add_all([bar, order])
    db.commit()
    auto_close_bars_once(db, now)
    closings = db.query(BarClosing).filter_by(bar_id=bar.id).all()
    assert len(closings) == 1
    assert float(closings[0].total_revenue) == 12.0
    order = db.query(Order).first()
    assert order.closing_id == closings[0].id
    db.close()
