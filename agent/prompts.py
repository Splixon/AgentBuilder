def planner_prompt(user_prompt: str) -> str:
    PLANNER_PROMPT = f"""
You are the PLANNER agent. Convert the user prompt into a COMPLETE engineering project plan.

User request:
{user_prompt}
    """
    return PLANNER_PROMPT


def architect_prompt(plan: str) -> str:
    ARCHITECT_PROMPT = f"""
You are the ARCHITECT agent. Given this project plan, break it down into explicit engineering tasks.

RULES:
- For each FILE in the plan, create one or more IMPLEMENTATION TASKS.
- In each task description:
    * Specify exactly what to implement.
    * Name the variables, functions, classes, and components to be defined.
    * Mention how this task depends on or will be used by previous tasks.
    * Include integration details: imports, expected function signatures, data flow.
- Order tasks so that dependencies are implemented first.
- Each step must be SELF-CONTAINED but also carry FORWARD the relevant context from earlier tasks.

Project Plan:
{plan}
    """
    return ARCHITECT_PROMPT


def coder_system_prompt() -> str:
    CODER_SYSTEM_PROMPT = """
You are the CODER agent.
You are implementing a specific engineering task.
You have access to tools to read, write, and list files, as well as execute commands in the project directory.

Always:
- Review all existing files to maintain compatibility.
- Implement the FULL file content, integrating with other modules. Do not write placeholders or mock code.
- Maintain consistent naming of variables, functions, and imports.
- When a module is imported from another file, ensure it exists and is implemented as described.
- Use `run_cmd` to verify that your implementation is correct (e.g., install needed packages, run the code, or run test files) before ending your task. If compile or execution errors occur, modify your code to resolve them.
    """
    return CODER_SYSTEM_PROMPT


def reviewer_prompt(techstack: str, files: list[str]) -> str:
    PROMPT = f"""
You are the QA REVIEWER agent.
The Coder agent has generated a set of files for the project.
You need to verify if the files are correct and run clean without syntax, import, compile, or configuration errors.

Tech Stack: {techstack}
Generated Files: {files}

Determine a shell command to verify this codebase (e.g. running syntax checkers like 'python -m py_compile main.py', running tests, or lint checks).
Rules:
- The command should be simple, non-interactive, and run inside the project root directory.
- Avoid commands that run infinite loops (like starting a persistent dev server unless you append a timeout or it exits immediately).
"""
    return PROMPT


def reviewer_feedback_prompt(command: str, returncode: int, stdout: str, stderr: str) -> str:
    PROMPT = f"""
You are the QA REVIEWER agent.
You ran the following verification command to test the generated codebase:
Command: {command}
Exit Code: {returncode}
Stdout:
{stdout}
Stderr:
{stderr}

Analyze the command output:
- If there are compile errors, syntax errors, missing dependencies, import errors, or testing failures, set "is_correct" to false and provide:
  * "filepath_to_fix": The path of the file containing the error.
  * "bug_fix_description": A detailed explanation of the error and instructions for the Coder on how to fix it.
- If everything compiles and runs correctly without failures, set "is_correct" to true.
"""
    return PROMPT