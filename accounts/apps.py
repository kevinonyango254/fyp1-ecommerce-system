from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(create_default_superadmin, sender=self)


def create_default_superadmin(sender, **kwargs):
    from django.contrib.auth.models import User
    from .models import UserProfile

    username = 'superadmin'
    email = 'academicexpert10@gmail.com'
    password = 'admin1234'

    if not User.objects.filter(username=username).exists():
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        UserProfile.objects.get_or_create(
            user=user,
            defaults={'role': 'admin'}
        )