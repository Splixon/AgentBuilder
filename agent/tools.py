import pathlib
import subprocess
import contextvars
from typing import Tuple

from langchain_core.tools import tool
from agent.manager import RunManager

# Base directory that holds one sub-folder per run session.
PROJECTS_BASE = pathlib.Path.cwd() / "generated_projects"

# Kept for backwards-compat (server.py fallback, __main__ mode).
PROJECT_ROOT = PROJECTS_BASE / "default"

current_run_id = contextvars.ContextVar("current_run_id", default=None)


def get_project_root() -> pathlib.Path:
    """Return the project root for the current run, creating it if needed."""
    run_id = current_run_id.get()
    root = PROJECTS_BASE / run_id if run_id else PROJECT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_path_for_project(path: str) -> pathlib.Path:
    root = get_project_root()
    p = (root / path).resolve()
    if root.resolve() not in p.parents and root.resolve() != p.parent and root.resolve() != p:
        raise ValueError("Attempt to write outside project root")
    return p


@tool
def write_file(path: str, content: str) -> str:
    """Writes content to a file at the specified path within the project root."""
    p = safe_path_for_project(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)

    run_id = current_run_id.get()
    root = get_project_root()
    if run_id:
        rel_path = str(p.relative_to(root))
        RunManager.publish_event(run_id, "file_written", {"path": rel_path})

    return f"WROTE:{p}"


@tool
def read_file(path: str) -> str:
    """Reads content from a file at the specified path within the project root."""
    p = safe_path_for_project(path)
    if not p.exists():
        return ""
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


@tool
def get_current_directory() -> str:
    """Returns the current working directory."""
    return str(get_project_root())


@tool
def list_files(directory: str = ".") -> str:
    """Lists all files in the specified directory within the project root."""
    root = get_project_root()
    p = safe_path_for_project(directory)
    if not p.is_dir():
        return f"ERROR: {p} is not a directory"
    files = [str(f.relative_to(root)) for f in p.glob("**/*") if f.is_file()]
    return "\n".join(files) if files else "No files found."

@tool
def run_cmd(cmd: str, cwd: str = None, timeout: int = 120) -> Tuple[int, str, str]:
    """Runs a shell command in the specified directory and returns the result."""
    root = get_project_root()
    cwd_dir = safe_path_for_project(cwd) if cwd else root

    run_id = current_run_id.get()
    if run_id:
        RunManager.publish_event(run_id, "command_start", {"command": cmd, "cwd": cwd})

    try:
        res = subprocess.run(cmd, shell=True, cwd=str(cwd_dir), capture_output=True, text=True, timeout=timeout)
        returncode = res.returncode
        stdout = res.stdout
        stderr = res.stderr
    except subprocess.TimeoutExpired as e:
        returncode = -1
        stdout = e.stdout or ""
        stderr = f"Command timed out after {timeout} seconds. Output so far: {e.stderr or ''}"

    if run_id:
        RunManager.publish_event(run_id, "command_end", {
            "command": cmd,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr
        })

    return returncode, stdout, stderr


def init_project_root():
    root = get_project_root()
    root.mkdir(parents=True, exist_ok=True)
    return str(root)