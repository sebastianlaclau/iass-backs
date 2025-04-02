import logging
import multiprocessing
import os

# Configuración de workers
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "custom": {
            "format": "%(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "custom",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "app.api.endpoints.webhook": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "gunicorn": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
