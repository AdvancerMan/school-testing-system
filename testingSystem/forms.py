from django import forms


class AuthForm(forms.Form):
    login = forms.CharField(max_length=32)
    password = forms.CharField(max_length=32)
    stay_authorized = forms.BooleanField(required=False)
