from django.contrib import admin

# Register your models here.

from dashboard import models

@admin.register(models.Streaming)
class StreamingAdmin(admin.ModelAdmin):
    list_display = 'id','name'