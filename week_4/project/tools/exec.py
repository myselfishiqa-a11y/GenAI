import os
import shlex
import subprocess
from pathlib import PurePath
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
TIMEOUT_DEFAULT = 30
MAX_OUTPUT_CHARS = 8_000

# Known-safe: run immediately once the path check passes.
READ_ONLY_PREFIXES = ("grep", "find", "ls", "cat", "head", "tail", "wc","git log", "git diff", "git status", "git blame", "git show",
                      "pytest", "python -m pytest", "ruff", "flake8", "mypy")

# Known-destructive: always ask, even if they'd otherwise look harmless.
DESTRUCTIVE_PATTERNS = ("rm ", "mv ", ">", ">>", "git commit", "git push", "git checkout --","pip install", "npm install", "curl ", "sudo "
                        , "chmod ")

def looks_like_path(s):

    p=PurePath(s)

    return ((len(p.parts)>1) or ("/" in s) or ("\\" in s) or (s.startswith(("~",".","/"))) or (p.suffix and " " not in s))


def truncate(s) -> str:
    return s[:MAX_OUTPUT_CHARS]

def was_truncated(s) -> bool:
    return (s!=truncate(s))

def resolved_path(path: str,workspace_root: str) -> str|None:   

    full=os.path.abspath(os.path.join(workspace_root,path))
    root=os.path.abspath(workspace_root)

    if not ((full==root) or full.startswith(root+os.sep)):
        return None
    
    return full

def paths_within_sandbox(command: str, workspace_root: str) -> bool:

    tokens=shlex.split(command)

    for token in tokens:
        if (looks_like_path(token)):
            if resolved_path(token,workspace_root) is None:
                return False
    
    return True

def classify_command(command: str) -> str:
    stripped = command.strip()

    if not stripped:
        return "ask"

    if any(pattern in stripped for pattern in DESTRUCTIVE_PATTERNS):
        return "ask"

    if any(stripped.startswith(prefix) for prefix in READ_ONLY_PREFIXES):
        return "read_only"

    return "ask"

def run_command(command: str, cwd: str = WORKSPACE_ROOT, timeout: int = TIMEOUT_DEFAULT) -> dict:

    if (not paths_within_sandbox(command,cwd)):
        return {"error": "blocked: command references a path outside the workspace"}

    if (classify_command(command)=="read_only"):
        return execute_and_format(command,cwd,timeout)
    
    print("WARNING: the agent wants to run a command that may write, delete, or install:")
    print("    " + command)
    approved = input("Allow this command? [y/N]: ").strip().lower() == "y"

    if not approved:
        return {"error": "blocked: user did not approve this command"}

    return execute_and_format(command, cwd, timeout)

def execute_and_format(command: str,cwd: str,timeout: int = TIMEOUT_DEFAULT) -> dict:

    result=subprocess.run(command,cwd=cwd,shell=True,timeout=timeout,capture_output=True,text=True)

    return {"stdout": truncate(result.stdout),"stderr": truncate(result.stderr),"exit_code": result.returncode,
            "truncated": was_truncated(result.stdout)}
