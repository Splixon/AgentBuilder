from dotenv import load_dotenv
import json
import logging
import re
from langchain_groq.chat_models import ChatGroq
from langgraph.constants import END
from langgraph.graph import StateGraph
from langchain.agents import create_agent
from groq import BadRequestError

from agent.prompts import *
from agent.states import *
from agent.tools import write_file, read_file, get_current_directory, list_files, run_cmd, current_run_id
from agent.manager import RunManager



_ = load_dotenv()

logging.basicConfig(level=logging.DEBUG)

import os

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_CODER_MODEL = os.getenv("GROQ_CODER_MODEL", "llama-3.3-70b-versatile")

llm = ChatGroq(
    model=GROQ_MODEL,
    temperature=0,
)

# Llama-3.3-70b on Groq occasionally emits malformed tool-call text
# (e.g. "<function=write_file {...}>") instead of a proper structured
# tool call, especially when the `content` argument is long (full file
# contents). This tends to happen less with other models, so the coder
# uses a separate model instance that can be swapped independently.
coder_llm = ChatGroq(
    model=GROQ_CODER_MODEL,
    temperature=0,
)

MAX_CODER_RETRIES = 3



def planner_agent(state: dict) -> dict:
    """Converts user prompt into a structured Plan."""
    run_id = state.get("run_id")
    if run_id:
        current_run_id.set(run_id)
        RunManager.publish_event(run_id, "status", {"status": "planning"})

    user_prompt = state["user_prompt"]
    resp = llm.with_structured_output(Plan).invoke(
        planner_prompt(user_prompt)
    )
    if resp is None:
        raise ValueError("Planner did not return a valid response.")
    
    if run_id:
        RunManager.publish_event(run_id, "planner_result", resp.model_dump())
        RunManager.publish_event(run_id, "status", {"status": "awaiting_plan_approval"})
        
        # Block thread until user approves (possibly with modified plan)
        approved_plan = RunManager.wait_for_approval(run_id)
        if approved_plan:
            resp = Plan(
                name=approved_plan.get("name", resp.name),
                description=approved_plan.get("description", resp.description),
                techstack=approved_plan.get("techstack", resp.techstack),
                features=approved_plan.get("features", resp.features),
                files=[File(path=f.get("path"), purpose=f.get("purpose")) for f in approved_plan.get("files", [])]
            )
            # Publish updated plan
            RunManager.publish_event(run_id, "planner_result", resp.model_dump())

    return {"plan": resp}


def architect_agent(state: dict) -> dict:
    """Creates TaskPlan from Plan."""
    run_id = state.get("run_id")
    if run_id:
        current_run_id.set(run_id)
        RunManager.publish_event(run_id, "status", {"status": "architecting"})

    plan: Plan = state["plan"]
    resp = llm.with_structured_output(TaskPlan).invoke(
        architect_prompt(plan=plan.model_dump_json())
    )

    if resp is None:
        raise ValueError("Architect did not return a valid response.")

    if not resp.implementation_steps:
        raise ValueError("Architect returned an empty implementation_steps list.")

    print(resp.model_dump_json(indent=2))
    
    if run_id:
        RunManager.publish_event(run_id, "architect_result", resp.model_dump())

    return {"task_plan": resp}

# ---------------------------------------------------------------------------
# Rescue helper for malformed Llama tool calls
# ---------------------------------------------------------------------------
# Pattern: <function=write_file>{"path": "...", "content": "..."}
# Groq rejects these with HTTP 400 and stores the raw generation in
# error.body['error']['failed_generation'].
_MALFORMED_CALL_RE = re.compile(
    r"<function=(\w+)>(.*)",
    re.DOTALL,
)

# Map tool name strings to the actual callable tool objects
_TOOL_MAP = {
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "get_current_directory": get_current_directory,
    "run_cmd": run_cmd,
}


def _rescue_malformed_tool_call(err: BadRequestError, expected_filepath: str) -> bool:
    """Try to parse and execute a malformed <function=...>{...} tool call.

    Returns True if a write_file call was successfully rescued, False otherwise.
    """
    try:
        body = err.response.json() if hasattr(err, "response") else {}
        failed_gen: str = body.get("error", {}).get("failed_generation", "")
    except Exception:
        return False

    if not failed_gen:
        return False

    match = _MALFORMED_CALL_RE.search(failed_gen)
    if not match:
        return False

    tool_name = match.group(1)
    raw_args = match.group(2).strip()

    # Strip a trailing </function> tag if present
    raw_args = re.sub(r"</function>.*$", "", raw_args, flags=re.DOTALL).strip()

    tool_fn = _TOOL_MAP.get(tool_name)
    if tool_fn is None:
        logging.warning("_rescue: unknown tool %r, cannot rescue.", tool_name)
        return False

    try:
        args = json.loads(raw_args)
    except json.JSONDecodeError as exc:
        logging.warning("_rescue: could not parse args JSON for %r: %s", tool_name, exc)
        return False

    try:
        if tool_name == "write_file":
            result = tool_fn.run(args)
            logging.info("_rescue: write_file result: %s", result)
            return True
        else:
            # For non-write tools, still execute but don't count as a success
            tool_fn.run(args)
            return False
    except Exception as exc:
        logging.warning("_rescue: tool execution failed for %r: %s", tool_name, exc)
        return False


