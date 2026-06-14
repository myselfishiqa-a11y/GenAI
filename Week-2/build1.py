import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client=OpenAI(base_url="https://openrouter.ai/api/v1",api_key=os.environ["OPENROUTER_API_KEY"])

MODEL="google/gemma-4-31b-it:free"

SYSTEM_PROMPT="""You are a helpful file assistant with access to the following tools:

- read_file(path: str): reads a file from disk and returns its content
- write_file(path: str,content: str): writes content to a file on disk

When you need to use a tool, emit EXACTLY this format and nothing else after it:

<tool_call>
{"name": "TOOL_NAME", "arguments": {"arg1": "value1"}}
</tool_call>

After you receive the tool result in a <tool_response> block, continue your response
normally. Do not emit a tool_call and prose in the same turn. Pick one or the other.
"""

def read_file(path: str) -> dict:

    try:
        with open(path,'r') as handle:
            return {"content":handle.read(),"path":path}
    
    except FileNotFoundError as e:
        return{"error":str(e)}
    
    except OSError as e:
        return{"error":str(e)}
    

def write_file(path:str,content:str) -> dict:
  
    try:
        with open(path,'w',encoding="utf-8") as handle:
            handle.write(content)
        
        return {"success":True,"path":path,"bytes_written":len(content.encode("utf-8"))}
    
    except OSError as e:
        return {"error":str(e)}
    

def parse_tool_call(response_text:str) -> dict | None:

    match=re.search(r"<tool_call>(.*?)</tool_call>",response_text,re.DOTALL)
    if not match:
        return None
    body=match.group(1).strip()
    return json.loads(body)


def strip_tool_call(response_text:str) -> str:

    return re.sub(r"<tool_call>.*?</tool_call>","",response_text,flags=re.DOTALL).strip()


TOOL_REGISTRY={"read_file":read_file,"write_file":write_file}

def dispatch(name:str,arguments:dict) -> str:

    try:
        tool=TOOL_REGISTRY[name]        
    except KeyError:
        return json.dumps({"error":f"Unknown tool: {name}"})
    
    try:
        result=tool(**arguments)
        return json.dumps(result)
        
    except Exception as e:
        return json.dumps({"error":str(e)})
    

#AGENT LOOP


MAX_ITERATIONS=6

def run_agent(user_message:str) -> str:

    messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":user_message}]

    for iteration in range(MAX_ITERATIONS):
        response=client.chat.completions.create(model=MODEL,messages=messages)
        reply=response.choices[0].message.content
        tool_call=parse_tool_call(reply)
    
        if (tool_call==None):
            return reply
        
        prose=strip_tool_call(reply)
        print(prose)
        print()
        messages.append({"role":"assistant","content":prose})
        tool_response=dispatch(tool_call["name"],tool_call["arguments"])
        block=f"<tool_response>\n{tool_response}\n</tool_response>"
        messages.append({"role":"user","content":block})

    return f"[Agent stopped after {MAX_ITERATIONS} iterations]"


#Entry Point


if (__name__=="__main__"):

    #Sample file for the agent to work with
    with open("sample.txt", "w") as f:
        f.write("IIT Delhi was established in 1961. It is one of the premier engineering institutions in India.\n")
        f.write("The campus spans 325 acres in Hauz Khas, New Delhi.\n")

    test_queries = ["Read sample.txt and summarise what it says.",
                    "Read sample.txt and write a one-sentence version of its content to " \
                    "summary.txt."]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        result = run_agent(query)
        print(f"Answer: {result}")
    