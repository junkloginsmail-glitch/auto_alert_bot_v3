"""
🇮🇳 Naukri Job Scraper — RSS + Login Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Strategy (in order):
  1. RSS feeds          — public, no auth, real-time
  2. Naukri internal API — unauthenticated REST
  3. Authenticated session — logs in with NAUKRI_EMAIL / NAUKRI_PASSWORD
     → bypasses IP blocks, returns fresh job results
seen_jobs.json dedup — only NEW job IDs trigger alert
NO deletion of old IDs — only adds new ones ✅
"""

import requests, time, xml.etree.ElementTree as ET, hashlib, os, json

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.naukri.com/",
}

# ScraperAPI key (optional - only needed if Naukri blocks GitHub IPs)
# Free tier: 5000 requests/month — signup at scraperapi.com
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")

# ── Naukri Login Credentials (set as GitHub Secrets) ─────────
NAUKRI_EMAIL    = os.environ.get("NAUKRI_EMAIL", "")
NAUKRI_PASSWORD = os.environ.get("NAUKRI_PASSWORD", "")

# Cached authenticated session (reused across all searches in one run)
_naukri_session: requests.Session | None = None


def _naukri_login() -> requests.Session | None:
    """
    Login to Naukri via their REST API and return an authenticated session.
    Called once per run; session is cached in _naukri_session.
    Requires NAUKRI_EMAIL and NAUKRI_PASSWORD env vars / GitHub Secrets.
    """
    global _naukri_session

    if _naukri_session is not None:
        return _naukri_session

    if not NAUKRI_EMAIL or not NAUKRI_PASSWORD:
        return None

    session = requests.Session()

    # Step 1 — visit homepage to pick up initial cookies (appId, device ID, etc.)
    try:
        session.get("https://www.naukri.com/", headers=HEADERS, timeout=15)
    except Exception:
        pass

    # Step 2 — POST login credentials to Naukri's central login REST endpoint
    login_headers = {
        **HEADERS,
        "Content-Type": "application/json",
        "appid":        "109",
        "systemid":     "109",
        "gid":          "LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE",
    }
    payload = {
        "username": NAUKRI_EMAIL,
        "password": NAUKRI_PASSWORD,
        "type":     "login",
    }

    try:
        resp = session.post(
            "https://www.naukri.com/central-login-services/v1/login",
            headers=login_headers,
            json=payload,
            timeout=20,
        )
    except Exception as e:
        print(f"  [Naukri Login] ❌ Network error: {e}")
        return None

    if resp.status_code == 200:
        try:
            data = resp.json()
            # Naukri returns the token inside data.customerDetails or headers
            token = (data.get("data", {}) or {}).get("authorizationToken", "")
            if token:
                session.headers.update({"appid": "109", "systemid": "109",
                                        "Authorization": token})
        except Exception:
            pass
        print("  [Naukri Login] ✅ Logged in successfully")
        _naukri_session = session
        return session
    elif resp.status_code == 401:
        print("  [Naukri Login] ❌ Invalid credentials — check NAUKRI_EMAIL / NAUKRI_PASSWORD")
    else:
        print(f"  [Naukri Login] ❌ Login failed (HTTP {resp.status_code})")
    return None


def _fetch_authenticated(slug: str, location: str) -> list:
    """
    Fetch jobs using an authenticated Naukri session.
    Falls back to the regular search API but with auth cookies — bypasses most blocks.
    """
    session = _naukri_login()
    if session is None:
        return []

    keyword = slug.replace("-", " ")
    try:
        r = session.get(
            "https://www.naukri.com/jobapi/v3/search",
            params={
                "noOfResults":  20,
                "urlType":      "search_by_key_loc",
                "searchType":   "adv",
                "keyword":      keyword,
                "location":     location,
                "experience":   0,
                "experienceDD": 6,
                "jobAge":       1,
            },
            headers={**HEADERS, "appid": "109", "systemid": "109"},
            timeout=15,
        )

        if r.status_code == 200:
            jobs = []
            for job in r.json().get("jobDetails", []):
                ph     = job.get("placeholders", [])
                loc    = ph[0].get("label", "") if ph else ""
                salary = ph[1].get("label", "") if len(ph) > 1 else ""
                exp    = ph[2].get("label", "") if len(ph) > 2 else ""
                jd     = job.get("jdURL", "")
                link   = f"https://www.naukri.com{jd}" if jd and not jd.startswith("http") else jd
                job_id = str(job.get("jobId", link))

                jobs.append({
                    "id":       hashlib.md5(job_id.encode()).hexdigest(),
                    "title":    job.get("title", ""),
                    "company":  job.get("companyName", ""),
                    "location": loc,
                    "link":     link,
                    "source":   "Naukri",
                    "posted":   job.get("footerPlaceholderLabel", "Recent"),
                    "salary":   salary,
                    "exp":      exp,
                })
            return jobs
    except Exception as e:
        print(f"  [Naukri Auth] Error for '{keyword}': {e}")
    return []

