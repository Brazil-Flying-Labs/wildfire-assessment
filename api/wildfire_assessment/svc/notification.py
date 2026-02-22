"""Service layer for Notification queries and mutations."""

from wildfire_assessment.models import Notification


def get_notifications_queryset(user):
    """Return notifications for a user with related objects eager-loaded."""
    return Notification.objects.filter(
        user=user,
    ).select_related("analysis_run", "analysis_run__area_of_interest")


def get_unread_count(user):
    """Return the number of unread notifications for a user."""
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_notification_read(notification):
    """Mark a single notification as read."""
    notification.is_read = True
    notification.save(update_fields=["is_read"])


def mark_notifications_read_by_run(user, analysis_run_id):
    """Mark all unread notifications for a given analysis run as read. Returns count."""
    return Notification.objects.filter(
        user=user,
        analysis_run_id=analysis_run_id,
        is_read=False,
    ).update(is_read=True)


def mark_all_notifications_read(user):
    """Mark all unread notifications for a user as read. Returns count."""
    return Notification.objects.filter(
        user=user,
        is_read=False,
    ).update(is_read=True)
