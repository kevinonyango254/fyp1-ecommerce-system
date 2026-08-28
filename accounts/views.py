from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.contrib.auth.views import PasswordResetView
from .forms import RegisterForm, ContactSupportForm
from .models import UserProfile, MailboxMessage


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user, defaults={'role': 'user'})
            login(request, user)

            if user.userprofile.role == 'admin':
                if not request.session.session_key:
                    request.session.save()

                user.userprofile.active_session_key = request.session.session_key
                user.userprofile.save(update_fields=['active_session_key'])

                return redirect('admin_dashboard')

            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'user'}
            )

            if profile.role == 'admin' and profile.active_session_key:
                Session.objects.filter(session_key=profile.active_session_key).delete()

            login(request, user)

            if profile.role == 'admin':
                if not request.session.session_key:
                    request.session.save()

                profile.active_session_key = request.session.session_key
                profile.save(update_fields=['active_session_key'])
                return redirect('admin_dashboard')

            return redirect('home')
        else:
            return render(request, 'accounts/login.html', {
                'error': 'Invalid username or password'
            })

    return render(request, 'accounts/login.html')


def logout_view(request):
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': 'user'}
        )

        if profile.role == 'admin' and profile.active_session_key == request.session.session_key:
            profile.active_session_key = None
            profile.save(update_fields=['active_session_key'])

    logout(request)
    return redirect('home')


@login_required
def mailbox(request):
    all_messages = MailboxMessage.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related('sender', 'receiver').order_by('-created_at')

    conversations = []
    seen_threads = set()

    for msg in all_messages:
        if not msg.thread_id:
            msg.thread_id = f"thread-{msg.id}"
            msg.save(update_fields=['thread_id'])

        if msg.thread_id in seen_threads:
            continue

        seen_threads.add(msg.thread_id)

        other_user = msg.receiver if msg.sender == request.user else msg.sender

        unread_count = MailboxMessage.objects.filter(
            thread_id=msg.thread_id,
            receiver=request.user,
            is_read=False
        ).count()

        conversations.append({
            'latest_message': msg,
            'thread_id': msg.thread_id,
            'other_user': other_user,
            'unread_count': unread_count,
        })

    return render(request, 'accounts/mailbox.html', {'conversations': conversations})


@login_required
def mailbox_detail(request, message_id):
    message = get_object_or_404(
        MailboxMessage.objects.select_related('sender', 'receiver'),
        id=message_id
    )

    # Only participants can view the conversation
    if request.user != message.sender and request.user != message.receiver:
        return redirect('mailbox')

    if not message.thread_id:
        message.thread_id = f"thread-{message.id}"
        message.save(update_fields=['thread_id'])

    thread_messages = MailboxMessage.objects.filter(
        thread_id=message.thread_id
    ).select_related('sender', 'receiver').order_by('created_at')

    MailboxMessage.objects.filter(
        thread_id=message.thread_id,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)

    first_message = thread_messages.first()

    other_user = (
        first_message.receiver
        if first_message.sender == request.user
        else first_message.sender
    )

    reply_error = None

    if request.method == 'POST':
        reply_content = request.POST.get('reply_content', '').strip()

        if reply_content:
            sender_role = request.user.userprofile.role
            receiver_role = other_user.userprofile.role

            # Normal users can ONLY communicate with Support
            if sender_role == 'user' and receiver_role != 'support':
                reply_error = 'Users can only contact support.'

            # Support can communicate with Users, Support and Admin
            elif sender_role == 'support' and receiver_role not in [
                'user',
                'support',
                'admin'
            ]:
                reply_error = 'You are not allowed to contact this account.'

            else:
                reply_message = MailboxMessage.objects.create(
                    sender=request.user,
                    receiver=other_user,
                    subject=first_message.subject,
                    content=reply_content,
                    thread_id=message.thread_id
                )

                return redirect(
                    'mailbox_detail',
                    message_id=reply_message.id
                )

        else:
            reply_error = 'Reply message cannot be empty.'

    return render(request, 'accounts/mailbox_detail.html', {
        'message': message,
        'thread_messages': thread_messages,
        'other_user': other_user,
        'reply_error': reply_error,
    })


@login_required
def contact_support(request):
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'role': 'user'}
    )

    # Only normal users can use Contact Support
    if profile.role != 'user':
        return redirect('mailbox')

    error = None

    # Normal users can contact SUPPORT ONLY
    support_users = UserProfile.objects.filter(
        role='support'
    ).select_related('user').order_by('user__username')

    if request.method == 'POST':
        form = ContactSupportForm(request.POST)

        receiver_id = request.POST.get('receiver')

        if form.is_valid():
            try:
                receiver_profile = support_users.get(id=receiver_id)
            except UserProfile.DoesNotExist:
                receiver_profile = None

            if receiver_profile is None:
                error = 'Please select a support staff member.'
            else:
                first_message = MailboxMessage.objects.create(
                    sender=request.user,
                    receiver=receiver_profile.user,
                    subject=form.cleaned_data['subject'],
                    content=form.cleaned_data['content']
                )

                return redirect(
                    'mailbox_detail',
                    message_id=first_message.id
                )

    else:
        form = ContactSupportForm()

    return render(request, 'accounts/contact_support.html', {
        'form': form,
        'error': error,
        'support_users': support_users,
    })

@login_required
def new_message(request):
    profile, created = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'role': 'user'}
    )

    # Only Support accounts can start new messages from this page
    if profile.role != 'support':
        return redirect('mailbox')

    error = None

    # Support can contact Users, other Support accounts, and Admins
    recipients = UserProfile.objects.filter(
        role__in=['user', 'support', 'admin']
    ).exclude(
        user=request.user
    ).select_related('user').order_by('role', 'user__username')

    if request.method == 'POST':
        form = ContactSupportForm(request.POST)
        receiver_id = request.POST.get('receiver')

        if form.is_valid():
            try:
                receiver_profile = recipients.get(id=receiver_id)
            except UserProfile.DoesNotExist:
                receiver_profile = None

            if receiver_profile is None:
                error = 'Please select a valid recipient.'
            else:
                first_message = MailboxMessage.objects.create(
                    sender=request.user,
                    receiver=receiver_profile.user,
                    subject=form.cleaned_data['subject'],
                    content=form.cleaned_data['content']
                )

                return redirect(
                    'mailbox_detail',
                    message_id=first_message.id
                )
    else:
        form = ContactSupportForm()

    return render(request, 'accounts/new_message.html', {
        'form': form,
        'error': error,
        'recipients': recipients,
    })


class DebugPasswordResetView(PasswordResetView):
    def form_valid(self, form):
        print("EMAILS FOUND:", list(form.get_users(form.cleaned_data["email"])))
        print("ABOUT TO SEND EMAIL")

        response = super().form_valid(form)

        print("EMAIL SEND FINISHED")
        return response