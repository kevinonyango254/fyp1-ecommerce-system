from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('support', 'Support'),
        ('user', 'User'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    active_session_key = models.CharField(max_length=40, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class MailboxMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=255)
    content = models.TextField()
    thread_id = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.thread_id:
            self.thread_id = f"thread-{self.id}"
            MailboxMessage.objects.filter(pk=self.pk).update(thread_id=self.thread_id)

    def __str__(self):
        return f"{self.subject} -> {self.receiver.username}"