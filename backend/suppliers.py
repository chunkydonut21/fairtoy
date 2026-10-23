from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import SupplierFlag


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def flag_supplier(session: Session, finisher_id: str, supplier_id: str, reason: str) -> SupplierFlag | None:
    flag = SupplierFlag(finisher_id=finisher_id, supplier_id=supplier_id, reason=reason, flagged_at=now())
    session.add(flag)
    try:
        session.commit()
    except IntegrityError:
        # An open flag already exists, or the finisher or supplier is unknown.
        session.rollback()
        return None
    return flag


def resolve_flag(session: Session, finisher_id: str, flag_id: int, outcome: str, note: str) -> SupplierFlag | None:
    # One conditional UPDATE, so two resolutions of the same flag cannot both succeed.
    resolved = session.execute(
        update(SupplierFlag)
        .where(
            SupplierFlag.id == flag_id, SupplierFlag.finisher_id == finisher_id,
            SupplierFlag.resolved_at.is_(None),
        )
        .values(resolved_at=now(), outcome=outcome, resolution_note=note)
    ).rowcount
    if not resolved:
        session.rollback()
        return None
    session.commit()
    return session.get(SupplierFlag, flag_id)
