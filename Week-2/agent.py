import os
import asyncio
import time
import sys
import re
import json
import requests
import trafilatura
import webbrowser
import httpx

from urllib.parse import parse_qs , urlparse
from openai import OpenAI , RateLimitError
from dotenv import load_dotenv
from markdownify import markdownify

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider , TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull , OAuthClientMetadata , OAuthToken

from textual.app import App,ComposeResult
from textual.binding import Binding
from textual.widgets import Header,Footer,Input,RichLog
from textual.containers import Horizontal

load_dotenv()

client=OpenAI(base_url="https://openrouter.ai/api/v1",api_key=os.environ["OPENROUTER_API_KEY"])

MODEL="openai/gpt-oss-120b:free"
SERPER_API_KEY=os.environ["SERPER_API_KEY"]
ALPHAXIV_MCP_URL="https://api.alphaxiv.org/mcp/v1"
REDIRECT_URI="http://localhost:8765/callback"
TOKEN_FILE=".alphaxiv_tokens.json"

# ---------------------------------------------------------------------------
# Web Tools
# ---------------------------------------------------------------------------

def web_search(query:str,num_results:int=5,log_callback=None) -> list[dict]:

    try:
        response=requests.post("https://google.serper.dev/search",headers={"X-API-KEY":SERPER_API_KEY,
                                "Content-Type":"application/json"},json={"q":query,"num":num_results},timeout=10)
        
        response.raise_for_status()
        data=response.json()
        results=[]

        for item in data.get("organic",[]):
            results.append({"title":item.get("title",""),"link":item.get("link",""),"snippet":item.get("snippet","")})
        
        return results
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR]:Couldn't search the web")

        return [{"error":str(e),"title":"","link":"","snippet":""}]
    
def web_fetch(url:str,log_callback=None) -> str:

    headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}

    try:
        response=requests.get(url,headers=headers,allow_redirects=True,timeout=10)

        response.raise_for_status()
        return response.text
    
    except requests.exceptions.HTTPError as e:
        if log_callback:
            log_callback(f"[ERROR]:Page not found or access denied - {e}")
        return (f"Error : Page not found or access denied - {e}")
    
    except requests.exceptions.Timeout:
        if log_callback:
            log_callback("[ERROR]:Request timed out")
        return("Error : Request timed out")
    
    except requests.exceptions.ConnectionError:
        if log_callback:
            log_callback("[ERROR]:Couldn't connect to the URL")
        return("Error : Couldn't connect to the URL")
    
def fetch_clean(url:str) -> str:
    html=web_fetch(url)
    if (html.startswith("Error")):
        return html
    
    text=trafilatura.extract(html,include_comments=False,include_tables=True)
    if text:
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text
    
    cleaned = markdownify(html, heading_style="ATX",strip=["script", "style", "nav", "footer"])
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned

MAX_CHARS=8000

def fetch_for_agent(url: str) -> str:
    content = fetch_clean(url)
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + "\n\n[...truncated]"
    return content

def smart_fetch(url: str) -> str:
    from urllib.parse import urlparse
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    try:
        response = requests.get(f"{base}/llms.txt", timeout=5)
        if response.status_code == 200:
            return f"[llms.txt found]\n\n{response.text}\n\n---\nOriginal URL: {url}"
    except Exception:
        pass
    
    return fetch_for_agent(url)

# ---------------------------------------------------------------------------
# Web Tool schema
# ---------------------------------------------------------------------------

search_tool = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information. Use this when the user asks "
            "about recent events, specific facts, or anything you are uncertain about. "
            "Returns a list of search results with titles, URLs, and snippets."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific and targeted.",
                }
            },
            "required": ["query"],
        },
    },
}

fetch_tool = {
    "type": "function",
    "function": {
        "name": "smart_fetch",
        "description": (
            "Fetch and read the full content of a web page. "
            "First checks if the site has an llms.txt summary file — "
            "if found, returns that instead of the full page. "
            "Use this after web_search to read a specific result in detail."
            "Use this only if the snippet is not enough."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch, including https://",
                }
            },
            "required": ["url"],
        },
    },
}

WEB_TOOLS=[search_tool,fetch_tool]
WEB_TOOL_REGISTRY={"smart_fetch":smart_fetch,"web_search":web_search}

# ---------------------------------------------------------------------------
# Web Dispatcher — handles only web tools
# ---------------------------------------------------------------------------

