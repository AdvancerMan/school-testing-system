from django.db import models
from django.contrib.auth import models as auth_models


class Class(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class Role(models.TextChoices):
    PUPIL = 'PU', 'Ученик'
    TEACHER = 'TC', 'Учитель'
    ADMIN = 'AD', 'Администратор'


class MyUser(models.Model):
    user = models.OneToOneField(auth_models.User, on_delete=models.CASCADE)
    middle_name = models.CharField(max_length=64)
    school = models.CharField(max_length=256)
    rating = models.IntegerField()
    school_class = models.ForeignKey(Class, null=True,
                                     on_delete=models.SET_NULL)
    role = models.CharField(max_length=2, choices=Role.choices)

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name} " \
               f"{self.middle_name}"


class Test(models.Model):
    input = models.CharField(max_length=256 * 1024)
    output = models.CharField(max_length=256 * 1024)


class Testset(models.Model):
    tests = models.ManyToManyField(Test)


class Task(models.Model):
    id = models.BigAutoField(primary_key=True)
    author = models.ForeignKey(MyUser, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=64)
    legend = models.CharField(max_length=2048)
    statement = models.CharField(max_length=16 * 1024)
    testset = models.ForeignKey(Testset, null=True, on_delete=models.SET_NULL)
    samples_prefix = models.IntegerField()
    time_limit = models.IntegerField()
    memory_limit = models.IntegerField()
    checker_path = models.CharField(null=True, max_length=128)
    post_processor_path = models.CharField(null=True, max_length=128)
    creation_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Задача {self.name} от пользователя {self.author}"


class Status(models.TextChoices):
    OK = 'OK', 'Решение зачтено'
    CE = 'CE', 'Ошибка компиляции'
    WA = 'WA', 'Неверный ответ'
    TL = 'TL', 'Превышен лимит времени'
    ML = 'ML', 'Превышен лимит памяти'
    RE = 'RE', 'Ошибка выполнения'
    IL = 'IL', 'Превышен лимит ожидания'
    RJ = 'RJ', 'Решение отклонено'


class Language(models.TextChoices):
    PYTHON = 'Python', 'Python'
    CPP = 'C++', 'Java'


class Attempt(models.Model):
    id = models.BigAutoField(primary_key=True)
    author = models.ForeignKey(MyUser, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    solution = models.CharField(max_length=256 * 1024)
    language = models.CharField(max_length=32, choices=Language.choices)
    status = models.CharField(max_length=2, choices=Status.choices)
    failed_test_index = models.IntegerField()
    memory_used = models.IntegerField()
    time_used = models.IntegerField()
    creation_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Попытка по задаче {self.task.name} " \
               f"от пользователя {self.author} [{self.status}]"
