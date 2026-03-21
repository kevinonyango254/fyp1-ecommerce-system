from django.urls import path
from .views import home, product_list, product_detail, buy_product, order_success, add_rating

urlpatterns = [
    path('', home, name='home'),
    path('products/', product_list, name='product_list'),
    path('products/<int:product_id>/', product_detail, name='product_detail'),
    path('products/<int:product_id>/buy/', buy_product, name='buy_product'),
    path('products/<int:product_id>/rate/', add_rating, name='add_rating'),
    path('order-success/<int:order_id>/', order_success, name='order_success'),
]