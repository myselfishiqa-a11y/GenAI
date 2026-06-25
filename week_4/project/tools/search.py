import ast
import os
import re
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_GREP_RESULTS = 50
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def resolved_path(path: str,workspace_root: str) -> str|None:   

    full=os.path.abspath(os.path.join(workspace_root,path))
    root=os.path.abspath(workspace_root)

    if not ((full==root) or full.startswith(root+os.sep)):
        return None
    
    return full


def grep(pattern: str,path: str = ".",case_sensitive: bool = False,max_results: int = MAX_GREP_RESULTS) -> dict:
    
    def is_binary(filepath: str) -> bool:
        try:
           with open(filepath, "rb") as f:
                return b"\x00" in f.read(1024)  
        except (OSError, PermissionError):
            return True
    
    full_path=resolved_path(path,WORKSPACE_ROOT)
    if (full_path is None):
        return {"error":"blocked: Path escapes workspace"}
    
    result={}
    result["matches"]=[]
    result["truncated"]=False
    result["total_matches"]=0
    flag=0 if case_sensitive else re.IGNORECASE

    for dirpath,dirnames,filenames in os.walk(full_path):
        dirnames[ : ]=[d for d in dirnames if d not in EXCLUDE_DIRS]
        
        for filename in filenames:
            filepath=os.path.join(dirpath,filename)
            if not is_binary(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no,line in enumerate(f,start=1):
                            if (re.search(pattern,line,flag)):
                                result["total_matches"] += 1
                                if result["total_matches"] <= max_results:
                                    result["matches"].append({"file": filepath, "line": line_no, "text": line})
                                else:
                                    result["truncated"] = True
                except Exception:
                    pass
    
    return result


def list_definitions(path: str) -> dict:

    full_path=resolved_path(path,WORKSPACE_ROOT)
    if (full_path is None):
        return {"error":"blocked: Path escapes workspace"}
    
    try:
        source=open(full_path).read()
    except FileNotFoundError:
        return {"error":"file not found"}
    
    try:
        tree=ast.parse(source)
    except SyntaxError as e:
        return {"error":f"syntax error: {e}"}
    
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent=node

    definitions=[]

    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            parent=getattr(node,"_parent",None)

            if isinstance(node,ast.ClassDef):
                kind="class"
            elif isinstance(node,ast.AsyncFunctionDef):
                kind="async function" if not isinstance(parent,ast.ClassDef) else "method"
            else: #isinstance(node,ast.FunctionDef)
                kind="function" if not isinstance(parent,ast.ClassDef) else "method"

            definitions.append({"kind":kind,"name":node.name,"line":node.lineno,"end_line":node.end_lineno})

    definitions.sort(key=lambda d:d["line"])

    return {"definitions":definitions}