from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg, Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import (
    Product,
    Category,
    Advertisement,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Rating,
)
from accounts.models import MailboxMessage
import json
import os

import google.generativeai as genai
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def home(request):
    advertisements = Advertisement.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'core/home.html', {'advertisements': advertisements})


def about(request):
    return render(request, 'core/about.html')


def product_list(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')

    products = Product.objects.annotate(
        avg_rating=Avg('ratings__stars')
    )

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    categories = Category.objects.all()

    return render(request, 'core/product_list.html', {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
    })


def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.annotate(avg_rating=Avg('ratings__stars')),
        id=product_id
    )
    ratings = product.ratings.all()

    can_rate = False
    already_rated = False
    is_admin = False

    if request.user.is_authenticated:
        is_admin = request.user.userprofile.role == 'admin'

        purchased = OrderItem.objects.filter(
            product=product,
            order__user=request.user,
            order__status='finished'
        ).exists()

        already_rated = Rating.objects.filter(
            user=request.user,
            product=product
        ).exists()

        can_rate = purchased and not already_rated

    return render(request, 'core/product_detail.html', {
        'product': product,
        'ratings': ratings,
        'can_rate': can_rate,
        'already_rated': already_rated,
        'is_admin': is_admin,
    })


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.stock <= 0:
        return redirect('product_detail', product_id=product.id)

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )

    if not item_created:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            cart_item.save()

    return redirect('view_cart')


@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'core/cart.html', {'cart': cart})


@login_required
def increase_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    if cart_item.quantity < cart_item.product.stock:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('view_cart')


@login_required
def decrease_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()

    return redirect('view_cart')


@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('view_cart')


@login_required
def checkout_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)

    if not cart.items.exists():
        return redirect('view_cart')

    for item in cart.items.all():
        if item.quantity > item.product.stock:
            return render(request, 'core/cart.html', {
                'cart': cart,
                'error': f"Sorry, only {item.product.stock} unit(s) of '{item.product.name}' are currently available."
            })

    total_amount = sum(item.subtotal for item in cart.items.all())

    order = Order.objects.create(
        user=request.user,
        customer_name=request.user.username,
        customer_email=request.user.email,
        total_amount=total_amount,
        status='draft',
        payment_status='pending'
    )

    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.product.price
        )

    cart.items.all().delete()

    return redirect('payment_page', order_id=order.id)


@login_required
def buy_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        customer_name = request.user.username
        customer_email = request.user.email
        quantity = int(request.POST.get('quantity'))

        if quantity > product.stock:
            return render(request, 'core/buy_product.html', {
                'product': product,
                'error': 'Not enough stock available.'
            })

        order = Order.objects.create(
            user=request.user,
            customer_name=customer_name,
            customer_email=customer_email,
            total_amount=product.price * quantity,
            status='draft',
            payment_status='pending'
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.price
        )

        return redirect('payment_page', order_id=order.id)

    return render(request, 'core/buy_product.html', {'product': product})


@login_required
def payment_page(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'core/payment_page.html', {'order': order})


@login_required
def process_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')

        if payment_method:
            # Prevent stock from being deducted more than once
            if order.payment_status != 'paid':
                # Check stock availability again before deducting
                for item in order.items.all():
                    if item.quantity > item.product.stock:
                        return render(request, 'core/payment_page.html', {
                            'order': order,
                            'error': f"Sorry, only {item.product.stock} unit(s) of '{item.product.name}' are available."
                        })

                # Automatically reduce stock after successful payment
                for item in order.items.all():
                    item.product.stock -= item.quantity
                    item.product.save()

            order.payment_method = payment_method
            order.payment_status = 'paid'
            order.status = 'waiting_admin_approve'
            order.save()

            return redirect('order_success', order_id=order.id)

    return redirect('payment_page', order_id=order.id)

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'core/order_success.html', {'order': order})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    for item in order.items.all():
        item.can_review = (
            order.status == 'finished' and
            not Rating.objects.filter(user=request.user, product=item.product).exists()
        )

    return render(request, 'core/order_detail.html', {'order': order})


