from datetime import datetime
import json
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from models import AuditLog


def log_action(
    db: Session,
    *,
    actor_user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    phone: Optional[str] = None,
    credit: Optional[float] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> AuditLog:
    """Persist an audit log entry to the database."""
    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=json.dumps(payload) if payload else None,
        ip=ip,
        user_agent=user_agent,
        phone=phone,
        latitude=Decimal(str(latitude)) if latitude is not None else None,
        longitude=Decimal(str(longitude)) if longitude is not None else None,
        actor_credit=Decimal(str(credit)) if credit is not None else None,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.flush()
    db.commit()
    return log
