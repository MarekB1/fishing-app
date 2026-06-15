from .models import Notification

def unread_notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications": 0, "recent_notifications": []}

    unread_qs = Notification.objects.filter(
        recipient=request.user, 
        read_at__isnull=True
    ).select_related('competition').order_by('-created_at')
    
    read_qs = Notification.objects.filter(
        recipient=request.user, 
        read_at__isnull=False
    ).select_related('competition').order_by('-created_at')[:3]

    combined_notifications = list(unread_qs) + list(read_qs)

    return {
        "unread_notifications": unread_qs.count(),
        "recent_notifications": combined_notifications,
    }