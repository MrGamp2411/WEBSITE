import os
import sys
import pathlib
import hashlib
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from urllib.parse import urlencode

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["BASE_URL"] = "http://localhost"
os.environ["WALLEE_SPACE_ID"] = "1"
os.environ["WALLEE_USER_ID"] = "1"
os.environ["WALLEE_API_SECRET"] = "secret"
os.environ["WALLEE_VERIFY_SIGNATURE"] = "false"

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
    unique = uuid4().hex
    user = User(
        username=f"testuser_{unique}",
        email=f"test_{unique}@example.com",
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
        with patch("app.wallee_client.tx_service") as MockTx, patch(
            "app.wallee_client.pp_service"
        ) as MockPage:
            MockTx.create.return_value = SimpleNamespace(id=123)
            MockPage.payment_page_url.return_value = "https://pay.example/123"
            resp = client.post("/api/topup/init", json={"amount": 10})
            create_kwargs = MockTx.create.call_args.kwargs
        assert resp.status_code == 200
        assert resp.json()["paymentPageUrl"] == "https://pay.example/123"
    db = SessionLocal()
    topup = db.query(WalletTopup).filter(WalletTopup.user_id == user.id).one()
    assert float(topup.amount_decimal) == 10.0
    assert topup.status == "PENDING"
    assert topup.wallee_tx_id == 123
    base_url = os.environ["BASE_URL"].rstrip("/")
    expected_success = f"{base_url}/wallet/topup/success?" + urlencode({"topup": topup.id})
    expected_failed = f"{base_url}/wallet/topup/failed?" + urlencode({"topup": topup.id})
    tx_create = create_kwargs["transaction"]
    assert tx_create.success_url == expected_success
    assert tx_create.failed_url == expected_failed
    updated = db.query(User).filter(User.id == user.id).first()
    assert float(updated.credit or 0) == 0.0
    db.close()


def test_topup_init_missing_wallee_config_returns_503():
    user = _register_user()
    with TestClient(app) as client:
        _login_user(client, user.email, "testpass")
        with patch.dict(
            os.environ,
            {
                "WALLEE_SPACE_ID": "",
                "WALLEE_USER_ID": "",
                "WALLEE_API_SECRET": "",
            },
            clear=False,
        ):
            resp = client.post("/api/topup/init", json={"amount": 10})
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Top-up service unavailable"


def test_topup_below_minimum_rejected():
    user = _register_user()
    with TestClient(app) as client:
        _login_user(client, user.email, "testpass")
        resp = client.post("/api/topup/init", json={"amount": 5})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Amount must be between 10 and 1000"


def test_topup_transaction_updates_wallet():
    user = _register_user()
    with TestClient(app) as client:
        _login_user(client, user.email, "testpass")
        with patch("app.wallee_client.tx_service") as MockTx, patch(
            "app.wallee_client.pp_service"
        ) as MockPage:
            MockTx.create.return_value = SimpleNamespace(id=456)
            MockPage.payment_page_url.return_value = "https://pay.example/456"
            resp = client.post("/api/topup/init", json={"amount": 12})
            assert resp.status_code == 200
        wallet = client.get("/wallet")
        assert "Processing" in wallet.text
        db = SessionLocal()
        topup = db.query(WalletTopup).filter(WalletTopup.user_id == user.id).one()
        db.close()
        client.post(
            "/webhooks/wallee",
            json={"entityId": topup.wallee_tx_id, "state": "COMPLETED"},
        )
        wallet = client.get("/wallet")
        assert "Completed" in wallet.text
        assert "CHF 12.00" in wallet.text


def test_failed_topup_shows_zero_amount():
    user = _register_user()
    with TestClient(app) as client:
        _login_user(client, user.email, "testpass")
        with patch("app.wallee_client.tx_service") as MockTx, patch(
            "app.wallee_client.pp_service"
        ) as MockPage:
            MockTx.create.return_value = SimpleNamespace(id=789)
            MockPage.payment_page_url.return_value = "https://pay.example/789"
            resp = client.post("/api/topup/init", json={"amount": 15})
            assert resp.status_code == 200
        db = SessionLocal()
        topup = db.query(WalletTopup).filter(WalletTopup.user_id == user.id).one()
        db.close()
        client.post(
            "/webhooks/wallee",
            json={"entityId": topup.wallee_tx_id, "state": "FAILED"},
        )
        wallet = client.get("/wallet")
        assert "Failed" in wallet.text
        assert "+ CHF 0.00" in wallet.text
        assert 'pill canceled">Failed</span>' in wallet.text


def test_wallet_transactions_ordered_newest_first():
    user = _register_user()
    with TestClient(app) as client:
        _login_user(client, user.email, "testpass")
        with patch("app.wallee_client.tx_service") as MockTx, patch(
            "app.wallee_client.pp_service"
        ) as MockPage:
            MockTx.create.return_value = SimpleNamespace(id=111)
            MockPage.payment_page_url.return_value = "https://pay.example/111"
            client.post("/api/topup/init", json={"amount": 12})
        with patch("app.wallee_client.tx_service") as MockTx, patch(
            "app.wallee_client.pp_service"
        ) as MockPage:
            MockTx.create.return_value = SimpleNamespace(id=222)
            MockPage.payment_page_url.return_value = "https://pay.example/222"
            client.post("/api/topup/init", json={"amount": 18})
        wallet = client.get("/wallet")
        assert wallet.text.index("CHF 18.00") < wallet.text.index("CHF 12.00")
