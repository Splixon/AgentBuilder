import asyncio
import logging
import uuid
import sys
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import json

from agent.graph import agent
from agent.tools import PROJECTS_BASE, current_run_id, safe_path_for_project, get_project_root, PROJECT_ROOT
from agent.manager import RunManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

app = FastAPI(title="AgentCrafter API")

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom logging handler to stream python logger outputs to SSE clients
class SSELogHandler(logging.Handler):
    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id
        self.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        
    def emit(self, record):
        try:
            log_entry = self.format(record)
            # Filter out noisy or loop logs if any
            if "HTTP" in log_entry or "GET" in log_entry or "POST" in log_entry:
                return
            RunManager.publish_event(self.run_id, "log", {"message": log_entry})
        except Exception:
            self.handleError(record)

def run_agent_workflow(run_id: str, prompt: str):
    """Executes the LangGraph agent in the background thread."""
    current_run_id.set(run_id)
    RunManager.create_run(run_id, prompt)
    
    # Attach log capturing for the duration of the run
    root_logger = logging.getLogger()
    sse_handler = SSELogHandler(run_id)
    root_logger.addHandler(sse_handler)
    
    try:
        logging.info(f"Starting agent run for prompt: {prompt}")
        agent.invoke({"user_prompt": prompt, "run_id": run_id})
        logging.info("Agent run completed successfully.")
    except Exception as e:
        logging.exception("Error executing agent workflow:")
        RunManager.publish_event(run_id, "status", {"status": "failed"})
    finally:
        root_logger.removeHandler(sse_handler)

@app.post("/api/run")
def start_run(payload: dict, background_tasks: BackgroundTasks):
    prompt = payload.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
        
    run_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(run_agent_workflow, run_id, prompt)
    return {"run_id": run_id}

@app.post("/api/run/{run_id}/approve")
def approve_run(run_id: str, payload: dict):
    plan = payload.get("plan")
    RunManager.approve_run(run_id, plan)
    return {"status": "approved"}

@app.get("/api/stream/{run_id}")
async def stream_run(run_id: str):
    queue = await RunManager.subscribe(run_id)
    
    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
                queue.task_done()
        except asyncio.CancelledError:
            RunManager.unsubscribe(run_id, queue)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/project/files")
def get_project_files(run_id: str = Query(default=None)):
    """List all generated files for a specific run session."""
    if run_id:
        root = PROJECTS_BASE / run_id
    else:
        # Fallback: list all runs as top-level folders
        if not PROJECTS_BASE.exists():
            return []
        all_files = []
        for run_dir in sorted(PROJECTS_BASE.iterdir()):
            if run_dir.is_dir():
                for root_dir, dirs, files in os.walk(run_dir):
                    if any(part.startswith(".") or part in ("__pycache__", "node_modules") for part in root_dir.split(os.sep)):
                        continue
                    for file in files:
                        full_path = os.path.join(root_dir, file)
                        rel = os.path.relpath(full_path, PROJECTS_BASE)
                        all_files.append(rel.replace(os.sep, "/"))
        return sorted(all_files)

    if not root.exists():
        return []

    file_list = []
    for root_dir, dirs, files in os.walk(root):
        if any(part.startswith(".") or part in ("__pycache__", "node_modules") for part in root_dir.split(os.sep)):
            continue
        for file in files:
            full_path = os.path.join(root_dir, file)
            rel_path = os.path.relpath(full_path, root)
            file_list.append(rel_path.replace(os.sep, "/"))

    return sorted(file_list)


@app.get("/api/project/file/{path:path}")
def get_file_content(path: str, run_id: str = Query(default=None)):
    """Read a specific file from the run's project directory."""
    try:
        if run_id:
            root = PROJECTS_BASE / run_id
            p = (root / path).resolve()
            if root.resolve() not in p.parents and root.resolve() != p.parent and root.resolve() != p:
                raise ValueError("Invalid path")
        else:
            root = PROJECTS_BASE
            p = (root / path).resolve()
            if root.resolve() not in p.parents and root.resolve() != p.parent and root.resolve() != p:
                raise ValueError("Invalid path")
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return {"content": f.read()}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/project/command")
async def run_project_command(payload: dict):
    command = payload.get("command")
    run_id = payload.get("run_id")
    if not command:
        raise HTTPException(status_code=400, detail="Command is required")
        
    async def cmd_generator():
        process = None
        try:
            # Run command asynchronously in generated project directory
            cwd = PROJECTS_BASE / run_id if run_id else PROJECT_ROOT
            if not cwd.exists():
                cwd = PROJECTS_BASE
                cwd.mkdir(parents=True, exist_ok=True)
                
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            q = asyncio.Queue()
            
            async def enqueue_stream(stream, prefix):
                try:
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        await q.put(f"{prefix}: {line.decode('utf-8', errors='replace').rstrip()}")
                except Exception as e:
                    await q.put(f"error: Stream reading failed for {prefix}: {str(e)}")
                    
            stdout_task = asyncio.create_task(enqueue_stream(process.stdout, "stdout"))
            stderr_task = asyncio.create_task(enqueue_stream(process.stderr, "stderr"))
            
            async def monitor_tasks():
                await asyncio.gather(stdout_task, stderr_task)
                await process.wait()
                await q.put(None)
                
            monitor_task = asyncio.create_task(monitor_tasks())
            
            while True:
                item = await q.get()
                if item is None:
                    break
                yield f"data: {item}\n\n"
                q.task_done()
                
            await monitor_task
            
        except Exception as e:
            yield f"data: error: {str(e)}\n\n"
        finally:
            if process and process.returncode is None:
                try:
                    if sys.platform == "win32":
                        import subprocess
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    else:
                        process.terminate()
                    await process.wait()
                except Exception:
                    pass
                    
    return StreamingResponse(cmd_generator(), media_type="text/event-stream")

@app.get("/api/history")
def get_history():
    return RunManager.list_runs()

@app.delete("/api/run/{run_id}")
def delete_run(run_id: str):
    try:
        RunManager.delete_run(run_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files frontend
@app.get("/")
def get_index():
    # If frontend index doesn't exist, return a simple text or create frontend folder
    if not os.path.exists("frontend/index.html"):
        os.makedirs("frontend", exist_ok=True)
    return FileResponse("frontend/index.html")

app.mount("/static", StaticFiles(directory="frontend"), name="static")
