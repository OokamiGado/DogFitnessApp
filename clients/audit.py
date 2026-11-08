from .models import AuditLog


def log_action(request, action, target_type, obj, description=''):
    """Tworzy wpis w dzienniku zmian. Wywolywane recznie z widokow po
    wykonaniu akcji (create/update/archive/restore/delete/toggle)."""
    user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    AuditLog.objects.create(
        user=user,
        action=action,
        target_type=target_type,
        target_id=getattr(obj, 'pk', None),
        target_repr=str(obj),
        description=description,
    )
