TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's contents with line numbers. Supports pagination via start_line and read_lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file, relative to workspace root."},
                    "start_line": {"type": "integer", "description": "First line to read (1-indexed). Default 1."},
                    "read_lines": {"type": "integer", "description": "Number of lines to read. Default 200."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or overwrite an existing file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing, deleting, or appending lines. Returns a diff preview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operation": {"type": "string", "enum": ["replace", "delete", "append"]},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "content": {"type": "string"},
                },
                "required": ["path", "operation", "start_line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to search. Default '.'."},
                    "pattern": {"type": "string", "description": "Glob pattern. Default '*'."},
                },
                "required": [],
            },
        },
    },
    {
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
    },
    {
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
    },
    {
        "type": "function",
        "function": {
            "name": "paper_search",
            "description":  "Search for machine learning and computer science papers. "
                            "Use this first when the user asks about research papers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query such as a paper title, topic, method, or keyword."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of papers to return. Default 5."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_paper",
            "description":  "Read the contents of a paper returned by paper_search. "
                            "Requires a paper ID from paper_search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "The paper's arXiv ID, e.g. '2205.14135', or an arXiv URL."
                    }
                },
                "required": ["paper_id"]
            }
        }
    }
]