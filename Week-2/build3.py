import os
import time
from openai import OpenAI , RateLimitError
from dotenv import load_dotenv
from textual.app import App,ComposeResult
from textual.binding import Binding
from textual.widgets import Header,Footer,Input,RichLog
from textual.containers import Vertical
from textual.worker import Worker

load_dotenv()

client=OpenAI(base_url="https://openrouter.ai/api/v1",
              api_key=os.environ["OPENROUTER_API_KEY"])

MODEL="openrouter/owl-alpha"

MAX_HISTORY_TURNS=20

def call_model(messages:list[dict]):
        #Retry upto 3 times on rate limit
        for attempt in range(3):
            try:
                response=client.chat.completions.create(
                    model=MODEL,messages=messages)

                return response.choices[0].message.content

            except RateLimitError:
                wait_time=30*(attempt+1)
                time.sleep(wait_time)

            except Exception as e:
                 return None
            
        return None


def trim_history(messages:list[dict],max_turns:int):
        #keeps the system message and last max_turns pairs of 
        # conversations.
        # 1 pair=1 user prompt+1 model response
        if (len(messages)>2*max_turns+1):
            system_msg=messages[0]
            conversation=messages[1:]
            conversation=conversation[2:]
        
            messages=[system_msg]+conversation
        return messages

# ---------------------------------------------------------------------------
# TUI
# ---------------------------------------------------------------------------

class ChatInput(Input):
     BINDINGS=[]
     
class ChatApp(App):
    """A full-screen terminal chatbot."""

    TITLE = "Week 2 Chatbot TUI"
    CSS = """
    Screen {
        layout: vertical;
    }

    RichLog {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }

    Input {
        dock: bottom;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear display",priority=True),
        Binding("ctrl+k", "clear_history", "Clear history",priority=True),
        Binding("f2", "quit_app", "Quit",priority=True)]
    
    def __init__(self):
        super().__init__()
        self.messages: list[dict] = [
            {"role": "system", "content": "You are a helpful "
            "assistant."}]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="log", wrap=True, markup=True, 
                      highlight=True)
        yield ChatInput(placeholder="Type a message and press Enter...")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        log.write("[bold yellow]Chat started.[/bold yellow]\n")
        self.query_one(Input).focus()

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted):
        """Called when the user presses Enter."""
        user_text = event.value.strip()
        if not user_text:
            return

        event.input.clear()

        self.run_worker(self.get_response(user_text), thread=True)

    
    async def get_response(self,user_text:str):

        log = self.query_one("#log", RichLog)
        self.call_from_thread(log.write, f"[bold blue][You][/bold blue] {user_text}")

        self.messages.append({"role":"user","content":user_text})
        response=call_model(self.messages)

        if (response):
            self.messages.append({"role":"assistant","content":response})
            self.messages=trim_history(self.messages,MAX_HISTORY_TURNS)

            self.call_from_thread(log.write, f"[bold green][Agent][/bold green] {response}")

        else:
             self.messages.pop()
             self.call_from_thread(log.write,"Error : Couldn't " \
             "generate response after 3 tries. Pls try again later.")

    # -----------------------------------------------------------------------
    # Actions (bound to keyboard shortcuts)
    # -----------------------------------------------------------------------

    def action_clear_display(self):
         self.notify("Clear display triggered.")
         log=self.query_one("#log", RichLog)
         log.clear()
         log.write("[bold yellow]Display cleared. Your history is stored safely![/bold yellow]\n")

    def action_clear_history(self):
         self.notify("Clear history triggered.")
         log=self.query_one("#log", RichLog)
         log.clear()
         self.messages=[self.messages[0]]
         log.write("[bold yellow]History cleared. Fresh start![/bold yellow]\n")

    def action_quit_app(self):
         self.notify("Quit action triggered.")
         log=self.query_one('#log', RichLog)
         log.write("[bold red]Exiting the app...[/bold red]")
         self.exit()
# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ChatApp().run()
