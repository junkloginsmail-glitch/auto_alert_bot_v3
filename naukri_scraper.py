"""
🇮🇳 Naukri Job Scraper — Playwright Stealth Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Strategy (in order):
  1. RSS feeds          — public, real-time (often blocked by Akamai)
  2. Naukri internal API — unauthenticated REST (often 406'd by Akamai)
  3. Playwright stealth — headless Chromium navigates search URL, intercepts
     the /jobapi/v3/search XHR that Naukri's own JS fires on page load.
     NO LOGIN REQUIRED — jobs are public. Stealth bypasses Akamai page-load
     bot detection. Works on GitHub Actions (Ubuntu) without credentials.
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

# ScraperAPI key (optional)
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY", "")

# ── Stealth browser state — opened once, reused for all searches ──
_naukri_stealth_cm = None
_naukri_browser    = None
_naukri_page       = None
_naukri_browser_failed = False  # sentinel — don't retry if browser failed to launch


def _ensure_browser():
    """
    Open a stealth headless Chromium browser (no login required).
    Naukri's job search page fires /jobapi/v3/search XHR for ALL users
    (logged in or not). We just need stealth to bypass Akamai's page-load
    bot detection. The browser is reused for all searches in one run.
    """
    global _naukri_stealth_cm, _naukri_browser, _naukri_page, _naukri_browser_failed

    if _naukri_browser_failed:
        return None
    if _naukri_page is not None:
        return _naukri_page

    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth
    except ImportError as e:
        print(f"  [Naukri Browser] ⚠️  Missing package: {e}")
        print("  [Naukri Browser] Run: pip install playwright playwright-stealth && playwright install --with-deps chromium")
        _naukri_browser_failed = True
        return None

    try:
        _naukri_stealth_cm = Stealth().use_sync(sync_playwright())
        pw = _naukri_stealth_cm.start()
        _naukri_browser = pw.chromium.launch(headless=True)
        ctx = _naukri_browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 800},
        )
        _naukri_page = ctx.new_page()
        return _naukri_page
    except Exception as e:
        print(f"  [Naukri Browser] ❌ Failed to launch browser: {e}")
        _naukri_browser_failed = True
        _close_naukri_browser()
        return None


def _close_naukri_browser():
    """Release browser resources after all searches finish."""
    global _naukri_stealth_cm, _naukri_browser, _naukri_page
    try:
        if _naukri_browser:
            _naukri_browser.close()
        if _naukri_stealth_cm:
            _naukri_stealth_cm.__exit__(None, None, None)
    except Exception:
        pass
    _naukri_stealth_cm = None
    _naukri_browser    = None
    _naukri_page       = None


def _fetch_browser(slug: str, location: str) -> list:
    """
    Navigate to Naukri search URL in a stealth browser and intercept the
    /jobapi/v3/search XHR that Naukri's own JS fires on page load.
    No login required — jobs are publicly visible to all users.
    """
    page = _ensure_browser()
    if page is None:
        return []

    captured: list = []

    def on_response(response):
        try:
            if "/jobapi/v3/search" in response.url and response.status == 200:
                data = response.json()
                captured.extend(data.get("jobDetails", []))
        except Exception:
            pass

    page.on("response", on_response)
    try:
        url = f"https://www.naukri.com/{slug}-jobs-in-{location}"
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        # Wait briefly for in-flight XHR to complete after DOM load
        page.wait_for_timeout(3000)
    except Exception as e:
        # Timeout on full page load is fine — XHR data is already captured
        pass
    finally:
        page.remove_listener("response", on_response)

    jobs = []
    for job in captured:
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
    Main entry — scrapes Naukri for all target job titles.
    Strategy (tried in order until one works per search):
      1. RSS feed      — fast, public
      2. Naukri API    — unauthenticated REST
      3. Browser (XHR) — stealth Chromium navigates search page, intercepts
                         the /jobapi/v3/search XHR Naukri fires automatically.
                         No login needed. Works on GitHub Actions.
    Returns deduplicated list — seen_jobs.json handles final dedup.
    """
    all_jobs = []
    seen_ids = set()
    any_source_worked = False

    print(f"  [Naukri] Checking {len(RSS_SEARCHES) * len(LOCATIONS)} searches...")

    for slug, label in RSS_SEARCHES:
        for location in LOCATIONS:

            # ── Try 1: RSS ────────────────────────────────────────
            jobs = _fetch_rss(slug, location)

            # ── Try 2: Unauthenticated API ────────────────────────
            if not jobs:
                jobs = _fetch_api(slug, location)

            # ── Try 3: Stealth browser XHR interception ───────────
            if not jobs:
                jobs = _fetch_browser(slug, location)

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
        print("  [Naukri] ⚠️  All sources (RSS, API, Browser) returned 0 jobs")

    _close_naukri_browser()

    print(f"[Naukri] Total: {len(all_jobs)} unique jobs found")
    return all_jobs
