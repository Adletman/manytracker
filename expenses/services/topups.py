from decimal import Decimal
from django.db import transaction
from expenses.models import Topup, AuditLog
from expenses.services.audit import write_audit


def create_topup(*, created_by, user, amount: Decimal, topup_date, comment: str = "", source: str = "admin"):
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    if source == "employee" and not comment.strip():
        raise ValueError("Комментарий обязателен для пополнения от сотрудника")
    with transaction.atomic():
        topup = Topup.objects.create(
            user=user, amount=amount, date=topup_date, comment=comment,
            created_by=created_by, source=source,
        )
        write_audit(
            user=created_by, action=AuditLog.ACTION_CREATE,
            entity=AuditLog.ENTITY_TOPUP, entity_id=topup.id,
            diff={
                "amount": str(amount), "user_id": user.id,
                "date": topup_date.isoformat(), "source": source,
            },
        )
    return topup
