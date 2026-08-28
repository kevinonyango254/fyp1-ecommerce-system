from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    register_view,
    login_view,
    logout_view,
    mailbox,
    mailbox_detail,
    contact_support,
    new_message,
    DebugPasswordResetView,
)

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('mailbox/', mailbox, name='mailbox'),
    path('mailbox/<int:message_id>/', mailbox_detail, name='mailbox_detail'),
    path('contact-support/', contact_support, name='contact_support'),
    path('new-message/', new_message, name='new_message'),

    path(
        'password-reset/',
        DebugPasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt'
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html'
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]