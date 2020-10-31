from . import views
from django.urls import path

urlpatterns = [
    path("auth/", views.AuthView.as_view(), name="auth"),
    # path("", views.IndexView.as_view(), name="index"),
    # path("register/", views.RegisterView.as_view(), name="register"),
    # path("forgot/", views.RecoverPasswordView.as_view(), name="forgot"),
]
