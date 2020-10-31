from django.shortcuts import render

# Create your views here.


def first(request):
    return render(request, 'testingSystem/student_first.html')


def second(request):
    return render(request, 'testingSystem/student_second.html')