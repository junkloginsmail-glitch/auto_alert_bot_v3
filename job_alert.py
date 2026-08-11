"""
🤖 AI Job Alert Bot v11 — Parallel Edition (3000+ Companies)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author: Akash Shinde (SpiDo)
Target: 3 YOE | Java Backend + AI/ML/GenAI/LLM Engineer

Checks: Lever / Greenhouse / Ashby / Workday
Roles : Backend Engineer, Java Developer, AI Engineer,
        ML Engineer, GenAI Engineer, LLM Engineer,
        Agentic AI Developer, Software Engineer (AI/Java)

v11 Speed Improvements:
  ✅ Concurrent fetching  — 60 workers (ThreadPoolExecutor)
  ✅ Per-ATS semaphores   — polite rate limiting, no bans
  ✅ Session pooling      — keep-alive TCP, no reconnect cost
  ✅ Dead-slug cache      — skip known-404 companies instantly
  ✅ Adaptive retry       — exponential backoff on 429/503
  ✅ Early timeout        — 8s hard limit, fail-fast
  ✅ Telegram batching    — digest mode (no 2s sleep per alert)
  Result: ~1300 companies in ~90s instead of ~600s
"""

import os, json, time, hashlib, requests, re, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ──────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
GOOGLE_API_KEY     = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID      = os.environ.get("GOOGLE_CSE_ID", "")

SEEN_JOBS_FILE  = "seen_jobs.json"
COMPANIES_FILE  = "companies.txt"
ATS_CACHE_FILE  = "ats_cache.json"   # caches known-dead slugs
HEADERS         = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}

# ──────────────────────────────────────────────────────
# CONCURRENCY SETTINGS
# ──────────────────────────────────────────────────────
MAX_WORKERS     = 60          # parallel HTTP workers
REQUEST_TIMEOUT = 8           # seconds per request

# Per-ATS semaphores — prevents flooding any single ATS
_SEM = {
    "lever":      threading.Semaphore(20),   # Lever handles load well
    "greenhouse": threading.Semaphore(20),   # Greenhouse too
    "ashby":      threading.Semaphore(15),   # Ashby is smaller infra
    "workday":    threading.Semaphore(5),    # Workday is strict
}

# Thread-local HTTP sessions (connection pooling per thread)
_local = threading.local()

def _get_session() -> requests.Session:
    """Return a thread-local session with retry adapter."""
    if not hasattr(_local, "session"):
        s = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        s.headers.update(HEADERS)
        _local.session = s
    return _local.session

# ──────────────────────────────────────────────────────
# DEAD-SLUG CACHE  — skip known-404 companies
# ──────────────────────────────────────────────────────
_dead_cache_lock = threading.Lock()

