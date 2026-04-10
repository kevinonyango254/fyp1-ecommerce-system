from django.urls import path
from .views import (
    home,
    about,
    product_list,
    product_detail,
    add_to_cart,
    view_cart,
    increase_cart_item,
    decrease_cart_item,
    remove_from_cart,
    checkout_cart,
    buy_product,
    payment_page,
    process_payment,
    add_rating,
    order_success,
    order_detail,
    admin_dashboard,
    admin_products,
    add_product,
    edit_product,
    delete_product,
    approve_order,
    reject_order,
    confirm_received,
    not_received,
    user_orders,
)

urlpatterns = [
    path('', home, name='home'),
    path('about/', about, name='about'),

    path('products/', product_list, name='product_list'),
    path('products/<int:product_id>/', product_detail, name='product_detail'),
    path('products/<int:product_id>/buy/', buy_product, name='buy_product'),
    path('products/<int:product_id>/rate/', add_rating, name='add_rating'),
    path('products/<int:product_id>/add-to-cart/', add_to_cart, name='add_to_cart'),

    path('cart/', view_cart, name='view_cart'),
    path('cart/increase/<int:item_id>/', increase_cart_item, name='increase_cart_item'),
    path('cart/decrease/<int:item_id>/', decrease_cart_item, name='decrease_cart_item'),
    path('cart/remove/<int:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/checkout/', checkout_cart, name='checkout_cart'),

    path('payment/<int:order_id>/', payment_page, name='payment_page'),
    path('payment/<int:order_id>/process/', process_payment, name='process_payment'),

    path('order-success/<int:order_id>/', order_success, name='order_success'),
    path('my-orders/<int:order_id>/', order_detail, name='order_detail'),

    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin-products/', admin_products, name='admin_products'),
    path('admin-products/add/', add_product, name='add_product'),
    path('admin-products/edit/<int:product_id>/', edit_product, name='edit_product'),
    path('admin-products/delete/<int:product_id>/', delete_product, name='delete_product'),
    path('admin-dashboard/approve/<int:order_id>/', approve_order, name='approve_order'),
    path('admin-dashboard/reject/<int:order_id>/', reject_order, name='reject_order'),

    path('my-orders/', user_orders, name='user_orders'),
    path('my-orders/confirm/<int:order_id>/', confirm_received, name='confirm_received'),
    path('my-orders/not-received/<int:order_id>/', not_received, name='not_received'),
]