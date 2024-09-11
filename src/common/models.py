from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()



class LogDBEntry(models.Model):
    msg = models.CharField(max_length=3000)
    logger = models.CharField(max_length=255, default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs')

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_created']


class BigLog(models.Model):
    msg = models.TextField()
    logger = models.CharField(max_length=255, default='')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='big_logs')

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_created']