def _load_dead_cache() -> dict:
    """Load {ats:slug → iso-date} of permanently failing slugs."""
    if os.path.exists(ATS_CACHE_FILE):
        try:
            with open(ATS_CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_dead_cache(cache: dict):
    with open(ATS_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

# Global dead cache loaded once at startup
_DEAD_CACHE: dict = {}
_DEAD_CACHE_DIRTY = False   # set True when we add new dead entries

def _mark_dead(ats: str, slug: str):
    global _DEAD_CACHE_DIRTY
    key = f"{ats}:{slug}"
    with _dead_cache_lock:
        _DEAD_CACHE[key] = datetime.now().strftime("%Y-%m-%d")
        _DEAD_CACHE_DIRTY = True

def _is_dead(ats: str, slug: str) -> bool:
    """Skip if slug failed within the last 7 days."""
    key = f"{ats}:{slug}"
    date_str = _DEAD_CACHE.get(key)
    if not date_str:
        return False
    try:
        dead_on = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now() - dead_on).days < 7
    except Exception:
        return False

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
    "Java full stack engineer", "Java fullstack engineer",
    "React developer", "React engineer", "Node.js developer", "Node.js engineer", "Java + React Fullstack"    
    "java spring", "spring boot engineer",
    # AI / ML roles
    "ai engineer", "ai developer", "Agen"
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

# ── Companies to exclude (mass hirers, spam) ──────────
EXCLUDE_COMPANIES = [
    "infosys", "accenture", # Other mass hirers (optional)
]

# ── Job status keywords to exclude ────────────────────
EXCLUDE_JOB_STATUS = [
    "closed", "no longer accepting", "position filled",
    "hiring closed", "applications closed", "not accepting",
]

# ── Location filter ───────────────────────────────────
# Priority 1: India-based jobs
INDIA_LOCATIONS = [
    "india", "bangalore", "bengaluru", "pune", "hyderabad",
    "mumbai", "chennai", "delhi", "noida", "gurgaon",
    "kolkata", "ahmedabad", "kochi", "trivandrum",
]

# Priority 2: Remote/Distributed (any country)
REMOTE_KEYWORDS = [
    "remote", "work from home", "wfh", "work-from-home",
    "worldwide", "global", "anywhere", "distributed",
    "work from anywhere",
]

# Priority 3: Visa sponsorship opportunities (relocation to any country)
VISA_KEYWORDS = [
    "visa", "sponsor", "relocation", "relocate",
    "immigration support", "work permit",
]

# Priority 4: Asia-Pacific tech hubs (easy relocation/remote options)
APAC_LOCATIONS = [
    "tokyo", "osaka", "seoul", "singapore", "hong kong",
    "taipei", "shanghai", "beijing", "bangkok", "kuala lumpur",
]

# BLOCK: Only block Pakistan and explicit onsite-only US/UK/EU roles
BLOCK_LOCATIONS = [
    "lahore", "karachi", "islamabad", "rawalpindi", "faisalabad",
    "onsite only - usa", "onsite only - uk", "onsite only - eu",
    "us only (no remote)", "uk only (no remote)",
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
    """
    Accept jobs if:
      1. Located in India
      2. Remote/worldwide/distributed (any country)
      3. Mentions visa/sponsorship/relocation
      4. Asia-Pacific tech hubs
      5. Blank/empty location (we'll apply anyway)
      6. Any other global location (US/EU/etc.) NOT explicitly blocked
    
    Block only:
      - Pakistan cities
      - Explicit "onsite only" for US/UK/EU (no remote)
    """
    loc = location.lower().strip()
    
    # Accept blank/empty locations
    if not loc or loc == "":
        return True
    
    # Block Pakistan and strict onsite-only roles
    if any(blocked in loc for blocked in BLOCK_LOCATIONS):
        return False
    
    # Accept India
    if any(city in loc for city in INDIA_LOCATIONS):
        return True
    
    # Accept Remote/Worldwide/Distributed
    if any(keyword in loc for keyword in REMOTE_KEYWORDS):
        return True
    
    # Accept Visa/Sponsorship/Relocation
    if any(keyword in loc for keyword in VISA_KEYWORDS):
        return True
    
    # Accept APAC tech hubs
    if any(city in loc for city in APAC_LOCATIONS):
        return True
    
    # Accept all other global locations (US, EU, etc.)
    # Unless they're explicitly "onsite only" (already blocked above)
    return True

def is_excluded_company(company: str) -> bool:
    """Check if company should be excluded (mass hirers, spam)"""
    comp = company.lower().strip()
    return any(exc in comp for exc in EXCLUDE_COMPANIES)

def is_job_closed(title: str, description: str = "") -> bool:
    """Check if job posting indicates it's closed"""
    text = (title + " " + description).lower()
    return any(status in text for status in EXCLUDE_JOB_STATUS)

def is_posted_recently(posted_date: str, source: str = "") -> bool:
    """
    Check if job was posted within the last 24 hours.
    Returns True if:
      - Posted date is within last 24 hours
      - Posted date is missing/empty (assume recent, don't filter out)
      - Posted date says "Today", "Recent", "< 24h" etc.
    Returns False if:
      - Posted date is older than 24 hours
    """
    if not posted_date or posted_date in ["N/A", "", "Recent", "Today", "< 24h"]:
        return True  # Assume recent if no date or marked as recent
    
    try:
        # Try parsing different date formats
        posted = None
        
        # Format 1: "dd MMM yyyy" (e.g., "11 Aug 2026")
        try:
            posted = datetime.strptime(posted_date, "%d %b %Y")
        except:
            pass
        
        # Format 2: "yyyy-mm-dd" (e.g., "2026-08-11")
        if not posted:
            try:
                posted = datetime.strptime(posted_date[:10], "%Y-%m-%d")
            except:
                pass
        
        # Format 3: ISO format (e.g., "2026-08-11T10:30:00Z")
        if not posted:
            try:
                posted = datetime.fromisoformat(posted_date.replace('Z', '+00:00').split('T')[0])
            except:
                pass
        
        # If we successfully parsed a date, check if it's within 24 hours
        if posted:
            hours_ago = (datetime.now() - posted).total_seconds() / 3600
            return hours_ago <= 24
        
        # If we couldn't parse the date, assume it's recent (don't filter out)
        return True
        
    except Exception:
        # If any error occurs, assume recent (don't filter out good jobs)
        return True

def has_acceptable_experience(title: str, description: str = "", exp: str = "") -> bool:
    """
    Check if job requires 2-5 years of experience.
    Returns True if:
      - Explicitly mentions 2+, 3+, 4+, 5+ years
      - Mentions 2-5, 3-5, 3-4 year ranges
      - No experience mentioned at all (we'll apply)
    Returns False if:
      - Requires 6+ years, 7+ years, etc.
      - Mentions "senior" level with high experience (handled by EXCLUDE_SENIORITY)
      - Requires 10+ years or similar
    """
    # Combine all text sources
    text = f"{title} {description} {exp}".lower()
    
    # Pattern 1: Check for explicit "X+ years" patterns
    # Match: "3+ years", "2+ years", "5+ years"
    import re
    
    # Find all patterns like "N+ years" or "N - N years"
    exp_patterns = re.findall(r'(\d+)\s*\+\s*(?:years|yrs|year|yr)', text)
    
    # If found "2+", "3+", "4+", "5+" → acceptable
    for match in exp_patterns:
        years = int(match)
        if years >= 2 and years <= 5:
            return True  # Explicitly matches our range
        elif years > 5:
            return False  # Too senior (6+, 7+, 8+, etc.)
    
    # Pattern 2: Check for range patterns "3-5 years", "2 to 5 years"
    range_patterns = re.findall(r'(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years|yrs|year|yr)', text)
    for min_exp, max_exp in range_patterns:
        min_years = int(min_exp)
        max_years = int(max_exp)
        
        # Accept if range overlaps with 2-5 years
        # e.g., "3-5 years" ✅, "2-4 years" ✅, "1-3 years" ✅
        # Reject if minimum is > 5, e.g., "6-8 years" ❌
        if min_years > 5:
            return False
        # Reject if maximum is explicitly high and minimum is also high
        # e.g., "5-7 years" borderline, but we'll be lenient
        if min_years >= 5 and max_years > 6:
            return False
        # Otherwise acceptable
        return True
    
    # Pattern 3: Check for standalone numbers like "5 years of experience"
    standalone = re.findall(r'(?:^|\s)(\d+)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)', text)
    for match in standalone:
        years = int(match)
        if years > 5:
            return False  # Too senior
        if years >= 2 and years <= 5:
            return True  # Perfect match
    
    # Pattern 4: Check for "minimum X years"
    min_patterns = re.findall(r'(?:minimum|min|at least|minimum of)\s*(\d+)\s*(?:years?|yrs?)', text)
    for match in min_patterns:
        years = int(match)
        if years > 5:
            return False  # Requires too much experience
        if years >= 2 and years <= 5:
            return True  # Acceptable minimum
    
    # If no experience mentioned at all → we'll apply (entry-level or flexible)
    return True

# ──────────────────────────────────────────────────────
# LOAD COMPANIES FROM FILE
# ──────────────────────────────────────────────────────
def load_companies() -> list:
    """
    Load companies from file. Supports two formats:
      1. Explicit: "ats:slug" (e.g., "greenhouse:openai")
      2. Auto-detect: "slug" (tries lever, greenhouse, ashby, workday)
    """
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
                # Explicit format: "ats:slug"
                ats, slug = line.split(":", 1)
                key = (ats.strip().lower(), slug.strip().lower())
                if key not in seen_slugs:
                    seen_slugs.add(key)
                    companies.append(key)
            else:
                # Auto-detect format: try all ATS platforms for this slug
                slug = line.strip().lower()
                
                # Try Lever
                if ("lever", slug) not in seen_slugs:
                    seen_slugs.add(("lever", slug))
                    companies.append(("lever", slug))
                
                # Try Greenhouse
                if ("greenhouse", slug) not in seen_slugs:
                    seen_slugs.add(("greenhouse", slug))
                    companies.append(("greenhouse", slug))
                
                # Try Ashby
                if ("ashby", slug) not in seen_slugs:
                    seen_slugs.add(("ashby", slug))
                    companies.append(("ashby", slug))
                
                # Try Workday if it's in the tenants list
                if slug in WORKDAY_TENANTS:
                    if ("workday", slug) not in seen_slugs:
                        seen_slugs.add(("workday", slug))
                        companies.append(("workday", slug))
    
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
# FETCH JOBS — LEVER  (concurrent-safe)
# ──────────────────────────────────────────────────────
def fetch_lever(slug: str) -> list:
    with _SEM["lever"]:
        try:
            s = _get_session()
            r = s.get(
                f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=100",
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code == 404:
                _mark_dead("lever", slug)
                return []
            if r.status_code != 200:
                return []
            data = r.json()
            if not isinstance(data, list):
                return []
            jobs = []
            for job in data:
                posted = job.get("createdAt", 0)
                # Extract description (plain text summary)
                description = job.get("description", "")
                if not description:
                    description = job.get("descriptionPlain", "")
                jobs.append({
                    "title":       job.get("text", ""),
                    "company":     slug.replace("-", " ").title(),
                    "location":    job.get("categories", {}).get("location", ""),
                    "link":        job.get("hostedUrl", ""),
                    "source":      "Lever",
                    "posted":      datetime.fromtimestamp(posted/1000).strftime("%d %b %Y") if posted else "N/A",
                    "description": description[:1000]  # First 1000 chars for filtering
                })
            return jobs
        except Exception:
            return []

# ──────────────────────────────────────────────────────
# FETCH JOBS — GREENHOUSE  (concurrent-safe)
# ──────────────────────────────────────────────────────
def fetch_greenhouse(slug: str) -> list:
    with _SEM["greenhouse"]:
        try:
            s = _get_session()
            r = s.get(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code == 404:
                _mark_dead("greenhouse", slug)
                return []
            if r.status_code != 200:
                return []
            jobs = []
            for job in r.json().get("jobs", []):
                # Extract description (Greenhouse has content field)
                description = job.get("content", "")
                jobs.append({
                    "title":       job.get("title", ""),
                    "company":     slug.replace("-", " ").title(),
                    "location":    job.get("location", {}).get("name", ""),
                    "link":        job.get("absolute_url", ""),
                    "source":      "Greenhouse",
                    "posted":      job.get("updated_at", "")[:10],
                    "description": description[:1000]  # First 1000 chars for filtering
                })
            return jobs
        except Exception:
            return []

# ──────────────────────────────────────────────────────
# FETCH JOBS — ASHBY  (concurrent-safe)
# ──────────────────────────────────────────────────────
def fetch_ashby(slug: str) -> list:
    with _SEM["ashby"]:
        try:
            s = _get_session()
            r = s.get(
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code == 404:
                _mark_dead("ashby", slug)
                return []
            if r.status_code != 200:
                return []
            jobs = []
            for job in r.json().get("jobs", []):
                # Extract description from Ashby
                description = job.get("description", "")
                jobs.append({
                    "title":       job.get("title", ""),
                    "company":     slug.replace("-", " ").title(),
                    "location":    job.get("location", "") or "Remote",
                    "link":        job.get("jobUrl", ""),
                    "source":      "Ashby",
                    "posted":      job.get("publishedAt", "")[:10] or "Recent",
                    "description": description[:1000]  # First 1000 chars for filtering
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

    with _SEM["workday"]:
        for search in search_terms:
            try:
                s = _get_session()
                url = f"https://{company_domain}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/External/jobs"
                r = s.post(
                    url,
                    json={"appliedFacets": {}, "limit": 20, "offset": 0,
                          "searchText": search},
                    headers={"Content-Type": "application/json"},
                    timeout=REQUEST_TIMEOUT
                )
                if r.status_code == 404:
                    _mark_dead("workday", slug)
                    break
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
                time.sleep(0.3)

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
# FETCH BY ATS — dispatcher (used by thread pool)
# ──────────────────────────────────────────────────────
def fetch_jobs(ats: str, slug: str) -> list:
    """Called from worker threads. Returns list of job dicts."""
    if _is_dead(ats, slug):
        return []          # skip known-dead slugs instantly
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
# PARALLEL FETCH — heart of v11 speed
# ──────────────────────────────────────────────────────
def fetch_all_companies(companies: list) -> tuple[list, dict]:
    """
    Fetches all companies concurrently.
    Returns (all_jobs, stats_dict).
    """
    all_jobs  = []
    stats     = {"lever": 0, "greenhouse": 0, "ashby": 0,
                 "workday": 0, "skipped": 0, "failed": 0}
    lock      = threading.Lock()
    done      = [0]        # mutable counter for progress

    total     = len(companies)

    def worker(ats: str, slug: str) -> tuple[str, str, list]:
        jobs = fetch_jobs(ats, slug)
        return ats, slug, jobs

    print(f"\n🚀 Fetching {total} companies with {MAX_WORKERS} parallel workers...\n")
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(worker, ats, slug): (ats, slug)
                   for ats, slug in companies}

        for future in as_completed(futures):
            ats, slug, jobs = future.result()
            with lock:
                done[0] += 1
                if jobs:
                    stats[ats] = stats.get(ats, 0) + 1
                    all_jobs.extend(jobs)
                    # Only log companies that returned results
                    print(f"  [{ats.upper():12}] {slug:35} → {len(jobs):3} jobs")
                else:
                    if _is_dead(ats, slug):
                        stats["skipped"] = stats.get("skipped", 0) + 1
                    else:
                        stats["failed"] = stats.get("failed", 0) + 1

                # Progress every 100 completions
                if done[0] % 100 == 0:
                    elapsed = time.time() - t_start
                    rate    = done[0] / elapsed
                    eta     = (total - done[0]) / rate if rate > 0 else 0
                    print(f"\n  📊 Progress: {done[0]}/{total} "
                          f"| {len(all_jobs)} jobs | "
                          f"{elapsed:.0f}s elapsed | ETA {eta:.0f}s\n")

    elapsed = time.time() - t_start
    print(f"\n  ✅ All {total} companies checked in {elapsed:.1f}s "
          f"({total/elapsed:.1f} companies/sec)\n")
    return all_jobs, stats

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
        ok = r.status_code == 200
        # Respect Telegram rate limit: 30 msgs/sec max → 0.05s min gap
        # Use 0.5s to be safe; batches of alerts are still fast
        time.sleep(0.5 if ok else 3)
        return ok
    except Exception as e:
        print(f"  [Telegram] Error: {e}")
        time.sleep(3)
        return False

def send_telegram_batch(jobs: list) -> int:
    """Send all new job alerts. Returns count sent."""
    sent = 0
    for job in jobs:
        print(f"🆕 {job['title']} @ {job['company']} | {job['location']}")
        if send_telegram(job):
            sent += 1
    return sent

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
def main():
    global _DEAD_CACHE
    _DEAD_CACHE = _load_dead_cache()

    t_start = time.time()
    print(f"\n{'━'*60}")
    print(f"🤖 AI Job Alert Bot v11 (Parallel) — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*60}\n")

    seen      = load_seen()
    companies = load_companies()

    # ── SOURCE 1-4: ATS (Lever / Greenhouse / Ashby / Workday) ──
    print(f"🔍 Fetching {len(companies)} companies with {MAX_WORKERS} parallel workers…\n")
    all_jobs, stats = fetch_all_companies(companies)

    # ── SOURCE 5: Google CSE ──────────────────────────────────
    print(f"\n🌐 SOURCE 5: Google CSE (last 24 h fresh postings)…")
    try:
        cse_jobs = scrape_google()
        all_jobs += cse_jobs
        print(f"  ✅ Google CSE returned {len(cse_jobs)} jobs")
    except Exception as e:
        print(f"  ⚠️  Google CSE failed: {e}")

    # ── Deduplicate by URL ────────────────────────────────────
    seen_urls, unique = set(), []
    for j in all_jobs:
        if j.get("link") and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    # ── Role + Location filter ────────────────────────────────
    matched       = []
    skip_role     = 0
    skip_location = 0
    skip_company  = 0
    skip_closed   = 0
    skip_old_jobs = 0
    skip_experience = 0
    for j in unique:
        if not is_relevant_role(j["title"]):
            skip_role += 1
            continue
        if not is_relevant_location(j["location"]):
            skip_location += 1
            continue
        if is_excluded_company(j.get("company", "")):
            skip_company += 1
            continue
        if is_job_closed(j["title"], j.get("description", "")):
            skip_closed += 1
            continue
        if not is_posted_recently(j.get("posted", ""), j.get("source", "")):
            skip_old_jobs += 1
            continue
        if not has_acceptable_experience(j["title"], j.get("description", ""), j.get("exp", "")):
            skip_experience += 1
            continue
        matched.append(j)

    # ── Sort: Remote > Pune > India > rest ───────────────────
    def _loc_priority(job):
        loc = job.get("location", "").lower()
        if any(w in loc for w in ["remote", "worldwide", "anywhere", "distributed", "global"]):
            return 0
        if "pune" in loc:
            return 1
        if any(w in loc for w in ["india", "bengaluru", "bangalore", "hyderabad",
                                   "mumbai", "chennai", "noida", "gurgaon"]):
            return 2
        return 3
    matched.sort(key=_loc_priority)

    # ── Summary ───────────────────────────────────────────────
    elapsed = time.time() - t_start
    print(f"\n{'━'*60}")
    print(f"📊 ATS Breakdown (companies with ≥1 hit):")
    print(f"   🟡 Lever      : {stats.get('lever', 0)}")
    print(f"   🟢 Greenhouse : {stats.get('greenhouse', 0)}")
    print(f"   🔵 Ashby      : {stats.get('ashby', 0)}")
    print(f"   🟠 Workday    : {stats.get('workday', 0)}")
    print(f"   ❌ Failed/404 : {stats.get('failed', 0)}")
    print(f"\n⏱️  Fetch time            : {elapsed:.1f}s")
    print(f"📋 Total jobs scraped    : {len(unique)}")
    print(f"❌ Filtered (role)       : {skip_role}")
    print(f"❌ Filtered (location)   : {skip_location}")
    print(f"❌ Filtered (company)    : {skip_company}")
    print(f"❌ Filtered (closed)     : {skip_closed}")
    print(f"❌ Filtered (old >24h)   : {skip_old_jobs}")
    print(f"❌ Filtered (experience) : {skip_experience}")
    print(f"✅ Matched for you       : {len(matched)}")
    print(f"{'━'*60}\n")

    # ── Send new alerts ───────────────────────────────────────
    new_jobs = []
    for job in matched:
        jid = make_id(job["link"])
        if jid not in seen:
            new_jobs.append(job)

    sent = send_telegram_batch(new_jobs)

    # Mark everything as seen
    for job in unique:
        if job.get("link"):
            seen.add(make_id(job["link"]))

    # Persist state
    save_seen(seen)
    global _DEAD_CACHE_DIRTY
    if _DEAD_CACHE_DIRTY:
        _save_dead_cache(_DEAD_CACHE)
        print(f"  💾 Dead-slug cache saved ({len(_DEAD_CACHE)} entries)")

    total_elapsed = time.time() - t_start
    print(f"\n{'━'*60}")
    print(f"✅ Done! {sent} new alerts sent to Telegram.  "
          f"Total time: {total_elapsed:.1f}s")
    print(f"{'━'*60}\n")

if __name__ == "__main__":
    main()
