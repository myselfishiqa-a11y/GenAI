import os
from openai import OpenAI , RateLimitError
import time
from dotenv import load_dotenv

load_dotenv()

class ChatAgent:

    def __init__(self,model,max_convos,system_prompt):
        self.model=model
        self.system_prompt=system_prompt
        self.max_convos=max_convos
        self.last_usage=None
        self.client=OpenAI(base_url="https://openrouter.ai/api/v1",
                    api_key=os.environ["OPENROUTER_API_KEY"])
        self.messages=[{"role":"system","content":system_prompt}]
    

    def trim_history(self):
        #keeps the system message and last max_convos pairs of conversations.
        # 1 pair=1 user prompt+1 model response
        system_msg=self.messages[0]
        conversation=self.messages[1:]
        conversation=conversation[2:]
        
        self.messages=[system_msg]+conversation
        print("\nOldest turn removed!\n")
   

    def chat(self,user_prompt,Models):
        #Guard: if two or more consecutive messages from user,
        #append them all into the last message so that model
        #doesn't hallucinate or behave wierdly
        if (self.messages!=[] and self.messages[-1]["role"]=="user"):
            self.messages[-1]["content"]+=user_prompt
        else:
            self.messages.append({"role":"user","content":user_prompt})
        
        #Retry upto 3 times on rate limit
        for attempt in range(3):
            try:
                response=self.client.chat.completions.create(
                    model=self.model,messages=self.messages,
                    stream=True)
                break

            except RateLimitError:
                wait_time=30*(attempt+1)
                print(f"\nRate limit hit! Retrying after {wait_time}s...\n")
                time.sleep(wait_time)
        else:
            print("\nCouldn't generate response after 3 tries." \
                  "Retrying with a fallback model\n")
            self.fall_back(self.model,Models,[])
            if (self.messages[-1]["role"]!="assistant"): #response not recieved
                self.messages[-1]["content"]=self.messages[-1]["content"].replace(user_prompt,"")
                if (self.messages[-1]["content"]==""):
                    self.messages.pop()
            return
        
        print()
        full_reply=""
        for chunk in response:

            if (chunk.choices):
                token=chunk.choices[0].delta.content
                if (token):
                    print(token,end="",flush=True)
                    full_reply+=token
            
            if (hasattr(chunk,"usage") and chunk.usage):
                self.last_usage=chunk.usage
        print("\n\n")
        self.messages.append({"role":"assistant","content":full_reply})
        return
    

    def reset(self):
        self.messages=[{"role":"system","content":self.system_prompt}]
        self.last_usage=None
        print("\nChat history has been reset!\n")

    def summarise_convo(self):
        system_msg=self.messages[0]
        conversation=self.messages[1:]
        summary_prompt="Summarise the conversation so far in 3" \
        " to 5 lines. Include all the key facts,names and decisions " \
        "so that context remains preserved."
        summary_messages=self.messages+[{"role":"user",
                                    "content":summary_prompt}]
        
        #try to generate summary upto 3 times
        for attempt in range(3):
            try:
                response=self.client.chat.completions.create(
                    model=self.model,messages=summary_messages)
                summary=response.choices[0].message.content
                break

            except RateLimitError:
                wait_time=30*(attempt+1)
                print(f"\nRate limit hit! Retrying after {wait_time}s...\n")
                time.sleep(wait_time)
        
        else:
            print("\nCouldn't summarise after 3 tries.Please try again.\n")
            return
        
        self.messages=[system_msg]+[{"role":"assistant",
        "content":"Conversation summary\n"+summary}]

        print("\nChat history summarised!\n")


    def manage_convo(self):
        if (len(self.messages)>=2*self.max_convos+1):
            print("\nMaximum number of turns limit hit!\n")
            self.summarise_convo()
            if (len(self.messages)>2): #couldn't summmarise
                self.trim_history()


    def show_usage(self):
        if (self.last_usage):
            u=self.last_usage
            print(f"\nTokens used for prompt : {u.prompt_tokens}\n",
                  f"Tokens used for response : {u.completion_tokens}\n",
                  f"Total tokens used : {u.total_tokens}\n")

        else:
            print("\nNo tokens used till now!\n")

    def fall_back(self,curr_model,Models,used_models=[]):

        if (len(used_models)==len(Models)):
            print("No models available for now. Please try again after 1 minute.")
            return
        
        used_models.append(curr_model)
        for model in Models.values():
            if (model not in used_models):
                new_model=model
                break

        for attempt in range(3):


            try:
                response=self.client.chat.completions.create(
                    model=new_model,messages=self.messages,
                    stream=True)
                
                full_reply=""
                for chunk in response:

                    if (chunk.choices):
                        token=chunk.choices[0].delta.content
                        if (token):
                            print(token,end="",flush=True)
                            full_reply+=token
            
                        if (hasattr(chunk,"usage") and chunk.usage):
                            self.last_usage=chunk.usage
                print("\n\n")
                self.messages.append({"role":"assistant","content":full_reply})
                return
            

            except RateLimitError:
                wait_time=30*(attempt+1)
                print("\nRate limit hit! Retrying after" \
                      f"{wait_time}s...\n")
                time.sleep(wait_time)
        

        print("Fallback model failed. Retrying with another" \
               " fallback model...")

        self.fall_back(new_model,Models,used_models)

