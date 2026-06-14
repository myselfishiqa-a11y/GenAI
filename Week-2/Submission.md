# **Research Agent Project Description:**



#### ***Objective*** : Building a TUI research agent that chains web search, page fetching, and academic paper search (via AlphaXiv MCP) to answer research questions it couldn't answer alone.



##### ***Foundation*** : 

###### I focussed on building build1.py,build2.py and build3.py , understood each part of it ,progressing from working without OpenAI SDK tools to working with it and finally learning how to work with TUI to give my project an app-like look.



### ***Project:***



###### *API Key Hygiene :*

###### 

1. OpenAI API key as well as Serper API key are stored in a .env file and loaded using python-dotenv.

2\. The .env file is listed in .gitignore to prevent accidental commits to GitHub.



###### *Extra dependencies and agent setup:*



To complete this week's project I had to install several dependencies like:

* requests
* markdownify
* trafilatura
* textual
* mcp
* httpx



Agent setup:



* I had to login into AlphaXiv for the first time to get authentication.The AlphaXiv MCP connection uses OAuth 2.0 — on first run, a browser opens for Google login, and the resulting access/refresh tokens are saved locally (.alphaxiv\_tokens.json) so future runs don't require re-authentication.



* I also signed in at Serper to get my Serper API key and stored it in .env.



###### *What have I built and how it works:*



I have built an AI Research Assistant which receives the query through the TUI, parses it to a smart router, which decides whether it is a research query, a web query or a general query. Accordingly, it calls the specific function and prints the type of query detected in the tool log. Then the specific function calls the AI model with that query and receives some tool calls from the model. Then the tools are called one-by-one and together they construct the output and send it back to the chat-panel as well as stored in a list for the model's future reference. All the tool calls are also stored in the same list for the model's future reference. There are some bindings available in my TUI, namely:

* Clear Chat Panel
* Clear Tool Log
* Clear History
* Save Chat
* Quit

All these functions are invoked through specific key bindings mentioned in the TUI itself.



###### *Design Decision:*



* I created a run\_smart\_router() function which takes the query and tests whether it is a research query, web search query or general query and calls the specific agent function accordingly. This was done to separate the types of queries and agent calls and make a clean design.
* I created a fallback to web tools which works in case MCP agent fails. The web agent function gets called automatically which handles the task.
* If a URL doesn't exist and the model is asked to fetch that, the error message is returned by the agent function to the model which calmly tells the user that the URL doesn't exist.



###### *Something that surprised me:*



When I tried key bindings like CTRL+Q,CTRL+D etc. for different functions, they weren't working. When I deep-dived into it, I found that they were being swallowed by the terminal itself before reaching the UI. Then I did trial and error several times and finally got a set of key bindings which were working fine and used them in my final submission. Also, I added a priority argument in all my bindings so that they will be sent directly to the UI instead of getting captured by the terminal.



###### *Areas for Improvements:*



Given more time, I would improve the UI of my project, enhancing its features and giving it a more refined and sophisticated look.

Also, I would improvise the error handling part of my project, adding new features like model fallback, in case one model is not working properly.



&#x20;

