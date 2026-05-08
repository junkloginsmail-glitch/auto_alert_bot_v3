"""
🤖 AI Job Alert Bot v10 — 474+ Companies, All ATS Platforms
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author: Akash Shinde (SpiDo)
Target: 3 YOE | Java Backend + AI/ML/GenAI/LLM Engineer

Checks: Lever / Greenhouse / Ashby / Workday
Roles : Backend Engineer, Java Developer, AI Engineer,
        ML Engineer, GenAI Engineer, LLM Engineer,
        Agentic AI Developer, Software Engineer (AI/Java)
"""

import os, json, time, hashlib, requests, re
from naukri_scraper import scrape_naukri
from datetime import datetime

# ──────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GOOGLE_API_KEY     = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID      = os.environ.get("GOOGLE_CSE_ID", "")

SEEN_JOBS_FILE = "seen_jobs.json"
COMPANIES_FILE = "companies.txt"
HEADERS        = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}

# ──────────────────────────────────────────────────────
# YOUR TARGET ROLES (3 YOE | Java + AI)
# Title must contain AT LEAST ONE of these
# ──────────────────────────────────────────────────────
TARGET_ROLES = [
    # Java / Backend roles
    "java developer", "java engineer", "java backend",
    "backend developer", "backend engineer",
    "software engineer", "software developer",
    "full stack engineer", "fullstack engineer",
    "full stack developer", "fullstack developer",
    "java spring", "spring boot engineer",
    # AI / ML roles
    "ai engineer", "ai developer",
    "ml engineer", "machine learning engineer",
    "genai engineer", "gen ai engineer",
    "llm engineer", "nlp engineer",
    "applied ai", "ai platform engineer",
    "mlops engineer", "deep learning engineer",
    "agentic ai", "ai agent", "rag engineer",
    "computer vision engineer", "ai researcher",
    "data scientist", "research engineer",
    # Combined
    "backend engineer", "python engineer",
    "engineer ii", "engineer 2", "sde ii", "sde 2",
    "sde-ii", "member of technical staff",
]

# ── Seniority EXCLUDE (too senior for 3 YOE) ─────────
EXCLUDE_SENIORITY = [
    "staff engineer", "staff software",
    "senior staff", "sr. staff", "sr staff",
    "principal engineer", "principal software",
    "principal data", "principal ml",
    "distinguished engineer", "fellow",
    "director", "vp ", "vice president",
    "head of ", "chief ", "cto", "cpo", "cmo",
    "engineering manager", "tech lead manager",
    "intern", "internship", "co-op", "apprentice",
    "solutions architect",  # pre-sales role
    "devrel", "developer advocate",
    "account executive", "account manager",
    "sales engineer",
]

# ── Non-tech roles to exclude ─────────────────────────
EXCLUDE_ROLES = [
    "product manager", "product owner",
    "business development", "marketing",
    "recruiter", "talent acquisition",
    "finance manager", "legal counsel",
    "ux designer", "ui designer",
    "scrum master", "customer success",
    "engagement manager", "program manager",
    "data analyst",  # not engineering
]

# ── Location filter ───────────────────────────────────
ACCEPT_LOCATIONS = [
    "india", "bangalore", "bengaluru", "pune", "hyderabad",
    "mumbai", "chennai", "delhi", "noida", "gurgaon",
    "kolkata", "ahmedabad", "kochi", "trivandrum",
    "remote", "worldwide", "global", "anywhere",
    "work from anywhere", "distributed",
    "visa", "sponsor", "relocation", "",
]

BLOCK_LOCATIONS = [
    "san francisco, ca", "new york, ny", "seattle, wa",
    "austin, tx", "boston, ma", "los angeles, ca",
    "mountain view, ca", "menlo park", "palo alto",
    "london, uk", "london, england",
    "toronto, on", "vancouver, bc",
    "berlin, germany", "munich, germany",
    "paris, france", "amsterdam, netherlands",
    "lahore", "karachi", "islamabad",
    "onsite - usa", "onsite - uk",
]

def is_relevant_role(title: str) -> bool:
    t = title.lower()
    if not any(role in t for role in TARGET_ROLES):
        return False
    if any(ex in t for ex in EXCLUDE_SENIORITY):
        return False
    if any(ex in t for ex in EXCLUDE_ROLES):
        return False
    return True

def is_relevant_location(location: str) -> bool:
    loc = location.lower().strip()
    if any(b in loc for b in BLOCK_LOCATIONS):
        return False
    if any(sig in loc for sig in ACCEPT_LOCATIONS):
        return True
    if "remote" in loc and not any(c in loc for c in [
        "usa", "uk", "canada", "germany", "france",
        "australia", "brazil", "ireland", "poland",
        "spain", "portugal", "netherlands", "singapore",
    ]):
        return True
    return False

