"""Kontiq Django and Celery configuration package."""

from .celery import app as celery_app

__all__ = ("celery_app",)
