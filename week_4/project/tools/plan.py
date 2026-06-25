import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from .exec import run_command

load_dotenv()

client = OpenAI(base_url="https://openrouter.ai/api/v1",api_key=os.environ["OPENROUTER_API_KEY"])

MODEL = "openrouter/owl-alpha"

TODO_FILE="week_4/project/.agent/todos.json"

TODOS_DATA={}

class TODO:
    
    def __init__(self, task: str, session_id: str):
        self.session_id = session_id

        if session_id not in TODOS_DATA:
            if os.path.isfile(TODO_FILE):
                with open(TODO_FILE, "r") as handle:
                    data = json.load(handle)
                if session_id in data:
                    self.task = data[session_id]["task"]
                    self.plan = data[session_id]["plan"]
                    TODOS_DATA[session_id] = {"task": self.task, "plan": self.plan}
                    return
            self.task = task
            self.plan = []
            TODOS_DATA[session_id] = {"task": self.task, "plan": self.plan}
        else:
            self.task = TODOS_DATA[session_id]["task"]
            self.plan = TODOS_DATA[session_id]["plan"]

    def add_todo(self, task: str, steps: list[dict]):
        self.task = task
        self.plan = []
        for i, step in enumerate(steps, start=1):
            self.plan.append({
                "id": str(i),
                "content": step["content"],
                "verification": step["verification"],
                "status": "pending"
            })
        self.save_todo()

    def get_todo(self) -> list[dict]:
        return self.plan

    def save_todo(self):
        TODOS_DATA[self.session_id] = {"task": self.task, "plan": self.plan}
        os.makedirs(".agent", exist_ok=True)
        with open(TODO_FILE, "w") as handle:
            json.dump(TODOS_DATA, handle)

    def mark_todo(self, step_no: int, status: str) -> dict:
        step = self.plan[step_no - 1]

        if status == "completed":
            verification_cmd = step.get("verification", "")
            if not verification_cmd:
                return {"error": "No verification command set — cannot mark completed"}
            
            result = run_command(verification_cmd)
            if result.get("exit_code") != 0:
                return {
                    "error": "Verification failed — step NOT marked completed",
                    "stdout": result.get("stdout"),
                    "stderr": result.get("stderr"),
                    "exit_code": result.get("exit_code")
                }

        step["status"] = status
        if step_no < len(self.plan):
            self.plan[step_no]["status"] = "in_progress"

        self.save_todo()
        return {"status": "ok", "updated": step}