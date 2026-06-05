import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_API_KEY"])

def call_model(prompt: str) -> str:
    response = client.chat.completions.create(model="openrouter/free",
                #adding system prompt
        messages=[{"role" : "system", "content" : "You are a helpful assistant."},
            {"role" : "user", "content" : prompt}])

    #The response object contains a unique id,the model which
    #handled our request,timestamp of when the response was
    #generated,finish reason,token usage etc.

    #print("Full response object:\n", response)          
    #print("\n\n")

    #response.usage contains the tokens used by the user for the
    #prompt as well as the tokens used by the model to generate
    #response

    #print("Usage:\n", response.usage)                   
    #print("\n\n")

    return response.choices[0].message.content

if __name__ == "__main__":
    prompt=input("Enter your prompt for the AI model:")
    print("\nGenerating AI response...\n")
    print(call_model(prompt))