# **CHATBOT PROJECT DESCRIPTION**



#### **Objectives :** Building a working multi-turn chatbot and 			    understanding each part of it, understanding API 		    calls, API key hygiene, token usage, stateless 		    feature of API etc.





##### ***Foundation :***



I completed build1.py and build2.py on my own, understanding each and every part of it, progressing gradually from single-turn chatbot to multi-turn chatbot, learning on the way how to delete the memory of the chatbot, feeling the loss of context, taking care of API Key hygiene etc.



##### ***Project:***



###### *API Key Hygiene :*

###### 

1. API key is stored in a .env file and loaded using python-dotenv.

2\. The .env file is listed in .gitignore to prevent accidental commits to GitHub. 





###### *Methods used in ChatAgent class :* 



|S.No.|Method|Its function|
|-|-|-|
|1|\_\_init\_\_(model,max\_convos,system\_prompt)|Initializing an agent object under this class using user-defined model and user-defined personality for creating system\_prompt and internally decided max turns limit.|
|2|trim\_history()|It is used only as a backup when the number of turns exceeds the max\_convos limit and summarise\_convo() doesn't generate a summary even after 3 tries.It trims off the oldest pair of chat i.e. the user prompt and AI response pair.This is not a preferable method of adhering to the max\_convo limit because it risks losing some of the context.|
|3|chat(user\_prompt,Models)|This is the method which sends the user\_prompt to the AI model and tries to generate response via streaming , i.e. printing the tokens as they come in, instead of waiting for the message completion.If response is not generated due to RateLimitError then it calls the fall\_back() function to temporarily switch to another model for generating response to that particular query.However if the fall\_back method also fails to generate reponse then it removes the current user\_prompt from chat history since it never received a response.It also has an option to accept two consecutive user prompts if  the user,by some means, manages to send them without having an AI response in between.All the consecutive user prompts are appended to the last user prompt so that the AI doesn't hallucinate or behave weirdly.|
|4|reset()|Used to erase the chat history by sending a fresh messages list to the AI model consisting of only the system prompt.|
|5|summarise\_convo()|Used to summarise the conversation done till now. It prompts the AI to summarise the conversation so far into a single message consisting of 3-5 bullet points while capturing all the key points and replaces the entire chat history with this summary.|
|6|manage\_convo()|This method is called after every prompt is given to the AI to capture the max\_convos limit overflow.As soon as the limit is hit, this method calls the summarise\_convo() method to summarise the conversation and free up space. However if even after 3 tries, this doesn't work then it calls the trim\_history() method as discussed above , which trims off the oldest chat pair.|
|7|show\_usage()|This method is  used to show the current usage of tokens i.e. tokens used by user prompt, tokens used by AI response and total used tokens.|
|8|fall\_back(curr\_model,Models,used\_models)|This is called by the chat() method if the current model is not able to generate response even after 3 tries due to RateLimitError. This method uses all the other available models to generate a response via streaming. It is a recursive function which updates the used\_models list everytime until it uses up all the models or generates a response successfully. If a response is generated the recursion stops else the user is informed that all the models have been exhausted temporarily.|





###### *Functions used outside the ChatAgent Class :* 



|S.No.|Function|Its Usage|
|-|-|-|
|1|pick\_model(Models)|Allows the user to choose a model out of the available Models dictionary.Prompts the user to choose a valid model until he chooses one.|
|2|pick\_personality(Personalities)|Allows the user to choose a personality out of the available Personalities dictionary. Prompts the user to choose a valid personality until he chooses one.|
|3|main()|This function handles the user inputs. It calls pick\_model() and pick\_personality() and creates a custom agent object under ChatAgent class using the given model and personality. It provide a menu of special commands to the user and takes the prompts and commands from the user and acts accordingly.|





###### *Special Commands allowed for the user :* 



|S.No.|Commands|Its usage|
|-|-|-|
|1|/reset|Calls the reset() method of the ChatAgent class.|
|2|/tokens|Calls the show\_usage() method of the ChatAgent class.|
|3|/compact|Calls the summarise\_convo() method of the ChatAgent class.|
|4|/exit|Exits the conversation loop.|





##### ***Higher Order Thinking Questions :*** 



**Question 1 - Every call is a clean slate. The model has no memory between requests. The only "memory" it has is what you pass in the messages list. What happens when that list gets too long?**



**Answer -** When the messages list gets too long, the responses are delayed because the AI has to re-read the entire list every time we make a call. It might hallucinate or behave weirdly , so in my program I have put a limit over the maximum no. of turns, after which the program automatically summarises the chat history, thereby maintaining context as well as max no. of turns limit.Also, if the list exceeds the model's context window limit, the API will throw an error.



**Question 2 - Token budgets are real. Check response.usage. How many tokens did that call cost? What's your strategy when conversation history approaches the model's context limit — truncate, summarise, or drop the oldest turns?**



**Answer -** In my build1 test, a simple question cost 29 prompt tokens + 31 completion tokens = 60 total tokens at zero cost using a free model.

When the conversation hits max\_convos turns, I first attempt to summarise the entire history into 3-5 bullet points using the model itself and replace the history with that summary. This preserves context while adhering to the model's context limit. If summarisation fails due to a rate limit error, I fall back to trimming the oldest user-assistant pair. This way context is never lost unnecessarily — summarisation is always tried first, trimming is only the last resort.



**Question 3 - Role integrity matters. The API expects user and assistant turns to alternate after the system message. What happens if you send two user turns in a row? Try it and find out.**



**Answer -** Through my program, two consecutive user inputs are never possible because if a user prompt fails to generate a response, that prompt itself is deleted from the chat history, so another prompt sent will be a fresh prompt. For testing, I had hardcoded two prompts and given them to the model without using the input() function. But it turned out that the model first took one query, responded to it, then took the second query and responded to it.  Even if somehow, the user manages to send two consecutive prompts via a script, the program appends all the consecutive prompts into a single prompt which is sent to the model. This is done so that the model doesn't hallucinate or behave weirdly by receiving consecutive user prompts.



**Question 4 - Context is not free. Every token you send in history costs latency (and eventually money). What would a good eviction policy look like?**



**Answer -** A good eviction policy would prioritise which messages to keep and which to not keep.The priority order is as follows:

1. The most efficient way is to summarise the chat history and store it as a single message for future use.This is done using the summarise\_convo() method.
2. The fallback option for the summarise\_convo() method is the trim\_history() method, which trims off the oldest user-assistant chat pair. The oldest pair is chosen because it is the least risky pair to remove.
3. The system\_prompt must never be removed, because it decides the personality for our model, which is explicitly defined by the user. Meddling with it will result in loss of memory of the model of who it is supposed to be.







#### **Learnings :**



###### Before this week, I had no idea how chatbots actually work under the hood. Building this from scratch taught me that the API remembers absolutely nothing between calls — I have to manually send the entire conversation history every single time. I felt this firsthand when I wiped the history mid-conversation and the model had no clue what we'd been talking about. I also learned to never hardcode API keys, how tokens are counted, and how conversations are structured as role-tagged messages.

###### 

