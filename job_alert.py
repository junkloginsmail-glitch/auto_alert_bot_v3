"""
🤖 AI Job Alert Bot v8 — Company Watchlist Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author: Akash Shinde (SpiDo)

HOW IT WORKS:
  1. Reads companies.txt from repo
  2. For each company — auto-detects their ATS:
     Lever → api.lever.co/v0/postings/{slug}
     Greenhouse → boards-api.greenhouse.io/v1/boards/{slug}/jobs
     Ashby → api.ashbyhq.com/posting-api/job-board/{slug}
     Workday → {company}.wd1.myworkdayjobs.com
  3. Filters for: AI/ML roles + India/Remote/Visa sponsor
  4. Pings Telegram for every new match
  5. Saves seen jobs — no duplicate alerts

TO ADD COMPANIES: just edit companies.txt in your repo!
"""

import os, json, time, hashlib, requests, re
from datetime import datetime

# ──────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GOOGLE_API_KEY     = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID      = os.environ.get("GOOGLE_CSE_ID", "")

SEEN_JOBS_FILE     = "seen_jobs.json"
COMPANIES_FILE     = "companies.txt"
HEADERS            = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}

# ──────────────────────────────────────────────────────
# LOAD COMPANIES FROM FILE
# ──────────────────────────────────────────────────────
def load_companies() -> list:
    """Read companies.txt — skip comments and empty lines"""
    if not os.path.exists(COMPANIES_FILE):
        print(f"❌ {COMPANIES_FILE} not found!")
        return []
    companies = []
    with open(COMPANIES_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                companies.append(line.lower())
    print(f"📋 Loaded {len(companies)} companies from {COMPANIES_FILE}")
    return companies

# ──────────────────────────────────────────────────────
# ATS AUTO-DETECTION
# Try each ATS for a company slug — return which one works
# ──────────────────────────────────────────────────────
def detect_ats(slug: str) -> str:
    """Auto-detect which ATS a company uses"""
    # Try Lever
    try:
        r = requests.get(
            f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=1",
            headers=HEADERS, timeout=5
        )
        if r.status_code == 200 and isinstance(r.json(), list):
            return "lever"
    except Exception:
        pass

    # Try Greenhouse
    try:
        r = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            headers=HEADERS, timeout=5
        )
        if r.status_code == 200 and "jobs" in r.json():
            return "greenhouse"
    except Exception:
        pass

    # Try Ashby
    try:
        r = requests.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
            headers=HEADERS, timeout=5
        )
        if r.status_code == 200 and "jobs" in r.json():
            return "ashby"
    except Exception:
        pass

    return "unknown"

# ──────────────────────────────────────────────────────
# ATS CACHE — save detected ATS to avoid re-detection
# ──────────────────────────────────────────────────────
ATS_CACHE_FILE = "ats_cache.json"

def load_ats_cache() -> dict:
    if os.path.exists(ATS_CACHE_FILE):
        with open(ATS_CACHE_FILE) as f:
            return json.load(f)
    return {}

def save_ats_cache(cache: dict):
    with open(ATS_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

# ──────────────────────────────────────────────────────
# FETCH JOBS BY ATS
# ──────────────────────────────────────────────────────
def fetch_lever(slug: str, company_name: str) -> list:
    try:
        r = requests.get(
            f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=100",
            headers=HEADERS, timeout=10
        )
        if r.status_code != 200:
            return []
        jobs = []
        for job in r.json():
            posted = job.get("createdAt", 0)
            jobs.append({
                "title":    job.get("text", ""),
                "company":  company_name,
                "location": job.get("categories", {}).get("location", ""),
                "link":     job.get("hostedUrl", ""),
                "desc":     job.get("descriptionPlain", "")[:200],
                "source":   "Lever",
                "posted":   datetime.fromtimestamp(posted/1000).strftime("%d %b %Y") if posted else "N/A"
            })
        return jobs
    except Exception:
        return []

def fetch_greenhouse(slug: str, company_name: str) -> list:
    try:
        r = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
            headers=HEADERS, timeout=10
        )
        if r.status_code != 200:
            return []
        jobs = []
        for job in r.json().get("jobs", []):
            jobs.append({
                "title":    job.get("title", ""),
                "company":  company_name,
                "location": job.get("location", {}).get("name", ""),
                "link":     job.get("absolute_url", ""),
                "desc":     "",
                "source":   "Greenhouse",
                "posted":   job.get("updated_at", "")[:10]
            })
        return jobs
    except Exception:
        return []

