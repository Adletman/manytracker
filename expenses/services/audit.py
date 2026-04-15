from expenses.models import AuditLog


def write_audit(*, user, action, entity, entity_id, diff=None):
    return AuditLog.objects.create(
        user=user,
        action=action,
        entity=entity,
        entity_id=entity_id,
        diff=diff or {},
    )
