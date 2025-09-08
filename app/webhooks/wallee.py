import os
import json
from datetime import datetime
import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User, WalletTopup, Payment, Order
from .wallee_verify import verify_signature_bytes

router = APIRouter()
logger = logging.getLogger(__name__)

VERIFY = os.getenv("WALLEE_VERIFY_SIGNATURE", "true").lower() == "true"


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
    try:
        raw = await request.body()
        if VERIFY:
            sig = request.headers.get("x-signature") or request.headers.get("X-Signature")
            verify_signature_bytes(raw, sig)
        else:
            print("WARNING: skipping signature verification (test mode)")

        payload = json.loads(raw.decode("utf-8"))
        entity = payload.get("entity") or {}
        tx_id = str(
            entity.get("id")
            or payload.get("entityId")
            or payload.get("id")
            or ""
        )
        state = (entity.get("state") or payload.get("state") or "").upper()
        amount = entity.get("amount") or payload.get("amount")
        currency = entity.get("currency") or payload.get("currency")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.warning("Malformed Wallee webhook payload")
        return {"ok": True}

    payment = db.query(Payment).filter(Payment.wallee_tx_id == tx_id).one_or_none()
    if payment:
        if payment.state != state:
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
        .filter(WalletTopup.wallee_transaction_id == int(tx_id or 0))
        .one_or_none()
    )
    if topup:
        if topup.status != state:
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
