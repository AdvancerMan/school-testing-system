
from django.urls import path, include
from . import views
urlpatterns = [

    path('', views.first),
    path('classwork', views.classwork),
    path('homework', views.homework),
    path('examwork', views.examwork)
]