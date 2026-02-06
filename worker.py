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
    
    redis_conn = Redis.from_url(settings.redis_url)
    
    with Connection(redis_conn):
        worker = Worker(['default'], connection=redis_conn)
        print("✅ Worker started. Listening for jobs...")
        worker.work()


if __name__ == "__main__":
    main()
