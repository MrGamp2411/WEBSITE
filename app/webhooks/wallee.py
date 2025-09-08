"""Wallee payment webhook.

Example (development, signature disabled)::

    curl -X POST http://localhost:8000/webhooks/wallee \
        -H "Content-Type: application/json" \
        -d '{"entity":{"id":"123456789","state":"COMPLETED"}}'
"""

import json
import logging
import os
from base64 import b64decode
from datetime import datetime, timedelta
from typing import Dict

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from wallee import ApiClient, Configuration
from wallee.api import WebhookEncryptionServiceApi

from database import get_db
from models import Order, Payment, User, WalletTopup


router = APIRouter()
logger = logging.getLogger(__name__)

_public_key_cache: Dict[str, tuple[bytes, datetime]] = {}
_CACHE_TTL = timedelta(hours=1)


def parse_x_signature(header: str) -> Dict[str, str]:
    parts = [p.strip() for p in header.split(",") if "=" in p]
    return {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in parts)}


def get_public_key_pem(key_id: str) -> bytes:
    cached = _public_key_cache.get(key_id)
    now = datetime.utcnow()
    if cached and cached[1] > now:
        return cached[0]

    config = Configuration()
    config.user_id = int(os.getenv("WALLEE_USER_ID", "0"))
    config.api_secret = os.getenv("WALLEE_API_SECRET", "")
    service = WebhookEncryptionServiceApi(ApiClient(config))
    key = service.read(id=key_id)
    pem = key.public_key.encode()
    _public_key_cache[key_id] = (pem, now + _CACHE_TTL)
    return pem


def verify_signature(raw_body: bytes, header: str) -> None:
    if not header:
        raise HTTPException(status_code=401, detail="missing signature")

    parsed = parse_x_signature(header)
    if parsed.get("algorithm") != "SHA256withECDSA":
        raise HTTPException(status_code=401, detail="invalid signature algorithm")

    key_id = parsed.get("keyId")
    signature_b64 = parsed.get("signature")
    if not key_id or not signature_b64:
        raise HTTPException(status_code=401, detail="invalid signature")

    public_pem = get_public_key_pem(key_id)
    public_key = serialization.load_pem_public_key(public_pem)
    signature = b64decode(signature_b64)
    try:
        public_key.verify(signature, raw_body, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise HTTPException(status_code=401, detail="invalid signature") from exc


def map_wallee_state(state: str) -> str | None:
    mapping = {
        "AUTHORIZED": "authorized",
        "COMPLETED": "paid",
        "FAILED": "failed",
        "DECLINE": "failed",
        "VOIDED": "voided",
        "EXPIRED": "voided",
    }
    return mapping.get(state)


@router.post("/webhooks/wallee")
async def handle_wallee_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()

    require_sig = os.getenv("WALLEE_SIGNATURE_REQUIRED", "true").lower() == "true"
    if require_sig:
        verify_signature(raw_body, request.headers.get("x-signature"))

    try:
        payload = json.loads(raw_body)
        entity = payload.get("entity") or {}
        tx_id = str(entity["id"])
        state = entity["state"]
        amount = entity.get("amount")
        currency = entity.get("currency")
    except Exception:
        logger.warning("Malformed Wallee webhook payload")
        return {"ok": True}

    payment = db.query(Payment).filter(Payment.wallee_tx_id == tx_id).one_or_none()
    if payment:
        if payment.state == state:
            return {"ok": True}

        payment.state = state
        payment.raw_payload = payload
        payment.updated_at = datetime.utcnow()
        if amount is not None:
            payment.amount = amount
        if currency:
            payment.currency = currency

        mapped = map_wallee_state(state)
        if mapped and payment.order_id:
            order = db.get(Order, payment.order_id)
            if order:
                order.status = mapped
        elif mapped == "paid" and payment.user_id:
            user = db.get(User, payment.user_id)
            if user and payment.amount:
                user.credit = (user.credit or 0) + payment.amount
        elif not payment.order_id and not payment.user_id:
            logger.warning("Payment %s received without order_id", tx_id)

        db.commit()
        logger.info("Processed Wallee transaction %s with state %s", tx_id, state)
        return {"ok": True}

    topup = (
        db.query(WalletTopup)
        .filter(WalletTopup.wallee_transaction_id == int(tx_id))
        .one_or_none()
    )
    if topup:
        if topup.status == state:
            return {"ok": True}
        if state in ["FULFILL", "COMPLETED"]:
            if not topup.processed_at:
                user = db.get(User, topup.user_id)
                if user:
                    user.credit = (user.credit or 0) + float(topup.amount_decimal)
                topup.processed_at = datetime.utcnow()
            topup.status = state
        elif state == "FAILED":
            topup.status = "FAILED"
        db.commit()
        logger.info("Processed Wallee topup %s with state %s", tx_id, state)
        return {"ok": True}

    logger.warning("Payment %s not linked to any record", tx_id)
    return {"ok": True}

