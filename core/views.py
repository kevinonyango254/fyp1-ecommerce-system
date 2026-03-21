from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg
from .models import Product, Order, OrderItem, Rating

def home(request):
    return render(request, 'core/home.html')


def product_list(request):
    products = Product.objects.annotate(avg_rating=Avg('ratings__stars'))
    return render(request, 'core/product_list.html', {'products': products})


def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.annotate(avg_rating=Avg('ratings__stars')), id=product_id)
    ratings = product.ratings.all()
    return render(request, 'core/product_detail.html', {
        'product': product,
        'ratings': ratings
    })


def buy_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        customer_email = request.POST.get('customer_email')
        quantity = int(request.POST.get('quantity'))

        if quantity > product.stock:
            return render(request, 'core/buy_product.html', {
                'product': product,
                'error': 'Not enough stock available.'
            })

        order = Order.objects.create(
            customer_name=customer_name,
            customer_email=customer_email,
            total_amount=product.price * quantity,
            payment_status='Pending'
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.price
        )

        order.payment_status = 'Paid'
        order.save()

        return redirect('order_success', order_id=order.id)

    return render(request, 'core/buy_product.html', {'product': product})


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'core/order_success.html', {'order': order})


def add_rating(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name')
        stars = int(request.POST.get('stars'))
        comment = request.POST.get('comment')

        Rating.objects.create(
            product=product,
            customer_name=customer_name,
            stars=stars,
            comment=comment
        )

    return redirect('product_detail', product_id=product.id)

    from django.contrib.auth.models import User

def create_admin():
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            username='admin',
            email='admin@gmail.com',
            password='root1234'
        )