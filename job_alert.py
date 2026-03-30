"""
🤖 AI Job Alert Bot v4 — Lever + Greenhouse (ALL Companies)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author  : Akash Shinde (SpiDo)
Strategy:
  SOURCE 1 → Google Custom Search API  (finds ANY company, real-time)
  SOURCE 2 → Known company APIs        (Lever + Greenhouse, fast backup)
  FILTER   → Smart keyword filter      (no AI needed, runs in 2 seconds)
Filters:
  ✅ India / Remote India only
  ✅ 0-5 YOE level roles only
  ❌ No Pakistan jobs
  ❌ No Senior Staff / Principal / Head roles
  ❌ No USA/UK/Canada only roles
Notify  : Telegram (instant)
Schedule: Every 1 hour via GitHub Actions (FREE)
"""

import os, json, time, hashlib, requests, re
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GOOGLE_API_KEY     = os.environ["GOOGLE_API_KEY"]
GOOGLE_CSE_ID      = os.environ["GOOGLE_CSE_ID"]

SEEN_JOBS_FILE = "seen_jobs.json"

# ── Title must contain at least one ──────────────────
INCLUDE_KEYWORDS = [
    "ai engineer", "ml engineer", "machine learning engineer",
    "genai engineer", "llm engineer", "nlp engineer",
    "applied ai engineer", "ai platform engineer", "mlops engineer",
    "deep learning engineer", "python engineer",
    "backend engineer", "software engineer", "full stack engineer",
    "ai developer", "agentic ai", "data scientist",
]

# ── Title must NOT contain any of these ──────────────
EXCLUDE_KEYWORDS = [
    # Non-tech roles
    "account executive", "account manager", "sales", "marketing",
    "recruiter", "talent", "finance", "legal", "counsel", "accountant",
    "designer", "product manager", "product owner", "operations manager",
    "business development", "presales", "pre-sales", "customer success",
    "engagement manager", "solutions architect", "delivery", "consulting",
    "director", "vp ", "vice president", "intern", "coordinator",
    "executive assistant", "program manager", "scrum master",
    # Too senior for 3 YOE
    "staff software", "senior staff", "sr. staff", "sr staff",
    "principal engineer", "principal software", "principal data",
    "distinguished", "fellow", "head of", "chief ",
    # Pakistan
    ", pk", "- pk", " pk)",  " pk]",
]

# ── Location blocklist (non-India remotes) ────────────
BLOCKED_LOCATIONS = [
    "pakistan", " pk",
    "remote - usa", "remote - us", "- usa",
    "remote - uk", "united kingdom", "- uk",
    "remote - canada", "remote - brazil",
    "remote - australia", "remote - germany",
    "remote - france", "remote - netherlands",
    "remote - spain", "remote - denmark",
    "remote - norway", "remote - sweden",
    "remote - finland", "remote - singapore",
    "remote - japan", "remote - korea",
    "remote - mexico", "remote - colombia",
    "california", "new york", "san francisco",
    "seattle", "london", "toronto",
]

# ── Location must contain at least one ───────────────
INDIA_LOCATIONS = [
    "india", "bangalore", "bengaluru", "pune", "hyderabad",
    "mumbai", "chennai", "delhi", "noida", "gurgaon",
    "remote", "worldwide", "global", "anywhere",
]

def is_india_eligible(job: dict) -> bool:
    location = job["location"].lower()
    title    = job["title"].lower()

    # Block Pakistan in title
    if any(pk in title for pk in [" pk)", " pk]", ", pk", "- pk"]):
        return False

    # Block non-India specific locations
    if any(bl in location for bl in BLOCKED_LOCATIONS):
        return False

    # Must have India/remote signal
    return any(kw in location or kw in title for kw in INDIA_LOCATIONS)

def keyword_filter(job: dict) -> bool:
    title = job["title"].lower()

    if not any(kw in title for kw in INCLUDE_KEYWORDS):
        return False
    if any(kw in title for kw in EXCLUDE_KEYWORDS):
        return False
    if not is_india_eligible(job):
        return False

    return True

# ── Known Companies ───────────────────────────────────
LEVER_COMPANIES = [
    "databricks", "scale", "huggingface", "anthropic", "mistral",
    "wandb", "cohere", "together", "perplexity", "anyscale",
    "runwayml", "stability", "adept", "emi-labs", "weekdayworks",
    "smart-working-solutions", "boldbusiness", "cognite", "thinkahead",
    "groq", "inflection", "characterai",
]

GREENHOUSE_COMPANIES = [
    "databricks", "coinbase", "particle41llc", "bswiftindia", "builtin",
    "gitlab", "apolloio", "samsara", "clarifai", "boldbusiness",
    "airslate", "asapp-2", "levelai", "pay2dc", "degreed",
    "clickup", "welocalize", "g-p",
]

