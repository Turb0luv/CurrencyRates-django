import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')

app = Celery('base')

app.config_from_object('django.conf:settings', namespace='CELERY')

if app.conf['task_serializer'] == 'auth' and app.conf['accept_content'] == [
    'auth',
]:
    app.setup_security(serializer='pickle')

app.autodiscover_tasks()
