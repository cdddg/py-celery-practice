from asgi_correlation_id.extensions.celery import (
    load_celery_current_and_parent_ids,
    load_correlation_ids,
)
from celery import Celery

from project.celerylogging import setup_celery_logging

app = Celery()
app.config_from_object(f'{__package__}.celeryconfig')
app.autodiscover_tasks([__package__], related_name='task')

load_correlation_ids()
load_celery_current_and_parent_ids(use_internal_celery_task_id=True)
setup_celery_logging()

if __name__ == '__main__':
    app.start()
