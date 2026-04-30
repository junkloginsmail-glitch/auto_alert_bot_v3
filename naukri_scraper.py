"""
🇮🇳 Naukri Job Scraper — RSS + Playwright Login Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Strategy (in order):
  1. RSS feeds          — public, no auth, real-time
  2. Naukri internal API — unauthenticated REST
  3. Playwright login   — real browser login with NAUKRI_EMAIL / NAUKRI_PASSWORD
     → Naukri uses Akamai bot-detection; playwright-stealth bypasses fingerprinting
     → API calls made via page.evaluate() INSIDE the browser — Akamai cookies
       stay in the browser and never need to be transferred to requests
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

# Cached browser state — kept open across all searches in one run
# Using page.evaluate() to call the API from inside the browser so Akamai
# fingerprint cookies never need to leave the browser context.
_naukri_stealth_cm   = None   # SyncWrappingContextManager (for cleanup)
_naukri_browser      = None   # Playwright Browser
_naukri_page         = None   # Playwright Page (reused for all fetch calls)


def _ensure_naukri_page():
    """
    Open a stealth headless browser, log in to Naukri, and return the live page.
    The browser stays open so _fetch_authenticated() can reuse it for all searches
    via page.evaluate() — keeping Akamai fingerprint cookies inside the browser.
    Call _close_naukri_browser() after all searches to release resources.
    """
    global _naukri_stealth_cm, _naukri_browser, _naukri_page

    if _naukri_page is not None:
        return _naukri_page

    if not NAUKRI_EMAIL or not NAUKRI_PASSWORD:
        return None

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        from playwright_stealth import Stealth
    except ImportError as e:
        print(f"  [Naukri Login] ⚠️  Missing package: {e}")
        print("  [Naukri Login] Run: pip install playwright playwright-stealth && playwright install --with-deps chromium")
        return None

    print("  [Naukri Login] 🌐 Launching stealth headless browser for login...")
    try:
        _naukri_stealth_cm = Stealth().use_sync(sync_playwright())
        pw = _naukri_stealth_cm.start()

        _naukri_browser = pw.chromium.launch(headless=True)
        ctx = _naukri_browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 800},
        )
        _naukri_page = ctx.new_page()

        # 1. Open Naukri login page
        _naukri_page.goto("https://www.naukri.com/nlogin/login", timeout=30000)
        _naukri_page.wait_for_load_state("networkidle", timeout=20000)

        # 2. Fill credentials (IDs confirmed from live page inspection)
        _naukri_page.fill("#usernameField", NAUKRI_EMAIL)
        _naukri_page.fill("#passwordField", NAUKRI_PASSWORD)

        # 3. Submit and wait for post-login page
        _naukri_page.click("button[type='submit']")
        try:
            _naukri_page.wait_for_url("**/mnjuser/**", timeout=15000)
        except PWTimeout:
            _naukri_page.wait_for_load_state("networkidle", timeout=10000)

        # 4. Verify we left the login page
        if "nlogin" in _naukri_page.url:
            print("  [Naukri Login] ❌ Login failed — check NAUKRI_EMAIL / NAUKRI_PASSWORD")
            _close_naukri_browser()
            return None

        print("  [Naukri Login] ✅ Logged in successfully")
        return _naukri_page

    except Exception as e:
        print(f"  [Naukri Login] ❌ Browser login error: {e}")
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


def _fetch_authenticated(slug: str, location: str) -> list:
    """
    Fetch jobs by navigating to the Naukri search URL inside the logged-in browser
    and intercepting the /jobapi/v3/search XHR response that Naukri's own JS sends.
    This bypasses reCAPTCHA because the request is initiated by Naukri's own code
    with all the correct headers, CSRF tokens, and Akamai fingerprint cookies.
    """
    page = _ensure_naukri_page()
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

    # Close the browser if it was opened for authenticated searches
    _close_naukri_browser()

    print(f"[Naukri] Total: {len(all_jobs)} unique jobs found")
    return all_jobs
