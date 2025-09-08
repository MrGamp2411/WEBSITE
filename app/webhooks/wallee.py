import os
import hmac
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import Order, Payment


router = APIRouter()


def verify_signature(raw: bytes, provided: Optional[str]) -> bool:
    """Verify HMAC-SHA512 signature using env secret.

    If ``WALLEE_WEBHOOK_SECRET`` is missing or empty, the signature is
    considered valid to ease local development.
    """

    secret = os.getenv("WALLEE_WEBHOOK_SECRET")
    if not secret:
        return True
    if not provided:
        return False
    computed = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
    return hmac.compare_digest(computed, provided)


def map_wallee_state(state: str) -> Optional[str]:
    """Map Wallee transaction states to order statuses."""

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
    signature = request.headers.get("x-signature")
    if not verify_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = json.loads(raw_body)
        entity = payload.get("entity") or {}
        tx_id = int(entity["id"])
        state = entity["state"]
    except Exception:
        logging.warning("Malformed Wallee webhook payload")
        return {"ok": True}

    payment = (
        db.query(Payment).filter(Payment.wallee_tx_id == tx_id).one_or_none()
    )

    if payment and payment.state == state:
        # Idempotent: same state already processed
        return {"ok": True}

    if payment is None:
        payment = Payment(wallee_tx_id=tx_id)
        db.add(payment)
        logging.warning("Payment %s not linked to any order", tx_id)

    payment.state = state
    payment.raw_payload = payload
    payment.updated_at = datetime.utcnow()

    mapped = map_wallee_state(state)
    if mapped and payment.order_id:
        order = db.get(Order, payment.order_id)
        if order:
            order.status = mapped
    elif not payment.order_id:
        logging.warning("Payment %s received without order_id", tx_id)

    db.commit()
    logging.info("Processed Wallee transaction %s with state %s", tx_id, state)
    return {"ok": True}

