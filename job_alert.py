"""
🤖 AI Job Alert Bot v7 — ALL Companies on Lever + Greenhouse + Ashby
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author: Akash Shinde (SpiDo)

Fixes in v7:
  - Relaxed location filter (was blocking valid India remote jobs)
  - Added debug logging to see what's being filtered out
  - Google quota saved (only 5 queries per run)
  - Telegram 2s delay to avoid rate limits
  - Node.js warning fixed in workflow
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

# Title must have at least one of these
INCLUDE_KEYWORDS = [
    "ai engineer", "ml engineer", "machine learning",
    "genai", "gen ai", "llm", "nlp engineer",
    "applied ai", "ai platform", "mlops",
    "deep learning", "python engineer",
    "backend engineer", "software engineer",
    "full stack engineer", "fullstack engineer",
    "ai developer", "agentic", "data scientist",
    "rag", "langchain", "llm engineer",
]

# Title must NOT have any of these
EXCLUDE_TITLE = [
    "account executive", "account manager",
    "sales representative", "sales manager",
    "marketing manager", "recruiter", "talent acquisition",
    "finance manager", "legal counsel", "accountant",
    "ux designer", "ui designer", "product designer",
    "product manager", "product owner",
    "business development", "presales", "pre-sales",
    "customer success manager", "engagement manager",
    "executive assistant", "program coordinator",
    "scrum master", "agile coach",
    # Too senior
    "principal engineer", "distinguished engineer",
    "head of engineering", "vp of engineering",
    "chief technology", "chief ai",
]

# ── Location Logic ────────────────────────────────────
# APPROACH: Allow if location contains India signal
# OR if location is empty/worldwide/remote (assume could be India)
# BLOCK only if location explicitly says another country

INDIA_SIGNALS = [
    "india", "bangalore", "bengaluru", "pune", "hyderabad",
    "mumbai", "chennai", "delhi", "noida", "gurgaon",
    "kolkata", "ahmedabad", "kochi", "trivandrum",
    "remote", "worldwide", "global", "anywhere", "",  # empty = unknown = allow
]

# Only block if location is VERY specific to another country
HARD_BLOCK_LOCATIONS = [
    "pakistan", "lahore", "karachi", "islamabad",
    "san francisco, ca", "new york, ny", "seattle, wa",
    "austin, tx", "boston, ma", "los angeles",
    "london, uk", "london, england",
    "toronto, on", "vancouver, bc",
    "berlin, germany", "munich, germany",
    "paris, france", "amsterdam, netherlands",
    "singapore only", "tokyo, japan",
]

def is_india_eligible(job: dict) -> bool:
    location = job["location"].lower().strip()
    title    = job["title"].lower()

    # Hard block Pakistan in title
    if any(pk in title for pk in [" pk)", " pk]", ", pk", "- pk"]):
        return False

    # Hard block specific non-India cities
    if any(bl in location for bl in HARD_BLOCK_LOCATIONS):
        return False

    # If location contains any India signal → allow
    if any(sig in location for sig in INDIA_SIGNALS):
        return True

    # If location is a vague "remote" without country → allow
    if "remote" in location and not any(
        country in location for country in [
            "usa", "uk", "canada", "germany", "france",
            "australia", "brazil", "ireland", "poland",
            "spain", "portugal", "netherlands",
        ]
    ):
        return True

    # Otherwise block
    return False

def keyword_filter(job: dict) -> bool:
    title = job["title"].lower()

    # Must match include keyword
    if not any(kw in title for kw in INCLUDE_KEYWORDS):
        return False

    # Must NOT match exclude keyword
    if any(kw in title for kw in EXCLUDE_TITLE):
        return False

    # Must be India eligible
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
    return {
        "title": title, "company": company, "location": location,
        "link": link, "description": str(desc)[:300],
        "source": source, "posted_at": posted
    }

# ──────────────────────────────────────────────────────
# SOURCE 1 — Lever (company-specific API)
# ──────────────────────────────────────────────────────
LEVER_COMPANIES = [
    # AI-first global
    "databricks", "scale", "huggingface", "anthropic", "mistral",
    "wandb", "cohere", "together", "perplexity",
    "runwayml", "stability", "adept",
    # India-focused
    "weekdayworks", "smart-working-solutions", "boldbusiness",
    "cognite", "thinkahead", "emi-labs",
    # Indian startups & tech
    "yellowai", "haptik", "uniphore", "observe-ai",
    "sprinklr", "freshworks", "browserstack",
    "hasura", "postman", "chargebee", "clevertap",
    # Global hiring India
    "servicenow", "pagerduty", "elastic",
    "confluent", "harness", "singlestore",
]

def scrape_lever() -> list:
    jobs = []
    for company in LEVER_COMPANIES:
        try:
            res = requests.get(
                f"https://api.lever.co/v0/postings/{company}?mode=json&limit=100",
                headers=HEADERS, timeout=10
            )
            if res.status_code != 200:
                continue
            data = res.json()
            if not isinstance(data, list):
                continue
            for job in data:
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
        time.sleep(0.3)
    print(f"[Lever] {len(jobs)} jobs fetched from {len(LEVER_COMPANIES)} companies")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 2 — Greenhouse Sitemap → ALL companies
# ──────────────────────────────────────────────────────
GREENHOUSE_FALLBACK = [
    "databricks", "coinbase", "particle41llc", "bswiftindia",
    "gitlab", "apolloio", "samsara", "clarifai", "airslate",
    "asapp-2", "levelai", "degreed", "clickup", "welocalize",
    "stripe", "twilio", "datadog", "cloudflare", "notion",
    "figma", "linear", "vercel", "openai", "scale-ai",
    "glean", "moveworks", "cresta", "forethought",
    "snorkel-ai", "roboflow", "encord", "labelbox",
    "groq", "together-ai", "anyscale",
]

def get_greenhouse_slugs() -> list:
    """Try sitemap first, fallback to known list"""
    try:
        res = requests.get(
            "https://boards.greenhouse.io/sitemap.xml",
            headers=HEADERS, timeout=20
        )
        if res.status_code == 200:
            root  = ET.fromstring(res.content)
            ns    = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            slugs = []
            for loc in root.findall(".//sm:loc", ns):
                url = loc.text or ""
                if url.startswith("https://boards.greenhouse.io/") and url.count("/") == 3:
                    slug = url.rstrip("/").split("/")[-1]
                    if slug:
                        slugs.append(slug)
            if slugs:
                print(f"[GH Sitemap] ✅ Found {len(slugs)} companies")
                return slugs
    except Exception as e:
        print(f"[GH Sitemap] Failed: {e}")

    print(f"[GH Sitemap] Using fallback list ({len(GREENHOUSE_FALLBACK)} companies)")
    return GREENHOUSE_FALLBACK

def scrape_greenhouse() -> list:
    jobs  = []
    slugs = get_greenhouse_slugs()

    for i, slug in enumerate(slugs):
        try:
            res = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                headers=HEADERS, timeout=8
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
            print(f"[GH] Processed {i+1}/{len(slugs)}, {len(jobs)} jobs so far...")
        time.sleep(0.1)

    print(f"[GH] {len(jobs)} total jobs from {len(slugs)} companies")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 3 — Ashby (AI startups)
# ──────────────────────────────────────────────────────
ASHBY_COMPANIES = [
    "anyscale", "together-ai", "modal", "replicate",
    "langchain", "llamaindex", "weaviate", "qdrant",
    "cohere", "adept", "sweep", "codeium", "cursor",
    "cognition", "luma-ai", "arcee-ai", "predibase",
    "baseten", "bentoml", "lightning-ai", "labelbox",
    "encord", "roboflow", "snorkel-ai", "unstructured",
    "chroma", "portkey-ai", "helicone", "braintrust-data",
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
                    location= job.get("location", "") or "Remote",
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
# ──────────────────────────────────────────────────────
GOOGLE_QUERIES = [
    "AI engineer India",
    "machine learning engineer India",
    "LLM engineer India",
    "GenAI engineer India",
    "applied AI engineer India remote",
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
                print("[Google] Daily quota exceeded — skipping")
                break
            if res.status_code != 200:
                print(f"[Google] HTTP {res.status_code} → {query}")
                continue

            items = res.json().get("items", [])
            print(f"[Google] {len(items)} results → {query}")
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
                                     f"{src} via Google", "< 24h"))
            time.sleep(1)
        except Exception as e:
            print(f"[Google] Error: {e}")

    print(f"[Google] {len(jobs)} fresh jobs")
    return jobs

# ──────────────────────────────────────────────────────
# TELEGRAM — 2s delay prevents rate limit
# ──────────────────────────────────────────────────────
def send_telegram(job: dict):
    icons = {"Lever": "🟡", "Greenhouse": "🟢", "Ashby": "🔵", "Google": "🌐"}
    icon  = next((v for k, v in icons.items() if k in job["source"]), "📌")
    msg   = f"""{icon} *New AI Job Alert!*

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
        time.sleep(2)
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        time.sleep(3)

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
def main():
    print(f"\n{'━'*60}")
    print(f"🤖 AI Job Alert Bot v7 — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*60}\n")

    seen     = load_seen()
    all_jobs = []

    print("🟡 SOURCE 1: Lever...")
    all_jobs += scrape_lever()

    print("\n🟢 SOURCE 2: Greenhouse (ALL companies via sitemap)...")
    all_jobs += scrape_greenhouse()

    print("\n🔵 SOURCE 3: Ashby (AI startups)...")
    all_jobs += scrape_ashby()

    print("\n🌐 SOURCE 4: Google CSE (last 24h)...")
    all_jobs += scrape_via_google()

    # Deduplicate
    seen_urls, unique = set(), []
    for j in all_jobs:
        if j["link"] and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    print(f"\n{'━'*60}")
    print(f"📊 Total unique jobs scraped : {len(unique)}")

    # Apply filter with debug info
    matched, skipped_kw, skipped_loc = [], 0, 0
    for j in unique:
        title = j["title"].lower()
        has_kw  = any(kw in title for kw in INCLUDE_KEYWORDS)
        no_excl = not any(kw in title for kw in EXCLUDE_TITLE)
        india   = is_india_eligible(j)

        if has_kw and no_excl and india:
            matched.append(j)
        elif not has_kw or not no_excl:
            skipped_kw += 1
        else:
            skipped_loc += 1

    print(f"🔑 Keyword filter removed    : {skipped_kw} jobs")
    print(f"📍 Location filter removed   : {skipped_loc} jobs")
    print(f"✅ Matched India AI/ML jobs  : {len(matched)}")
    print(f"{'━'*60}\n")

    new_count = 0
    for job in matched:
        jid = make_id(job["link"])
        if jid in seen:
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
