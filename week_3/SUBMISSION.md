# **Research Agent Project Description:**

# 

#### ***Objectives :*** 



###### Building a Research Desk - a full research agent that searches the web and academic papers, reads primary sources, picks up where the user left off, and saves findings for future reference.



##### ***Foundation :***



I completed build1.py and build2.py on my own, understanding how to work with sessions and later how to associate them with agents. My build2.py consists of Sessions class along with Agent class which defines all the methods used to handle a session.



##### ***Project:***



###### ***Extra dependencies:***



To complete this project, I installed a few new dependencies and used them as well as many old dependencies which were used in week-2 project. The new dependencies are:

* nanoid
* glob



###### ***What I have built:***



I have built a smarter version of the last week's project Research Desk. This version has access to more tools than the previous one and all of them are hand-written tools. This Research Desk can search the web, read papers, fetch URLs from the web, search for a particular paper, return its summary, read from a file, write to a file, edit a file, make its own notes and switch to a previous session at the user's command. Conversations are saved to the disk as JSON files, so the assistant can pick up the files on the next run and continue where it left off.



The agent runs three different ways from the same underlying brain:





python agent.py "question" — a one-shot CLI query, prints the answer and exits

python agent.py — an interactive REPL in the terminal

python agent.py --tui — a full-screen Textual UI with a separate chat panel and tool-activity log





All three modes share one Agent class — the loop logic, tool dispatch, and session handling live in exactly one place, so a bug fix or a new tool only needs to be written once.





###### ***Architecture:***



agent.py       — Agent (brain), REPLAgent (terminal), main()

tui.py         — TUIAgent(Agent), Textual App

tools/

&#x20; files.py     — read\_file, write\_file, edit\_file, list\_files

&#x20; web.py       — web\_search, web\_fetch, smart\_fetch

&#x20; papers.py    — paper\_search, read\_paper

&#x20; tools\_schema.py — TOOLS (OpenAI function-calling schema)

.agent/sessions/ — one JSON file per conversation

notes/           — markdown notes the agent writes for itself

AGENTS.md        — project rules loaded into the system prompt



Agent holds everything the model needs to think: the message loop, the tool registry, and session save/load. It has no idea whether it's being driven by a terminal or a UI. REPLAgent only adds a run() loop with input(); TUIAgent only adds a Textual run() and overrides \_emit() so tool calls show up in a UI panel instead of being printed to stderr.



###### ***Memory:***



Every session is a JSON file named after an 8-character hex ID, holding the full message history, a title, and timestamps. Session can either generate a brand-new ID or load an existing one from disk by ID — which is what makes /resume <id> possible. Sessions are listed by reading every JSON file in .agent/sessions/ directly off disk (not from an in-memory cache), so resuming works correctly even across separate runs of the program — not just within one running process.



The REPL also has /list\_sessions to browse past sessions and an auto-title feature: if a session is never given an explicit title, the agent asks the model itself to summarize the conversation into a five-word title when it's saved.



AGENTS.md is loaded into the system prompt on every session start, alongside a short base prompt that tells the model which tool family to reach for (web vs. papers vs. files) and reminds it to explore with list\_files before assuming a path.





###### ***File Tools:***



Built in the OpenCode style: every path goes through a sandboxing resolve\_path() that refuses anything resolving outside WORKSPACE\_ROOT. read\_file supports start\_line/read\_lines pagination, returns line-numbered output, and a has\_more flag so the model knows whether it's seen the whole file. edit\_file is line-based — replace, delete, append — and returns a small diff preview (-/+ lines with line numbers) so the model can see exactly what changed and self-correct if it targeted the wrong lines.



The trickiest part of this whole project was getting edit\_file's line-index math right at the edges — editing line 1 of a file, or editing through the last line, kept producing either wrong context lines or IndexError crashes because Python's negative indexing (lines\[-1]) silently returns the wrong line instead of failing loudly. I had to add explicit bounds checks before touching the "context line before/after the edit" rather than assuming the index was always valid.



###### ***Paper Tools:***



paper\_search and read\_paper replace the AlphaXiv MCP from Week 2 with hand-written calls to the Hugging Face Papers API — paper\_search hits /api/papers/search, read\_paper fetches both the metadata endpoint and the paper's markdown content, cleans the arxiv ID out of full URLs if one is passed in, and truncates long content to stay within a safe context size.



###### ***TUI:***



The Textual UI runs the same Agent.chat() underneath — the only new code is the UI shell: a chat panel, a separate tool-activity panel, and an input box. Tool calls stream into the right-hand panel via the \_emit() hook so that the user can watch what the agent is doing in real time instead of just waiting for a final answer.



###### ***What I'd Improve With More Time:***





* /resume currently only works by exact session ID — a fuzzy search or "resume the most recent session" shortcut would be friendlier.
* More input validation in edit\_file (e.g. rejecting an out-of-range start\_line with a clear error instead of trusting the model never sends one).

