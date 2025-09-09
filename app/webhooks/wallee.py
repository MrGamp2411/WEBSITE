import os
import json
from datetime import datetime
import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
from decimal import Decimal

from models import User, WalletTopup, Payment, Order, OrderItem, Bar, WalletTransaction
from .wallee_verify import verify_signature_bytes

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhooks/wallee")
async def handle_wallee_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        raw = await request.body()
        verify = os.getenv("WALLEE_VERIFY_SIGNATURE", "true").lower() == "true"
        if verify:
            sig = request.headers.get("x-signature") or request.headers.get("X-Signature")
            verify_signature_bytes(raw, sig)
        else:
            print("WARNING: skipping signature verification (test mode)")

        payload = json.loads(raw.decode("utf-8"))
        tx_id_raw = payload.get("entityId") or payload.get("id")
        try:
            tx_id = int(tx_id_raw)
        except Exception:
            return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.warning("Malformed Wallee webhook payload")
        return {"ok": True}

    payment = (
        db.query(Payment)
        .with_for_update()
        .filter(Payment.wallee_tx_id == str(tx_id))
        .one_or_none()
    )
    if payment:
        state = (payload.get("state") or "").upper()
        payment.state = state
        db.add(payment)
        order = db.get(Order, payment.order_id) if payment.order_id else None
        if state in ("FULFILL", "COMPLETED"):
            if not order:
                data = payment.raw_payload or {}
                items = [
                    OrderItem(
                        menu_item_id=i["menu_item_id"],
                        qty=i["qty"],
                        unit_price=Decimal(str(i["unit_price"])),
                        line_total=Decimal(str(i["line_total"])),
                    )
                    for i in data.get("items", [])
                ]
                order = Order(
                    bar_id=data.get("bar_id"),
                    customer_id=data.get("customer_id"),
                    table_id=data.get("table_id"),
                    subtotal=Decimal(str(data.get("subtotal", 0))),
                    status="PLACED",
                    payment_method=data.get("payment_method", "card"),
                    paid_at=datetime.utcnow(),
                    items=items,
                    notes=data.get("notes"),
                )
                db.add(order)
                db.commit()
                payment.order_id = order.id
                db.add(payment)
            else:
                order.paid_at = datetime.utcnow()
                db.add(order)
            db.commit()
            from main import (
                send_order_update,
                user_carts,
                save_cart_for_user,
                Cart,
            )
            customer_id = order.customer_id if order else None
            if customer_id:
                user_carts.pop(customer_id, None)
                save_cart_for_user(customer_id, Cart())
            await send_order_update(order)
            from main import users, Transaction, TransactionItem
            if order and order.customer_id:
                cached = users.get(order.customer_id)
                if cached:
                    exists = any(
                        getattr(t, "order_id", None) == order.id
                        for t in cached.transactions
                    )
                    if not exists:
                        bar = order.bar or db.get(Bar, order.bar_id)
                        tx = Transaction(
                            bar.id if bar else order.bar_id,
                            bar.name if bar else "",
                            [],
                            float(order.total),
                            order.payment_method,
                            order_id=order.id,
                            status="PROCESSING",
                            created_at=order.created_at,
                        )
                        tx.items = [
                            TransactionItem(
                                i.menu_item_name or "",
                                i.qty,
                                float(i.unit_price),
                            )
                            for i in order.items
                        ]
                        cached.transactions.append(tx)
                        db.add(
                            WalletTransaction(
                                user_id=order.customer_id,
                                type="payment",
                                bar_id=bar.id if bar else order.bar_id,
                                bar_name=bar.name if bar else "",
                                items_json=[
                                    {
                                        "name": i.menu_item_name or "",
                                        "quantity": i.qty,
                                        "price": float(i.unit_price),
                                    }
                                    for i in order.items
                                ],
                                total=Decimal(str(order.total)),
                                payment_method=order.payment_method,
                                order_id=order.id,
                                status="PROCESSING",
                                created_at=order.created_at,
                            )
                        )
                        db.commit()
        elif state in ("FAILED", "DECLINE", "DECLINED", "VOIDED"):
            if order:
                order.status = "CANCELED"
                if not order.cancelled_at:
                    order.cancelled_at = datetime.utcnow()
                db.add(order)
                db.commit()
                from main import send_order_update
                await send_order_update(order)
            else:
                db.commit()
        else:
            db.commit()
        return {"ok": True}

    topup = (
        db.query(WalletTopup)
        .with_for_update()
        .filter(WalletTopup.wallee_tx_id == tx_id)
        .one_or_none()
    )

    if not topup:
        return {"ok": True}

    state = (payload.get("state") or "").upper()
    if state in ("COMPLETED", "FULFILL") and topup.processed_at is None:
        user = db.get(User, topup.user_id)
        if user:
            user.credit = (user.credit or Decimal("0")) + topup.amount_decimal
            db.add(user)
            from main import users
            cached = users.get(user.id)
            if cached:
                cached.credit = float(user.credit)
                for tx in cached.transactions:
                    if getattr(tx, "topup_id", None) == topup.id:
                        tx.status = "COMPLETED"
                        break
        topup.status = state
        topup.processed_at = datetime.utcnow()
        db.add(topup)
        wallet_tx = (
            db.query(WalletTransaction)
            .filter(WalletTransaction.topup_id == topup.id)
            .one_or_none()
        )
        if wallet_tx:
            wallet_tx.status = "COMPLETED"
            db.add(wallet_tx)
        db.commit()
        logger.info("Processed Wallee topup %s with state %s", tx_id, state)
    elif state in ("FAILED", "DECLINE", "DECLINED", "VOIDED", "CANCELED", "CANCELLED"):
        topup.status = "FAILED"
        db.add(topup)
        wallet_tx = (
            db.query(WalletTransaction)
            .filter(WalletTransaction.topup_id == topup.id)
            .one_or_none()
        )
        if wallet_tx:
            wallet_tx.status = "FAILED"
            wallet_tx.total = Decimal("0")
            db.add(wallet_tx)
        db.commit()
        from main import users
        cached = users.get(topup.user_id)
        if cached:
            for tx in cached.transactions:
                if getattr(tx, "topup_id", None) == topup.id:
                    tx.status = "FAILED"
                    tx.total = 0.0
                    break

    return {"ok": True}
