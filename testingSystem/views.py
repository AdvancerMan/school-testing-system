from django.shortcuts import render

# Create your views here.


def classwork(request):
    return render(request, 'testingSystem/student_classwork.html')


def first(request):
    return render(request, 'testingSystem/student_first.html')


def homework(request):
    return render(request, 'testingSystem/student_homework.html')

def examwork(request):
    return render(request, 'testingSystem/student_examwork.html')