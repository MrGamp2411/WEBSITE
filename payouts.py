from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Order, Payout


def schedule_payout(db: Session, bar_id: int, period_start: datetime, period_end: datetime) -> Payout:
    """Aggregate completed orders for a bar and create a payout entry.

    Args:
        db: Database session.
        bar_id: Bar identifier for which to schedule the payout.
        period_start: Start datetime of the aggregation window (inclusive).
        period_end: End datetime of the aggregation window (inclusive).

    Returns:
        The created ``Payout`` instance.

    Raises:
        ValueError: If no completed orders exist in the given range.
    """
    totals = db.query(
        func.sum(Order.payout_due_to_bar).label("payout_total")
    ).filter(
        Order.bar_id == bar_id,
        Order.status == "completed",
        Order.created_at >= period_start,
        Order.created_at <= period_end,
    ).first()

    if not totals or totals.payout_total is None:
        raise ValueError("No completed orders for given range")

    payout_total = Decimal(totals.payout_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    payout = Payout(
        bar_id=bar_id,
        amount_chf=payout_total,
        period_start=period_start,
        period_end=period_end,
        status="scheduled",
    )
    db.add(payout)
    db.commit()
    db.refresh(payout)
    return payout
