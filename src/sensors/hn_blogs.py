#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HN Top Blogs Sensor
从 OPML 列表抓取 HN 社区精选技术博客 RSS

数据源: https://gist.github.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b
协议: RSS/Atom (公开、免费、合法)
"""

import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import ssl
import socket

# 全局 TCP 超时：防 CF 盾/Tarpit 无限挂起 GitHub Actions
socket.setdefaulttimeout(15.0)

# OPML Source
OPML_URL = "https://gist.githubusercontent.com/emschwartz/e6d2bf860ccc367fe37ff953ba6de66b/raw/hn-popular-blogs-2025.opml"

# Fallback feeds if OPML fails
FALLBACK_FEEDS = [
    {"title": "Simon Willison", "rss": "https://simonwillison.net/atom/everything/", "html": "https://simonwillison.net"},
    {"title": "Mitchell Hashimoto", "rss": "https://mitchellh.com/feed.xml", "html": "https://mitchellh.com"},
    {"title": "antirez", "rss": "http://antirez.com/rss", "html": "http://antirez.com"},
    {"title": "Paul Graham", "rss": "http://www.aaronsw.com/2002/feeds/pgessays.rss", "html": "http://paulgraham.com"},
    {"title": "Pluralistic", "rss": "https://pluralistic.net/feed/", "html": "https://pluralistic.net"},
]

# Newsletter feeds — 保证每次跑批都抓取（不依赖 OPML 是否包含）
# 2026-04-22: 新增 AI 公司官方博客 + 高价值 Newsletter，填补 AI 情报盲区
NEWSLETTER_FEEDS = [
    {"title": "Latent Space", "rss": "https://www.latent.space/feed", "html": "https://www.latent.space"},
    {"title": "Ahead of AI", "rss": "https://magazine.sebastianraschka.com/feed", "html": "https://magazine.sebastianraschka.com"},
    # --- AI Company Official Blogs ---
    {"title": "OpenAI Blog", "rss": "https://openai.com/news/rss.xml", "html": "https://openai.com/news"},
    {"title": "Google DeepMind", "rss": "https://deepmind.google/blog/rss.xml", "html": "https://deepmind.google"},
    {"title": "Anthropic News", "rss": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "html": "https://www.anthropic.com/news"},
    {"title": "Anthropic Engineering", "rss": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_engineering.xml", "html": "https://www.anthropic.com/engineering"},
    {"title": "Cloudflare Blog", "rss": "https://blog.cloudflare.com/rss", "html": "https://blog.cloudflare.com"},
    {"title": "GitHub Blog", "rss": "https://github.blog/feed/", "html": "https://github.blog"},
    # --- High-Value Newsletters ---
    {"title": "ByteByteGo", "rss": "https://blog.bytebytego.com/feed", "html": "https://blog.bytebytego.com"},
    {"title": "Last Week in AI", "rss": "https://lastweekin.ai/feed/", "html": "https://lastweekin.ai"},
]

# Config
FETCH_TIMEOUT = 10
MAX_BLOGS_TO_FETCH = 20  # Only fetch from top N blogs for speed
MAX_ARTICLES_PER_BLOG = 2


@dataclass
class BlogArticle:
    """Represents a blog article from HN Top Blogs."""
    title: str
    url: str
    source: str
    pub_date: str = ""
    content: str = ""  # Article description/summary from RSS
    author: str = ""   # Real author from dc:creator/author tag


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from text."""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    clean = clean.replace('&quot;', '"').replace('&#39;', "'")
    clean = clean.replace('&nbsp;', ' ')
    # Clean up whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def _create_ssl_context():
    """Create SSL context with proper certificate verification."""
    return ssl.create_default_context()


