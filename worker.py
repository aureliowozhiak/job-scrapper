"""RQ Worker entry point."""
import sys
from pathlib import Path
from redis import Redis
from rq import Worker, Queue, Connection

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import settings


def main():
    """Start RQ worker."""
    print(f"🔧 Starting RQ Worker")
    print(f"🔴 Redis: {settings.redis_url}")
    print(f"⏱️  Job timeout: {settings.job_timeout}s")
    
    redis_conn = Redis.from_url(settings.redis_url)
    
    with Connection(redis_conn):
        # Process pipeline queue first (higher priority), then default queue
        # This ensures pipeline tasks execute sequentially within each group
        worker = Worker(['pipeline', 'default'], connection=redis_conn, job_monitoring_interval=30)
        print("✅ Worker started. Listening for jobs on queues: pipeline (priority), default")
        worker.work(with_scheduler=False, logging_level='INFO')


if __name__ == "__main__":
    main()
