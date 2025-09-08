import os
import pathlib
import sys

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import Bar  # noqa: E402
from main import app, DemoUser, users, users_by_email, users_by_username, bars  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def teardown_module(module):
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
    bars.clear()


def test_bar_admin_cannot_edit_rating():
    db = SessionLocal()
    bar = Bar(
        name='Test Bar',
        slug='test-bar',
        rating=3.5,
        address='Addr',
        city='City',
        state='State',
        latitude=0.0,
        longitude=0.0,
        description='Desc',
    )
    db.add(bar)
    db.commit()
    db.refresh(bar)
    bars[bar.id] = bar
    db.close()

    admin = DemoUser(
        id=1,
        username='baradmin',
        password='pass',
        email='admin@example.com',
        role='bar_admin',
        bar_ids=[bar.id],
    )
    users[admin.id] = admin
    users_by_email[admin.email] = admin
    users_by_username[admin.username] = admin

    client = TestClient(app)
    client.post('/login', data={'email': admin.email, 'password': admin.password})

    resp = client.get(f'/admin/bars/edit/{bar.id}/info')
    assert resp.status_code == 200
    assert 'name="rating"' not in resp.text

    resp = client.post(
        f'/admin/bars/edit/{bar.id}/info',
        data={
            'name': 'Test Bar',
            'address': 'Addr',
            'city': 'City',
            'state': 'State',
            'latitude': '0',
            'longitude': '0',
            'description': 'Desc',
            'rating': '4.9',
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303

    check = SessionLocal()
    updated = check.get(Bar, bar.id)
    assert updated.rating == 3.5
    check.close()
