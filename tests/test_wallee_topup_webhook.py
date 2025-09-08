import os
import sys
import pathlib
import hashlib

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["WALLEE_SIGNATURE_REQUIRED"] = "false"

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import User, RoleEnum, WalletTopup  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_webhook_credits_user():
    db = SessionLocal()
    password_hash = hashlib.sha256("pass".encode("utf-8")).hexdigest()
    user = User(
        username="webhookuser",
        email="hook@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
        credit=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    topup = WalletTopup(
        id="abc",
        user_id=user.id,
        amount_decimal=10,
        currency="CHF",
        status="PENDING",
        wallee_transaction_id=123,
    )
    db.add(topup)
    db.commit()
    db.close()

    with TestClient(app) as client:
        resp = client.post(
            "/webhooks/wallee",
            json={"entity": {"id": "123", "state": "COMPLETED", "amount": 10, "currency": "CHF"}},
        )
        assert resp.status_code == 200

    db = SessionLocal()
    updated = db.query(User).filter(User.id == user_id).first()
    assert float(updated.credit) == 10.0
    topup = db.query(WalletTopup).filter(WalletTopup.id == "abc").one()
    assert topup.status == "COMPLETED"
    assert topup.processed_at is not None
    db.close()
