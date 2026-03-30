"""
🤖 AI Job Alert Bot v6 — ALL Companies on Lever + Greenhouse + Ashby
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author: Akash Shinde (SpiDo)
Fixes in v6:
  - Telegram rate limit fixed (2s delay between messages)
  - Stricter India-only location filter (no USA/Ireland/Poland etc)
  - Google CSE reduced to 5 queries (saves daily quota)
  - Lever fallback to company list (global API returned 404)
"""

import os, json, time, hashlib, requests, re, xml.etree.ElementTree as ET
from datetime import datetime

# ──────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GOOGLE_API_KEY     = os.environ["GOOGLE_API_KEY"]
GOOGLE_CSE_ID      = os.environ["GOOGLE_CSE_ID"]

SEEN_JOBS_FILE = "seen_jobs.json"
HEADERS        = {"User-Agent": "Mozilla/5.0"}

# ──────────────────────────────────────────────────────
# FILTERS
# ──────────────────────────────────────────────────────
INCLUDE_KEYWORDS = [
    "ai engineer", "ml engineer", "machine learning engineer",
    "genai engineer", "llm engineer", "nlp engineer",
    "applied ai engineer", "ai platform engineer", "mlops engineer",
    "deep learning engineer", "python engineer",
    "backend engineer", "software engineer", "full stack engineer",
    "ai developer", "agentic ai", "data scientist",
]

EXCLUDE_KEYWORDS = [
    "account executive", "account manager", "sales", "marketing",
    "recruiter", "talent", "finance", "legal", "counsel", "accountant",
    "designer", "product manager", "product owner", "operations manager",
    "business development", "presales", "pre-sales", "customer success",
    "engagement manager", "solutions architect", "delivery", "consulting",
    "director", "vp ", "vice president", "intern", "coordinator",
    "executive assistant", "program manager", "scrum master",
    "staff software", "senior staff", "sr. staff", "sr staff",
    "principal engineer", "principal software", "principal data",
    "distinguished", "fellow", "head of", "chief ",
    ", pk", "- pk", " pk)", " pk]",
]

# ── STRICT India-only locations ───────────────────────
# Location must contain at least one of these EXACTLY
INDIA_MUST_HAVE = [
    "india", "bangalore", "bengaluru", "pune", "hyderabad",
    "mumbai", "chennai", "delhi", "noida", "gurgaon",
    "remote", "worldwide", "global", "anywhere",
]

# If location contains any of these → BLOCKED even if "remote"
STRICT_BLOCK = [
    "pakistan", " pk",
    "united states", "- usa", "- us", "remote - us",
    "united kingdom", "- uk", "remote - uk",
    "canada", "brazil", "australia",
    "germany", "france", "netherlands", "spain",
    "ireland", "portugal", "romania", "poland",
    "estonia", "switzerland", "sweden", "norway",
    "denmark", "finland", "singapore", "japan",
    "korea", "mexico", "colombia", "argentina",
    "sf bay area", "san francisco", "new york",
    "california", "seattle", "london", "toronto",
    "emea", "americas", "apac", "latam",
]

def is_india_eligible(job: dict) -> bool:
    location = job["location"].lower()
    title    = job["title"].lower()

    # Block Pakistan in title
    if any(pk in title for pk in [" pk)", " pk]", ", pk", "- pk"]):
        return False

    # Strictly block non-India locations
    if any(bl in location for bl in STRICT_BLOCK):
        return False

    # Must have India signal
    return any(kw in location or kw in title for kw in INDIA_MUST_HAVE)

def keyword_filter(job: dict) -> bool:
    title = job["title"].lower()
    if not any(kw in title for kw in INCLUDE_KEYWORDS):
        return False
    if any(kw in title for kw in EXCLUDE_KEYWORDS):
        return False
    if not is_india_eligible(job):
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

def make_job(title, company, location, link, desc, source, posted="Recent"):
    return {"title": title, "company": company, "location": location,
            "link": link, "description": str(desc)[:300], "source": source,
            "posted_at": posted}

# ──────────────────────────────────────────────────────
# SOURCE 1 — Lever (known AI companies)
# Global API returned 404, using company-specific API
# ──────────────────────────────────────────────────────
LEVER_COMPANIES = [
    # AI-first
    "databricks", "scale", "huggingface", "anthropic", "mistral",
    "wandb", "cohere", "together", "perplexity",
    "runwayml", "stability", "adept", "emi-labs", "weekdayworks",
    "smart-working-solutions", "boldbusiness", "cognite", "thinkahead",
    # Indian AI companies
    "sarvam-ai", "krutrim", "yellowai", "haptik", "uniphore",
    "observe-ai", "sprinklr", "freshworks", "browserstack",
    "hasura", "postman", "chargebee", "clevertap",
    # Global companies hiring India
    "servicenow", "pagerduty", "elastic", "mongodb",
    "confluent", "harness", "singlestore", "airbyte",
]

