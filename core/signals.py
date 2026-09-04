from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import Product, AdminNotification


@receiver(pre_save, sender=Product)
def check_low_stock_before_save(sender, instance, **kwargs):
    """
    Store the previous stock value before the Product is saved.
    This allows us to detect when a product newly enters
    the low-stock condition.
    """

    if not instance.pk:
        instance._previous_stock = None
        return

    try:
        previous = Product.objects.get(pk=instance.pk)
        instance._previous_stock = previous.stock
    except Product.DoesNotExist:
        instance._previous_stock = None


@receiver(post_save, sender=Product)
def create_low_stock_notification(sender, instance, created, **kwargs):
    """
    Create a notification for active admin users when a product
    newly enters the low-stock condition.
    """

    previous_stock = getattr(
        instance,
        '_previous_stock',
        None
    )

    newly_low_stock = (
        instance.is_low_stock
        and (
            previous_stock is None
            or previous_stock > instance.low_stock_threshold
        )
    )

    if newly_low_stock:

        admins = User.objects.filter(
            is_staff=True,
            is_active=True
        )

        for admin in admins:
            AdminNotification.objects.create(
                recipient=admin,
                notification_type='low_stock',
                title='Low Stock Warning',
                message=(
                    f'{instance.name} is running low on stock. '
                    f'Current stock: {instance.stock}. '
                    f'Low-stock threshold: '
                    f'{instance.low_stock_threshold}.'
                )
            )