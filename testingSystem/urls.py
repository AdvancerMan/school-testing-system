from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.IndexView, name='index'),
    path('classwork/', views.ClassWorkView.as_view(), name='classwork'),
    path('homework/', views.HomeWorkView.as_view(), name='homework'),
    path('examwork/', views.ExamWorkView.as_view(), name='examwork'),
    path("auth/", views.AuthView.as_view(), name="auth"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("forgot/", views.RecoverPasswordView.as_view(), name="forgot"),
    path("task/<int:id>", views.TaskView.as_view(), name="task"),
    path("attempt/<int:id>", views.AttemptView.as_view(), name="attempt"),
    re_path('', views.get404Response)
]
