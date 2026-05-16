import httpx

from app.config import get_settings


def tavily_search(query: str) -> dict:
    settings = get_settings()
    api_key = settings.TAVILY_API_KEY.get_secret_value()
    if api_key.startswith("tvly-replace"):
        return {
            "query": query,
            "stub": True,
            "results": [],
            "message": "Tavily is stubbed because the API key is a placeholder.",
        }

    response = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": api_key, "query": query, "max_results": 5},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
