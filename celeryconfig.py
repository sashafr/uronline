# config file for Celery Daemon

DJANGO_SETTINGS_MODULE='uronline.settings'

# default RabbitMQ broker
BROKER_URL = 'amqp://'

# default RabbitMQ backend
CELERY_RESULT_BACKEND = 'amqp://'