# ──────────────────────────────────────────────────────
# LOAD COMPANIES FROM FILE
# ──────────────────────────────────────────────────────
def load_companies() -> list:
    if not os.path.exists(COMPANIES_FILE):
        print(f"❌ {COMPANIES_FILE} not found!")
        return []
    companies = []
    seen_slugs = set()
    with open(COMPANIES_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                ats, slug = line.split(":", 1)
                key = (ats.strip().lower(), slug.strip().lower())
                if key not in seen_slugs:   # skip duplicates in file
                    seen_slugs.add(key)
                    companies.append(key)
    print(f"📋 Loaded {len(companies)} companies (deduped)")
    return companies

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
# FETCH JOBS — LEVER
# ──────────────────────────────────────────────────────
def fetch_lever(slug: str) -> list:
    try:
        r = requests.get(
            f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=100",
            headers=HEADERS, timeout=10
        )
        if r.status_code != 200:
            return []
        data = r.json()
        if not isinstance(data, list):
            return []
        jobs = []
        for job in data:
            posted = job.get("createdAt", 0)
            jobs.append({
                "title":    job.get("text", ""),
                "company":  slug.replace("-", " ").title(),
                "location": job.get("categories", {}).get("location", ""),
                "link":     job.get("hostedUrl", ""),
                "source":   "Lever",
                "posted":   datetime.fromtimestamp(posted/1000).strftime("%d %b %Y") if posted else "N/A"
            })
        return jobs
    except Exception:
        return []

# ──────────────────────────────────────────────────────
# FETCH JOBS — GREENHOUSE
# ──────────────────────────────────────────────────────
def fetch_greenhouse(slug: str) -> list:
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
                "company":  slug.replace("-", " ").title(),
                "location": job.get("location", {}).get("name", ""),
                "link":     job.get("absolute_url", ""),
                "source":   "Greenhouse",
                "posted":   job.get("updated_at", "")[:10]
            })
        return jobs
    except Exception:
        return []

# ──────────────────────────────────────────────────────
# FETCH JOBS — ASHBY
# ──────────────────────────────────────────────────────
def fetch_ashby(slug: str) -> list:
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
                "company":  slug.replace("-", " ").title(),
                "location": job.get("location", "") or "Remote",
                "link":     job.get("jobUrl", ""),
                "source":   "Ashby",
                "posted":   job.get("publishedAt", "")[:10] or "Recent"
            })
        return jobs
    except Exception:
        return []

# ──────────────────────────────────────────────────────
# FETCH JOBS — WORKDAY
# Standard Workday API pattern used by Amazon, Microsoft,
# IBM, Oracle, Cisco, Intel and 1000s of enterprises
# ──────────────────────────────────────────────────────
WORKDAY_TENANTS = {
    # Format: slug → (company_domain, tenant_id)
    "amazon":       ("amazon",          "amazon"),
    "apple":        ("apple",           "apple"),
    "microsoft":    ("microsoft",       "microsoft"),
    "google":       ("google",          "googlejobs"),
    "meta":         ("meta",            "meta"),
    "intel":        ("intel",           "intel"),
    "ibm":          ("ibm",             "ibm"),
    "oracle":       ("oracle",          "oracle"),
    "cisco":        ("cisco",           "cisco"),
    "qualcomm":     ("qualcomm",        "qualcomm"),
    "amd":          ("amd",             "amd"),
    "nvidia":       ("nvidia",          "nvidia"),
    "salesforce":   ("salesforce",      "salesforce"),
    "adobe":        ("adobe",           "adobe"),
    "servicenow":   ("servicenow",      "servicenow"),
    "workday":      ("workday",         "workday"),
    "visa":         ("visa",            "visa"),
    "mastercard":   ("mastercard",      "mastercard"),
    "jpmorgan":     ("jpmorgan",        "jpmorgan"),
    "goldmansachs": ("goldmansachs",    "goldmansachs"),
    "morganstanley":("morganstanley",   "morganstanley"),
    "deloitte":     ("deloitte",        "deloitte"),
    "capgemini":    ("capgemini",       "capgemini"),
    "accenture":    ("accenture",       "accenture"),
    "cognizant":    ("cognizant",       "cognizant"),
    "infosys":      ("infosys",         "infosys"),
    "tcs":          ("tcs",             "tata"),
    "wipro":        ("wipro",           "wipro"),
    "siemens":      ("siemens",         "siemens"),
    "bosch":        ("bosch",           "bosch"),
    "samsung":      ("samsung",         "samsung"),
    "huawei":       ("huawei",          "huawei"),
}