def dispatch_web(tool_call,log_callback=None) -> str:
    
    try:
        name=tool_call.function.name
        arguments=json.loads(tool_call.function.arguments)

    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR]: {e}")

        return json.dumps({"error":str(e)})
    
    try:
        tool=WEB_TOOL_REGISTRY[name]
    
    except KeyError:
        if log_callback:
            log_callback(f"[ERROR]: Unknown tool name: {name}")

        return json.dumps({"error":f"Unknown tool name:{name}"})
    
    if log_callback:
        log_callback(f"[WEB TOOL CALLED]: {name}")

    try:
        result=tool(**arguments)
        if isinstance(result,str):
            return result
        return json.dumps(result)
    
    except Exception as e:
        if log_callback:
            log_callback(f"[ERROR]: {e}")
        return json.dumps({"error":str(e)})
    
# ---------------------------------------------------------------------------
# Web Agent loop (no MCP — for simple web queries)
# ---------------------------------------------------------------------------

MAX_ITERATIONS=8

def run_agent(user_message:str,messages:list[dict],log_callback=None) -> str:

    messages.append({"role":"user","content":user_message})

    for _ in range(MAX_ITERATIONS):

        try:
            response=client.chat.completions.create(model=MODEL,messages=messages,tools=WEB_TOOLS)
        except Exception as e:
            if log_callback:
                log_callback(f"[API ERROR]: {e}")
            return (f"[API Error] : {e}")
        
        if (not response or not response.choices):
            if log_callback:
                log_callback("[ERROR]: Empty response received")
            return ("[Error] : Empty response recieved.")
        
        message=response.choices[0].message
        finish_reason=response.choices[0].finish_reason

        if (finish_reason=="stop"):
            messages.append({"role":"assistant","content":message.content})
            return message.content
        
        if (finish_reason=="tool_calls" and message.tool_calls):
            messages.append(message)
            for tool_call in message.tool_calls:
                result=dispatch_web(tool_call,log_callback)
                messages.append({"role":"tool","tool_call_id":tool_call.id,"content":result})
        else:
            return message.content or ("[No response]")
    
    if log_callback:
        log_callback(f"[WARNING]: Agent stopped after {MAX_ITERATIONS} iterations")
    return (f"[Agent stopped after {MAX_ITERATIONS} iterations without a final answer]")

# --- Token storage ---
# The MCP SDK calls these methods to persist OAuth tokens between runs.

class FileTokenStorage(TokenStorage):
    def __init__(self):
        self.tokens : OAuthToken|None = None
        self.client_info : OAuthClientInformationFull|None = None
        if os.path.exists(TOKEN_FILE):
            try:
                data=json.loads(open(TOKEN_FILE).read())
                if (data.get("tokens")):
                    self.tokens=OAuthToken(**data["tokens"])
                if (data.get("client_info")):
                    self.client_info=OAuthClientInformationFull(**data["client_info"])
            except Exception:
                pass

    def _save(self):
        # mode="json" converts Pydantic types like AnyUrl to plain strings
        data = {}
        if self.tokens:
            data["tokens"] = self.tokens.model_dump(mode="json")
        if self.client_info:
            data["client_info"] = self.client_info.model_dump(mode="json")
        open(TOKEN_FILE, "w").write(json.dumps(data, indent=2))

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens
        self._save()

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info
        self._save()
        
# --- OAuth browser flow ---
# The MCP SDK calls redirect_handler with the auth URL, then callback_handler
# once the user has authorized and the browser is redirected to localhost.

async def open_browser(auth_url: str) -> None:
    print(f"Opening browser for login...\nIf it doesn't open: {auth_url}\n")
    webbrowser.open(auth_url)


async def wait_for_callback(log_callback=None) -> tuple[str, str | None]:
    from http.server import BaseHTTPRequestHandler, HTTPServer

    code = state = None

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal code, state
            params = parse_qs(urlparse(self.path).query)
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorized. You can close this tab.</h1>")

        def log_message(self, *args):
            pass  # silence request logs\

    if log_callback:
        log_callback(f"Waiting for callback on {REDIRECT_URI} ...")
    server = HTTPServer(("localhost", 8765), Handler)
    server.timeout = 120
    server.handle_request()
    server.server_close()

    if not code:
        raise RuntimeError("OAuth callback received no authorization code.")
    return code, state

