from . import views
from django.urls import path

urlpatterns = [
    path("auth/", views.AuthView.as_view(), name="auth"),
    path("", views.IndexView.as_view(), name="index"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("forgot/", views.RecoverPasswordView.as_view(), name="forgot"),
    path("task/<int:id>", views.TaskView.as_view(), name="task"),
    path("attempt/<int:id>", views.AttemptView.as_view(), name="attempt"),
]
