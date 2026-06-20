import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv
from nanoid import generate
from datetime import datetime

load_dotenv()

from tools.files import read_file,write_file,edit_file,list_files
from tools.web import web_search,web_fetch,fetch_for_agent,smart_fetch,fetch_clean
from tools.papers import read_paper,paper_search
from tools.tools_schema import TOOLS


WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_ITERATIONS = 10

client = OpenAI(base_url="https://openrouter.ai/api/v1",api_key=os.environ["OPENROUTER_API_KEY"])

MODEL = "openai/gpt-oss-120b:free"
BASE_PROMPT = "You are Research Desk, a helpful research assistant.Use tools when appropriate and update your research notes as and when " \
                "required."


TOOL_REGISTRY={"read_file":read_file,"write_file":write_file,"edit_file":edit_file,"list_files":list_files,"smart_fetch":smart_fetch,
               "web_search":web_search,"paper_search":paper_search,"read_paper":read_paper}

# ---------------------------------------------------------------------------
# Session Handling
# ---------------------------------------------------------------------------

SESSIONS_DIR = os.path.join(WORKSPACE_ROOT, ".agent", "sessions")
AGENTS_PATHS = (os.path.join(WORKSPACE_ROOT, "AGENTS.md"), 
                os.path.join(WORKSPACE_ROOT, ".agent", "AGENTS.md"))

os.makedirs(SESSIONS_DIR, exist_ok=True)

def build_system_prompt() -> str:
    parts = [BASE_PROMPT]
    for path in AGENTS_PATHS:
        if os.path.isfile(path):
            parts.append(f"## Project rules\n{open(path).read()}")
            break
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
                    print("DEBUG raw response:", repr(response.choices[0].message.content))   # <- yeh line add karo
                    self.title = response.choices[0].message.content.strip()
                except Exception as e:
                    print("DEBUG exception:", e)   # <- yeh bhi add karo
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

session_objects={}          

class Agent:
    """Core agent: loop, tools, sessions. No UI."""

    def __init__(self, session_id: str | None = None):
        self.session = Session(session_id=session_id)
        self.session_id = self.session.id
        session_objects[self.session_id] = self.session
        self.messages = self.session.messages
            

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

        if name == "read_file":
            result = read_file(**args)
        elif name == "write_file":
            result = write_file(**args)
        elif name == "edit_file":
            result = edit_file(**args)
        elif name == "list_files":
            result = list_files(**args)
        elif name == "web_search":
            result = web_search(**args)
        elif name == "smart_fetch":
            result = smart_fetch(**args)
        elif name == "paper_search":
            result = paper_search(**args)
        elif name == "read_paper":
            result = read_paper(**args)
        else:
            result = {"error": f"Unknown tool: {name}"}

        self._emit("tool_call", name=name, args=args, result=result)
        return json.dumps(result)

    def _emit(self, event: str, **data) -> None:
        """Override in REPLAgent/TUIAgent for tool logging."""
        pass

class REPLAgent(Agent):
    """Terminal REPL + one-shot CLI."""

    def run(self) -> None:

        print(f"Research Desk [{self.session_id}] — \n /quit to exit \n /list_sessions to view all the sessions \n"\
              "/resume <session_id> to resume the discussion held in that session_id")
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
                archive_prompt=f"{json.dumps(self.session.messages)} \n - Write down whatever has been discovered from this research in"\
                " not more than 500 words in notes/ in markdown format.Follow the file-naming convention defined earlier.Don't include "\
                    "the summary in your reply just update once the summary is saved."
                reply=self.chat(archive_prompt)
                if (reply!="Max iterations reached."):
                    print(reply)
                print("\nThank you for using Research Desk! The research history has been saved!")
                break

            elif (user_input=="/list_sessions"):
                for session in list_sessions():
                    print (f"{session["id"]} : {session["title"]}")
            
            elif (user_input.startswith("/resume")):
                session_id=user_input.split(" ")[-1]

                try:
                    self.session = Session(session_id=session_id)
                    self.session_id = self.session.id
                    self.messages = self.session.messages
                    print(f"Resumed session {self.session_id} — {self.session.title}")
                except ValueError as e:
                    print(f"Error: {e}")
                
            else:
                print(self.chat(user_input))
                print()

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            print(f"  [tool] {data.get('name')}", file=sys.stderr)

    
def main():
    if "--tui" in sys.argv:
        from tui import TUIAgent   
        TUIAgent().run()
        return
    agent = REPLAgent()
    if len(sys.argv) > 1:
        print(agent.run_once(" ".join(sys.argv[1:])))
        return
    agent.run()


if __name__ == "__main__":
    main()