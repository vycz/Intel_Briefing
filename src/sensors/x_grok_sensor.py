import os
import sys
import datetime
import json
import httpx
from dotenv import load_dotenv

# Force UTF-8 stdout for Windows
sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Configuration
XAI_API_KEY = os.getenv("XAI_API_KEY")
# Default to official endpoint, but allow override for Relay Services (中转站)
XAI_BASE_URL = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1/chat/completions")
MODEL_NAME = os.getenv("XAI_MODEL", "grok-beta")  # Relay users: set to 'grok-3' or 'grok-4'

def fetch_grok_intel(query: str, override_prompt: str = None, timeout: int = 60, plugins: list = None) -> str:
    """
    Fetch intelligence from X using xAI's Grok API.
    Returns the markdown report.
    """
    if not XAI_API_KEY:
        print("❌ Error: XAI_API_KEY not found in .env files.")
        return "Error: No API Key."

    print(f"🦅 Grok Sensor: contacting xAI for '{query}'...")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    year_str = datetime.datetime.now().strftime("%Y")

    if override_prompt:
        system_content = f"You are an specialized Data Analyst. Current Date: {today_str}. Follow the user's instructions strictly."
        user_content = override_prompt
    else:
        system_content = (
            f"You are a Commercial Intelligence Analyst. **CURRENT DATE: {today_str}**. "
            "Your goal is to find high-signal discussions from the **LAST 24 HOURS ONLY**. "
            f"❌ CRITICAL RULE: Do NOT report events from {int(year_str)-2} or {int(year_str)-1} as 'new'. "
            "If the trend is from 2024/2025, explicitly label it as 'Historical Context'. "
            "**IMPORTANT: You must answer in Simplified Chinese (简体中文).**"
        )
        user_content = f"Search X for the latest trends about '{query}' happened in {year_str}. Focus on specific recent events. Reply in Chinese."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}",
        "HTTP-Referer": "https://7brief.com",
        "X-Title": "Intel Briefing Engine"
    }

    # 强制启用 Web Search 插件（无 Web Search 的 Grok 输出 100% 幻觉）
    if not plugins:
        plugins = [{"id": "web"}]
        print("  [!] Web Search 未指定，已自动启用（防幻觉必备）")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system", 
                "content": system_content
            },
            {
                "role": "user", 
                "content": user_content
            }
        ],
        "stream": False,
        "temperature": 0.5,
        "plugins": plugins
    }

    try:
        response = httpx.post(XAI_BASE_URL, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        
        data = response.json()
        content = data['choices'][0]['message']['content']
        
        print("\n" + "="*60)
        print(f"  🦅 Grok Intelligence Report: {query}")
        print("="*60 + "\n")
        print(content)
        
        return content
        
    except httpx.HTTPStatusError as e:
        err = f"⚠️ API Error: {e.response.status_code} - {e.response.text}"
        print(err)
        return err
    except Exception as e:
        err = f"⚠️ Connection Error: {e}"
        print(err)
        return err

def fetch_horizon_scan(
    focus: str = "AI, technology breakthroughs, stealth startups, geopolitics, energy",
    timeframe: str = "last 48 hours"
) -> str:
    """
    使用 GROK HORIZON EXPANDER 5步协议对 X 进行深度情报扫描。
    专为 7Brief HUNT 行动系统定制。
    比 fetch_grok_intel() 的默认 prompt 质量高 10 倍。
    """

    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    horizon_prompt = f"""You are a Senior Frontier Intelligence Analyst for 7Brief, an elite technology intelligence service. Your mandate is to surface high-signal, under-reported developments that mainstream media has not yet covered, and deliver them as a structured, decision-ready briefing.

## Mission Parameters
- Current Date: {today_str}
- Scan Window: {timeframe}
- Focus Domains: {focus}
- Output Language: Simplified Chinese (简体中文). Keep English only for proper nouns, @handles, URLs, and technical terms.

## Search Methodology (CRITICAL)
- Use parallel search across X and the web to find diverse sources representing multiple viewpoints.
- Cross-reference every claim with primary sources: research papers, GitHub repos, official announcements, SEC filings, patent databases.
- Assume that subjective viewpoints from mainstream media may carry bias. Prioritize firsthand accounts from researchers, founders, and engineers over journalist summaries.
- Mark evidence quality: use [VERIFIED] for claims you confirmed via browsing the source, [UNVERIFIED] for claims based only on social posts without primary source confirmation.
- ABSOLUTE RULE: Report fewer real, verified signals rather than fabricating or guessing any. If you find only 3 high-quality signals, report 3. Never invent usernames, links, or engagement metrics.

## ⛔ ANTI-FABRICATION RULES (SYSTEM ENFORCED)
Your output will be processed by an automated verification pipeline. The following violations will cause your entire report to be DISCARDED:
1. **NEVER use placeholder links** like `x.com/user123/status/...`, `github.com/example/repo`, or `arxiv.org/abs/0000.00000`. If you cannot find a real URL, write `[NO SOURCE FOUND]` instead.
2. **NEVER fabricate @usernames**. Only cite real accounts you found via search. If unsure, omit the username.
3. **NEVER use phrases like** "假设链接", "hypothetical", "fictional", "placeholder", "示例", "for illustration" to describe any link, username, or data point. Any paragraph containing such phrases will be automatically deleted by our pipeline.
4. **NEVER invent engagement metrics** (likes, reposts, views). If metrics are unavailable, state "engagement data unavailable" instead of guessing.
5. **Prefer fewer real sources over many fake ones.** A report with 3 verified signals is infinitely more valuable than one with 10 fabricated signals.

## 5-Step Analytical Protocol

### Step 1: Signal Sweep
Conduct parallel searches on X and the web for the most significant recent developments within the focus domains and scan window. Targets:
- Viral X posts (high likes/reposts) from domain experts, not influencers
- GitHub repos with sudden star surges
- Pre-print papers (arXiv, bioRxiv) generating discussion
- Stealth startup launches, funding rounds, or talent movements
- Regulatory shifts, patent filings, or policy proposals
Identify 8-12 raw signals with high engagement but limited mainstream media coverage (not yet on CNN, BBC, Reuters, Bloomberg front pages).

### Step 2: Noise Filter
Ruthlessly eliminate:
- Celebrity gossip, political theater, culture war bait
- Crypto/token pump schemes without technological substance
- Recycled news from >72 hours ago repackaged as "breaking"
- Vague hype with no verifiable evidence ("AI will change everything")
Retain only signals with genuine potential for long-term, second-order effects on technology, energy, biology, space, economic structure, or power dynamics. Narrow to the top 4-6 highest-quality signals.

### Step 3: Deep Analysis
For each surviving signal, provide:
- **Core Development**: Plain-language summary in 2-3 sentences
- **Primary Evidence**: Cite real X posts with @username and timestamp (format: @user, YYYY-MM-DD HH:MM UTC), or link to real papers/repos/announcements. Tag each as [VERIFIED] or [UNVERIFIED]. If no real source can be found, use `[NO SOURCE FOUND]`.
- **Why Underreported**: Explain specifically why mainstream outlets have not covered this
- **Second-Order Implications**: What paradigm shift, power redistribution, or structural change could this trigger in 6-24 months?
- **Impact Probability**: Your estimated probability (%) of major long-term impact, with 1-sentence justification based on historical precedent or structural analysis

### Step 4: Cross-Signal Synthesis
- **Convergence Pattern**: What meta-trend connects these top signals? Name it.
- **Challenged Assumption**: What widely-held belief are these signals quietly invalidating?
- **Non-Obvious Insight**: One key observation that a Wall Street analyst, venture capitalist, or policy maker would find valuable but most observers would miss.

### Step 5: HUNT Action Tags
Provide exactly 4 recommendations using these exact label formats:
- **[LEARN 学习]:** One specific concept, technology, or framework the reader should deep-dive into this week, with a concrete starting resource (paper, repo, course)
- **[CREATE 创作]:** One content piece, product feature, or creative opportunity that emerges from these signals — be specific about format and audience
- **[ARB 套利]:** One actionable market, attention, or tooling arbitrage opportunity — include timing window and entry point
- **[ON HOLD 略过]:** One currently hyped signal that is actually noise — explain why it should be ignored and what to watch instead

## Output Format
- Use clean Markdown with ## headers for each step and ### for sub-sections.
- Aim for 3000-5000 Chinese characters total. Be dense and informative, not verbose.
- Every factual claim must have an inline citation link or X post reference. If you cannot provide a real link, use `[NO SOURCE FOUND]` — never fabricate."""

    print(f"[*] GROK HORIZON EXPANDER: Scanning X for '{focus}' ({timeframe})...")
    print(f"    This deep scan may take up to 2 minutes...")

    # Enable native Web Search + X Search via OpenRouter
    # For xAI models, this activates real-time X/Twitter search
    # Cost: ~$5 per 1000 searches ($0.005 per call)
    web_search_plugin = [{"id": "web"}]

    return fetch_grok_intel(
        query="Horizon Scan",
        override_prompt=horizon_prompt,
        timeout=120,
        plugins=web_search_plugin
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python x_grok_sensor.py <query>")
        print("Example: python x_grok_sensor.py 'AI Agents'")
    else:
        q = sys.argv[1]
        fetch_grok_intel(q)