def fetch_workday(slug: str) -> list:
    """
    Workday standard API — used by Amazon, Microsoft, IBM etc.
    Pattern: company.wd1.myworkdayjobs.com/wday/cxs/tenant/External/jobs
    """
    tenant_info = WORKDAY_TENANTS.get(slug)
    if not tenant_info:
        return []

    company_domain, tenant = tenant_info
    jobs = []

    # Search for Java and AI roles
    search_terms = [
        "backend engineer java india",
        "software engineer AI india",
        "machine learning engineer india",
        "AI engineer india",
    ]

    for search in search_terms:
        try:
            url = f"https://{company_domain}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/External/jobs"
            r = requests.post(
                url,
                json={"appliedFacets": {}, "limit": 20, "offset": 0,
                      "searchText": search},
                headers={**HEADERS, "Content-Type": "application/json"},
                timeout=12
            )
            if r.status_code != 200:
                break

            for job in r.json().get("jobPostings", []):
                ext_path = job.get("externalPath", "")
                link     = f"https://{company_domain}.wd1.myworkdayjobs.com/External/job/{ext_path}" if ext_path else ""
                jobs.append({
                    "title":    job.get("title", ""),
                    "company":  slug.replace("-", " ").title(),
                    "location": job.get("locationsText", ""),
                    "link":     link,
                    "source":   "Workday",
                    "posted":   job.get("postedOn", "")[:10] or "Recent"
                })
            time.sleep(0.5)

        except Exception:
            break

    # Deduplicate by title
    seen, unique = set(), []
    for j in jobs:
        if j["title"] not in seen:
            seen.add(j["title"])
            unique.append(j)
    return unique

# ──────────────────────────────────────────────────────
# GOOGLE CSE — last 24h fresh jobs
# ──────────────────────────────────────────────────────
GOOGLE_QUERIES = [
    "java developer india remote",
    "backend engineer java india",
    "AI engineer india remote",
    "machine learning engineer india",
    "software engineer AI india",
]

def scrape_google() -> list:
    if not GOOGLE_API_KEY:
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
                print("[Google] Quota exceeded")
                break
            if r.status_code != 200:
                continue
            for item in r.json().get("items", []):
                link = item.get("link", "")
                if not link or link in seen_urls:
                    continue
                if not any(d in link for d in [
                    "jobs.lever.co", "job-boards.greenhouse.io",
                    "jobs.ashbyhq.com"
                ]):
                    continue
                title = re.sub(
                    r"\s*[-|]\s*(Lever|Greenhouse|Ashby).*$",
                    "", item.get("title", "")
                ).strip()
                seen_urls.add(link)
                jobs.append({
                    "title":    title,
                    "company":  link.split("/")[3].replace("-", " ").title(),
                    "location": "India / Remote",
                    "link":     link,
                    "source":   "Google CSE",
                    "posted":   "< 24h"
                })
            time.sleep(1)
        except Exception as e:
            print(f"[Google] {e}")
    print(f"[Google] {len(jobs)} fresh jobs")
    return jobs

# ──────────────────────────────────────────────────────
# FETCH BY ATS
# ──────────────────────────────────────────────────────
def fetch_jobs(ats: str, slug: str) -> list:
    if ats == "lever":
        return fetch_lever(slug)
    elif ats == "greenhouse":
        return fetch_greenhouse(slug)
    elif ats == "ashby":
        return fetch_ashby(slug)
    elif ats == "workday":
        return fetch_workday(slug)
    return []

# ──────────────────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────────────────
SOURCE_ICONS = {
    "Lever": "🟡", "Greenhouse": "🟢",
    "Ashby": "🔵", "Workday": "🟠",
    "Google CSE": "🌐", "Naukri": "🔴"
}

