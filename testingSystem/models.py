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


class Status(models.TextChoices):
    OK = 'OK', 'Решение зачтено'
    CE = 'CE', 'Ошибка компиляции'
    WA = 'WA', 'Неверный ответ'
    TL = 'TL', 'Превышен лимит времени'
    ML = 'ML', 'Превышен лимит памяти'
    RE = 'RE', 'Ошибка выполнения'
    IL = 'IL', 'Превышен лимит ожидания'
    SE = 'SE', 'Ошибка сервера'
    RJ = 'RJ', 'Решение отклонено'
    TS = 'TS', 'Рещение тестируется'


class Test(models.Model):
    input = models.CharField(max_length=256 * 1024)
    output = models.CharField(max_length=256 * 1024)

    def __str__(self):
        return f"Вход: {self.input};; " \
               f"Выход: {self.output}"


class Testset(models.Model):
    tests = models.ManyToManyField(Test)


class CheckedTest(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    status = models.CharField(max_length=2, choices=Status.choices)
    memory_used = models.IntegerField()
    time_used = models.IntegerField()
    message = models.CharField(default="", max_length=256 * 1024)

    def __str__(self):
        return f"{self.message} " \
               f"[{self.status}] " \
               f"Использовано памяти: {self.memory_used} Килобайт; " \
               f"Использовано времени: {self.time_used} миллисекунд"


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
    checker_name = models.CharField(null=True, max_length=128)
    post_processor_name = models.CharField(null=True, max_length=128)
    creation_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Language(models.TextChoices):
    PYTHON = 'Python', 'Python'
    CPP = 'C++', 'C++'


class Attempt(models.Model):
    id = models.BigAutoField(primary_key=True)
    author = models.ForeignKey(MyUser, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    solution = models.CharField(max_length=256 * 1024)
    language = models.CharField(max_length=32, choices=Language.choices)
    checked_tests = models.ManyToManyField(CheckedTest)
    score = models.FloatField(default=0)
    creation_time = models.DateTimeField(auto_now_add=True)

    def get_status(self):
        statuses = [test.status for test in self.checked_tests.all()]
        not_ok = [status for status in statuses if status != Status.OK]
        if len(not_ok) != 0:
            return not_ok[0]
        return Status.OK

    def __str__(self):
        return f"Попытка по задаче {self.task.name}"
