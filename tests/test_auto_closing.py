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
    canceled = Order(bar=bar, status="CANCELED", subtotal=5, vat_total=1)
    db.add_all([bar, order, canceled])
    db.commit()
    auto_close_bars_once(db, now)
    closings = db.query(BarClosing).filter_by(bar_id=bar.id).all()
    assert len(closings) == 1
    assert float(closings[0].total_revenue) == 12.0
    orders = db.query(Order).order_by(Order.id).all()
    assert [o.closing_id for o in orders] == [closings[0].id, closings[0].id]
    db.close()
