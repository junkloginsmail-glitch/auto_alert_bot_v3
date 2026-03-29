"""
🤖 AI Job Alert Bot v3 — Lever + Greenhouse (ALL Companies)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author  : Akash Shinde (SpiDo)
Strategy:
  SOURCE 1 → Google Custom Search API  (finds ANY company, real-time)
  SOURCE 2 → Known company APIs        (Lever + Greenhouse, fast backup)
  FILTER   → Smart keyword filter      (no AI needed, runs in 2 seconds)
Notify  : Telegram (instant)
Schedule: Every 1 hour via GitHub Actions (FREE)
"""

import os, json, time, hashlib, requests, re
from datetime import datetime

# ──────────────────────────────────────────────────────
# CONFIG — All values come from GitHub Secrets
# ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GOOGLE_API_KEY     = os.environ["GOOGLE_API_KEY"]
GOOGLE_CSE_ID      = os.environ["GOOGLE_CSE_ID"]

SEEN_JOBS_FILE = "seen_jobs.json"

# ──────────────────────────────────────────────────────
# KEYWORD FILTER
# Job title must match at least one INCLUDE keyword
# and must NOT match any EXCLUDE keyword
# ──────────────────────────────────────────────────────
INCLUDE_KEYWORDS = [
    "ai engineer", "ml engineer", "machine learning engineer",
    "genai engineer", "gen ai", "llm engineer", "nlp engineer",
    "applied ai", "ai platform", "mlops engineer",
    "deep learning engineer", "data scientist",
    "python engineer", "backend engineer",
    "software engineer", "full stack engineer",
    "ai developer", "ai researcher", "agentic",
]

EXCLUDE_KEYWORDS = [
    "account executive", "account manager",
    "sales", "marketing", "recruiter", "talent",
    "finance", "legal", "counsel", "accountant",
    "designer", "product manager", "product owner",
    "operations manager", "business development",
    "presales", "pre-sales", "customer success",
    "engagement manager", "solutions architect",
    "delivery", "consulting", "director", "vp ",
    "vice president", "intern", "coordinator",
    "executive assistant", "program manager",
]

INDIA_KEYWORDS = [
    "india", "bangalore", "bengaluru", "pune", "hyderabad",
    "mumbai", "chennai", "delhi", "remote", "worldwide",
    "global", "anywhere",
]

def is_india_eligible(job: dict) -> bool:
    """Check if job is open to India / remote"""
    text = (job["location"] + " " + job["title"] + " " + job["description"]).lower()
    return any(kw in text for kw in INDIA_KEYWORDS)

def keyword_filter(job: dict) -> bool:
    """Fast keyword filter — runs in microseconds"""
    title = job["title"].lower()

    # Must match an include keyword in title
    has_include = any(kw in title for kw in INCLUDE_KEYWORDS)
    if not has_include:
        return False

    # Must NOT match exclude keywords in title
    has_exclude = any(kw in title for kw in EXCLUDE_KEYWORDS)
    if has_exclude:
        return False

    # Must be India eligible
    if not is_india_eligible(job):
        return False

    return True

# ──────────────────────────────────────────────────────
# KNOWN COMPANIES LIST
# ──────────────────────────────────────────────────────
LEVER_COMPANIES = [
    "databricks", "scale", "huggingface", "anthropic", "mistral",
    "wandb", "cohere", "together", "perplexity", "anyscale",
    "runwayml", "stability", "adept", "emi-labs", "weekdayworks",
    "smart-working-solutions", "boldbusiness", "cognite", "thinkahead",
    "groq", "inflection", "characterai", "moonshot-ai",
]

GREENHOUSE_COMPANIES = [
    "databricks", "coinbase", "particle41llc", "bswiftindia", "builtin",
    "gitlab", "apolloio", "samsara", "clarifai", "boldbusiness",
    "airslate", "asapp-2", "levelai", "pay2dc", "degreed",
    "clickup", "welocalize", "g-p",
]

# ──────────────────────────────────────────────────────
# GOOGLE SEARCH QUERIES
# ──────────────────────────────────────────────────────
GOOGLE_QUERIES = [
    'site:jobs.lever.co "AI engineer" "India"',
    'site:jobs.lever.co "ML engineer" OR "LLM engineer" "India"',
    'site:jobs.lever.co "machine learning engineer" "India" OR "remote"',
    'site:jobs.lever.co "GenAI" OR "applied AI" "India"',
    'site:jobs.lever.co "backend engineer" "AI" "India"',
    'site:job-boards.greenhouse.io "AI engineer" "India"',
    'site:job-boards.greenhouse.io "ML engineer" OR "LLM" "India"',
    'site:job-boards.greenhouse.io "machine learning" "India" OR "remote"',
    'site:job-boards.greenhouse.io "GenAI" OR "applied AI" "India"',
    'site:job-boards.greenhouse.io "python engineer" "AI" "India"',
]

# ──────────────────────────────────────────────────────
# SEEN JOBS
# ──────────────────────────────────────────────────────
def load_seen() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)

def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

