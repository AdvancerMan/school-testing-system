from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse
from django.contrib.auth import authenticate, login
from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render

from . import models, forms
from .testSolution.testing import submit_attempt_async


def extract_from_session(name, request, context):
    parameter = request.session.get(name)
    if parameter is not None:
        context[name] = parameter
        del request.session[name]
    return context


class AuthView(TemplateView):
    template_name = "testingSystem/auth.html"

    def get_context_data(self, **kwargs):
        context = super(AuthView, self).get_context_data(**kwargs)
        return extract_from_session('error', self.request, context)

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
class RegisterView(TemplateView):
    template_name = "testingSystem/auth.html"

    def get_context_data(self, **kwargs):
        context = super(RegisterView, self).get_context_data(**kwargs)
        return extract_from_session('error', self.request, context)


# TODO
class RecoverPasswordView(TemplateView):
    template_name = "testingSystem/auth.html"

    def get_context_data(self, **kwargs):
        context = super(RecoverPasswordView, self).get_context_data(**kwargs)
        return extract_from_session('error', self.request, context)


# TODO
class IndexView(TemplateView):
    template_name = "testingSystem/auth.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        return extract_from_session('error', self.request, context)


class TaskView(View):
    def get(self, request, id, *args, **kwargs):
        task = models.Task.objects.filter(id=id).first()
        if task is None:
            # TODO 404 page
            return HttpResponseNotFound()

        return render(request, 'testingSystem/task.html',
                      context=self.get_context_data(request, task))

    def get_context_data(self, request, task):
        context = {
            'task': task,
            'attempts': models.Attempt.objects.filter(
                task__id=task.id,
                author__user_id=request.user.id
            ),
            'languages': [choice[1] for choice in models.Language.choices],
        }
        return extract_from_session('solution', request, context)

    def post(self, request, id, *args, **kwargs):
        form = forms.TaskForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            language = data.get('language')
            solution = data.get('solution_file')
            if solution is None:
                solution = data.get('solution')
            if solution is not None:
                attempt = models.Attempt.objects.create(
                    author=models.MyUser.objects.filter(
                        user__id=request.user.id
                    ).first(),
                    task=models.Task.objects.filter(id=id).first(),
                    solution=solution,
                    language=language,
                )
                submit_attempt_async(attempt)
                request.session['solution'] = data.get('solution')
        return HttpResponseRedirect('')


class AttemptView(View):
    def get(self, request, id, *args, **kwargs):
        attempt = models.Attempt.objects.filter(id=id).first()
        if attempt is None:
            # TODO 404 page
            return HttpResponseNotFound()
        return HttpResponseNotFound(":((")
        # return render(request, 'testingSystem/task.html',
        #               context=self.get_context_data(request, task))
