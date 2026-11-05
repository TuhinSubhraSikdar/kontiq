from django.contrib import admin

from .models import GeneratedContent, GeneratedContentVersion

admin.site.register(GeneratedContent)
admin.site.register(GeneratedContentVersion)