# ── ALL target job titles → Naukri RSS URLs ───────────────────
# Pattern: naukri.com/rss/searchresults/{title}-jobs-in-india.rss
# Each RSS returns latest 20 jobs for that search
RSS_SEARCHES = [
    # AI / GenAI / LLM
    ("ai-engineer",                "AI Engineer"),
    ("applied-ai-engineer",        "Applied AI Engineer"),
    ("generative-ai-engineer",     "Generative AI Engineer"),
    ("genai-engineer",             "GenAI Engineer"),
    ("llm-engineer",               "LLM Engineer"),
    ("agentic-ai",                 "Agentic AI"),
    ("nlp-engineer",               "NLP Engineer"),
    ("machine-learning-engineer",  "Machine Learning Engineer"),
    ("ml-engineer",                "ML Engineer"),
    ("deep-learning-engineer",     "Deep Learning Engineer"),
    ("mlops-engineer",             "MLOps Engineer"),
    ("computer-vision-engineer",   "Computer Vision Engineer"),
    ("rag-engineer",               "RAG Engineer"),
    ("langchain-developer",        "LangChain Developer"),
    ("ai-backend-engineer",        "AI Backend Engineer"),
    ("ai-developer",               "AI Developer"),
    ("conversational-ai",          "Conversational AI"),
    # Java / Backend
    ("java-developer",             "Java Developer"),
    ("java-backend-developer",     "Java Backend Developer"),
    ("java-backend-engineer",      "Java Backend Engineer"),
    ("spring-boot-developer",      "Spring Boot Developer"),
    ("java-microservices",         "Java Microservices"),
    ("java-full-stack-developer",  "Java Full Stack Developer"),
    ("java-software-engineer",     "Java Software Engineer"),
    # Python Backend
    ("python-backend-developer",   "Python Backend Developer"),
    ("python-developer",           "Python Developer"),
    ("fastapi-developer",          "FastAPI Developer"),
    ("python-ai-developer",        "Python AI Developer"),
    # General Backend / SWE
    ("backend-developer",          "Backend Developer"),
    ("backend-engineer",           "Backend Engineer"),
    ("software-engineer",          "Software Engineer"),
    ("full-stack-developer",       "Full Stack Developer"),
    ("sde-2",                      "SDE 2"),
]

LOCATIONS = ["india", "remote"]

