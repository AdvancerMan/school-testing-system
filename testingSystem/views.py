from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login
from django.views.generic import TemplateView

from . import models, forms


def move_error_message(request, context):
    error = request.session.get('error')
    if error is not None:
        context['error'] = error
        del request.session['error']
    return context


class AuthView(TemplateView):
    template_name = "testingSystem/auth.html"

    def get_context_data(self, **kwargs):
        context = super(AuthView, self).get_context_data(**kwargs)
        return move_error_message(self.request, context)

    def post(self, request, *args, **kwargs):
        form = forms.AuthForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = authenticate(username=data['login'],
                                password=data['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponseRedirect(reverse('index'))
                else:
                    request.session['error'] = 'Этот пользователь заблокирован'
            else:
                request.session['error'] = 'Неправильный логин или пароль'
        else:
            request.session['error'] = 'Пожалуйста, попробуйте еще раз'
        return HttpResponseRedirect('')

# TODO
# class RegisterView(TemplateView):
#     template_name = "testingSystem/register.html"
#
#     def get_context_data(self, **kwargs):
#         context = super(RegisterView, self).get_context_data(**kwargs)
#         return move_error_message(self.request, context)

# TODO
# class RecoverPasswordView(TemplateView):
#     template_name = "testingSystem/forgot.html"
#
#     def get_context_data(self, **kwargs):
#         context = super(RecoverPasswordView, self).get_context_data(**kwargs)
#         return move_error_message(self.request, context)
