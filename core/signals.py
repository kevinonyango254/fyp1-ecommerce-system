from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import Product, AdminNotification


@receiver(pre_save, sender=Product)
def check_low_stock_before_save(sender, instance, **kwargs):
    """
    Store the previous stock value before the Product is saved.
    This allows us to detect the stock level before the change.
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
    Create an admin notification whenever a product is saved
    with stock at or below its low-stock threshold.

    This ensures that a purchase such as:
        7 stock -> purchase 4 -> 3 stock

    still generates a low-stock warning.
    """

    previous_stock = getattr(
        instance,
        '_previous_stock',
        None
    )

    # Only create a notification when the product has stock
    # at or below the configured threshold.
    low_stock_after_change = (
        instance.stock > 0
        and instance.stock <= instance.low_stock_threshold
    )

    # Avoid creating another notification when the product was
    # already low-stock and its stock remains low after a change.
    newly_low_or_reduced = (
        previous_stock is None
        or previous_stock > instance.low_stock_threshold
        or (
            previous_stock > instance.stock
            and instance.stock <= instance.low_stock_threshold
        )
    )

    if low_stock_after_change and newly_low_or_reduced:

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