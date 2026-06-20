import os
import requests
import re
import trafilatura
from markdownify import markdownify
from urllib.parse import parse_qs , urlparse

SERPER_API_KEY=os.environ["SERPER_API_KEY"]
MAX_READ_CHARS = 12000


def web_search(query:str,num_results:int=5) -> list[dict]:

    try:
        response=requests.post("https://google.serper.dev/search",headers={"X-API-KEY":SERPER_API_KEY,
                                "Content-Type":"application/json"},json={"q":query,"num":num_results}
                                ,timeout=10)
        
        response.raise_for_status()
        data=response.json()
        results=[]

        for item in data.get("organic",[]):
            results.append({"title":item.get("title",""),"link":item.get("link",""),"snippet":item.get("snippet","")})
        
        return results
    
    except Exception as e:
        return [{"error":str(e),"title":"","link":"","snippet":""}]


def web_fetch(url:str) -> str:

    headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}

    try:
        response=requests.get(url,headers=headers,allow_redirects=True,timeout=10)

        response.raise_for_status()
        return response.text
    
    except requests.exceptions.HTTPError as e:
        return (f"Error : Page not found or access denied - {e}")
    
    except requests.exceptions.Timeout:
        return("Error : Request timed out")
    
    except requests.exceptions.ConnectionError:
        return("Error : Couldn't connect to the URL")
    

def fetch_clean(url:str) -> str:
    html=web_fetch(url)
    if (html.startswith("Error")):
        return html
    
    text=trafilatura.extract(html,include_comments=False,include_tables=True)
    if text:
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text
    
    cleaned = markdownify(html, heading_style="ATX",strip=["script", "style", "nav", "footer"])
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned


def fetch_for_agent(url: str) -> str:
    content = fetch_clean(url)
    if len(content) > MAX_READ_CHARS:
        content = content[:MAX_READ_CHARS] + "\n\n[...truncated]"
    return content


def smart_fetch(url: str) -> str:
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    try:
        response = requests.get(f"{base}/llms.txt", timeout=5)
        if response.status_code == 200:
            return f"[llms.txt found]\n\n{response.text}\n\n---\nOriginal URL: {url}"
    except Exception:
        pass
    
    return fetch_for_agent(url)
