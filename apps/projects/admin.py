from django.contrib import admin

from .models import Project, ProjectLink, ProjectReference

admin.site.register(Project)
admin.site.register(ProjectLink)
admin.site.register(ProjectReference)