def scrape_lever() -> list:
    jobs = []
    for company in LEVER_COMPANIES:
        try:
            res = requests.get(
                f"https://api.lever.co/v0/postings/{company}?mode=json&limit=50",
                headers=HEADERS, timeout=8
            )
            if res.status_code != 200:
                continue
            for job in res.json():
                posted = job.get("createdAt", 0)
                jobs.append(make_job(
                    title   = job.get("text", ""),
                    company = company.replace("-", " ").title(),
                    location= job.get("categories", {}).get("location", ""),
                    link    = job.get("hostedUrl", ""),
                    desc    = job.get("descriptionPlain", ""),
                    source  = "Lever",
                    posted  = datetime.fromtimestamp(posted/1000).strftime("%d %b %Y") if posted else "N/A"
                ))
        except Exception as e:
            print(f"[Lever] {company}: {e}")
        time.sleep(0.2)
    print(f"[Lever] {len(jobs)} jobs fetched")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 2 — Greenhouse Sitemap (ALL companies)
# ──────────────────────────────────────────────────────
def get_all_greenhouse_slugs() -> list:
    try:
        res = requests.get(
            "https://boards.greenhouse.io/sitemap.xml",
            headers=HEADERS, timeout=15
        )
        if res.status_code != 200:
            print(f"[GH Sitemap] HTTP {res.status_code} — using fallback")
            return []

        root  = ET.fromstring(res.content)
        ns    = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        slugs = []
        for loc in root.findall(".//sm:loc", ns):
            url = loc.text or ""
            if url.startswith("https://boards.greenhouse.io/") and url.count("/") == 3:
                slug = url.rstrip("/").split("/")[-1]
                if slug:
                    slugs.append(slug)
        print(f"[GH Sitemap] Found {len(slugs)} companies")
        return slugs
    except Exception as e:
        print(f"[GH Sitemap] Error: {e}")
        return []

GREENHOUSE_FALLBACK = [
    "databricks", "coinbase", "particle41llc", "bswiftindia", "builtin",
    "gitlab", "apolloio", "samsara", "clarifai", "airslate",
    "asapp-2", "levelai", "degreed", "clickup", "welocalize",
    "stripe", "twilio", "datadog", "cloudflare", "notion",
    "figma", "linear", "vercel", "openai", "scale-ai",
    "glean", "moveworks", "cresta", "forethought",
    "snorkel-ai", "roboflow", "encord", "labelbox",
]

def scrape_greenhouse_all() -> list:
    jobs  = []
    slugs = get_all_greenhouse_slugs() or GREENHOUSE_FALLBACK

    print(f"[GH] Polling {len(slugs)} companies...")
    for i, slug in enumerate(slugs):
        try:
            res = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                headers=HEADERS, timeout=6
            )
            if res.status_code != 200:
                continue
            for job in res.json().get("jobs", []):
                jobs.append(make_job(
                    title   = job.get("title", ""),
                    company = slug.replace("-", " ").title(),
                    location= job.get("location", {}).get("name", ""),
                    link    = job.get("absolute_url", ""),
                    desc    = "",
                    source  = "Greenhouse",
                    posted  = job.get("updated_at", "")[:10]
                ))
        except Exception:
            pass
        if (i + 1) % 100 == 0:
            print(f"[GH] {i+1}/{len(slugs)} done, {len(jobs)} jobs so far...")
        time.sleep(0.1)

    print(f"[GH] {len(jobs)} total jobs")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 3 — Ashby (AI-native startups)
# ──────────────────────────────────────────────────────
ASHBY_COMPANIES = [
    "anyscale", "together-ai", "modal", "replicate",
    "langchain", "llamaindex", "weaviate", "qdrant",
    "cohere", "adept", "sweep", "codeium", "cursor",
    "cognition", "imbue", "luma-ai", "pika",
    "arcee-ai", "predibase", "baseten", "bentoml",
    "lightning-ai", "labelbox", "encord", "roboflow",
    "snorkel-ai", "dspy-ai", "guardrails-ai",
    "unstructured", "chroma", "pinecone",
    "helicone", "braintrust-data", "portkey-ai",
]

def scrape_ashby() -> list:
    jobs = []
    for company in ASHBY_COMPANIES:
        try:
            res = requests.get(
                f"https://api.ashbyhq.com/posting-api/job-board/{company}",
                headers=HEADERS, timeout=8
            )
            if res.status_code != 200:
                continue
            for job in res.json().get("jobs", []):
                jobs.append(make_job(
                    title   = job.get("title", ""),
                    company = company.replace("-", " ").title(),
                    location= job.get("location", "") or "",
                    link    = job.get("jobUrl", ""),
                    desc    = job.get("descriptionSafe", ""),
                    source  = "Ashby",
                    posted  = job.get("publishedAt", "")[:10] or "Recent"
                ))
        except Exception as e:
            print(f"[Ashby] {company}: {e}")
        time.sleep(0.2)
    print(f"[Ashby] {len(jobs)} jobs fetched")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 4 — Google CSE (only 5 queries to save quota)
