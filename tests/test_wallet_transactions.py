import os
import sys
import pathlib

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from main import app, user_carts, users, users_by_email, users_by_username  # noqa: E402
from test_cancel_order import setup_db, create_order  # noqa: E402


def test_wallet_transaction_status_updates():
    setup_db()
    with TestClient(app) as client:
        ids = create_order(client, 'wallet')

        client.post('/login', data={'email': ids['customer_email'], 'password': 'pass'})
        wallet = client.get('/wallet')
        assert 'Processing' in wallet.text
        client.get('/logout')

        client.post('/login', data={'email': ids['bartender_email'], 'password': 'pass'})
        client.post(f"/api/orders/{ids['order_id']}/status", json={'status': 'ACCEPTED'})
        client.get('/logout')

        client.post('/login', data={'email': ids['customer_email'], 'password': 'pass'})
        wallet = client.get('/wallet')
        assert 'Completed' in wallet.text
        client.get('/logout')

        client.post('/login', data={'email': ids['bartender_email'], 'password': 'pass'})
        client.post(f"/api/orders/{ids['order_id']}/status", json={'status': 'CANCELED'})
        client.get('/logout')

        client.post('/login', data={'email': ids['customer_email'], 'password': 'pass'})
        wallet = client.get('/wallet')
        assert 'Canceled' in wallet.text
        assert '- CHF 0.00' in wallet.text

    user_carts.clear()
    users.clear()
    users_by_email.clear()
    users_by_username.clear()