def send_telegram(job: dict):
    icon = SOURCE_ICONS.get(job["source"], "📌")
    parts = [
        f"{icon} *New Job Alert!*",
        "",
        f"📌 *{job['title']}*",
        f"🏢 {job['company']}",
        f"📍 {job['location']}",
    ]
    if job.get('salary'): parts.append(f"💰 {job['salary']}")
    if job.get('exp'):    parts.append(f"🧑‍💻 {job['exp']}")
    parts += [
        f"📅 {job['posted']}",
        f"🔍 {job['source']}",
        "",
        f"🔗 [Apply Now]({job['link']})"
    ]
    msg = "\n".join(parts)
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg.strip(),
                  "parse_mode": "Markdown",
                  "disable_web_page_preview": False},
            timeout=15
        )
        print(f"  [Telegram] {'✅' if r.status_code==200 else '❌'} "
              f"{job['title']} @ {job['company']}")
        time.sleep(2)
    except Exception as e:
        print(f"  [Telegram] Error: {e}")
        time.sleep(3)

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
def main():
    print(f"\n{'━'*60}")
    print(f"🤖 AI Job Alert Bot v10 — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*60}\n")

    seen      = load_seen()
    companies = load_companies()
    all_jobs  = []
    stats     = {"lever": 0, "greenhouse": 0, "ashby": 0,
                 "workday": 0, "failed": 0}

    print(f"\n🔍 Checking {len(companies)} companies...\n")

    for i, (ats, slug) in enumerate(companies):
        jobs = fetch_jobs(ats, slug)

        if jobs:
            stats[ats] = stats.get(ats, 0) + 1
            all_jobs.extend(jobs)
            print(f"  [{ats.upper():12}] {slug:30} → {len(jobs)} jobs")
        else:
            stats["failed"] = stats.get("failed", 0) + 1

        if (i + 1) % 50 == 0:
            print(f"\n  📊 Progress: {i+1}/{len(companies)} | "
                  f"{len(all_jobs)} jobs collected...\n")

        time.sleep(0.2)

    # Naukri
    print(f"\n🔴 SOURCE 5: Naukri (ALL new Java + AI jobs in India)...")
    try:
        naukri_jobs = scrape_naukri()
        all_jobs += naukri_jobs
    except Exception as e:
        print(f"[Naukri] Failed: {e}")

    # ── STEP 2+3: Naukri ─────────────────────────────────────
    # Searches ALL target job titles on Naukri (last 24h)
    # jobAge=1 → within 2hr cycle catches any new posting
    # seen_jobs.json dedup → same logic as Lever/Greenhouse
    print(f"\n🔴 SOURCE 5: Naukri (last 24h | all Java + AI titles)...")
    try:
        naukri_jobs = scrape_naukri()
        for j in naukri_jobs:
            all_jobs.append({
                "title":    j["title"],
                "company":  j["company"],
                "location": j["location"],
                "link":     j["link"],
                "source":   "Naukri",
                "posted":   j.get("posted", "Today"),
                "salary":   j.get("salary", ""),
                "exp":      j.get("exp", ""),
            })
    except Exception as e:
        print(f"[Naukri] Error: {e}")

    # Google CSE
    print(f"\n🌐 SOURCE 6: Google CSE (last 24h fresh postings)...")
    all_jobs += scrape_google()

    # Deduplicate
    seen_urls, unique = set(), []
    for j in all_jobs:
        if j.get("link") and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    # Filter for YOUR profile
    matched        = []
    skip_role      = 0
    skip_location  = 0

    for j in unique:
        if not is_relevant_role(j["title"]):
            skip_role += 1
            continue
        if not is_relevant_location(j["location"]):
            skip_location += 1
            continue
        matched.append(j)

    # Sort: Remote / worldwide first → Pune second → rest
    def _location_priority(job):
        loc = job.get("location", "").lower()
        if any(w in loc for w in ["remote", "worldwide", "anywhere", "distributed", "global"]):
            return 0
        if "pune" in loc:
            return 1
        if any(w in loc for w in ["india", "bengaluru", "bangalore", "hyderabad", "mumbai", "chennai", "noida", "gurgaon"]):
            return 2
        return 3
    matched.sort(key=_location_priority)

    print(f"\n{'━'*60}")
    print(f"📊 ATS Breakdown:")
    print(f"   🟡 Lever      : {stats.get('lever',0)} companies")
    print(f"   🟢 Greenhouse : {stats.get('greenhouse',0)} companies")
    print(f"   🔵 Ashby      : {stats.get('ashby',0)} companies")
    print(f"   🟠 Workday    : {stats.get('workday',0)} companies")
    print(f"   ❌ Failed     : {stats.get('failed',0)} companies")
    print(f"\n📋 Total jobs scraped  : {len(unique)}")
    print(f"❌ Filtered (role)     : {skip_role}")
    print(f"❌ Filtered (location) : {skip_location}")
    print(f"✅ Matched for you     : {len(matched)}")
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

    # Mark all seen
    for job in unique:
        if job.get("link"):
            seen.add(make_id(job["link"]))

    save_seen(seen)
    print(f"\n{'━'*60}")
    print(f"✅ Done! {new_count} new alerts sent to Telegram.")
    print(f"{'━'*60}\n")

if __name__ == "__main__":
    main()
