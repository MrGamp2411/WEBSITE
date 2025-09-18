import os
import sys
import pathlib
import hashlib
from decimal import Decimal
from urllib.parse import urlparse, parse_qs

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from models import Bar, Category, MenuItem, Table, User  # noqa: E402
from main import app, load_bars_from_db  # noqa: E402


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_checkout_redirects_when_wallet_credit_missing():
    setup_db()
    with TestClient(app) as client:
        db = SessionLocal()
        bar = Bar(name='Test Bar', slug='test-bar')
        db.add(bar)
        db.commit()
        db.refresh(bar)

        cat = Category(bar_id=bar.id, name='Drinks')
        db.add(cat)
        db.commit()
        db.refresh(cat)

        item = MenuItem(bar_id=bar.id, category_id=cat.id, name='Water', price_chf=5)
        db.add(item)

        table = Table(bar_id=bar.id, name='T1')
        db.add(table)

        pwd = hashlib.sha256('pass'.encode('utf-8')).hexdigest()
        user = User(
            username='u',
            email='u@example.com',
            password_hash=pwd,
            credit=Decimal('2.00'),
        )
        db.add(user)
        db.commit()
        db.refresh(item)
        db.refresh(table)
        db.refresh(user)
        item_id, bar_id, table_id, user_email, user_id = (
            item.id,
            bar.id,
            table.id,
            user.email,
            user.id,
        )
        db.close()
        load_bars_from_db()

        client.post('/login', data={'email': user_email, 'password': 'pass'})
        client.post(f'/bars/{bar_id}/add_to_cart', data={'product_id': item_id})

        resp = client.post(
            '/cart/checkout',
            data={'table_id': table_id, 'payment_method': 'wallet'},
            follow_redirects=False,
        )

        assert resp.status_code == 303
        location = resp.headers['location']
        parsed = urlparse(location)
        assert parsed.path == '/cart'
        qs = parse_qs(parsed.query)
        assert qs.get('notice') == ['wallet_insufficient']
        assert qs.get('noticeTitle') == ['Add wallet credit']

        db = SessionLocal()
        refreshed = db.get(User, user_id)
        assert refreshed.credit == Decimal('2.00')
        db.close()