def fetch_ashby(slug: str, company_name: str) -> list:
    try:
        r = requests.get(
            f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
            headers=HEADERS, timeout=10
        )
        if r.status_code != 200:
            return []
        jobs = []
        for job in r.json().get("jobs", []):
            jobs.append({
                "title":    job.get("title", ""),
                "company":  company_name,
                "location": job.get("location", "") or "Remote",
                "link":     job.get("jobUrl", ""),
                "desc":     job.get("descriptionSafe", "")[:200],
                "source":   "Ashby",
                "posted":   job.get("publishedAt", "")[:10] or "Recent"
            })
        return jobs
    except Exception:
        return []

def fetch_jobs_for_company(slug: str, ats: str) -> list:
    """Fetch jobs from the right ATS"""
    company_name = slug.replace("-", " ").title()
    if ats == "lever":
        return fetch_lever(slug, company_name)
    elif ats == "greenhouse":
        return fetch_greenhouse(slug, company_name)
    elif ats == "ashby":
        return fetch_ashby(slug, company_name)
    return []

# ──────────────────────────────────────────────────────
# FILTERS
# ──────────────────────────────────────────────────────
INCLUDE_KEYWORDS = [
    "ai engineer", "ml engineer", "machine learning",
    "genai", "llm", "nlp engineer", "applied ai",
    "ai platform", "mlops", "deep learning",
    "python engineer", "backend engineer",
    "software engineer", "full stack",
    "ai developer", "agentic", "data scientist",
    "rag", "langchain", "computer vision",
    "recommendation", "search engineer",
]

EXCLUDE_TITLE = [
    "account executive", "account manager",
    "sales", "marketing manager", "recruiter",
    "talent acquisition", "finance manager",
    "legal counsel", "accountant", "ux designer",
    "ui designer", "product designer",
    "product manager", "product owner",
    "business development", "presales",
    "customer success", "engagement manager",
    "executive assistant", "program coordinator",
    "scrum master", "chief ", "head of ",
    "vp ", "vice president",
]

# Locations that indicate India / Remote / Visa sponsor
INDIA_REMOTE_SIGNALS = [
    # India locations
    "india", "bangalore", "bengaluru", "pune", "hyderabad",
    "mumbai", "chennai", "delhi", "noida", "gurgaon",
    "kolkata", "ahmedabad", "kochi",
    # Remote signals
    "remote", "worldwide", "global", "anywhere",
    "work from anywhere", "distributed",
    # Visa sponsorship signals
    "visa", "sponsor", "relocation",
    # Empty location (assume remote/global)
    "",
]

# Hard block — very specific non-India onsite locations
HARD_BLOCK = [
    "san francisco, ca", "new york, ny", "seattle, wa",
    "austin, tx", "boston, ma", "los angeles, ca",
    "london, uk", "london, england",
    "toronto, on", "vancouver, bc",
    "berlin, germany", "munich, germany",
    "paris, france", "amsterdam, netherlands",
    "lahore", "karachi", "islamabad",
    "sf bay area only", "onsite only - us",
]

def is_relevant_location(location: str) -> bool:
    loc = location.lower().strip()
    # Hard block specific onsite non-India cities
    if any(b in loc for b in HARD_BLOCK):
        return False
    # Allow if contains India/remote signal
    if any(sig in loc for sig in INDIA_REMOTE_SIGNALS):
        return True
    # Allow vague "remote" without country
    if "remote" in loc and not any(
        c in loc for c in ["- usa", "- uk", "- canada",
                            "- germany", "- france", "- australia",
                            "- ireland", "- poland"]
    ):
        return True
    return False

def is_relevant_job(job: dict) -> bool:
    title = job["title"].lower()
    # Must match AI/ML keyword
    if not any(kw in title for kw in INCLUDE_KEYWORDS):
        return False
    # Must not be excluded role
    if any(kw in title for kw in EXCLUDE_TITLE):
        return False
    # Must be India/remote/visa eligible
    if not is_relevant_location(job["location"]):
        return False
    return True

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
# GOOGLE CSE — last 24h fresh jobs (backup source)
# ──────────────────────────────────────────────────────
GOOGLE_QUERIES = [
    "AI engineer India remote",
    "machine learning engineer India",
    "LLM engineer India",
    "GenAI engineer India",
    "applied AI engineer India",
]

