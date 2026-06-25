TIMEOUT_DEFAULT = 30
MAX_GREP_RESULTS = 50

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command in the workspace and return its output. "
                "Use this to search (grep/find), inspect history (git log/diff), "
                "run tests, or make a change. Read-only commands run immediately. "
                "Anything that writes, deletes, or installs will pause and ask the "
                "human operator for approval — expect that pause, it's not a failure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": f"Seconds before the command is killed. Default {TIMEOUT_DEFAULT}.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": (
                "Search file contents for a pattern across the workspace. "
                "Use this before read_file when you don't already know which "
                "file you need."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Text or regex to search for."},
                    "path": {"type": "string", "description": "Subdirectory to search, default workspace root."},
                    "case_sensitive": {"type": "boolean", "description": "Default false."},
                    "max_results": {
                        "type": "integer",
                        "description": f"Cap on matches returned. Default {MAX_GREP_RESULTS}.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_definitions",
            "description": (
                "List the functions and classes declared in a Python file, "
                "with line numbers, without reading the whole file. Use this "
                "right after grep to decide which match is worth reading in "
                "full with read_file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to a Python file."},
                },
                "required": ["path"],
            },
        },
    },
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
                    "start_line": {"type": "integer",
                                "description": "Line number to start the operation (1-indexed). Required for replace and delete. "
                                "For append, this is the line after which content is inserted."},
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
            "name": "add_todo",
            "description": (
                "Generate a plan of up to 8 steps for the given task and store it. "
                "For each step, set a concrete verification command that proves the step is done. "
                "Call this once at the start before doing anything else."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The task to generate a plan for.",
                    },
                    "steps": {
                        "type": "array",
                        "description": "List of steps with verification commands.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "What to do in this step.",
                                },
                                "verification": {
                                    "type": "string",
                                    "description": (
                                        "Shell command that proves this step is done. "
                                        "Must exit with code 0 on success. "
                                        "e.g. 'pytest tests/test_auth.py', \"python -c 'import flask'\"."
                                    ),
                                },
                            },
                            "required": ["content", "verification"],
                        },
                    },
                },
                "required": ["task", "steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_todo",
            "description": (
                "Return the current todo list with all steps and their statuses. "
                "Use this to check what's pending, in_progress, or completed."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_todo",
            "description": (
                "Persist the current todo list to disk. "
                "Call this after every status change so progress survives a restart."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "TODOS_DATA": {
                        "type": "array",
                        "description": "The full todo list to save.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id":      {"type": "string"},
                                "content": {"type": "string"},
                                "status":  {"type": "string"},
                                "verification": {"type": "string"}
                            },
                        },
                    },
                },
                "required": ["TODOS_DATA"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_todo",
            "description": (
                "Update a step's status. For 'completed', the system will automatically "
                "re-run the verification command — if it fails, step will NOT be marked completed. "
                "Only use 'blocked' if the step cannot proceed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "step_no": {
                        "type": "integer",
                        "description": "1-based index of the step to update.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["completed", "blocked"],
                        "description": "New status for this step.",
                    },
                },
                "required": ["step_no", "status"],
            },
        },
    }
]