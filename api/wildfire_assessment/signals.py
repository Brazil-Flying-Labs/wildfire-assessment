from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    from wildfire_assessment.models import UserProfile

    if created:
        UserProfile.objects.create(user=instance)
