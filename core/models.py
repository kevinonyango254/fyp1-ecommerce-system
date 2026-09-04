from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
    Category,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='products'
)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    low_stock_threshold = models.IntegerField(default=5)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_out_of_stock(self):
        return self.stock <= 0

    @property
    def is_low_stock(self):
        return self.stock > 0 and self.stock <= self.low_stock_threshold

class AdminNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('low_stock', 'Low Stock'),
        ('inventory', 'Inventory'),
        ('system', 'System'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_notifications'
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default='system'
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"

class InventoryMovement(models.Model):
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase'),
        ('restock', 'Restock'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory_movements'
    )

    movement_type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPES
    )

    quantity = models.IntegerField()

    stock_before = models.IntegerField()
    stock_after = models.IntegerField()

    reference = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_movements'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.movement_type} - "
            f"{self.quantity}"
        )
class Advertisement(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='advertisements/')
    button_text = models.CharField(max_length=100, default='Shop Now')
    link = models.CharField(max_length=255, default='/products/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Cart"

    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cart', 'product'], name='unique_cart_product')
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('waiting_admin_approve', 'Waiting Admin Approve'),
        ('waiting_user_received', 'Waiting User Received Item'),
        ('finished', 'Finished'),
        ('rejected', 'Rejected'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('tng', 'TNG E-Wallet'),
        ('card', 'Master Card'),
        ('bank', 'Bank Transfer'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        null=True,
        blank=True
    )

    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='draft'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not is_new:
            previous = Order.objects.get(pk=self.pk)

            if (
                previous.status != 'waiting_user_received'
                and self.status == 'waiting_user_received'
            ):

                # Check stock before approval
                for item in self.items.all():
                    if item.product.stock < item.quantity:
                        raise ValueError(
                            f"Not enough stock for {item.product.name}."
                        )

                super().save(*args, **kwargs)

                # Deduct stock once
                for item in self.items.all():
                    product = item.product
                    product.stock -= item.quantity
                    product.save(update_fields=['stock'])

                return

        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.IntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class Rating(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ratings',
        null=True,
        blank=True
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='ratings'
    )

    customer_name = models.CharField(max_length=255)
    stars = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_product_rating'
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.stars} stars"