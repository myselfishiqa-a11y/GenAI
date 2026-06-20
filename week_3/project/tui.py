from agent import Agent
from textual.app import App,ComposeResult
from textual.binding import Binding
from textual.widgets import Header,Footer,Input,RichLog
from textual.containers import Horizontal

from agent import Agent

class TUIAgent(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app_ref = None   

    def run(self) -> None:
        app = ResearchDeskApp(agent=self)
        self.app_ref = app
        app.run()

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call" and self.app_ref is not None:
            self.app_ref.log_tool_call(data.get("name"))

class ResearchDeskApp(App):

    TITLE = "🔬 Research Desk"         
    SUB_TITLE = "AI Smart Research Assistant"
    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
        text-style: bold;
    }

    Horizontal {
        height: 1fr;
    }

    #chat-panel {
        width: 60%;
        border: round $primary;
        border-title-color: $primary;
        background: $panel;
        padding: 0 1;
    }

    #tool-panel {
        width: 40%;
        border: round $warning;
        background: $panel-darken-1;
        padding: 0 1;
    }

    Input {
        dock: bottom;
        height: 3;
        border: tall $accent;
    }

    Footer > .footer--key {
        color: $accent;
        text-style: bold;
    }
    """

    BINDINGS = [Binding("ctrl+l", "clear_chat_panel", "Clear Chat Panel", priority=True),
                Binding("ctrl+t", "clear_tool_log", "Clear Tool Log", priority=True),
                Binding("f2", "quit_app", "Quit App", priority=True)]


    def __init__(self,agent:TUIAgent):
        super().__init__()
        self.agent=agent

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True,icon="🤖")
        with Horizontal():
            yield RichLog(id="chat-panel", wrap=True, markup=True)
            yield RichLog(id="tool-panel", wrap=True, markup=True)
        yield Input(placeholder="Ask anything...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat-panel").write("[bold yellow]Chat Panel[/bold yellow]\n")
        self.query_one("#chat-panel").write(f"[bold yellow]Session ID : {self.agent.session_id}[/bold yellow]")
        self.query_one("#tool-panel").write("[bold yellow]Tool Log[/bold yellow]\n")

    # -----------------------------------------------------------------------
    # Actions (bound to keyboard shortcuts)
    # -----------------------------------------------------------------------

    def action_clear_chat_panel(self) -> None:
        log1=self.query_one("#chat-panel", RichLog)
        log2=self.query_one("#tool-panel", RichLog)
        log1.clear()
        log2.write("[bold yellow]Chat cleared.Chat history is intact![/bold yellow]")
    
    def action_clear_tool_log(self) -> None:
        log2=self.query_one("#tool-panel", RichLog)
        log2.clear()
        log2.write("[bold yellow]Tool log cleared.Log history is intact![/bold yellow]")

    def action_quit_app(self) -> None:
        log2=self.query_one("#tool-panel", RichLog)
        log2.write("[bold red]Exiting app...[/bold red]")
        self.exit()

    # -----------------------------------------------------------------------
    # Event handlers
    # -----------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted):
        """Called when the user presses Enter."""
        user_text = event.value.strip()
        event.input.clear()

        self.run_worker(self.get_response(user_text),thread=True)
    
    async def get_response(self,user_text:str) -> None:
        log = self.query_one("#chat-panel", RichLog)
        self.call_from_thread(log.write,f"[bold cyan]You:[/bold cyan] {user_text}")

        reply = self.agent.chat(user_text)
        self.call_from_thread(log.write,f"[bold green]Agent:[/bold green] {reply}")

    def log_tool_call(self, name: str) -> None:
        log = self.query_one("#tool-panel", RichLog)
        self.call_from_thread(log.write,f"[dim][TOOL CALLED]: {name}[/dim]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    TUIAgent().run()