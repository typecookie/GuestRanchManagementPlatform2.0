from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    DASHBOARD_DEFAULT = "default"
    DASHBOARD_OWNER = "owner"

    DASHBOARD_CHOICES = [
        (DASHBOARD_DEFAULT, "Operations Dashboard (Default)"),
        (DASHBOARD_OWNER, "Ranch Owner Photo Dashboard"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    dashboard = models.CharField(
        max_length=50,
        choices=DASHBOARD_CHOICES,
        default=DASHBOARD_DEFAULT,
        verbose_name="Home Dashboard",
        help_text="Select the default home screen dashboard displayed upon login.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile ({self.get_dashboard_display()})"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)
