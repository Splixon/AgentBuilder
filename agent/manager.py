import asyncio
import time
import threading
from typing import Dict, List, Any, Optional
import json
import pathlib

PROJECTS_BASE = pathlib.Path.cwd() / "generated_projects"
SESSIONS_FILE = PROJECTS_BASE / "sessions.json"

class RunManager:
    _lock = threading.Lock()
    # Maps run_id -> list of event dicts
    _run_histories: Dict[str, List[Dict[str, Any]]] = {}
    # Maps run_id -> list of asyncio.Queue
    _subscribers: Dict[str, List[asyncio.Queue]] = {}
    # Maps run_id -> run metadata (status, prompt, name, techstack, etc.)
    _run_metadata: Dict[str, Dict[str, Any]] = {}
    # Threading events to pause agents for approval
    _approval_events: Dict[str, threading.Event] = {}
    # Stores the edited plan data approved by user
    _approved_plans: Dict[str, Any] = {}
    # Event loop to communicate thread-safely
    _loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def _save_sessions(cls):
        with cls._lock:
            try:
                PROJECTS_BASE.mkdir(parents=True, exist_ok=True)
                data = {
                    "metadata": cls._run_metadata,
                    "histories": cls._run_histories,
                    "approved_plans": cls._approved_plans
                }
                # Write atomically using a temporary file
                temp_file = SESSIONS_FILE.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                temp_file.replace(SESSIONS_FILE)
            except Exception as e:
                print(f"Error saving sessions: {e}")

    @classmethod
    def _load_sessions(cls):
        with cls._lock:
            try:
                if SESSIONS_FILE.exists():
                    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    cls._run_metadata = data.get("metadata", {})
                    cls._run_histories = data.get("histories", {})
                    cls._approved_plans = data.get("approved_plans", {})
                    for run_id in cls._run_metadata:
                        if run_id not in cls._approval_events:
                            cls._approval_events[run_id] = threading.Event()
            except Exception as e:
                print(f"Error loading sessions: {e}")

    @classmethod
    def create_run(cls, run_id: str, prompt: str):
        cls._run_histories[run_id] = []
        cls._subscribers[run_id] = []
        cls._approval_events[run_id] = threading.Event()
        cls._approved_plans[run_id] = None
        cls._run_metadata[run_id] = {
            "run_id": run_id,
            "prompt": prompt,
            "status": "idle",
            "start_time": time.time(),
            "name": "",
            "techstack": "",
            "features": []
        }
        cls.publish_event(run_id, "status", {"status": "started"})

    @classmethod
    def publish_event(cls, run_id: str, event_type: str, data: Any):
        if not run_id:
            return
            
        event = {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        
        # Update metadata if needed
        if run_id in cls._run_metadata:
            if event_type == "status":
                cls._run_metadata[run_id]["status"] = data.get("status")
            elif event_type == "planner_result":
                cls._run_metadata[run_id]["name"] = data.get("name", "")
                cls._run_metadata[run_id]["techstack"] = data.get("techstack", "")
                cls._run_metadata[run_id]["features"] = data.get("features", [])

        # Store in history
        if run_id not in cls._run_histories:
            cls._run_histories[run_id] = []
        cls._run_histories[run_id].append(event)

        # Distribute to subscribers thread-safely
        if run_id in cls._subscribers:
            for queue in cls._subscribers[run_id]:
                if cls._loop and cls._loop.is_running():
                    cls._loop.call_soon_threadsafe(queue.put_nowait, event)
                else:
                    queue.put_nowait(event)

        cls._save_sessions()

    @classmethod
    async def subscribe(cls, run_id: str) -> asyncio.Queue:
        cls._loop = asyncio.get_running_loop()
        queue = asyncio.Queue()
        if run_id not in cls._subscribers:
            cls._subscribers[run_id] = []
        
        # Populate with existing history first
        if run_id in cls._run_histories:
            for event in cls._run_histories[run_id]:
                queue.put_nowait(event)
                
        cls._subscribers[run_id].append(queue)
        return queue

    @classmethod
    def unsubscribe(cls, run_id: str, queue: asyncio.Queue):
        if run_id in cls._subscribers:
            if queue in cls._subscribers[run_id]:
                cls._subscribers[run_id].remove(queue)

    @classmethod
    def get_run_metadata(cls, run_id: str) -> Dict[str, Any]:
        return cls._run_metadata.get(run_id, {})

    @classmethod
    def list_runs(cls) -> List[Dict[str, Any]]:
        return list(cls._run_metadata.values())

    @classmethod
    def wait_for_approval(cls, run_id: str) -> Any:
        if run_id not in cls._approval_events:
            return None
        # Block active thread
        cls._approval_events[run_id].wait()
        return cls._approved_plans.get(run_id)

    @classmethod
    def approve_run(cls, run_id: str, approved_plan: Any):
        if run_id in cls._approval_events:
            cls._approved_plans[run_id] = approved_plan
            cls._approval_events[run_id].set()
            cls._save_sessions()

    @classmethod
    def delete_run(cls, run_id: str):
        with cls._lock:
            if run_id in cls._run_metadata:
                del cls._run_metadata[run_id]
            if run_id in cls._run_histories:
                del cls._run_histories[run_id]
            if run_id in cls._approved_plans:
                del cls._approved_plans[run_id]
            if run_id in cls._approval_events:
                cls._approval_events[run_id].set()
                del cls._approval_events[run_id]

            # Clean up generated files folder for this run
            run_dir = PROJECTS_BASE / run_id
            if run_dir.exists() and run_dir.is_dir() and run_id != "default":
                import shutil
                try:
                    shutil.rmtree(run_dir)
                except Exception as e:
                    print(f"Error deleting directory {run_dir}: {e}")

        cls._save_sessions()

# Load existing sessions on startup
RunManager._load_sessions()

