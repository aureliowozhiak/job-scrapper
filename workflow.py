import threading
import time
import inspect
from enum import Enum
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

class JobStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"

class WorkflowContext:
    """Context passed execution steps effectively."""
    def __init__(self):
        self.stop_requested = False
        self.data = {}

class Pulse:
    """
    Central Orchestrator for Job Scrapper Pipelines.
    Manages dependency execution, state tracking, and waiting mechanisms.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._status: Dict[str, Dict[str, Any]] = {
            "scraper": self._init_state(),
            "loader": self._init_state(),
            "validator": self._init_state(),
            "pipeline": self._init_state() # Overall pipeline state
        }
        self._active_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def _init_state(self) -> Dict[str, Any]:
        return {
            "status": JobStatus.IDLE.value,
            "message": "Ready",
            "last_run": None,
            "running": False,  # Compatibility with existing UI
            "success": None,   # Compatibility with existing UI
            "duration": 0
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns the full status copy for the API."""
        with self._lock:
            # Deep copy to prevent race conditions during read
            return {k: v.copy() for k, v in self._status.items()}

    def _update_state(self, component: str, status: JobStatus, message: str = ""):
        with self._lock:
            if component in self._status:
                s = self._status[component]
                s["status"] = status.value
                s["message"] = message
                s["running"] = status == JobStatus.RUNNING
                
                if status == JobStatus.SUCCESS:
                    s["success"] = True
                    s["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                elif status == JobStatus.ERROR:
                    s["success"] = False
                elif status == JobStatus.RUNNING:
                    # Reset success on new run
                    s["success"] = None 

    def is_busy(self) -> bool:
        """Check if any operation is currently running."""
        with self._lock:
            return any(s["running"] for s in self._status.values())

    def run_job(self, name: str, func: Callable, args=(), callback=None):
        """Run a single job safely."""
        if self.is_busy():
            raise RuntimeError("System is busy with another operation")

        def wrapper():
            start_time = time.time()
            self._update_state(name, JobStatus.RUNNING, f"Starting {name}...")
            self._update_state("pipeline", JobStatus.RUNNING, f"Executing single task: {name}")
            
            try:
                func(*args)
                duration = time.time() - start_time
                self._update_state(name, JobStatus.SUCCESS, f"Completed in {duration:.2f}s")
                self._update_state("pipeline", JobStatus.SUCCESS, "Single task completed")
                if callback: callback(True)
            except Exception as e:
                logger.error(f"Job {name} failed: {e}", exc_info=True)
                self._update_state(name, JobStatus.ERROR, str(e))
                self._update_state("pipeline", JobStatus.ERROR, f"Task failed: {e}")
                if callback: callback(False)

        self._active_thread = threading.Thread(target=wrapper, name=f"Job-{name}")
        self._active_thread.start()

    def run_pipeline(self, steps: List[tuple[str, Callable]]):
        """
        Run a sequence of dependent steps.
        Format: [('scraper', run_scraper_func), ('loader', run_loader_func)]
        Execution stops if any step fails.
        """
        if self.is_busy():
            raise RuntimeError("System is busy with another pipeline")

        def pipeline_wrapper():
            pipeline_start = time.time()
            self._update_state("pipeline", JobStatus.RUNNING, "Starting pipeline...")
            
            success = True
            failed_at = None
            
            for name, func in steps:
                if self._stop_event.is_set():
                    self._update_state("pipeline", JobStatus.SKIPPED, "Pipeline stopped by user")
                    return

                # Update step status
                self._update_state(name, JobStatus.RUNNING, "Starting dependency...")
                self._update_state("pipeline", JobStatus.RUNNING, f"Running step: {name}")
                
                step_start = time.time()
                try:
                    logger.info(f"Pipeline triggering step: {name}")
                    func()
                    
                    step_duration = time.time() - step_start
                    self._update_state(name, JobStatus.SUCCESS, f"Completed in {step_duration:.2f}s")
                    
                except Exception as e:
                    logger.error(f"Pipeline failed at step {name}: {e}", exc_info=True)
                    self._update_state(name, JobStatus.ERROR, str(e))
                    failed_at = name
                    success = False
                    break
            
            total_duration = time.time() - pipeline_start
            
            with self._lock:
                if success:
                    self._status["pipeline"]["status"] = JobStatus.SUCCESS.value
                    self._status["pipeline"]["message"] = f"Pipeline finished successfully in {total_duration:.2f}s"
                    self._status["pipeline"]["success"] = True
                    self._status["pipeline"]["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    self._status["pipeline"]["status"] = JobStatus.ERROR.value
                    self._status["pipeline"]["message"] = f"Pipeline failed at {failed_at}"
                    self._status["pipeline"]["success"] = False
                    
                self._status["pipeline"]["running"] = False

        self._active_thread = threading.Thread(target=pipeline_wrapper, name="PipelineWorker")
        self._active_thread.start()

    def wait(self, timeout=None) -> bool:
        """Wait for the current operation to complete."""
        if self._active_thread and self._active_thread.is_alive():
            self._active_thread.join(timeout)
            return not self._active_thread.is_alive()
        return True

# Singleton instance
pulse = Pulse()
