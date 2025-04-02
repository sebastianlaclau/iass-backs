web: gunicorn core.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --timeout 120 --bind 0.0.0.0:$PORT --log-level info