def _fetch_rss(slug: str, location: str) -> list:
    """
    Fetch Naukri RSS feed for a job title + location
    Returns list of raw job dicts from RSS XML
    """
    url = f"https://www.naukri.com/rss/searchresults/{slug}-jobs-in-{location}.rss"

    # If ScraperAPI key provided — use it to bypass IP blocks
    if SCRAPER_API_KEY:
        url = (f"http://api.scraperapi.com?api_key={SCRAPER_API_KEY}"
               f"&url={requests.utils.quote(url)}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code == 403:
            return []  # IP blocked — ScraperAPI needed
        if r.status_code != 200:
            return []

        # Parse RSS XML
        root = ET.fromstring(r.content)
        jobs = []

        for item in root.findall(".//item"):
            title       = item.findtext("title", "").strip()
            link        = item.findtext("link", "").strip()
            description = item.findtext("description", "").strip()
            pub_date    = item.findtext("pubDate", "").strip()
            guid        = item.findtext("guid", link).strip()

            if not title or not link:
                continue

            # Extract company from description (Naukri RSS format)
            company  = ""
            location_str = location.title()

            # Parse description HTML for company/location
            import re
            comp_match = re.search(r"Company\s*:?\s*([^<\n]+)", description, re.I)
            loc_match  = re.search(r"Location\s*:?\s*([^<\n]+)", description, re.I)
            if comp_match:
                company = comp_match.group(1).strip()
            if loc_match:
                location_str = loc_match.group(1).strip()

            jobs.append({
                "id":       hashlib.md5(guid.encode()).hexdigest(),
                "title":    title,
                "company":  company,
                "location": location_str,
                "link":     link,
                "source":   "Naukri",
                "posted":   pub_date[:16] if pub_date else "Recent",
                "salary":   "",
                "exp":      "",
            })

        return jobs

    except ET.ParseError:
        return []
    except Exception as e:
        return []

def _fetch_api(slug: str, location: str) -> list:
    """
    Fallback: Naukri internal search API
    Works if IP not blocked
    """
    keyword = slug.replace("-", " ")
    try:
        r = requests.get(
            "https://www.naukri.com/jobapi/v3/search",
            params={
                "noOfResults":  20,
                "urlType":      "search_by_key_loc",
                "searchType":   "adv",
                "keyword":      keyword,
                "location":     location,
                "experience":   0,
                "experienceDD": 6,
                "jobAge":       1,
            },
            headers=HEADERS,
            timeout=15
        )
        if r.status_code != 200:
            return []

        jobs = []
        for job in r.json().get("jobDetails", []):
            ph     = job.get("placeholders", [])
            loc    = ph[0].get("label", "") if ph else ""
            salary = ph[1].get("label", "") if len(ph) > 1 else ""
            exp    = ph[2].get("label", "") if len(ph) > 2 else ""
            jd     = job.get("jdURL", "")
            link   = f"https://www.naukri.com{jd}" if jd and not jd.startswith("http") else jd
            job_id = str(job.get("jobId", link))

            jobs.append({
                "id":       hashlib.md5(job_id.encode()).hexdigest(),
                "title":    job.get("title", ""),
                "company":  job.get("companyName", ""),
                "location": loc,
                "link":     link,
                "source":   "Naukri",
                "posted":   job.get("footerPlaceholderLabel", "Recent"),
                "salary":   salary,
                "exp":      exp,
            })
        return jobs
    except Exception:
        return []

def scrape_naukri() -> list:
    """
    Main entry — scrapes Naukri for all target job titles
    Strategy (tried in order until one works):
      1. RSS feed      — public, no auth, real-time
      2. Naukri API    — unauthenticated REST call
      3. Login session — authenticated via NAUKRI_EMAIL / NAUKRI_PASSWORD
         Bypasses IP blocks; set as GitHub Secrets to enable
    Returns deduplicated list — seen_jobs.json handles final dedup
    NO deletion of old IDs — only new job IDs added ✅
    """
    all_jobs = []
    seen_ids = set()
    any_source_worked = False

    login_available = bool(NAUKRI_EMAIL and NAUKRI_PASSWORD)

    print(f"  [Naukri] Checking {len(RSS_SEARCHES) * len(LOCATIONS)} searches...")
    if login_available:
        print(f"  [Naukri] 🔐 Login credentials found — will use if RSS/API blocked")

    for slug, label in RSS_SEARCHES:
        for location in LOCATIONS:

            # ── Try 1: RSS ────────────────────────────────────────
            jobs = _fetch_rss(slug, location)

            # ── Try 2: Unauthenticated API ────────────────────────
            if not jobs:
                jobs = _fetch_api(slug, location)

            # ── Try 3: Authenticated session ──────────────────────
            if not jobs and login_available:
                jobs = _fetch_authenticated(slug, location)

            if jobs and not any_source_worked:
                any_source_worked = True

            new = 0
            for job in jobs:
                uid = job.get("id") or job.get("link", "")
                if not uid or uid in seen_ids:
                    continue
                seen_ids.add(uid)
                all_jobs.append(job)
                new += 1

            if new > 0:
                print(f"  [Naukri] '{label}' in {location}: {new} new jobs")

            time.sleep(0.3)

    if not any_source_worked:
        if login_available:
            print("  [Naukri] ⚠️  All sources failed (RSS, API, Login)")
            print("  [Naukri] 💡 Verify NAUKRI_EMAIL / NAUKRI_PASSWORD are correct")
        else:
            print("  [Naukri] ⚠️  RSS and API are blocked by Naukri")
            print("  [Naukri] 💡 Add NAUKRI_EMAIL + NAUKRI_PASSWORD as GitHub Secrets to bypass")
            print("  [Naukri] 💡 Or add SCRAPER_API_KEY (scraperapi.com, 5000 req/month free)")

    print(f"[Naukri] Total: {len(all_jobs)} unique jobs found")
    return all_jobs
