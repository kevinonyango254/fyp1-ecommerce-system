from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.contrib.auth.models import User
        from .models import UserProfile

        if not User.objects.filter(username='superadmin').exists():
            user = User.objects.create_superuser(
                username='superadmin',
                email='academicexpert10@gmail.com',
                password='admin1234'
            )

            UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'admin'}
            )