# **CODE SCOUT PROJECT DESCRIPTION:**



#### ***Objectives :*** 



##### Building a CLI agent that can investigate and fix issues in a real, unfamiliar codebase — searching, reading, editing, running tests, and working through an explicit todo list until the fix is actually verified, not just claimed.

##### 

##### ***Foundation :***



I completed build1.py,build2.py and build3.py on my own, covering command execution, finding and searching for code and working with todo tools. These were small parts which were later merged together to form my project, Code Scout.



##### ***Project:***



###### ***Extra Dependencies:***



No extra dependencies were installed for this project- I used many previous weeks' dependencies as well as some new modules which did not require installation.



###### ***What I have built:***



I have built an autonomous agent which works on real-life problems it has never seen before. It has access to four types of tools:

* Planning tools - plan.py - consists of TODO class containing methods like add\_todo,mark\_todo,save\_todo etc.

&#x20;  add\_todo method is called before anything else to make sure the model designs a plan to accomplish the given task and keeps ticking the completed tasks off the list.

* Searching tools - search.py - consists of functions like grep and list\_definitions which are used to search file contents by pattern and get a structural outline of the file without reading it entirely.
* Command Execution tools - exec.py - consists of functions like run\_command and execute\_and\_format which are used to run the commands sent by the agent. In case of any suspicious command,  human approval is sought first.
* File tools - files.py - imported from week\_3/project and consists of functions like read\_file, write\_file, edit\_file etc.



###### ***Safety Rail:***



* All the process happens inside a sandboxed workspace and any attempt to move out of that workspace is blocked by my program.
* Anything potentially harmful or doubtful is not blocked directly- the user is asked to approve or disapprove the exact action. If the user disapproves, 'blocked' status is sent to the agent, which then finds either a workaround or entirely skips that command. This follows from the philosophy of "Gate the action, don't ban the capability."



###### ***Repo used for testing:***	



Pointed it at D:\\target\_repo — a local clone of pallets/flask. Flask is a good target because it has a real test suite, a non-trivial routing system, and enough files that you actually need grep and list\_definitions to find anything.



###### ***Example 1 — Agent Fixed Something and Verified It***



***Task: Add a comment to Flask's request routing code explaining how it works, and confirm the test suite still passes.***



The agent did not know where routing lived. It ran grep "add\_url\_rule" across the repo, got back matches in src/flask/sansio/app.py, then called list\_definitions on that file to see the full structure without reading every line. It found the right method, added a block comment explaining how @app.route becomes a Werkzeug Rule, and then ran:



python -c "import flask; app = flask.Flask(\_\_name\_\_); @app.route('/') 

def index(): return 'OK'; assert app.url\_map.is\_endpoint\_expecting('index')"



Exit code 0. mark\_todo accepted it and moved to the next step. The whole thing — grep, read, edit, verify — happened without the user touching a file.



###### ***Example 2 — Verification Rejected a Deliberately Wrong Test***

***Task: Add a function halve(n) to utils.py. Write a test that expects halve(10) == 4. Mark every step completed when done.***

The agent added halve(n) correctly — it returns n/2, so halve(10) == 5.0. 
The test deliberately expected 4. When the agent called mark_todo("completed") 
for the test step, the system ran pytest tests/test_utils.py automatically. 
Exit code 1. mark_todo returned:

{
  "error": "Verification failed — step NOT marked completed",
  "exit_code": 1
}

The agent could not mark it done. It said:
"I can only mark a step completed if its verification exits with code 0. 
The system rejects the completion."

The step stayed in_progress. The agent had to either fix the test or mark 
it blocked — it could not just claim success.

###### ***What Did Not Work Perfectly***



A few things I noticed during testing:



* The model sometimes refused tasks like "delete all .pyc files" on its own instead of calling run\_command and letting the approval prompt handle it. This is a prompt issue — I updated BASE\_PROMPT to tell the model to always attempt the tool call and let the system decide.
* pip install commands time out at 10 seconds. I set TIMEOUT\_DEFAULT to 30 seconds to avoid obstructions in install commands.
* On the first test run, max\_iterations hit 10 before the agent finished. I increased it to 20.





###### ***Something I would improve given more time:***



The verification system works but it is rigid — every step needs a shell command, which does not always make sense for steps like "read the routing code and understand it." A better design might allow two kinds of verification: a command-based one for code changes and a human-confirmation one for research steps.









&#x20;





















