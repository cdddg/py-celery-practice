from datetime import timedelta

from decouple import config

from . import SCHEDULED_TASK_NAME_KEY, SCHEDULER_TASK_FLAG_KEY

# common configuration - applies to both celery worker and beat
broker_url = config('CELERY_BROKER_URL')
result_backend = config('CELERY_RESULT_BACKEND', default=None)
enable_utc = True
task_default_queue = config('CELERY_TASK_QUEUE')
broker_connection_retry_on_startup = (
    True  # retry broker connections on startup (relevant for celery 6.0+)
)

# worker-specific configuration
worker_redirect_stdouts = False
worker_cancel_long_running_tasks_on_connection_loss = True
worker_concurrency = config('CELERY_WORKER_CONCURRENCY', cast=int)

# beat-specific configuration - scheduling of periodic tasks
beat_schedule = {
    'test-nested-job': {
        'task': f'{__package__}.task.first_task',
        'schedule': timedelta(seconds=10),
        'options': {SCHEDULER_TASK_FLAG_KEY: True, SCHEDULED_TASK_NAME_KEY: 'test-nested-job'},
    },
}
beat_schedule_filename = config('CELERY_BEAT_SCHEDULE_FILENAME')
