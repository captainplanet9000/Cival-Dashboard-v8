# =============================================================================
# RAILWAY PROCFILE - AUTONOMOUS TRADING SYSTEM
# Complete system deployment with single FastAPI application
# =============================================================================

# Primary web process - FastAPI application with all services
web: python main_consolidated.py

# Alternative process configurations (commented out for single-service deployment)
# web: gunicorn main_consolidated:app --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker --timeout 300 --preload --max-requests 1000 --max-requests-jitter 50

# Development process (for staging environment)
# dev: uvicorn main_consolidated:app --host 0.0.0.0 --port $PORT --reload --log-level debug

# Worker processes (if needed for background tasks)
# worker: python -m celery worker -A main_consolidated.celery --loglevel=info --concurrency=2
# beat: python -m celery beat -A main_consolidated.celery --loglevel=info

# Database migration process (run before deployment)
# migrate: python scripts/migrate_database.py

# Backup process (scheduled via cron in railway.json)
# backup: python scripts/backup_database.py