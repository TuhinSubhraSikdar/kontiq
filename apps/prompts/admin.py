from django.contrib import admin

from .models import PromptTemplate, PromptVersion

admin.site.register(PromptTemplate)
admin.site.register(PromptVersion)