async def run_agent_with_mcp(user_message:str,messages:list[dict],log_callback=None) -> str:

    storage=FileTokenStorage()

    auth=OAuthClientProvider(server_url=ALPHAXIV_MCP_URL,client_metadata=OAuthClientMetadata(client_name="ResearchBot Agent",
                            redirect_uris=[REDIRECT_URI],grant_types=["authorization_code","refresh_token"],response_types=["code"],
                            scope="read"),storage=storage,redirect_handler=open_browser,callback_handler=wait_for_callback)
    
    try:
        async with httpx.AsyncClient(auth=auth, follow_redirects=True, timeout=60) as http:
            async with streamable_http_client(ALPHAXIV_MCP_URL, http_client=http) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # 1. Discover tools from the MCP server
                    mcp_tools = await session.list_tools()

                    # 2. Convert MCP tool definitions to OpenAI format
                    OPENAI_TOOLS = []
                    for tool in mcp_tools.tools:
                        OPENAI_TOOLS.append({"type": "function","function": {"name": tool.name,"description": tool.description,
                                             "parameters": tool.inputSchema}})

                    messages.append({"role": "user", "content": user_message})

                    # 3. Combining both types of tools so that agent can use any tool
                    ALL_TOOLS = WEB_TOOLS + OPENAI_TOOLS

                    for _ in range(MAX_ITERATIONS):
                        try:
                            response=client.chat.completions.create(model=MODEL,messages=messages,tools=ALL_TOOLS)
                        except Exception as e:
                            if log_callback:
                                log_callback(f"[API ERROR]: {e}")
                            return (f"[API Error] : {e}")
                        
                        if (not response or not response.choices):
                            if log_callback:
                                log_callback("[ERROR]: Empty response from API")
                            return ("[Error] : Empty response from API")
                        
                        message=response.choices[0].message
                        finish_reason=response.choices[0].finish_reason

                        if (finish_reason=="stop"):
                            messages.append({"role":"assistant","content":message.content})
                            return message.content
                        
                        if (finish_reason=="tool_calls" and message.tool_calls):
                            messages.append(message)

                            for tool_call in message.tool_calls:
                                name=tool_call.function.name
                                arguments=json.loads(tool_call.function.arguments)

                                if (name in WEB_TOOL_REGISTRY):
                                    result=dispatch_web(tool_call,log_callback)

                                else:
                                    if log_callback:
                                        log_callback(f"[MCP TOOL CALLED]: {name}")
                                    mcp_result=await session.call_tool(name,arguments)
                                    result=mcp_result.content[0].text if mcp_result.content else ""

                                messages.append({"role":"tool","tool_call_id":tool_call.id,"content":result})
                        
                        else:
                            return message.content or ("[No response]")
                    
                    if log_callback:
                        log_callback(f"[WARNING]: Agent stopped after {MAX_ITERATIONS} iterations")
                    return (f"[Agent stopped after {MAX_ITERATIONS} without a final answer]")
                
    except Exception as e:
        if log_callback:
            log_callback(f"[MCP ERROR - falling back to web]: {e}")
        return run_agent(user_message,messages)

def call_chatbot(user_prompt: str, messages: list[dict],log_callback=None) -> str:
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] += user_prompt
    else:
        messages.append({"role": "user", "content": user_prompt})

    for attempt in range(3):
        try:
            response = client.chat.completions.create(model=MODEL, messages=messages)
            return response.choices[0].message.content
        except RateLimitError:
            wait=30*(attempt+1)
            if log_callback:
                log_callback(f"[WARNING]: Rate limit hit! Retrying after {wait}s...")
            time.sleep(wait)
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR]: {e}")
            return (f"Error: {e}")

    if log_callback:
                log_callback(f"[ERROR]: Couldn't generate response even after 3 tries")
    return "Couldn't generate response even after 3 tries."


#Smart router - decides whether to send the query to MCP Agent or Web Agent

RESEARCH_KEYWORDS = ["paper", "papers", "research","study", "studies","literature", "published", "findings", "authors", "survey",
                     "abstract"]

WEB_SEARCH_KEYWORDS = ["latest", "current", "currently", "today", "now", "recent", "news", "update", "released", "search","fetch", 
                       "http://", "https://", "www.","price", "weather", "score", "who","where","when","internet","browse"]

