from django import forms
from . import models


class AuthForm(forms.Form):
    login = forms.CharField(max_length=32)
    password = forms.CharField(max_length=32)
    stay_authorized = forms.BooleanField(required=False)


class TaskForm(forms.Form):
    language = forms.ChoiceField(choices=models.Language.choices)
    solution = forms.CharField(required=False, empty_value=None,
                               max_length=256 * 1024)
    solution_file = forms.FileField(required=False, max_length=256 * 1024)
