from arq.connections import RedisSettings

from app.core.config import get_settings
from app.worker import tasks


class WorkerSettings:
    functions = [tasks.match_workers_for_job]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    job_timeout = 120
