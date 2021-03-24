import logging
import os

import logging.config

from .settings import LOGS_DIR

logger_service = logging.getLogger('service')


def configure_logging():
    logging.config.dictConfig(LOGGING)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'main_formatter': {
            'format': '(%(asctime)s; %(filename)s:%(lineno)d)'
                      '%(levelname)s:%(name)s: %(message)s ',
            'datefmt': "%Y-%m-%d %H:%M:%S",
            },
        },
    'handlers': {
        'console': {
            'level': 'INFO',
            # 'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            },
        'service_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'service.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 7,
            'formatter': 'main_formatter',
            },
        },
    'loggers': {
        'aiopg': {
            'handlers': ['console', 'service_file'],
            'level': "DEBUG",
            'propagate': False,
            },
        'service': {
            'handlers': ['console', 'service_file'],
            'level': "DEBUG",
            'propagate': False,
            },

        }
    }