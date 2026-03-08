# serp_search.py
import os
from serpapi.google_search import GoogleSearch

def search_company(company_name):
    params = {
        "q": f"{company_name} company overview executives strategy",
        "api_key": os.getenv("SERPAPI_KEY"),
        "num": 10
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    urls = []
    for r in results.get("organic_results", []):
        urls.append({
            "title": r.get("title"),
            "link": r.get("link"),
            "snippet": r.get("snippet")
        })
    return urls