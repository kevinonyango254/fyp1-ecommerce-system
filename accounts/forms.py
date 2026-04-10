from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class ContactSupportForm(forms.Form):
    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter subject'
        })
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Describe your issue clearly...',
            'rows': 6
        })
    )