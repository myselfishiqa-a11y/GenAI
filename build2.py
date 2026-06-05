import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_API_KEY"])

def run_chatbot():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    last_usage = None
    print("\nChat started. Use the following commands for special functions:\n" \
    "1.exit/quit - Quitting the chat\n2./reset - Erasing the " \
    "context (memory of the model)\n3./tokens - Getting the " \
    "total count of tokens used till now.\nType your prompt " \
    "below:\n")

    while True:
        user_input = input("[YOU] : ").strip()

        if (user_input.lower()=='exit' or 
            user_input.lower()=='quit'):
            print("Goodbye!")
            break
        elif (user_input == "/reset"):
            messages = [{"role" : "system", "content" : "You are a helpful assistant."}]
            print("\nHistory cleared.\n")
            continue
        elif (user_input == "/tokens"):
            print(f"Last usage :\n{last_usage}\n")
            continue

        messages.append({"role" : "user", "content" : user_input})

        response = client.chat.completions.create(
            model="z-ai/glm-4.5-air:free",
            messages=messages,
        )

        last_usage = response.usage
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        print(f"[MODEL] : {reply}\n")

if __name__ == "__main__":
    run_chatbot()