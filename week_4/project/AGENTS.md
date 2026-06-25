# Code Scout Rules

## Tools
- Prefer `run_command` for git history, tests, and broad search (grep/find)
- Use `grep` or `list_definitions` first to locate the right file and lines before calling `read_file`
- Prefer `edit_file` over `run_command` for precise, line-level changes; use `run_command` for anything `edit_file` doesn't cover
- Destructive or unclassified commands will pause for human approval — that's normal, not an error
- All file paths must stay within the workspace — paths outside will be blocked automatically

## Planning
- For any task, call `add_todo` first with your full plan and a concrete `verification` command for every step — before doing anything else
- A verification command must be a real shell command that exits with code 0 on success (e.g. `pytest tests/test_auth.py`, `python -c 'import flask'`) — not a description
- Work through steps one by one — mark each step `in_progress` before starting it
- Only call `mark_todo` with `completed` after you are certain the verification command will pass — the system will re-run it automatically and reject the update if it fails
- Mark a step `blocked` if it cannot proceed, with a note explaining why — then move to the next step
- Never batch `mark_todo` calls at the end — update as you go

## Citations
- Always cite `file:line` for any claim about code behavior
- If `grep` or `run_command` returns zero results, try a broader search term before reporting something doesn't exist
- Never claim a step is done on your own say-so — exit code 0 is the only evidence that counts 