import requests

HF_BASE = "https://huggingface.co"
MAX_READ_CHARS = 12000


def paper_search(query: str, limit: int = 5) -> list[dict]:
    """Search papers on HuggingFace Papers."""

    url = f"{HF_BASE}/api/papers/search"
    try:
        response = requests.get(url,params={"q": query,"limit": limit})

        response.raise_for_status()

        data = response.json()

        results = []

        for item in data:

            paper = item.get("paper", item)

            results.append({"title": paper.get("title",""),"id": paper.get("id",""),
                            "snippet": paper.get("summary", "")[:300]})

        return results
    
    except Exception as e:
        return [{"error":str(e)}]


def read_paper(paper_id: str) -> dict:
    """Read a paper's metadata and content."""

    paper_id = (paper_id.replace("https://arxiv.org/abs/", "").replace("http://arxiv.org/abs/", "").strip())
    
    meta_url = f"{HF_BASE}/api/papers/{paper_id}"
    
    meta_resp = requests.get(meta_url)

    if meta_resp.status_code == 404:
        return {"error": "Paper not indexed on HF"}

    meta_resp.raise_for_status()

    metadata = meta_resp.json()

    md_url = f"{HF_BASE}/papers/{paper_id}.md"

    md_resp = requests.get(md_url)

    content = ""

    if md_resp.status_code == 200:
        content = md_resp.text[:MAX_READ_CHARS]

    return {"title": metadata.get("title",""),"authors": metadata.get("authors",""),"abstract": metadata.get("summary",""),"content": content}