def scrape_google() -> list:
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return []
    jobs      = []
    seen_urls = set()
    for query in GOOGLE_QUERIES:
        try:
            r = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID,
                        "q": query, "num": 10, "dateRestrict": "d1"},
                timeout=10
            )
            if r.status_code == 429:
                print("[Google] Quota exceeded today")
                break
            if r.status_code != 200:
                continue
            for item in r.json().get("items", []):
                link = item.get("link", "")
                if not link or link in seen_urls:
                    continue
                if not any(d in link for d in ["jobs.lever.co", "job-boards.greenhouse.io", "jobs.ashbyhq.com"]):
                    continue
                title = re.sub(r"\s*[-|]\s*(Lever|Greenhouse|Ashby).*$", "",
                               item.get("title", "")).strip()
                seen_urls.add(link)
                jobs.append({
                    "title":    title,
                    "company":  link.split("/")[3].replace("-", " ").title(),
                    "location": "India / Remote",
                    "link":     link,
                    "desc":     item.get("snippet", "")[:200],
                    "source":   "Google CSE",
                    "posted":   "< 24h"
                })
            time.sleep(1)
        except Exception as e:
            print(f"[Google] {e}")
    print(f"[Google] {len(jobs)} fresh jobs")
    return jobs

# ──────────────────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────────────────
SOURCE_ICONS = {
    "Lever": "🟡", "Greenhouse": "🟢",
    "Ashby": "🔵", "Google CSE": "🌐"
}

def send_telegram(job: dict):
    icon = SOURCE_ICONS.get(job["source"], "📌")
    msg  = f"""{icon} *New Job Alert!*

📌 *{job['title']}*
🏢 {job['company']}
📍 {job['location']}
📅 {job['posted']}
🔍 {job['source']}

🔗 [Apply Now]({job['link']})"""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg.strip(),
                  "parse_mode": "Markdown",
                  "disable_web_page_preview": False},
            timeout=15
        )
        ok = r.status_code == 200
        print(f"  [Telegram] {'✅' if ok else '❌'} {job['title']} @ {job['company']}")
        time.sleep(2)  # Telegram rate limit
    except Exception as e:
        print(f"  [Telegram] Error: {e}")
        time.sleep(3)

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
def main():
    print(f"\n{'━'*60}")
    print(f"🤖 AI Job Alert Bot v8 — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*60}\n")

    seen      = load_seen()
    ats_cache = load_ats_cache()
    companies = load_companies()

    all_jobs  = []
    detected  = {"lever": 0, "greenhouse": 0, "ashby": 0, "unknown": 0}

    print(f"\n🔍 Checking {len(companies)} companies...\n")

    for i, slug in enumerate(companies):
        # Get ATS from cache or detect
        if slug in ats_cache:
            ats = ats_cache[slug]
        else:
            ats = detect_ats(slug)
            ats_cache[slug] = ats
            time.sleep(0.3)  # polite detection delay

        detected[ats] = detected.get(ats, 0) + 1

        if ats == "unknown":
            continue

        # Fetch jobs
        jobs = fetch_jobs_for_company(slug, ats)
        all_jobs.extend(jobs)

        if jobs:
            print(f"  [{ats.upper()}] {slug}: {len(jobs)} jobs")

        # Progress every 50 companies
        if (i + 1) % 50 == 0:
            print(f"\n  📊 Progress: {i+1}/{len(companies)} companies, {len(all_jobs)} jobs so far\n")

        time.sleep(0.2)

    # Save ATS cache
    save_ats_cache(ats_cache)

    # Add Google CSE results
    print(f"\n🌐 Google CSE (last 24h)...")
    all_jobs += scrape_google()

    # Deduplicate by URL
    seen_urls, unique = set(), []
    for j in all_jobs:
        if j.get("link") and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    # Filter
    matched = [j for j in unique if is_relevant_job(j)]

    print(f"\n{'━'*60}")
    print(f"📊 ATS breakdown:")
    print(f"   🟡 Lever      : {detected.get('lever', 0)} companies")
    print(f"   🟢 Greenhouse : {detected.get('greenhouse', 0)} companies")
    print(f"   🔵 Ashby      : {detected.get('ashby', 0)} companies")
    print(f"   ❓ Unknown    : {detected.get('unknown', 0)} companies")
    print(f"\n📋 Total jobs scraped  : {len(unique)}")
    print(f"✅ Matched jobs        : {len(matched)}")
    print(f"{'━'*60}\n")

    new_count = 0
    for job in matched:
        jid = make_id(job["link"])
        if jid in seen:
            continue
        print(f"🆕 {job['title']} @ {job['company']} | {job['location']}")
        send_telegram(job)
        new_count += 1
        seen.add(jid)

    # Mark all as seen
    for job in unique:
        if job.get("link"):
            seen.add(make_id(job["link"]))

    save_seen(seen)
    print(f"\n{'━'*60}")
    print(f"✅ Done! {new_count} new alerts sent to Telegram.")
    print(f"{'━'*60}\n")

if __name__ == "__main__":
    main()
