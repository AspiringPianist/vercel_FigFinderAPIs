from tavily import TavilyClient
import os

TAVILY_API_KEY = "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"

def get_tavily_search_results(query):
    client = TavilyClient(api_key=TAVILY_API_KEY)
    
    try:
        search_results = client.search(query, search_depth="advanced")
        return search_results["results"]
    except Exception as e:
        print(f"An error occurred while fetching search results: {e}")
        return None