def is_research_query(query:str) -> bool:
    words=query.lower().split()

    for word in words:
        if (word in RESEARCH_KEYWORDS):
            return True
    
    return False

def is_web_search_query(query:str) -> bool:
    words=query.lower().split()

    for word in words:
        if (word in WEB_SEARCH_KEYWORDS):
            return True
    
    return False

async def run_smart_router(user_message:str,messages:list[dict],log_callback=None) -> str:

    if is_research_query(user_message):
        if log_callback:
            log_callback("[ROUTER]: Research query — using MCP agent")
        return await run_agent_with_mcp(user_message,messages,log_callback)
    
    elif is_web_search_query(user_message):
        if log_callback:
            log_callback("[ROUTER]: Web query — using Web agent")
        return run_agent(user_message,messages,log_callback)
    
    else:
        if log_callback:
            log_callback("[ROUTER]: General query — using Chatbot")
        return call_chatbot(user_message,messages)


MAX_HISTORY_TURNS=10

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

class AgentApp(App):
    TITLE = "🔬 ResearchBot"         
    SUB_TITLE = "AI Research Assistant"
    CSS = """
    Horizontal {
        height: 1fr;
    }
    #chat-panel {
        width: 60%;
        border: solid $primary;
    }
    #tool-panel {
        width: 40%;
        border: solid $warning;
    }
    Input {
        dock: bottom;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_chat_panel", "Clear Chat Panel", priority=True),
        Binding("ctrl+t", "clear_tool_log", "Clear Tool Log", priority=True),
        Binding("ctrl+k", "clear_history", "Clear History", priority=True),
        Binding("ctrl+s", "save_chat", "Save Chat", priority=True),
        Binding("f2", "quit_app", "Quit App", priority=True)
    ]

    def __init__(self):
        super().__init__()
        self.messages: list[dict] = [
            {"role": "system", "content": "You are a helpful assistant. Use tools when appropriate."}]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True,icon="🤖")
        with Horizontal():
            yield RichLog(id="chat-panel", wrap=True, markup=True)
            yield RichLog(id="tool-panel", wrap=True, markup=True)
        yield Input(placeholder="Ask anything...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat-panel").write("[bold yellow]Chat Panel[/bold yellow]\n")
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

    def action_clear_history(self) -> None:
        log1=self.query_one("#chat-panel", RichLog)
        log1.clear()
        log2=self.query_one("#tool-panel", RichLog)
        log2.clear()
        self.messages=[self.messages[0]]
        log2.write("[bold yellow]History cleared.Fresh start![/bold yellow]")
    
    def action_save_chat(self) -> None:
        with open("chat_history.json","w",encoding="utf-8") as file:
            json.dump(self.messages,file,indent=4)
        log2=self.query_one("#tool-panel", RichLog)
        log2.write("[bold yellow]Chat history saved![/bold yellow]")

    def action_quit_app(self) -> None:
        log2=self.query_one("#tool-panel", RichLog)
        log2.write("[bold red]Exiting app...[/bold red]")
        self.action_save_chat()
        self.exit()
    
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

        log1 = self.query_one("#chat-panel", RichLog)
        log2=self.query_one("#tool-panel", RichLog)

        self.call_from_thread(log1.write, f"[bold blue][You][/bold blue] {user_text}")

        self.messages.append({"role":"user","content":user_text})

        def log_to_tools(msg: str):
        # color-code by type
            if msg.startswith("[ERROR]") or msg.startswith("[API ERROR]") or msg.startswith("[MCP ERROR"):
                styled = f"[bold red]{msg}[/bold red]"
            elif msg.startswith("[WARNING]"):
                styled = f"[bold yellow]{msg}[/bold yellow]"
            elif msg.startswith("[ROUTER]"):
                styled = f"[dim]{msg}[/dim]"
            else:
                styled = f"[cyan]{msg}[/cyan]"
            self.call_from_thread(log2.write, styled)


        response=await run_smart_router(user_text,self.messages,log_to_tools)

        if (response):
            self.messages.append({"role":"assistant","content":response})
            self.messages=trim_history(self.messages,MAX_HISTORY_TURNS)

            self.call_from_thread(log1.write, f"[bold green][Agent][/bold green] {response}")

        else:
             self.messages.pop()
             log_to_tools("[ERROR]: Couldn't generate response after 3 tries.")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    AgentApp().run()
