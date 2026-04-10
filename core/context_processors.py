from .models import Cart
from accounts.models import MailboxMessage


def cart_count(request):
    count = 0

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = sum(item.quantity for item in cart.items.all())
        except Cart.DoesNotExist:
            count = 0

    return {'cart_count': count}


def unread_mailbox_count(request):
    count = 0

    if request.user.is_authenticated:
        count = MailboxMessage.objects.filter(
            receiver=request.user,
            is_read=False
        ).count()

    return {'unread_mailbox_count': count}