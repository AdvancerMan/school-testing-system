from django.contrib import admin
from . import models

admin.site.register(models.MyUser)
admin.site.register(models.Class)
admin.site.register(models.Test)
admin.site.register(models.CheckedTest)
admin.site.register(models.Testset)
admin.site.register(models.Task)
admin.site.register(models.Attempt)