def _fetch_url(url: str, timeout: int = FETCH_TIMEOUT) -> Optional[str]:
    """Fetch URL content with timeout and error handling."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; 7Brief/1.0; +https://7brief.com)"
        })
        with urllib.request.urlopen(req, timeout=timeout, context=_create_ssl_context()) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"    [WARN] Failed to fetch {url[:50]}...: {e}")
        return None


def parse_opml(opml_content: str) -> List[dict]:
    """Parse OPML content to extract blog feeds."""
    blogs = []
    # Match <outline type="rss" ... />
    pattern = r'<outline[^>]+type="rss"[^>]*>'
    for match in re.finditer(pattern, opml_content):
        outline = match.group(0)
        text_match = re.search(r'text="([^"]+)"', outline)
        xml_url_match = re.search(r'xmlUrl="([^"]+)"', outline)
        html_url_match = re.search(r'htmlUrl="([^"]+)"', outline)
        
        if text_match and xml_url_match:
            blogs.append({
                "title": text_match.group(1),
                "rss": xml_url_match.group(1),
                "html": html_url_match.group(1) if html_url_match else ""
            })
    return blogs


def _extract_author(entry, ns=None) -> str:
    """Extract author from RSS/Atom entry with type-safe fallback chain."""
    raw = None
    if ns:
        # Atom: <atom:author><atom:name>
        author_el = entry.find('atom:author/atom:name', ns)
        if author_el is None:
            author_el = entry.find('atom:author', ns)
        if author_el is not None and author_el.text:
            raw = author_el.text
    if raw is None:
        # RSS 2.0: <dc:creator> or <author>
        dc_ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
        creator = entry.find('dc:creator', dc_ns)
        if creator is None:
            creator = entry.find('author')
        if creator is not None and creator.text:
            raw = creator.text
    if raw is None:
        return ""
    # Sanitize: unescape HTML entities, strip control chars, truncate
    safe = html.unescape(str(raw)).replace('\n', ' ').replace('\r', '').strip()
    return safe[:40]


def _first(*elements):
    """Return the first non-None element.

    ElementTree Elements with no children are falsy, so plain ``a or b``
    chains silently skip valid leaf elements (e.g. <title>text</title>).
    """
    for el in elements:
        if el is not None:
            return el
    return None


def parse_rss_feed(feed_content: str, source_title: str) -> List[BlogArticle]:
    """Parse RSS/Atom feed content to extract articles."""
    articles = []
    try:
        root = ET.fromstring(feed_content)
        
        # Handle Atom feeds
        if 'atom' in root.tag.lower() or root.tag == '{http://www.w3.org/2005/Atom}feed':
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('.//atom:entry', ns) or root.findall('.//entry')
            for entry in entries[:MAX_ARTICLES_PER_BLOG]:
                title = _first(entry.find('atom:title', ns), entry.find('title'))
                link = _first(entry.find('atom:link[@rel="alternate"]', ns), entry.find('atom:link', ns), entry.find('link'))
                published = _first(entry.find('atom:published', ns), entry.find('atom:updated', ns), entry.find('published'), entry.find('updated'))
                # Extract content/summary for Atom feeds
                summary = _first(entry.find('atom:summary', ns), entry.find('atom:content', ns), entry.find('summary'), entry.find('content'))
                
                title_text = title.text if title is not None and title.text else "Untitled"
                link_href = link.get('href', '') if link is not None else ""
                pub_text = published.text[:10] if published is not None and published.text else ""
                content_text = _strip_html(summary.text) if summary is not None and summary.text else ""
                author_text = _extract_author(entry, ns)
                
                if title_text and link_href:
                    articles.append(BlogArticle(
                        title=title_text,
                        url=link_href,
                        source=source_title,
                        pub_date=pub_text,
                        content=content_text,
                        author=author_text
                    ))
        
        # Handle RSS 2.0 feeds
        else:
            items = root.findall('.//item')
            for item in items[:MAX_ARTICLES_PER_BLOG]:
                title = item.find('title')
                link = item.find('link')
                pub_date = item.find('pubDate')
                # Extract description for RSS 2.0 feeds
                description = item.find('description')
                
                title_text = title.text if title is not None and title.text else "Untitled"
                link_text = link.text if link is not None and link.text else ""
                pub_text = pub_date.text[:16] if pub_date is not None and pub_date.text else ""
                content_text = _strip_html(description.text) if description is not None and description.text else ""
                author_text = _extract_author(item)
                
                if title_text and link_text:
                    articles.append(BlogArticle(
                        title=title_text,
                        url=link_text,
                        source=source_title,
                        pub_date=pub_text,
                        content=content_text,
                        author=author_text
                    ))
    except ET.ParseError as e:
        print(f"    [WARN] XML parse error for {source_title}: {e}")
    except Exception as e:
        print(f"    [WARN] Error parsing feed from {source_title}: {e}")
    
    return articles


def fetch_hn_blogs(limit: int = 5) -> List[BlogArticle]:
    """
    Fetch latest articles from HN Top Blogs OPML.
    
    Args:
        limit: Maximum number of articles to return
        
    Returns:
        List of BlogArticle objects, sorted by recency
    """
    print(f"[*] Fetching HN Top Blogs (OPML)...")
    
    # 1. Fetch OPML
    opml_content = _fetch_url(OPML_URL)
    if opml_content:
        blogs = parse_opml(opml_content)
        print(f"    Found {len(blogs)} blogs in OPML")
    else:
        print("    [WARN] OPML fetch failed, using fallback feeds")
        blogs = FALLBACK_FEEDS
    
    if not blogs:
        print("    [ERROR] No blogs available")
        return []
    
    # 1.5. Identify newsletter feeds already in OPML (for dedup)
    existing_rss = {b["rss"] for b in blogs}
    newsletters_to_fetch = [nf for nf in NEWSLETTER_FEEDS if nf["rss"] not in existing_rss]
    for nf in newsletters_to_fetch:
        print(f"    [+] Newsletter queued: {nf['title']}")
    
    # 2. Fetch RSS from top N OPML blogs
    all_articles = []
    blogs_to_fetch = blogs[:MAX_BLOGS_TO_FETCH]
    
    for i, blog in enumerate(blogs_to_fetch):
        try:
            feed_content = _fetch_url(blog["rss"])
            if feed_content:
                articles = parse_rss_feed(feed_content, blog["title"])
                all_articles.extend(articles)
                if articles:
                    print(f"    [{i+1}/{len(blogs_to_fetch)}] {blog['title']}: {len(articles)} articles")
            else:
                print(f"    [{i+1}/{len(blogs_to_fetch)}] {blog['title']}: failed")
        except Exception as e:
            print(f"    [{i+1}/{len(blogs_to_fetch)}] {blog['title']}: ERROR {e}")
    
    # 2.5. Fetch newsletter feeds (guaranteed, outside top-N limit)
    for nf in newsletters_to_fetch:
        try:
            feed_content = _fetch_url(nf["rss"])
            if feed_content:
                articles = parse_rss_feed(feed_content, nf["title"])
                all_articles.extend(articles)
                print(f"    [NL] {nf['title']}: {len(articles)} articles")
            else:
                print(f"    [NL] {nf['title']}: failed")
        except Exception as e:
            print(f"    [NL] {nf['title']}: ERROR {e}")
    
    # 3. Sort by date and return top N
    # Note: Date parsing is best-effort (supports ISO 8601 + RFC822)
    def parse_date(article):
        if not article.pub_date:
            return datetime.min
        # Try ISO 8601 first (Atom feeds)
        try:
            return datetime.fromisoformat(article.pub_date.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
        # Try RFC822 (RSS 2.0 feeds like OpenAI, Cloudflare, GitHub)
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(article.pub_date)
        except Exception:
            pass
        return datetime.min
    
    all_articles.sort(key=parse_date, reverse=True)
    result = all_articles[:limit]
    
    print(f"    Collected {len(result)} articles total")
    return result


# CLI test
if __name__ == "__main__":
    articles = fetch_hn_blogs(limit=5)
    print("\n--- Top 5 HN Blog Articles ---")
    for i, a in enumerate(articles, 1):
        print(f"{i}. [{a.source}] {a.title}")
        print(f"   {a.url}")
        print()
