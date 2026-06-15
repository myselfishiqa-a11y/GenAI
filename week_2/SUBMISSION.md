# **Research Agent Project Description**

# 

### ***Objective:***

###### Building a TUI research agent that chains web search, page fetching, and academic paper search (via AlphaXiv MCP) to answer research questions it couldn't answer alone.

# 

### ***Foundation:***

###### I worked through build1.py, build2.py, and build3.py — progressing from a hand-rolled tool-calling format, to the OpenAI SDK's native tool calling, and finally to wrapping the agent in a Textual TUI.

# 

## ***Project:***

# 

##### ***Extra Dependencies and Agent Setup:***



###### To complete this project, I installed several dependencies:

###### 

* ###### requests
* ###### &#x20;httpx
* ###### markdownify
* ###### trafilatura
* ###### textual
* ###### mcp





###### **Agent Setup:**

###### 

* ###### I logged into AlphaXiv to obtain authentication. The AlphaXiv MCP connection uses OAuth 2.0. During the first run, a browser opens for Google login, and the generated access and refresh tokens are stored locally in `.alphaxiv\_tokens.json`, allowing future runs without re-authentication.
* ###### I also signed up for Serper, obtained an API key, and stored it in the `.env` file.

# 

##### ***What I Have Built and How It Works:***



###### I built an AI Research Assistant that receives user queries through a Textual TUI and either responds directly or uses tools when required. The assistant has access to three tools:

###### 

* ###### web\_search (Serper API)
* ###### smart\_fetch (checks for `llms.txt` before falling back to content extraction using trafilatura and markdownify)
* ###### discover\_papers from AlphaXiv through MCP

###### 

###### A chatbot function handles general conversations.

###### 

###### The workflow starts when the user enters a query in the UI. The query is passed to a smart router that determines whether it is a research query, web query, or general query. Based on the classification, the appropriate agent function is called, and the detected query type is logged in the tool panel.

###### 

###### The selected agent then sends the query to the AI model, which may return tool calls. These tools are executed one by one, their outputs are combined, and the final response is shown in the chat panel. Responses are also stored in conversation history so the model can reference previous interactions. Tool calls are stored as well, allowing future context-aware responses.

###### 

###### The TUI provides the following functions:

###### 

* ###### Clear Chat Panel
* ###### Clear Tool Log
* ###### Clear History
* ###### Save Chat
* ###### Quit

###### 

###### All functions can be accessed through dedicated key bindings displayed within the interface.

###### 

##### ***Design Decisions:***

###### 

* ###### I created a `run\_smart\_router()` function that determines whether a query is research-related, web-related, or general, and routes it to the appropriate agent. This separation keeps the design modular and easier to maintain.
* ###### I implemented a fallback mechanism so that if the MCP agent fails, the web agent is automatically invoked to continue handling the request.
* ###### When a user requests content from a non-existent URL, the corresponding error is returned to the model, which then communicates the issue gracefully.
* ###### Tool calls, routing decisions, and errors are sent to the tool-activity panel through a `log\_callback` function, keeping the chat panel focused on the conversation itself.

###### 

##### ***Something That Surprised Me:***

###### 

###### While implementing key bindings, I noticed that combinations such as CTRL+Q and CTRL+D were not working. After investigating, I discovered that the terminal was intercepting these shortcuts before they reached the Textual application. Through experimentation, I identified a set of key bindings that worked reliably and used them in the final version. I also added the `priority` argument to all bindings so that they are handled by the UI before the terminal can capture them.

###### 

##### ***Areas for Improvement:***

###### 

* ###### With more time, I would improve the UI, adding more features and making it look more polished.
* ###### I would strengthen error handling and add model fallback capabilities so the system can switch to another model if one becomes unavailable.
* ###### I would also implement streaming responses, allowing users to see output appear token-by-token instead of waiting for the complete response.

###### 

