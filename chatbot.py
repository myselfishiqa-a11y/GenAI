import os
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
import time

load_dotenv()


AVAILABLE_MODELS = {
    "1": "nvidia/nemotron-3-nano-30b-a3b:free",
    "2": "meta-llama/llama-3.3-70b-instruct:free",
    "3": "mistralai/mistral-7b-instruct:free",
    "4": "deepseek/deepseek-chat-v3-0324:free",
}


class ChatAgent:
    def __init__(self,model,max_turns= 10,
        system_prompt= "You are a helpful assistant who gives "\
        "concise answers."):

        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.last_usage = None

        self.client = OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ["OPENROUTER_API_KEY"],)

        # Always starts with the system message
        self.messages = [{"role": "system", "content": system_prompt}]

    #internal helper
    def _trim_history(self):
        """
        Keep only the system message + last max_turns pairs.
        Each pair = 1 user message + 1 assistant message = 2 items.
        """
        system = self.messages[0]           # always preserve
        conversation = self.messages[1:]    # everything after system

        max_messages = self.max_turns * 2   # pairs → individual messages
        if len(conversation) > max_messages:
            conversation = conversation[-max_messages:]

        self.messages = [system] + conversation

    # ── public API ───────────────────────────
    def chat(self, user_input: str) -> str:
        """Send a message and return the assistant's reply."""
        self.messages.append({"role": "user", "content": user_input})
        self._trim_history()

        # Retry up to 3 times on rate limit
        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                )
                break
            except RateLimitError:
                wait = 30 * (attempt + 1)
                print(f"\n⚠  Rate limited. Retrying in {wait}s...")
                time.sleep(wait)
        else:
            return "Error: Could not get a response after 3 retries."

        self.last_usage = response.usage
        reply = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        """Clear conversation history, keeping only the system message."""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.last_usage = None

    def compact(self):
        """
        Summarise the entire conversation history into a single context
        message, then replace history with that summary.
        """
        if len(self.messages) <= 1:
            print("Nothing to compact yet.\n")
            return

        # Ask the model to summarise the conversation so far
        summary_prompt = (
            "Summarise the conversation so far in 3-5 concise bullet points. "
            "Capture key facts, names, and decisions so the context is preserved."
        )
        summary_messages = self.messages + [
            {"role": "user", "content": summary_prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=summary_messages,
            )
            summary = response.choices[0].message.content
        except Exception as e:
            print(f"Compact failed: {e}\n")
            return

        # Replace history with a single context message
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "assistant", "content": f"[Conversation summary]\n{summary}"},
        ]
        print("History compacted into a summary.\n")

    def show_usage(self):
        if self.last_usage:
            u = self.last_usage
            print(
                f"\n📊 Tokens — prompt: {u.prompt_tokens}, "
                f"completion: {u.completion_tokens}, "
                f"total: {u.total_tokens}\n"
            )
        else:
            print("No usage data yet.\n")


# ─────────────────────────────────────────────
#  Model selection helper
# ─────────────────────────────────────────────
def pick_model() -> str:
    print("╔══════════════════════════════════════════╗")
    print("║         Choose a model to chat with      ║")
    print("╠══════════════════════════════════════════╣")
    for key, name in AVAILABLE_MODELS.items():
        print(f"║  {key}. {name[:40]:<40}║")
    print("╚══════════════════════════════════════════╝")

    while True:
        choice = input("Enter number (default 1): ").strip() or "1"
        if choice in AVAILABLE_MODELS:
            return AVAILABLE_MODELS[choice]
        print("Invalid choice, try again.")


# ─────────────────────────────────────────────
#  Main chat loop
# ─────────────────────────────────────────────
def main():
    print("\n🤖  Welcome to ChatAgent\n")
    model = pick_model()

    agent = ChatAgent(
        model=model,
        system_prompt="You are a helpful, friendly assistant.",
        max_turns=10,       # keeps last 10 conversation pairs
    )

    print(f"\nUsing: {model}")
    print("Commands: /reset  /compact  /tokens  exit\n")

    while True:
        user_input = input("[YOU] ").strip()

        if not user_input:
            continue
        elif user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break
        elif user_input == "/reset":
            agent.reset()
            print("History cleared.\n")
        elif user_input == "/compact":
            agent.compact()
        elif user_input == "/tokens":
            agent.show_usage()
        else:
            reply = agent.chat(user_input)
            print(f"[MODEL] {reply}\n")


if __name__ == "__main__":
    main()