#MODEL SELECTION

def pick_model(Models):
    
    print("Here is a list of available models:\n")
    for sno,model in Models.items():
        print(f"{sno} : {model}")
    print()

    #Taking model_no as input and validating it
    while True:
        model_no=input("\nPlease choose a model and enter its" \
        " serial number:\n").strip()
        try:
            return Models[model_no]
        except:
            print("\nInvalid model number. Please try again!\n")

def pick_personality(Personalities):
    
    print("\nHere is a list of available personalities:\n")
    for sno,personality in Personalities.items():
        print (f"{sno} : {personality}")
    print()

    #Taking personality_no as input and validating it
    while True:
        personality_no=input("\nPlease choose a personality and " \
        "enter its serial number:\n").strip()
        try:
            return (Personalities[personality_no])
        except:
            print("\nInvalid personality number.Please try again.\n")


def main():
    print("\n\t\tWelcome To ChatAgent!!\n\n\tInteract with a " \
          "chatbot designed by you,for you!\n")

    Models={"1": "openai/gpt-oss-20b:free",
            "2": "openai/gpt-oss-120b:free",
            "3": "z-ai/glm-4.5-air:free",
            "4": "google/gemma-4-31b-it:free",
            "5": "openrouter/owl-alpha"}
    
    model=pick_model(Models)

    Personalities={"1":"Helpful","2":"Funny","3":"Friendly",
                    "4":"Sarcastic","5":"Educator","6":"Poetic",
                    "7":"Talkative"}
    
    personality=pick_personality(Personalities)
    personality_prompt="You are a "+personality+" assistant."
    agent=ChatAgent(model=model,system_prompt=personality_prompt,
                    max_convos=10)
    
    print(f"Using : {model}\n")

    print("Special Commands :\n")
    print("/tokens - Tells you the number of tokens used till now\n" \
    "/reset - Deletes the chat history i.e. the memory of chatbot\n" \
    "/compact - Summarises the chat history into a single " \
               "message which will be used for further conversation.\n" \
    "/exit - Exits the conversation\n")

    while True:
        prompt=input("\nEnter your prompt or any of the " \
                     "special commands:\n").strip()

        if (prompt=="/tokens"):
            agent.show_usage()

        elif (prompt=="/reset"):
            agent.reset()

        elif (prompt=="/compact"):
            if (len(agent.messages)<=1):
                print("No chat history to summarise!")
            else:
                agent.summarise_convo()

        elif (prompt=="/exit"):
            print("Goodbye!")
            break

        else:
            agent.chat(prompt,Models)
            agent.manage_convo()
       
main()