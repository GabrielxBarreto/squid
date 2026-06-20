import os
from celery import Celery

# Define o módulo de configurações padrão do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Lê as configurações do Django com o prefixo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carrega tarefas de todos os apps registrados
app.autodiscover_tasks()
