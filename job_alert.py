"""
🤖 AI Job Alert Bot v5 — ALL Companies on Lever + Greenhouse + Ashby
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author  : Akash Shinde (SpiDo)

HOW IT FINDS EVERY JOB FROM EVERY COMPANY:

  SOURCE 1 → Lever Global API
             api.lever.co/v0/postings?mode=json
             → Returns ALL jobs from ALL companies on Lever at once
             → Thousands of companies, one API call

  SOURCE 2 → Greenhouse Sitemap
             boards.greenhouse.io/sitemap.xml
             → Lists ALL company slugs on Greenhouse
             → We poll each one for new jobs

  SOURCE 3 → Ashby Global Feed
             jobs.ashbyhq.com (Google indexed)
             → AI-native startups (LangChain, Modal, Cursor etc)

  SOURCE 4 → Google CSE
             → Catches anything missed by above
             → Real-time, last 24h only

  FILTER   → Keyword filter (India + AI/ML roles only)
  NOTIFY   → Telegram instant ping
  SCHEDULE → Every 1 hour via GitHub Actions (FREE)
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

BLOCKED_LOCATIONS = [
    "pakistan", " pk",
    "remote - usa", "remote - us", "- usa",
    "remote - uk", "united kingdom",
    "remote - canada", "remote - brazil",
    "remote - australia", "remote - germany",
    "remote - france", "remote - netherlands",
    "remote - spain", "remote - singapore",
    "california", "new york", "san francisco",
    "seattle", "london", "toronto",
]

INDIA_LOCATIONS = [
    "india", "bangalore", "bengaluru", "pune", "hyderabad",
    "mumbai", "chennai", "delhi", "noida", "gurgaon",
    "remote", "worldwide", "global", "anywhere",
]

def is_india_eligible(job: dict) -> bool:
    location = job["location"].lower()
    title    = job["title"].lower()
    if any(pk in title for pk in [" pk)", " pk]", ", pk", "- pk"]):
        return False
    if any(bl in location for bl in BLOCKED_LOCATIONS):
        return False
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
            "link": link, "description": desc[:300], "source": source,
            "posted_at": posted}

# ──────────────────────────────────────────────────────
# SOURCE 1 — Lever Global API (ALL companies at once)
# api.lever.co/v0/postings?mode=json returns every single
# job posted on Lever platform across ALL companies
# ──────────────────────────────────────────────────────
def scrape_lever_global() -> list:
    jobs  = []
    limit = 100
    skip  = 0

    print("[Lever Global] Fetching all jobs...")
    while True:
        try:
            res = requests.get(
                "https://api.lever.co/v0/postings",
                params={"mode": "json", "limit": limit, "skip": skip},
                headers=HEADERS, timeout=15
            )
            if res.status_code != 200:
                print(f"[Lever Global] HTTP {res.status_code}")
                break

            batch = res.json()
            if not batch:
                break

            for job in batch:
                posted = job.get("createdAt", 0)
                link   = job.get("hostedUrl", "")
                company = link.split("jobs.lever.co/")[-1].split("/")[0].replace("-"," ").title() if "jobs.lever.co" in link else "Unknown"
                jobs.append(make_job(
                    title   = job.get("text", ""),
                    company = company,
                    location= job.get("categories", {}).get("location", ""),
                    link    = link,
                    desc    = job.get("descriptionPlain", ""),
                    source  = "Lever Global",
                    posted  = datetime.fromtimestamp(posted/1000).strftime("%d %b %Y") if posted else "N/A"
                ))

            skip += limit
            if len(batch) < limit:
                break
            time.sleep(0.5)

        except Exception as e:
            print(f"[Lever Global] Error: {e}")
            break

    print(f"[Lever Global] {len(jobs)} total jobs from ALL Lever companies")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 2 — Greenhouse Sitemap (ALL companies)
# boards.greenhouse.io/sitemap.xml lists every single
# company that uses Greenhouse ATS
# We parse it → get all company slugs → poll each one
# ──────────────────────────────────────────────────────
def get_greenhouse_companies_from_sitemap() -> list:
    """Parse Greenhouse sitemap to get ALL company slugs"""
    try:
        res = requests.get(
            "https://boards.greenhouse.io/sitemap.xml",
            headers=HEADERS, timeout=15
        )
        if res.status_code != 200:
            print(f"[GH Sitemap] HTTP {res.status_code}")
            return []

        root = ET.fromstring(res.content)
        ns   = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        slugs = []

        for loc in root.findall(".//sm:loc", ns):
            url = loc.text or ""
            # URLs look like: https://boards.greenhouse.io/companyslug
            if url.startswith("https://boards.greenhouse.io/") and url.count("/") == 3:
                slug = url.rstrip("/").split("/")[-1]
                if slug and slug not in ["sitemap.xml", ""]:
                    slugs.append(slug)

        print(f"[GH Sitemap] Found {len(slugs)} companies on Greenhouse")
        return slugs

    except Exception as e:
        print(f"[GH Sitemap] Error: {e}")
        return []

def scrape_greenhouse_all() -> list:
    """Poll ALL Greenhouse companies from sitemap"""
    jobs    = []
    slugs   = get_greenhouse_companies_from_sitemap()

    if not slugs:
        print("[GH] Sitemap failed — using fallback list")
        slugs = [
            "databricks", "coinbase", "particle41llc", "bswiftindia",
            "gitlab", "apolloio", "samsara", "clarifai", "airslate",
            "asapp-2", "levelai", "degreed", "clickup", "welocalize",
            "stripe", "twilio", "datadog", "cloudflare", "notion",
            "figma", "linear", "vercel", "openai", "scale-ai",
            "glean", "moveworks", "cresta", "forethought", "rasa",
        ]

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

        # Progress log every 50 companies
        if (i + 1) % 50 == 0:
            print(f"[GH] Processed {i+1}/{len(slugs)} companies, {len(jobs)} jobs so far...")

        time.sleep(0.1)  # polite rate limit

    print(f"[GH] {len(jobs)} total jobs from ALL Greenhouse companies")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 3 — Ashby (AI-native startups)
# Ashby is used by most modern AI startups
# ──────────────────────────────────────────────────────
ASHBY_COMPANIES = [
    "anyscale", "together-ai", "modal", "replicate",
    "langchain", "llamaindex", "weaviate", "qdrant",
    "cohere", "adept", "fixie", "dust", "sweep",
    "codeium", "cursor", "cognition", "imbue",
    "sakana-ai", "mistral", "luma-ai", "pika",
    "arcee-ai", "predibase", "baseten", "bentoml",
    "lightning-ai", "scale-ai", "labelbox", "encord",
    "roboflow", "snorkel-ai", "weights-biases",
    "dspy-ai", "guardrails-ai", "vellum-ai",
    "portkey-ai", "helicone", "braintrust-data",
    "unstructured", "chroma", "pinecone", "milvus",
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
# SOURCE 4 — Google CSE (catches anything missed)
# Searches Lever + Greenhouse for last 24h postings
# ──────────────────────────────────────────────────────
GOOGLE_QUERIES = [
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
    "AI engineer remote India",
    "machine learning engineer remote India",
    "LLM engineer remote",
    "applied AI engineer remote",
    "backend AI engineer India",
    "software engineer LLM India",
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
            if res.status_code != 200:
                print(f"[Google] HTTP {res.status_code} → {query[:40]}: {res.text[:100]}")
                continue

            items = res.json().get("items", [])
            print(f"[Google] {len(items):2d} results → {query[:50]}")

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
                    slug, source = link.split("jobs.lever.co/")[-1].split("/")[0], "Lever"
                elif "job-boards.greenhouse.io" in link:
                    slug, source = link.split("job-boards.greenhouse.io/")[-1].split("/")[0], "Greenhouse"
                else:
                    slug, source = link.split("jobs.ashbyhq.com/")[-1].split("/")[0], "Ashby"

                seen_urls.add(link)
                jobs.append(make_job(
                    title   = title,
                    company = slug.replace("-", " ").title(),
                    location= "India / Remote",
                    link    = link,
                    desc    = snippet,
                    source  = f"{source} via Google",
                    posted  = "< 24 hours ago"
                ))
            time.sleep(0.5)

        except Exception as e:
            print(f"[Google] Error: {e}")

    print(f"[Google] {len(jobs)} fresh jobs found")
    return jobs

# ──────────────────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────────────────
def send_telegram(job: dict):
    icons = {"Lever Global": "🟡", "Greenhouse": "🟢",
             "Ashby": "🔵", "Google": "🌐"}
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
            timeout=10
        )
        print(f"[Telegram] {'✅' if r.status_code==200 else '❌'} — {job['title']} @ {job['company']}")
    except Exception as e:
        print(f"[Telegram] Error: {e}")

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
def main():
    print(f"\n{'━'*60}")
    print(f"🤖 AI Job Alert Bot v5 — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*60}\n")

    seen     = load_seen()
    all_jobs = []

    print("🌐 SOURCE 1: Lever Global API (ALL companies on Lever)...")
    all_jobs += scrape_lever_global()

    print("\n🌐 SOURCE 2: Greenhouse Sitemap (ALL companies on Greenhouse)...")
    all_jobs += scrape_greenhouse_all()

    print("\n🔵 SOURCE 3: Ashby (AI-native startups)...")
    all_jobs += scrape_ashby()

    print("\n🔍 SOURCE 4: Google CSE (last 24h fresh postings)...")
    all_jobs += scrape_via_google()

    # Deduplicate by URL
    seen_urls, unique = set(), []
    for j in all_jobs:
        if j["link"] and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    # Filter
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
        time.sleep(0.5)

    # Mark all as seen
    for job in unique:
        if job["link"]:
            seen.add(make_id(job["link"]))

    save_seen(seen)
    print(f"\n{'━'*60}")
    print(f"✅ Done! {new_count} new alerts sent to Telegram.")
    print(f"{'━'*60}\n")

if __name__ == "__main__":
    main()
