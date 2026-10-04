from sqlalchemy.orm import Session
from typing import Optional


def log_action(
    db         : Session,
    action     : str,
    user_id    : Optional[int] = None,
    details    : Optional[str] = None,
    ip_address : Optional[str] = None
) -> None:
    """
    Log important actions for audit trail.
    Called inside existing transaction — no commit here.
    """
    from models.game import AuditLog

    log = AuditLog(
        user_id    = user_id,
        action     = action,
        details    = details,
        ip_address = ip_address
    )
    db.add(log)
