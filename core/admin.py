from django.contrib import admin
from .models import Product, Advertisement, Order, OrderItem, Rating


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'price',
        'stock',
        'low_stock_threshold',
        'stock_warning',
        'created_at'
    )

    def stock_warning(self, obj):
        if obj.is_out_of_stock:
            return 'Out of Stock'
        elif obj.is_low_stock:
            return 'Low Stock'
        return 'Normal'

    stock_warning.short_description = 'Stock Warning'


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'button_text', 'link', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'subtitle')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'customer_email', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'customer_email')
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'unit_price')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'customer_name', 'stars', 'created_at')
    readonly_fields = ('product', 'customer_name', 'stars', 'comment', 'created_at')

    def has_add_permission(self, request):
        return False