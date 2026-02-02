from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def broadcast_unread_count(user_id: int, *, unread_count=None, refresh_pending=False, message=None):
    if unread_count is None:
        unread_count = Notification.objects.filter(recipient_id=user_id, read_at__isnull=True).count()

    data = {"unread_count": unread_count}
    if refresh_pending:
        data["refresh_pending"] = True
    if message:
        data["message"] = message

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {"type": "notify", "data": data},
    )
