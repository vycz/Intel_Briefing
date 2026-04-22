"""
Hugging Face Daily Papers Sensor - Fetches community-curated top AI/ML papers.
Uses the HF Daily Papers API (undocumented, no auth required).
Fallback: ArXiv sensor.
"""
import sys
from dataclasses import dataclass
from typing import List

# Force UTF-8 stdout for Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import httpx

# Reuse ArxivPaper dataclass for compatibility
from sensors.arxiv_ai import ArxivPaper

HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"
USER_AGENT = "7Brief-Engine/1.0 (https://github.com/77AutumN/Intel_Briefing)"


def fetch_hf_daily_papers(limit: int = 10) -> List[ArxivPaper]:
    """Fetch today's top AI/ML papers from Hugging Face Daily Papers.
    
    Returns ArxivPaper objects for compatibility with existing pipeline.
    Papers are sorted by community upvotes (descending).
    """
    print(f"  → Fetching top {limit} papers from HF Daily Papers...")
    
    try:
        resp = httpx.get(
            HF_DAILY_PAPERS_URL,
            timeout=20,
            headers={"User-Agent": USER_AGENT}
        )
        
        if resp.status_code != 200:
            print(f"    ⚠ HF Daily Papers API returned {resp.status_code}")
            return []
        
        data = resp.json()
        if not data:
            print("    ⚠ HF Daily Papers returned empty response")
            return []
        
        # Sort by upvotes (community quality signal)
        data.sort(key=lambda x: x.get("paper", {}).get("upvotes", 0), reverse=True)
        
        papers = []
        for item in data[:limit]:
            paper = item.get("paper", {})
            if not paper:
                continue
            
            paper_id = paper.get("id", "")
            title = paper.get("title", "").strip()
            
            if not paper_id or not title:
                continue
            
            # Extract authors (first 3)
            authors = [a.get("name", "") for a in paper.get("authors", [])[:3]]
            # Extract summary
            summary = paper.get("summary", "")
            
            # Build categories from ai_keywords
            keywords = paper.get("ai_keywords", [])
            categories = keywords[:3] if keywords else ["cs.AI"]
            
            # Published date
            published = paper.get("publishedAt", "")[:10]
            
            papers.append(ArxivPaper(
                id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                published=published,
                categories=categories
            ))
        
        if papers:
            print(f"    [OK] Got {len(papers)} papers from HF Daily Papers (sorted by upvotes)")
        else:
            print("    ⚠ HF Daily Papers: no valid papers parsed")
        
        return papers
    
    except Exception as e:
        print(f"    ERROR: HF Daily Papers failed: {e}")
        return []


def print_papers(papers: List[ArxivPaper]):
    """Print papers in a readable format."""
    print(f"\n{'='*60}")
    print(f"  🤗 HF Daily Papers - Top AI/ML Research")
    print(f"{'='*60}\n")
    
    for i, p in enumerate(papers, 1):
        print(f"{i}. {p.title}")
        print(f"   👤 {', '.join(p.authors)}")
        print(f"   📅 {p.published} | 🏷️ {', '.join(p.categories)}")
        print(f"   🔗 {p.url}")
        print()


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    papers = fetch_hf_daily_papers(limit)
    if papers:
        print_papers(papers)
    else:
        print("No papers found.")
