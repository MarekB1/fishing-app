from .models import Notification

def unread_notifications(request):
    if request.user.is_authenticated:
        return {
            "unread_notifications": Notification.objects.filter(
                recipient=request.user, read_at__isnull=True
            ).count()
        }
    return {"unread_notifications": 0}
