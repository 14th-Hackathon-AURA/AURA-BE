from django.db import IntegrityError, transaction

from .models import Notification


def create_notification(*, user, type, title, body, action_url="", event_key=None):
    defaults = {
        "type": type,
        "title": title,
        "body": body,
        "action_url": action_url,
    }
    if not event_key:
        return Notification.objects.create(user=user, **defaults)

    try:
        with transaction.atomic():
            notification, _ = Notification.objects.get_or_create(
                user=user,
                event_key=event_key,
                defaults=defaults,
            )
            return notification
    except IntegrityError:
        return Notification.objects.get(user=user, event_key=event_key)