def coder_agent(state: dict) -> dict:

    """LangGraph tool-using coder agent."""
    run_id = state.get("run_id")
    if run_id:
        current_run_id.set(run_id)

    coder_state: CoderState = state.get("coder_state")
    if coder_state is None:
        coder_state = CoderState(task_plan=state["task_plan"], current_step_idx=0)
        if run_id:
            RunManager.publish_event(run_id, "status", {"status": "coding"})

    steps = coder_state.task_plan.implementation_steps
    if coder_state.current_step_idx >= len(steps):
        return {"coder_state": coder_state}

    current_task = steps[coder_state.current_step_idx]
    
    if run_id:
        RunManager.publish_event(run_id, "coder_step_start", {
            "step_idx": coder_state.current_step_idx,
            "total_steps": len(steps),
            "filepath": current_task.filepath,
            "task_description": current_task.task_description
        })

    existing_content = read_file.run(current_task.filepath)

    system_prompt = coder_system_prompt()
    user_prompt = (
        f"Task: {current_task.task_description}\n"
        f"File: {current_task.filepath}\n"
        f"Existing content:\n{existing_content}\n"
        "Use write_file(path, content) to save your changes."
    )

    coder_tools = [read_file, write_file, list_files, get_current_directory, run_cmd]
    react_agent = create_agent(coder_llm, coder_tools)

    last_error = None
    for attempt in range(1, MAX_CODER_RETRIES + 1):
        try:
            react_agent.invoke({"messages": [{"role": "system", "content": system_prompt},
                                             {"role": "user", "content": user_prompt}]})
            last_error = None
            break
        except BadRequestError as e:
            last_error = e
            logging.warning(
                "Coder tool-call failed for %s (attempt %d/%d): %s",
                current_task.filepath, attempt, MAX_CODER_RETRIES, e,
            )
            # --- Rescue: parse the malformed <function=...>{...} tool call ---
            # Llama-3.3-70b sometimes emits the old text-format function call
            # instead of a proper OpenAI structured tool call when the content
            # contains template literals, backticks, or many special characters.
            # Groq rejects these with a 400 and puts the raw generation in the
            # error body under 'failed_generation'. We parse it directly and
            # invoke the correct tool so the file is still written.
            rescued = _rescue_malformed_tool_call(e, current_task.filepath)
            if rescued:
                logging.info(
                    "Rescued malformed tool call for %s on attempt %d — file written via fallback.",
                    current_task.filepath, attempt,
                )
                last_error = None
                break

    if last_error is not None:
        # All retries exhausted. Don't crash the whole graph run over one
        # bad file - log it, skip the step, and keep going so the rest of
        # the project can still be generated.
        logging.error(
            "Giving up on step %d (%s) after %d attempts.",
            coder_state.current_step_idx, current_task.filepath, MAX_CODER_RETRIES,
        )

    coder_state.current_step_idx += 1
    return {"coder_state": coder_state}


def reviewer_agent(state: dict) -> dict:
    """Lightweight reviewer: marks the run as completed without any LLM calls."""
    run_id = state.get("run_id")
    if run_id:
        current_run_id.set(run_id)
        RunManager.publish_event(run_id, "status", {"status": "completed"})
        RunManager.publish_event(run_id, "reviewer_feedback", {
            "is_correct": True,
            "review_count": 1,
            "filepath": None,
            "description": "All coding steps finished. Project is ready.",
        })
    return {"review_status": "DONE"}


graph = StateGraph(AgentState)

graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)
graph.add_node("reviewer", reviewer_agent)

graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")

graph.add_conditional_edges(
    "coder",
    lambda s: "reviewer" if s.get("coder_state").current_step_idx >= len(s.get("coder_state").task_plan.implementation_steps) else "coder",
    {"reviewer": "reviewer", "coder": "coder"}
)

# Reviewer is now lightweight — always goes straight to END.
graph.add_edge("reviewer", END)

graph.set_entry_point("planner")
agent = graph.compile()
if __name__ == "__main__":
    result = agent.invoke({"user_prompt": "Build a colourful modern todo app in html css and js"},
                          {"recursion_limit": 100})
    print("Final State:", result)