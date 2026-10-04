from sqlalchemy.orm import Session
from models.audit import AuditLog
from typing import Optional
import json


def log_action(
    db        : Session,
    action    : str,
    user_id   : Optional[int] = None,
    entity    : Optional[str] = None,
    entity_id : Optional[int] = None,
    details   : Optional[dict] = None,
    ip_address: Optional[str] = None
):
    """
    Log important actions for audit trail.
    Used in gambling/gaming apps for compliance.
    Never raises exception — audit failure should not break main flow.
    """
    try:
        log = AuditLog(
            user_id    = user_id,
            action     = action,
            entity     = entity,
            entity_id  = entity_id,
            details    = json.dumps(details) if details else None,
            ip_address = ip_address
        )
        db.add(log)
        # Note: we do NOT commit here
        # audit log commits with the main transaction
        # if main transaction rolls back, audit log rolls back too
        # this ensures consistency
    except Exception as e:
        print(f"Audit log failed: {e}")  # log but don't raise