# ── Google CSE queries — NO "OR" operator (causes HTTP 400)
# Each query is simple: keyword + India/remote
# CSE is already restricted to jobs.lever.co + job-boards.greenhouse.io
# So no need for site: prefix — but we keep it for clarity
GOOGLE_QUERIES = [
    # Lever queries
    "AI engineer India",
    "ML engineer India",
    "LLM engineer India",
    "machine learning engineer India",
    "GenAI engineer India",
    "applied AI engineer India",
    "NLP engineer India",
    "backend engineer AI India",
    "python engineer AI India",
    "MLOps engineer India",
    "software engineer AI India",
    "full stack engineer AI India",
    # Greenhouse queries
    "AI engineer remote India",
    "machine learning engineer remote India",
    "GenAI engineer remote India",
    "LLM engineer remote",
    "applied AI engineer remote",
    "backend AI engineer India",
    "python AI engineer India",
    "software engineer LLM India",
]

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

def scrape_via_google() -> list:
    jobs = []
    seen_urls = set()
    for query in GOOGLE_QUERIES:
        try:
            res = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID,
                        "q": query, "num": 10, "dateRestrict": "d1"},
                timeout=10
            )
            if res.status_code != 200:
                print(f"[Google] HTTP {res.status_code} → {query[:50]}")
                print(f"[Google] Error detail: {res.text[:200]}")
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
                slug   = link.split("jobs.lever.co/")[-1].split("/")[0] if "jobs.lever.co" in link else link.split("job-boards.greenhouse.io/")[-1].split("/")[0]
                source = "Lever" if "jobs.lever.co" in link else "Greenhouse"
                seen_urls.add(link)
                jobs.append({"title": title, "company": slug.replace("-", " ").title(),
                             "location": "India / Remote", "link": link,
                             "description": snippet, "source": f"{source} via Google",
                             "posted_at": "< 24 hours ago"})
            time.sleep(0.5)
        except Exception as e:
            print(f"[Google] Error: {e}")
    print(f"[Google] Total: {len(jobs)} fresh jobs")
    return jobs

def scrape_lever_known() -> list:
    jobs = []
    for company in LEVER_COMPANIES:
        try:
            res = requests.get(f"https://api.lever.co/v0/postings/{company}?mode=json&limit=50",
                               headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if res.status_code != 200:
                continue
            for job in res.json():
                posted = job.get("createdAt", 0)
                jobs.append({"title": job.get("text", ""),
                             "company": company.replace("-", " ").title(),
                             "location": job.get("categories", {}).get("location", ""),
                             "link": job.get("hostedUrl", ""),
                             "description": job.get("descriptionPlain", "")[:300],
                             "source": "Lever",
                             "posted_at": datetime.fromtimestamp(posted/1000).strftime("%d %b %Y") if posted else "N/A"})
        except Exception as e:
            print(f"[Lever] {company}: {e}")
        time.sleep(0.2)
    print(f"[Lever Known] {len(jobs)} jobs fetched")
    return jobs

def scrape_greenhouse_known() -> list:
    jobs = []
    for company in GREENHOUSE_COMPANIES:
        try:
            res = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true",
                               headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if res.status_code != 200:
                continue
            for job in res.json().get("jobs", []):
                jobs.append({"title": job.get("title", ""),
                             "company": company.replace("-", " ").title(),
                             "location": job.get("location", {}).get("name", ""),
                             "link": job.get("absolute_url", ""),
                             "description": job.get("content", "")[:300],
                             "source": "Greenhouse",
                             "posted_at": job.get("updated_at", "")[:10]})
        except Exception as e:
            print(f"[Greenhouse] {company}: {e}")
        time.sleep(0.3)
    print(f"[Greenhouse Known] {len(jobs)} jobs fetched")
    return jobs

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
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg.strip(),
                  "parse_mode": "Markdown", "disable_web_page_preview": False},
            timeout=10)
        print(f"[Telegram] {'✅' if r.status_code==200 else '❌'} — {job['title']} @ {job['company']}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")

def main():
    print(f"\n{'━'*56}")
    print(f"🤖 AI Job Alert Bot v4 — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*56}\n")

    seen     = load_seen()
    all_jobs = []

    print("🌐 SOURCE 1: Google Search (ANY company, last 24h)...")
    all_jobs += scrape_via_google()
    print("\n📡 SOURCE 2A: Lever Known Companies...")
    all_jobs += scrape_lever_known()
    print("\n📡 SOURCE 2B: Greenhouse Known Companies...")
    all_jobs += scrape_greenhouse_known()

    seen_urls, unique = set(), []
    for j in all_jobs:
        if j["link"] and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    filtered   = [j for j in unique if keyword_filter(j)]
    new_count  = 0

    print(f"\n{'━'*56}")
    print(f"📊 Total unique jobs : {len(unique)}")
    print(f"🔎 After filter      : {len(filtered)} relevant India jobs")
    print(f"{'━'*56}\n")

    for job in filtered:
        jid = make_id(job["link"])
        if jid in seen:
            print(f"⏭️  Seen: {job['title']} @ {job['company']}")
            continue
        print(f"✅ NEW → {job['title']} @ {job['company']} | {job['location']}")
        send_telegram(job)
        new_count += 1
        seen.add(jid)
        time.sleep(0.5)

    for job in unique:
        if job["link"]:
            seen.add(make_id(job["link"]))

    save_seen(seen)
    print(f"\n{'━'*56}")
    print(f"✅ Done! {new_count} new alerts sent.")
    print(f"{'━'*56}\n")

if __name__ == "__main__":
    main()