# ──────────────────────────────────────────────────────
# SOURCE 1 — Google Custom Search
# ──────────────────────────────────────────────────────
def scrape_via_google() -> list:
    jobs = []
    seen_urls = set()

    for query in GOOGLE_QUERIES:
        try:
            res = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key":          GOOGLE_API_KEY,
                    "cx":           GOOGLE_CSE_ID,
                    "q":            query,
                    "num":          10,
                    "dateRestrict": "d1",
                },
                timeout=10
            )
            if res.status_code != 200:
                print(f"[Google] HTTP {res.status_code} → {query[:50]}")
                continue

            items = res.json().get("items", [])
            print(f"[Google] {len(items):2d} results → {query[:55]}")

            for item in items:
                link    = item.get("link", "")
                title   = item.get("title", "")
                snippet = item.get("snippet", "")

                if not link or link in seen_urls:
                    continue
                if "jobs.lever.co" not in link and "job-boards.greenhouse.io" not in link:
                    continue

                title = re.sub(r"\s*[-|]\s*(Lever|Greenhouse).*$", "", title).strip()

                if "jobs.lever.co" in link:
                    slug   = link.split("jobs.lever.co/")[-1].split("/")[0]
                    source = "Lever"
                else:
                    slug   = link.split("job-boards.greenhouse.io/")[-1].split("/")[0]
                    source = "Greenhouse"

                seen_urls.add(link)
                jobs.append({
                    "title":       title,
                    "company":     slug.replace("-", " ").title(),
                    "location":    "India / Remote",
                    "link":        link,
                    "description": snippet,
                    "source":      f"{source} via Google",
                    "posted_at":   "< 24 hours ago",
                })
            time.sleep(0.5)

        except Exception as e:
            print(f"[Google] Error: {e}")

    print(f"[Google] Total: {len(jobs)} fresh jobs found")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 2A — Lever Known Companies
# ──────────────────────────────────────────────────────
def scrape_lever_known() -> list:
    jobs = []
    for company in LEVER_COMPANIES:
        try:
            res = requests.get(
                f"https://api.lever.co/v0/postings/{company}?mode=json&limit=50",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=8
            )
            if res.status_code != 200:
                continue
            for job in res.json():
                posted = job.get("createdAt", 0)
                jobs.append({
                    "title":       job.get("text", ""),
                    "company":     company.replace("-", " ").title(),
                    "location":    job.get("categories", {}).get("location", ""),
                    "link":        job.get("hostedUrl", ""),
                    "description": job.get("descriptionPlain", "")[:300],
                    "source":      "Lever",
                    "posted_at":   datetime.fromtimestamp(posted/1000).strftime("%d %b %Y") if posted else "N/A"
                })
        except Exception as e:
            print(f"[Lever] {company}: {e}")
        time.sleep(0.2)
    print(f"[Lever Known] {len(jobs)} jobs fetched")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 2B — Greenhouse Known Companies
# ──────────────────────────────────────────────────────
def scrape_greenhouse_known() -> list:
    jobs = []
    for company in GREENHOUSE_COMPANIES:
        try:
            res = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=8
            )
            if res.status_code != 200:
                continue
            for job in res.json().get("jobs", []):
                jobs.append({
                    "title":       job.get("title", ""),
                    "company":     company.replace("-", " ").title(),
                    "location":    job.get("location", {}).get("name", ""),
                    "link":        job.get("absolute_url", ""),
                    "description": job.get("content", "")[:300],
                    "source":      "Greenhouse",
                    "posted_at":   job.get("updated_at", "")[:10]
                })
        except Exception as e:
            print(f"[Greenhouse] {company}: {e}")
        time.sleep(0.3)
    print(f"[Greenhouse Known] {len(jobs)} jobs fetched")
    return jobs

# ──────────────────────────────────────────────────────
# TELEGRAM NOTIFICATION
# ──────────────────────────────────────────────────────
def send_telegram(job: dict):
    icon = "🟡" if "Lever" in job["source"] else "🟢"
    msg  = f"""{icon} *New AI Job Alert!*

📌 *{job['title']}*
🏢 {job['company']}
📍 {job['location']}
📅 {job['posted_at']}
🔍 {job['source']}

🔗 [Apply Now]({job['link']})"""

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id":                  TELEGRAM_CHAT_ID,
                "text":                     msg.strip(),
                "parse_mode":               "Markdown",
                "disable_web_page_preview": False
            },
            timeout=10
        )
        status = "✅" if r.status_code == 200 else f"❌ {r.text[:100]}"
        print(f"[Telegram] {status} — {job['title']} @ {job['company']}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
def main():
    print(f"\n{'━'*56}")
    print(f"🤖 AI Job Alert Bot v3 — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*56}\n")

    seen      = load_seen()
    new_count = 0
    all_jobs  = []

    print("🌐 SOURCE 1: Google Search (ANY company, last 24h)...")
    all_jobs += scrape_via_google()

    print("\n📡 SOURCE 2A: Lever Known Companies...")
    all_jobs += scrape_lever_known()

    print("\n📡 SOURCE 2B: Greenhouse Known Companies...")
    all_jobs += scrape_greenhouse_known()

    # Deduplicate by URL
    seen_urls, unique = set(), []
    for j in all_jobs:
        if j["link"] and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    print(f"\n{'━'*56}")
    print(f"📊 Total unique jobs: {len(unique)}")

    # Fast keyword filter
    filtered = [j for j in unique if keyword_filter(j)]
    print(f"🔎 After keyword filter: {len(filtered)} relevant jobs")
    print(f"{'━'*56}\n")

    for job in filtered:
        jid = make_id(job["link"])
        if jid in seen:
            print(f"⏭️  Already alerted: {job['title']} @ {job['company']}")
            continue

        print(f"✅ NEW MATCH → {job['title']} @ {job['company']} | {job['location']}")
        send_telegram(job)
        new_count += 1
        seen.add(jid)
        time.sleep(0.5)  # gentle Telegram rate limit

    # Mark ALL jobs seen to avoid re-checking next hour
    for job in unique:
        if job["link"]:
            seen.add(make_id(job["link"]))

    save_seen(seen)

    print(f"\n{'━'*56}")
    print(f"✅ Done! {new_count} new job alerts sent to Telegram.")
    print(f"{'━'*56}\n")

if __name__ == "__main__":
    main()
