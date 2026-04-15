from decimal import Decimal
from django.db import transaction
from expenses.models import Topup, AuditLog
from expenses.services.audit import write_audit


def create_topup(*, admin, user, amount: Decimal, topup_date, comment: str = ""):
    if amount <= 0:
        raise ValueError("Сумма должна быть больше нуля")
    with transaction.atomic():
        topup = Topup.objects.create(
            user=user, amount=amount, date=topup_date, comment=comment,
            created_by=admin,
        )
        write_audit(
            user=admin, action=AuditLog.ACTION_CREATE,
            entity=AuditLog.ENTITY_TOPUP, entity_id=topup.id,
            diff={"amount": str(amount), "user_id": user.id, "date": topup_date.isoformat()},
        )
    return topup