# 100 free queries/day — previous runs used them all up
# ──────────────────────────────────────────────────────
GOOGLE_QUERIES = [
    "AI engineer India",
    "machine learning engineer India",
    "LLM engineer India remote",
    "GenAI engineer India",
    "applied AI engineer India",
]

def scrape_via_google() -> list:
    jobs      = []
    seen_urls = set()

    for query in GOOGLE_QUERIES:
        try:
            res = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": GOOGLE_API_KEY, "cx": GOOGLE_CSE_ID,
                        "q": query, "num": 10, "dateRestrict": "d1"},
                timeout=10
            )
            if res.status_code == 429:
                print(f"[Google] Quota exceeded for today — skipping remaining")
                break
            if res.status_code != 200:
                print(f"[Google] HTTP {res.status_code} → {query}")
                continue

            items = res.json().get("items", [])
            print(f"[Google] {len(items):2d} results → {query}")

            for item in items:
                link    = item.get("link", "")
                title   = item.get("title", "")
                snippet = item.get("snippet", "")
                if not link or link in seen_urls:
                    continue
                if "jobs.lever.co" not in link and "job-boards.greenhouse.io" not in link and "jobs.ashbyhq.com" not in link:
                    continue
                title = re.sub(r"\s*[-|]\s*(Lever|Greenhouse|Ashby).*$", "", title).strip()
                if "jobs.lever.co" in link:
                    slug, src = link.split("jobs.lever.co/")[-1].split("/")[0], "Lever"
                elif "job-boards.greenhouse.io" in link:
                    slug, src = link.split("job-boards.greenhouse.io/")[-1].split("/")[0], "Greenhouse"
                else:
                    slug, src = link.split("jobs.ashbyhq.com/")[-1].split("/")[0], "Ashby"
                seen_urls.add(link)
                jobs.append(make_job(title, slug.replace("-"," ").title(),
                                     "India / Remote", link, snippet,
                                     f"{src} via Google", "< 24 hours ago"))
            time.sleep(1)
        except Exception as e:
            print(f"[Google] Error: {e}")

    print(f"[Google] {len(jobs)} fresh jobs")
    return jobs

# ──────────────────────────────────────────────────────
# TELEGRAM — 2 second delay to avoid rate limits
# ──────────────────────────────────────────────────────
def send_telegram(job: dict):
    icons = {"Lever": "🟡", "Greenhouse": "🟢", "Ashby": "🔵", "Google": "🌐"}
    icon  = next((v for k, v in icons.items() if k in job["source"]), "📌")

    msg = f"""{icon} *New AI Job Alert!*

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
            timeout=15
        )
        print(f"[Telegram] {'✅' if r.status_code==200 else '❌'} — {job['title']} @ {job['company']}")
        time.sleep(2)  # ← 2 second delay — prevents Telegram rate limit
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        time.sleep(3)  # extra wait on error

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
def main():
    print(f"\n{'━'*60}")
    print(f"🤖 AI Job Alert Bot v6 — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*60}\n")

    seen     = load_seen()
    all_jobs = []

    print("🟡 SOURCE 1: Lever (known AI companies)...")
    all_jobs += scrape_lever()

    print("\n🟢 SOURCE 2: Greenhouse Sitemap (ALL companies)...")
    all_jobs += scrape_greenhouse_all()

    print("\n🔵 SOURCE 3: Ashby (AI-native startups)...")
    all_jobs += scrape_ashby()

    print("\n🌐 SOURCE 4: Google CSE (last 24h)...")
    all_jobs += scrape_via_google()

    # Deduplicate
    seen_urls, unique = set(), []
    for j in all_jobs:
        if j["link"] and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    # Filter — strict India only
    filtered  = [j for j in unique if keyword_filter(j)]
    new_count = 0

    print(f"\n{'━'*60}")
    print(f"📊 Total unique jobs : {len(unique)}")
    print(f"🔎 After filter      : {len(filtered)} India AI/ML jobs")
    print(f"{'━'*60}\n")

    for job in filtered:
        jid = make_id(job["link"])
        if jid in seen:
            print(f"⏭️  Seen: {job['title']} @ {job['company']}")
            continue
        print(f"✅ NEW → {job['title']} @ {job['company']} | {job['location']}")
        send_telegram(job)
        new_count += 1
        seen.add(jid)

    # Mark all seen
    for job in unique:
        if job["link"]:
            seen.add(make_id(job["link"]))

    save_seen(seen)
    print(f"\n{'━'*60}")
    print(f"✅ Done! {new_count} new alerts sent to Telegram.")
    print(f"{'━'*60}\n")

if __name__ == "__main__":
    main()
