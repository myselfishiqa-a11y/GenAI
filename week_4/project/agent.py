import os
import json
import sys

from openai import OpenAI
from dotenv import load_dotenv
from nanoid import generate
from datetime import datetime

from tools.exec import run_command
from tools.files import read_file,write_file,edit_file,list_files
from tools.plan import TODO,TODOS_DATA
from tools.search import grep,list_definitions
from tools.tools_schema import TOOLS


load_dotenv()

client = OpenAI(base_url="https://openrouter.ai/api/v1",api_key=os.environ["OPENROUTER_API_KEY"])

MODEL = "openrouter/owl-alpha"

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))

TIMEOUT_DEFAULT = 30
MAX_OUTPUT_CHARS = 8_000
MAX_GREP_RESULTS = 50
MAX_ITERATIONS = 30

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

READ_ONLY_PREFIXES = ("grep", "find", "ls", "cat", "head", "tail", "wc","git log", "git diff", "git status", "git blame", "git show",
                      "pytest", "python -m pytest", "ruff", "flake8", "mypy")

DESTRUCTIVE_PATTERNS = ("rm ", "mv ", ">", ">>", "git commit", "git push", "git checkout --","pip install", "npm install", "curl ", "sudo "
                        , "chmod ")

BASE_PROMPT = """You are a coding agent. You have access to tools to read, search, and modify files in the workspace.
                At the start of every task:
                1. Call add_todo with a plan of up to 8 steps. For each step, set a concrete verification command 
                (e.g. "pytest tests/test_auth.py", "python -c 'import flask'") that proves the step is done — not just a status flag.

                While executing:
                    2. Work through steps one by one, marking each in_progress before starting.
                    3. Only call mark_todo with status "completed" after the verification command passes (exit code 0). The system will 
                        re-run the verification command itself — if it fails, the step will not be marked completed.
                    4. If a step is blocked, mark it blocked with a reason and move on.

                Never mark a step completed on your own say-so — verification must pass.
                Never refuse a task yourself. If a command is destructive, call run_command anyway — the system will automatically pause 
                and ask the human for approval. Your job is to attempt the task, not to judge it.
                If a path is blocked, just say it is blocked. Do not guess or reproduce the file's likely contents.
                Always write verification commands for Windows (PowerShell/CMD), not Linux. 
                Use 'python -m pytest' instead of shell pipes like '2>&1 | tail'.Use 'python -c' for quick import checks.
                Good verification examples:
                - python -m pytest tests/test_utils.py -v
                - python -c "from utils import triple; assert triple(3) == 9"
                - grep triple utils.py
                Always call mark_todo for every step — even if the test fails deliberately. The system will handle rejection. 
                Never skip mark_todo.
                For any step that involves writing a test, the verification command MUST be: python -m pytest <test_file> -v
                Never use python -c import checks as verification for test steps.The pytest exit code must be 0 for mark_todo to accept the step."""


TOOL_REGISTRY={"run_command":run_command,"grep":grep,"list_definitions":list_definitions,"read_file":read_file,"write_file":write_file,
               "edit_file":edit_file,"list_files":list_files}

SESSIONS_DIR = os.path.join(WORKSPACE_ROOT, ".agent", "sessions")
AGENTS_PATH = os.path.join(WORKSPACE_ROOT, "AGENTS.md")

SESSION_OBJECTS={}

os.makedirs(SESSIONS_DIR, exist_ok=True)

def build_system_prompt() -> str:
    parts = [BASE_PROMPT]
    path=AGENTS_PATH
    if os.path.isfile(path):
        parts.append(f"## Project rules\n{open(path).read()}")
    return "\n\n".join(parts)

def trim_history(messages: list, max_messages: int = 20) -> list:
    system = messages[0]
    rest = messages[1:]
    if len(rest) <= max_messages:
        return messages

    trimmed = rest[-max_messages:]
    while trimmed and trimmed[0]["role"] == "tool":
        trimmed = trimmed[1:]

    return [system] + trimmed

class Session:

    def __init__(self, session_id: str | None = None):
        if session_id is None:
            while True:
                new_id = generate("0123456789abcdef", 8)
                for filename in os.listdir(SESSIONS_DIR):
                    if filename.replace(".json", "") == new_id:
                        break
                else:
                    self.id = new_id
                    break

            self.title = ""
            self.created_at = datetime.now().isoformat(timespec="seconds")
            self.updated_at = ""
            self.messages = [{"role": "system", "content": build_system_prompt()}]

            ses_dict = {"id": self.id, "title": self.title, "created_at": self.created_at,
                        "updated_at": self.updated_at, "messages": self.messages}
            with open(os.path.join(SESSIONS_DIR, f"{self.id}.json"), "w") as handle:
                json.dump(ses_dict, handle)

        else:
            filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
            if not os.path.isfile(filepath):
                raise ValueError(f"Session {session_id} not found")

            with open(filepath, "r") as handle:
                ses_dict = json.load(handle)

            self.id = ses_dict["id"]
            self.title = ses_dict["title"]
            self.created_at = ses_dict["created_at"]
            self.updated_at = ses_dict["updated_at"]
            self.messages = ses_dict["messages"]

    def save_session(self, messages: list, title: str = "Untitled") -> None:
        FILENAME = SESSIONS_DIR + "/" + self.id + ".json"
        if title.lower() == "untitled":
            with open(FILENAME, "r") as handle:
                ses_dict = json.load(handle)

            relevant = [m for m in ses_dict["messages"] if m["role"] in ("user", "assistant") and m.get("content")]
            content = "\n".join(f"{m['role']}: {m['content']}" for m in relevant)

            if not content:
                self.title = title
            else:
                try:
                    title_prompt = (f"Here is a conversation:\n\n{content}\n\n""Generate a concise 5-word title that summarizes what this "
                                        "conversation is about. Reply with ONLY the title text — ""no quotes, no explanation, no extra words.")
                    response = client.chat.completions.create(messages=[{"role": "user", "content": title_prompt}],model=MODEL) 
                    self.title = response.choices[0].message.content.strip()
                except Exception as e: 
                    self.title = title
        else:
            self.title = title
        
        self.messages=messages
        self.updated_at=datetime.now().isoformat(timespec="seconds")
        ses_dict={"id": self.id,"title": self.title,"created_at": self.created_at,"updated_at": self.updated_at,"messages": self.messages}
        FILENAME=SESSIONS_DIR+"/"+self.id+".json"
        with open(FILENAME,"w") as handle:
            json.dump(ses_dict,handle)

    def load_session(self) -> dict:
        FILENAME=SESSIONS_DIR+"/"+self.id+".json"
        with open(FILENAME,"r") as handle:
            ses_dict=json.load(handle)
    
        return ses_dict
    
