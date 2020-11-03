from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse
from django.contrib.auth import authenticate, login
from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render

from . import models, forms
from .testSolution.testing import submit_attempt_async, invoke_post_processor


def extract_from_session(name, request, context):
    parameter = request.session.get(name)
    if parameter is not None:
        context[name] = parameter
        del request.session[name]
    return context


def get404Response(request, *args, **kwargs):
    return HttpResponseNotFound(render(
        request, "testingSystem/404.html"
    ))


class ClassWorkView(TemplateView):
    template_name = 'testingSystem/student_classwork.html'


class IndexView(TemplateView):
    template_name = 'testingSystem/student_first.html'


class HomeWorkView(TemplateView):
    template_name = 'testingSystem/student_homework.html'


class ExamWorkView(TemplateView):
    template_name = 'testingSystem/student_examwork.html'


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


def tests_snapshot(attempt):
    tests = list(attempt.checked_tests.all())
    if models.Status.TS in [test.status for test in tests]:
        attempt.score = invoke_post_processor(attempt, tests)
    return tests


class TaskView(View):
    def get(self, request, id, *args, **kwargs):
        task = models.Task.objects.filter(id=id).first()
        if task is None:
            return get404Response(request)
        return render(request, 'testingSystem/task.html',
                      context=self.get_context_data(request, task))

    def get_context_data(self, request, task):
        context = {
            'task': task,
            'attempts': list(models.Attempt.objects.filter(
                task__id=task.id,
                author__user_id=request.user.id
            ).all()),
            'languages': [choice[0] for choice in models.Language.choices]
        }
        for attempt in context['attempts']:
            tests_snapshot(attempt)
        extract_from_session('error', request, context)
        return extract_from_session('solution', request, context)

    def post(self, request, id, *args, **kwargs):
        form = forms.TaskForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            language = data.get('language')
            solution_file = data.get('solution_file')
            solution = data.get('solution')
            if solution_file is not None:
                solution = solution_file.file.read().decode()
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
                request.session['solution'] = solution
            else:
                request.session['error'] = 'Пожалуйста, добавьте свое ' \
                                           'решение перед отправкой'
            request.session['language'] = language
        else:
            request.session['error'] = 'Некорректный ввод'
        return HttpResponseRedirect('')


class AttemptView(View):
    def get(self, request, id, *args, **kwargs):
        attempt = models.Attempt.objects.filter(id=id).first()
        if attempt is None:
            return get404Response(request)
        return render(request, 'testingSystem/attempt.html',
                      context={
                          'attempt': attempt,
                          'tests': tests_snapshot(attempt)
                      })
