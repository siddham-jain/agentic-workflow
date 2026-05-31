"""Web search tool using the Exa API."""
import os
from typing import Optional
import httpx

__all__ = ["run"]

EXA_API_URL = "https://api.exa.ai/search"


def run(action_input: str) -> str:
    """Search the web using Exa API.
    
    Args:
        action_input: Search query string
        
    Returns:
        Structured search results or error message
    """
    api_key = os.getenv("EXA_API_KEY", "")
    if not api_key:
        return "Error: Exa search unavailable - API key not configured. Set EXA_API_KEY environment variable."
    
    if not action_input or not action_input.strip():
        return "Error: Empty search query provided."
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                EXA_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": action_input,
                    "numResults": 5,
                    "type": "neural",
                },
            )
            
            if response.status_code == 429:
                return "Error: Exa search unavailable - Rate limit exceeded. Try again later."
            
            if response.status_code == 401:
                return "Error: Exa search unavailable - Invalid API key."
            
            if response.status_code != 200:
                return f"Error: Exa search unavailable - HTTP {response.status_code}. Try a different approach."
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return f"No results found for query '{action_input}'."
            
            lines = [f"Found {len(results)} result(s):"]
            for i, result in enumerate(results, 1):
                title = result.get("title", "No title")
                url = result.get("url", "No URL")
                snippet = result.get("text", "")[:300]
                lines.append(f"[{i}] {title} - {url}")
                if snippet:
                    lines.append(f"    Snippet: {snippet}...")
            
            return '\n'.join(lines)
            
    except httpx.TimeoutException:
        return "Error: Exa search unavailable - Request timed out. Try a different approach."
    except httpx.NetworkError:
        return "Error: Exa search unavailable - Network error. Try a different approach."
    except Exception as e:
        return f"Error: Exa search unavailable - {type(e).__name__}: {e}. Try a different approach."