def list_sessions() -> list[dict]:
    result = []
    for filename in os.listdir(SESSIONS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(SESSIONS_DIR, filename)
            with open(filepath, "r") as handle:
                result.append(json.load(handle))
    result.sort(key=lambda s: s["updated_at"], reverse=True)
    return result

class Agent:
    
    def __init__(self, session_id: str | None = None):
        self.session = Session(session_id=session_id)
        self.session_id = self.session.id
        SESSION_OBJECTS[self.session_id] = self.session
        self.messages = self.session.messages
        self.todo=None

    def chat(self, user_message: str) -> str:

        self.messages.append({"role":"user","content":user_message})
        reply=self._run_loop()
        self.messages=trim_history(self.messages)
        self.session.save_session(messages=self.messages,title=self.session.title if self.session.title else "Untitled")
        return reply
    
    def run_once(self, prompt: str) -> str:
        return self.chat(prompt)
    
    def _run_loop(self) -> str:
        for _ in range(MAX_ITERATIONS):
            response = client.chat.completions.create(model=MODEL,messages=self.messages,tools=TOOLS)
            msg = response.choices[0].message
            self.messages.append(msg.model_dump())

            if not msg.tool_calls:
                return msg.content  # model gave final answer, no more tools needed

            for tool_call in msg.tool_calls:
                result_str = self.dispatch(tool_call)
                self.messages.append({"role": "tool","tool_call_id": tool_call.id,"content": result_str})

        return "Max iterations reached."
    
    def dispatch(self, tool_call) -> str:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)

        #TODO tools-class methods

        if (name=="add_todo"):
            self.todo=TODO(args["task"],self.session_id)
            self.todo.add_todo(args["task"],args["steps"])
            result=self.todo.get_todo()

        elif (name=="get_todo"):
            result=self.todo.get_todo() if self.todo else {"error":"No todo list yet"}

        elif (name=="mark_todo"):
            result=self.todo.mark_todo(**args)
        
        elif (name=="save_todo"):
            self.todo.save_todo()
            result={"status":"saved"}

        #Remaining are registry tools

        elif (name in TOOL_REGISTRY):
            result=TOOL_REGISTRY[name](**args)
        
        else:
            result={"error":f"Unknown tool: {name}"}

        self._emit("tool_call",name=name,args=args,result=result)
        return json.dumps(result)
    
    def _emit(self,event: str,**data) -> None:
        pass

class REPLAgent(Agent):

    def run(self) -> None:

        print(f"Coding Agent [{self.session_id}] — /quit to exit | /list_sessions | /resume <id>")

        while True:
            try:
                user_input = input("[YOU]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nInvalid input. Please try again.\n")
                continue

            if not user_input:
                print("\nInvalid input. Please try again.\n")
                continue

            if (user_input=="/quit"):
                archive_prompt = "Save a brief summary of this session to .agent/notes/ as a markdown file." \
                "Keep the file name in lowercase which contains a short title for the discussion."
                reply=self.chat(archive_prompt)
                if (reply!="Max iterations reached."):
                    print(reply)
                print("\nThank you for using Code Scout! The chat history has been saved!")
                break

            elif (user_input=="/list_sessions"):
                for session in list_sessions():
                    print (f"{session['id']} : {session['title']}")
            
            elif (user_input.startswith("/resume")):
                session_id=user_input.split(" ")[-1]

                try:
                    self.session = Session(session_id=session_id)
                    self.session_id = self.session.id
                    SESSION_OBJECTS[self.session_id] = self.session
                    self.messages = self.session.messages
                    self.todo=None
                    print(f"Resumed session {self.session_id} — {self.session.title}")
                except ValueError as e:
                    print(f"Error: {e}")
                
            else:
                print(f"[AGENT]: {self.chat(user_input)}")
                print()

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            print(f"  [tool] {data.get('name')}", file=sys.stderr)

def main():
    agent = REPLAgent()
    if len(sys.argv) > 1:
        print(agent.run_once(" ".join(sys.argv[1:])))
        return
    agent.run()


if __name__ == "__main__":
    main()

    
