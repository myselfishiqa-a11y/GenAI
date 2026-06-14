import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "openrouter/owl-alpha"

# ---------------------------------------------------------------------------
# Tool schemas (the contract between you and the model)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Returns the current weather for a given city. "
                "Call this whenever the user asks about weather, temperature, or climate. "
                "Do not guess weather. Always call this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, e.g. 'Delhi' or 'San Francisco'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit. Default to celsius.",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Evaluates a mathematical expression and returns the result. "
                "Use this for any arithmetic the user asks about. "
                "Pass the expression as a string, e.g. '1337 * 42 + 7'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A Python arithmetic expression, e.g. '100 / 4 + 3'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": (
                "Returns the current time for a given timezone. "
                "Use this whenever the user asks for current time in a place or timezone. "
                "Timezone should be in IANA format like 'Asia/Kolkata'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": (
                            "IANA timezone name such as "
                            "'Asia/Kolkata', 'Europe/London', "
                            "'America/New_York'"
                        ),
                    }
                },
                "required": ["timezone"],
            },
        },
    }
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_weather(city: str, unit: str = "celsius") -> dict:

    WEATHER_DATA = {"delhi":         {"temperature": 38, "condition": "hot and sunny"},
                    "tokyo":         {"temperature": 22, "condition": "partly cloudy"},
                    "london":        {"temperature": 14, "condition": "overcast with drizzle"},
                    "san francisco": {"temperature": 17, "condition": "foggy"},
                    "new york":      {"temperature": 24, "condition": "clear skies"},
                    "dubai":         {"temperature": 42, "condition": "dry and sunny"},
                    "sydney":        {"temperature": 19, "condition": "mild and breezy"}}

    key=city.lower()
    data=WEATHER_DATA.get(key,{"temperature":25,"condition":"clear skies"})

    temp=data["temperature"]
    if (unit=="fahrenheit"):
        temp=(temp*9/5)+32

    return {"city":city,"temperature":temp,"unit":unit,"condition":data["condition"]}

def calculate (expression:str) -> dict:

    SAFE_GLOBALS = {"__builtins__": {},"abs": abs,"round": round,"min": min,"max": max,
                    "pow": pow}
    
    BLOCKED = ["import", "open", "exec", "eval", "__"]

    for pattern in BLOCKED:
        if (pattern in expression):
            return {"error":f"Expression not allowed: '{pattern}' is blocked."}
        
    try:
        result=eval(expression,SAFE_GLOBALS,{})
        return({"result":result})
    
    except  ZeroDivisionError:
        return {"error": "Division by zero"}
    
    except Exception as e:
        return {"error": f"Invalid expression: {e}"}

def get_time(timezone: str) -> dict:

    try:  
    
        current=datetime.now(ZoneInfo(timezone))
        return ({"date":str(current.date()),"time":str(current.time())})
    
    except Exception as e:
        return ({"error":str(e)})


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "get_weather": get_weather,"calculate": calculate,"get_time": get_time}


def dispatch(tool_call) -> str:

    try:
        name=tool_call.function.name                            
        arguments=json.loads(tool_call.function.arguments)      
    except Exception as e:
        return json.dumps({"error":str(e)})
    
    try:
        tool=TOOL_REGISTRY[name]
    except KeyError:
        return json.dumps({"error":f"Unknown tool : {name}"})
    
    try:
        result=tool(**arguments)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error":str(e)})
    
# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 8

def run_agent(user_message: str) -> str:

    messages = [{"role": "system", "content": "You are a helpful assistant. Use tools when appropriate."},
                {"role": "user", "content": user_message}]

    total_tokens=0

    for iteration in range(MAX_ITERATIONS):

        response = client.chat.completions.create(model=MODEL,messages=messages,tools=TOOLS)
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        total_tokens=response.usage.total_tokens

        if (finish_reason=="stop"):
            print(f"Total tokens used are : {total_tokens}")
            return message.content
        
        messages.append(message)

        for tool_call in message.tool_calls:
            result=dispatch(tool_call)
            print(f"[Tool called]: {tool_call.function.name}", file=sys.stderr)
            messages.append({"role": "tool","tool_call_id": tool_call.id,"content": result})
    
    print(f"Total tokens used are : {total_tokens}")
    return f"[Agent stopped after {MAX_ITERATIONS} iterations without a final answer]"

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    test_queries = ["What's the weather in Tokyo?",
                    "Calculate: (2**10) - 1",
                    "What is the current time in Asia/Kolkata?",
                    "Tell me the weather in Delhi and also calculate 451 * 3",
                    "Compare the weather in London and Delhi, tell me the current time in Europe/London, "
                    "and calculate (125 + 375) / 5"]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        result = run_agent(query)
        print(f"\nFinal answer:\n{result}")