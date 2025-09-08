import os
import sys
import pathlib
import hashlib
from types import SimpleNamespace
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["BASE_URL"] = "http://localhost"
os.environ["WALLEE_SPACE_ID"] = "1"
os.environ["WALLEE_USER_ID"] = "1"
os.environ["WALLEE_API_SECRET"] = "secret"

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from models import User, RoleEnum, WalletTopup  # noqa: E402
from main import app  # noqa: E402


def setup_module(module):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _register_user():
    db = SessionLocal()
    password_hash = hashlib.sha256("testpass".encode("utf-8")).hexdigest()
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=password_hash,
        role=RoleEnum.CUSTOMER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _login_user(client: TestClient, email: str, password: str) -> None:
    resp = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_topup_init_creates_record():
    user = _register_user()
    with TestClient(app) as client:
        _login_user(client, user.email, "testpass")
        with patch("main.TransactionServiceApi") as MockTx, patch(
            "main.TransactionPaymentPageServiceApi"
        ) as MockPage:
            MockTx.return_value.create.return_value = SimpleNamespace(id=123)
            MockPage.return_value.payment_page_url.return_value = "https://pay.example/123"
            resp = client.post("/api/topup/init", json={"amount": 10})
        assert resp.status_code == 200
        assert resp.json()["paymentPageUrl"] == "https://pay.example/123"
    db = SessionLocal()
    topup = db.query(WalletTopup).filter(WalletTopup.user_id == user.id).one()
    assert float(topup.amount_decimal) == 10.0
    assert topup.status == "PENDING"
    assert topup.wallee_transaction_id == 123
    updated = db.query(User).filter(User.id == user.id).first()
    assert float(updated.credit or 0) == 0.0
    db.close()
