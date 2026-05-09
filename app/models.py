from django.db import models


class Channel(models.Model):
    tg_id = models.BigIntegerField()
    channel_link = models.URLField(null=True, blank=True)
    channel_username = models.CharField(max_length=255, null=True, blank=True)
    channel_title = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.channel_title

    class Meta:
        db_table = "channels"
        verbose_name = "Channel"
        verbose_name_plural = "Channels"


class User(models.Model):
    tg_id = models.BigIntegerField()
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    is_blocked = models.BooleanField(default=False)
    last_activity = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} ({self.tg_id})"

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
