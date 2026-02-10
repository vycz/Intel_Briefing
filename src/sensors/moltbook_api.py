#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Moltbook API Sensor — Agent Ecosystem Feed
从 Moltbook (AI Agent 社交平台) 拉取热门帖子

数据源: https://www.moltbook.com/api/v1/posts
协议: REST API (Bearer Token 认证)
更新频率: 实时
质量门槛: votes >= 3
"""

import os
import json
import urllib.request
import ssl
from dataclasses import dataclass
from typing import List


API_BASE = "https://www.moltbook.com/api/v1"
FETCH_TIMEOUT = 15
MIN_VOTES = 3  # 质量门槛：过滤低质量帖子


@dataclass
class MoltbookPost:
    """A Moltbook hot post."""
    title: str
    url: str
    votes: int
    comments: int = 0
    submolt: str = ""
    author: str = ""
    time: str = ""
    content_preview: str = ""

    @property
    def heat(self) -> str:
        """Display heat based on votes."""
        if self.votes >= 50:
            return f"🔥🔥 {self.votes} votes"
        elif self.votes >= 10:
            return f"🔥 {self.votes} votes"
        return f"{self.votes} votes"


def _create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_moltbook_hot(limit: int = 10) -> List[MoltbookPost]:
    """
    Fetch hot posts from Moltbook API.

    Requires MOLTBOOK_API_KEY environment variable.
    Falls back gracefully if API is unavailable.

    Args:
        limit: Maximum number of posts to return

    Returns:
        List of MoltbookPost objects, filtered by MIN_VOTES threshold
    """
    api_key = os.environ.get("MOLTBOOK_API_KEY", "")
    if not api_key:
        print("    [WARN] MOLTBOOK_API_KEY not set, skipping Moltbook sensor.")
        return []

    url = f"{API_BASE}/posts?sort=hot&limit={limit * 2}"  # fetch extra for filtering
    print(f"  → Fetching Moltbook hot posts (target {limit})...")

    try:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Intel-Briefing-MoltbookSensor/1.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT, context=_create_ssl_context()) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
    except urllib.error.HTTPError as e:
        print(f"    [ERROR] Moltbook API HTTP {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"    [ERROR] Moltbook API fetch failed: {e}")
        return []

    # Parse response — handle both array and {posts: [...]} formats
    posts_raw = data if isinstance(data, list) else data.get("posts", data.get("data", []))
    if not isinstance(posts_raw, list):
        print(f"    [WARN] Unexpected Moltbook API response format: {type(data)}")
        return []

    posts = []
    for item in posts_raw:
        try:
            upvotes = int(item.get("upvotes", 0))
            downvotes = int(item.get("downvotes", 0))
            net_votes = upvotes - downvotes

            # 质量门槛过滤
            if net_votes < MIN_VOTES:
                continue

            post_id = item.get("id", "")
            post_url = item.get("url", f"https://www.moltbook.com/post/{post_id}")

            title = item.get("title", "").strip()
            if not title:
                # Some posts may not have titles, use content preview
                content = item.get("content", "")
                title = content[:80] + "..." if len(content) > 80 else content
            if not title:
                continue

            posts.append(MoltbookPost(
                title=title,
                url=post_url,
                votes=net_votes,
                comments=int(item.get("comments", item.get("comment_count", 0))),
                submolt=item.get("submolt", "general"),
                author=item.get("author", item.get("agent_name", "Agent")),
                time=item.get("created_at", "")[:16],  # Truncate timestamp
                content_preview=item.get("content", "")[:150],
            ))
        except (ValueError, TypeError) as e:
            print(f"    [WARN] Skipping malformed Moltbook post: {e}")
            continue

    # Sort by votes (descending) and take top N
    posts.sort(key=lambda p: p.votes, reverse=True)
    result = posts[:limit]

    print(f"    Fetched {len(result)} hot posts from Moltbook (filtered from {len(posts_raw)} raw)")
    return result


# CLI test
if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    posts = fetch_moltbook_hot(limit)
    print(f"\n{'='*60}")
    print(f"  🤖 Moltbook Hot Top {limit}")
    print(f"{'='*60}\n")
    if not posts:
        print("  No posts fetched. Check MOLTBOOK_API_KEY env var.")
    for i, p in enumerate(posts, 1):
        print(f"{i}. {p.title}")
        print(f"   📊 {p.heat} | 💬 {p.comments} comments | 📁 m/{p.submolt}")
        print(f"   🤖 {p.author}")
        print(f"   🔗 {p.url}")
        print()
