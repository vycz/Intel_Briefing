"""
Commercial Agent - GitHub Trending Sensor (GraphQL API Version)

Uses GitHub GraphQL API to find high-potential repositories.
Focuses on "Breakout" repos: created recently with high star velocity.

Dependencies: httpx (or requests)
Usage: python github_trending.py [language]
"""

import os
import sys
import datetime
from dataclasses import dataclass, field
from typing import Optional

# Use unified config layer
try:
    from config import cfg
except ImportError:
    from src.config import cfg

# Use httpx if available, fall back to requests
try:
    import httpx
    HTTP_CLIENT = "httpx"
except ImportError:
    try:
        import requests
        HTTP_CLIENT = "requests"
    except ImportError:
        HTTP_CLIENT = None

GITHUB_API_URL = "https://api.github.com/graphql"

@dataclass
class GitHubTrend:
    """A single trending repository."""
    name: str                   # e.g., "owner/repo"
    url: str
    description: str
    language: Optional[str]
    stars: int
    forks: int
    created_at: str
    pushed_at: str
    readme_text: Optional[str] = None  # Fetched via GraphQL
    hype_score: int = field(init=False)

    def __post_init__(self):
        import math
        self.hype_score = min(100, int(math.log10(max(self.stars, 1)) * 25))

def fetch_trending(language: Optional[str] = None) -> list[GitHubTrend]:
    """
    Fetch trending repositories using GitHub GraphQL API.
    Strategy: Search for repos created in the last 7 days, sorted by stars.
    """
    token = cfg.github_token
    if not token:
        print("ERROR: GITHUB_TOKEN not found in .env or environment variables.")
        return []

    if HTTP_CLIENT is None:
        print("ERROR: No HTTP client available. Install httpx or requests.")
        return []

    # Calculate date 7 days ago
    seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Build Search Query
    # Query: "created:>YYYY-MM-DD sort:stars"
    search_query = f"created:>{seven_days_ago} sort:stars"
    if language:
        search_query += f" language:{language}"

    graphql_query = """
    query($search_query: String!) {
      search(query: $search_query, type: REPOSITORY, first: 10) {
        edges {
          node {
            ... on Repository {
              nameWithOwner
              url
              description
              stargazerCount
              forkCount
              createdAt
              pushedAt
              primaryLanguage {
                name
              }
              object(expression: "HEAD:README.md") {
                ... on Blob {
                  text
                }
              }
            }
          }
        }
      }
    }
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Commercial-Agent-Sensor"
    }

    payload = {
        "query": graphql_query,
        "variables": {"search_query": search_query}
    }
    
    try:
        print(f"  → Sending GraphQL query to GitHub ({search_query})...")
        if HTTP_CLIENT == "httpx":
            response = httpx.post(GITHUB_API_URL, json=payload, headers=headers, timeout=30.0)
        else:
            response = requests.post(GITHUB_API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"ERROR: API returned {response.status_code}")
            print(response.text)
            return []
            
        data = response.json()
        if "errors" in data:
            print(f"ERROR: GraphQL errors: {data['errors']}")
            return []

        return _parse_graphql_response(data)

    except Exception as e:
        print(f"ERROR: Request failed: {e}")
        return []

def _parse_graphql_response(data: dict) -> list[GitHubTrend]:
    trends = []
    edges = data.get("data", {}).get("search", {}).get("edges", [])
    
    for edge in edges:
        node = edge.get("node")
        if not node:
            continue
            
        # Extract README
        readme_obj = node.get("object")
        readme_text = readme_obj.get("text", "") if readme_obj else ""
            
        trends.append(GitHubTrend(
            name=node["nameWithOwner"],
            url=node["url"],
            description=node["description"] or "(No description)",
            language=node["primaryLanguage"]["name"] if node["primaryLanguage"] else None,
            stars=node["stargazerCount"],
            forks=node["forkCount"],
            created_at=node["createdAt"],
            pushed_at=node["pushedAt"],
            readme_text=readme_text[:5000]  # Truncate to save memory/tokens
        ))
        
    return trends

def print_trends(trends: list[GitHubTrend]) -> None:
    print(f"\n{'='*60}")
    print(f" 🚀 Breakout Repos (Last 7 Days) - Top {len(trends)}")
    print(f"{'='*60}\n")

    for i, t in enumerate(trends, 1):
        print(f"{i}. [{t.hype_score:3d}] {t.name}")
        print(f"   ⭐ {t.stars} | 🍴 {t.forks} | Created: {t.created_at[:10]}")
        if t.language:
            print(f"   📝 {t.language}")
        print(f"   {t.description[:100]}...")
        print(f"   🔗 {t.url}")
        print()


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else None
    trends = fetch_trending(lang)
    if trends:
        print_trends(trends)
    else:
        print("No trends found.")