@login_required
def add_rating(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    purchased = OrderItem.objects.filter(
        product=product,
        order__user=request.user,
        order__status='finished'
    ).exists()

    if not purchased:
        return redirect('product_detail', product_id=product.id)

    existing_rating = Rating.objects.filter(
        user=request.user,
        product=product
    ).exists()

    if existing_rating:
        return redirect('product_detail', product_id=product.id)

    if request.method == 'POST':
        stars = int(request.POST.get('stars'))
        comment = request.POST.get('comment')

        Rating.objects.create(
            user=request.user,
            product=product,
            customer_name=request.user.username,
            stars=stars,
            comment=comment
        )

    return redirect('product_detail', product_id=product.id)


@login_required
def delete_rating(request, rating_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    rating = get_object_or_404(Rating, id=rating_id)
    product_id = rating.product.id
    rating.delete()

    return redirect('product_detail', product_id=product_id)


@login_required
def admin_dashboard(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    orders = Order.objects.all()

    # Search by customer name or email
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(customer_name__icontains=search) |
            Q(customer_email__icontains=search)
        )

    # Filter by order status
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)

    # Sort orders
    sort = request.GET.get('sort', '-created_at')

    allowed_sort_fields = {
        '-created_at',
        'created_at',
        'total_amount',
        '-total_amount'
    }

    if sort not in allowed_sort_fields:
        sort = '-created_at'

    orders = orders.order_by(sort)

    return render(request, 'core/admin_dashboard.html', {
        'orders': orders,
        'search': search,
        'status': status,
        'sort': sort,
    })


@login_required
def admin_products(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    products = Product.objects.all().order_by('-created_at')
    return render(request, 'core/admin_products.html', {'products': products})


@login_required
def add_product(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        stock = request.POST.get('stock')
        low_stock_threshold = request.POST.get('low_stock_threshold')
        image = request.FILES.get('image')
        category_id = request.POST.get('category')

        category = None
        if category_id:
            category = Category.objects.get(id=category_id)

        Product.objects.create(
            name=name,
            category=category,
            description=description,
            price=price,
            stock=stock,
            low_stock_threshold=low_stock_threshold or 5,
            image=image
        )

        return redirect('admin_products')

    categories = Category.objects.all()


    return render(request, 'core/add_product.html', {
        'categories': categories,
    })


@login_required
def edit_product(request, product_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        product.low_stock_threshold = request.POST.get('low_stock_threshold') or 5

        category_id = request.POST.get('category')
        if category_id:
            product.category = Category.objects.get(id=category_id)
        else:
            product.category = None

        if request.FILES.get('image'):
            product.image = request.FILES.get('image')

        product.save()

        return redirect('admin_products')

    return render(request, 'core/edit_product.html', {
        'product': product,
        'categories': Category.objects.all(),
    })


@login_required
def delete_product(request, product_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return redirect('admin_products')


@login_required
def admin_advertisements(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    advertisements = Advertisement.objects.all().order_by('-created_at')
    return render(request, 'core/admin_advertisements.html', {'advertisements': advertisements})


@login_required
def add_advertisement(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        title = request.POST.get('title')
        subtitle = request.POST.get('subtitle')
        button_text = request.POST.get('button_text')
        link = request.POST.get('link')
        image = request.FILES.get('image')
        is_active = request.POST.get('is_active') == 'on'

        Advertisement.objects.create(
            title=title,
            subtitle=subtitle,
            button_text=button_text or 'Shop Now',
            link=link or '/products/',
            image=image,
            is_active=is_active
        )

        return redirect('admin_advertisements')

    return render(request, 'core/add_advertisement.html')


@login_required
def edit_advertisement(request, advertisement_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    advertisement = get_object_or_404(Advertisement, id=advertisement_id)

    if request.method == 'POST':
        advertisement.title = request.POST.get('title')
        advertisement.subtitle = request.POST.get('subtitle')
        advertisement.button_text = request.POST.get('button_text') or 'Shop Now'
        advertisement.link = request.POST.get('link') or '/products/'
        advertisement.is_active = request.POST.get('is_active') == 'on'

        if request.FILES.get('image'):
            advertisement.image = request.FILES.get('image')

        advertisement.save()
        return redirect('admin_advertisements')

    return render(request, 'core/edit_advertisement.html', {'advertisement': advertisement})


@login_required
def delete_advertisement(request, advertisement_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    advertisement = get_object_or_404(Advertisement, id=advertisement_id)
    advertisement.delete()
    return redirect('admin_advertisements')


@login_required
def approve_order(request, order_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    order = get_object_or_404(Order, id=order_id)
    order.status = 'waiting_user_received'
    order.save()

    return redirect('admin_dashboard')


@login_required
def reject_order(request, order_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    order = get_object_or_404(Order, id=order_id)
    order.status = 'rejected'
    order.save()

    MailboxMessage.objects.create(
        sender=request.user,
        receiver=order.user,
        subject='Order Rejected',
        content=f'Your order #{order.id} has been rejected by admin. Please check your order details or contact support.'
    )

    return redirect('admin_dashboard')


@login_required
def confirm_received(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'waiting_user_received':
        order.status = 'finished'
        order.save()
    return redirect('user_orders')


@login_required
def not_received(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'waiting_user_received':
        order.status = 'waiting_admin_approve'
        order.save()

        MailboxMessage.objects.create(
            sender=request.user,
            receiver=order.user,
            subject='Delivery Issue Reported',
            content=f'You reported that order #{order.id} was not received. The order has been returned to admin for review.'
        )

    return redirect('user_orders')


@login_required
def user_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    for order in orders:
        order.pending_reviews = []
        if order.status == 'finished':
            for item in order.items.all():
                already_rated = Rating.objects.filter(
                    user=request.user,
                    product=item.product
                ).exists()
                if not already_rated:
                    order.pending_reviews.append(item)

    return render(request, 'core/user_orders.html', {'orders': orders})


@login_required
def admin_users(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    role = request.GET.get('role', '')

    users = User.objects.all().select_related('userprofile')

    if role in ['user', 'support', 'admin']:
        users = users.filter(userprofile__role=role)

    return render(request, 'core/admin_users.html', {
        'users': users,
        'selected_role': role,
    })


@login_required
def change_user_role(request, user_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_role = request.POST.get('role')

        if new_role in ['admin', 'support', 'user']:
            old_role = user.userprofile.role

            if old_role != new_role:
                user.userprofile.role = new_role
                user.userprofile.save()

                return redirect(
                    f'/admin-users/?role={request.GET.get("role", "")}&role_changed=1'
                )

    return redirect('admin_users')

@login_required
def delete_user(request, user_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    user = get_object_or_404(User, id=user_id)

    # Prevent admin from deleting their own account
    if user == request.user:
        return redirect('admin_users')

    if request.method == 'POST':
        user.delete()

    return redirect('admin_users')

@login_required
def admin_categories(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    categories = Category.objects.all().order_by('name')

    return render(request, 'core/admin_categories.html', {
        'categories': categories
    })


@login_required
def add_category(request):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name')

        if name:
            Category.objects.create(name=name)

        return redirect('admin_categories')

    return render(request, 'core/add_category.html')


@login_required
def edit_category(request, category_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.save()
        return redirect('admin_categories')

    return render(request, 'core/edit_category.html', {
        'category': category
    })


@login_required
def delete_category(request, category_id):
    if request.user.userprofile.role != 'admin':
        return redirect('home')

    category = get_object_or_404(Category, id=category_id)
    category.delete()

    return redirect('admin_categories')

@csrf_exempt
def chatbot(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required"}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "")

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = f"""
        You are GoBuy's AI shopping assistant.

        Help customers politely.
        Recommend products.
        Answer shopping questions.
        Keep answers concise.

        Customer:
        {user_message}
        """

        response = model.generate_content(prompt)

        return JsonResponse({
            "reply": response.text
        })

    except Exception as e:
        return JsonResponse({
            "error": str(e)
        }, status=500)

def chatbot_page(request):
    return render(request, "core/chatbot.html")