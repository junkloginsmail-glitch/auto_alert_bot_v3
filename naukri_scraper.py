"""
🇮🇳 Naukri Scraper
━━━━━━━━━━━━━━━━━━
STEP 2 → Search by job TITLE (last 24h) for all target roles
STEP 3 → Same but broader keyword search
Both use jobAge=1 → catches any job posted within 2hr cycle
seen_jobs.json dedup → same as Lever/Greenhouse logic ✅
"""

import requests, time
from bs4 import BeautifulSoup

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.naukri.com/",
    "appid":           "109",
    "systemid":        "109",
})

# ── ALL target job titles (Java + AI) ─────────────────────────
# These are searched on Naukri every 2 hours
# Any new posting matching these → Telegram notification
TARGET_TITLES = [
    # ── AI / GenAI / LLM ──────────────────────────────────
    "ai engineer",
    "applied ai engineer",
    "ai platform engineer",
    "generative ai engineer",
    "genai engineer",
    "llm engineer",
    "agentic ai engineer",
    "ai agent developer",
    "nlp engineer",
    "machine learning engineer",
    "ml engineer",
    "deep learning engineer",
    "mlops engineer",
    "computer vision engineer",
    "rag engineer",
    "langchain developer",
    "ai backend engineer",
    "ai developer",
    "ai researcher",
    "conversational ai engineer",
    "prompt engineer",
    "ai ml engineer",
    # ── Java / Backend ────────────────────────────────────
    "java developer",
    "java engineer",
    "java backend developer",
    "java backend engineer",
    "spring boot developer",
    "spring boot engineer",
    "java microservices developer",
    "java full stack developer",
    "java software engineer",
    "java software developer",
    "java api developer",
    "java cloud developer",
    "java developer ai",
    # ── Python Backend ────────────────────────────────────
    "python backend developer",
    "python developer",
    "fastapi developer",
    "python ai developer",
    "python engineer",
    # ── General SWE / Backend ─────────────────────────────
    "backend developer",
    "backend engineer",
    "software engineer",
    "software developer",
    "full stack developer",
    "full stack engineer",
    "sde 2",
    "sde ii",
    "member of technical staff",
]

# Search in these locations
LOCATIONS = ["india", "remote"]

def _init_session():
    """Visit homepage to get session cookies — avoids 403"""
    try:
        SESSION.get("https://www.naukri.com/", timeout=10)
        time.sleep(1)
    except Exception:
        pass

def _api_search(keyword: str, location: str) -> list:
    """
    Naukri internal API search
    jobAge=1 → only jobs posted in last 24 hours
    Within 2hr cycle → catches any new posting ✅
    """
    try:
        r = SESSION.get(
            "https://www.naukri.com/jobapi/v3/search",
            params={
                "noOfResults":  50,
                "urlType":      "search_by_key_loc",
                "searchType":   "adv",
                "keyword":      keyword,
                "location":     location,
                "experience":   0,     # 0 years min
                "experienceDD": 6,     # 6 years max
                "jobAge":       1,     # ← LAST 24 HOURS ONLY
            },
            timeout=15
        )
        if r.status_code == 200:
            return r.json().get("jobDetails", [])
        print(f"  [Naukri API] HTTP {r.status_code} for '{keyword}'")
    except Exception as e:
        print(f"  [Naukri API] Error for '{keyword}': {e}")
    return []

def _html_search(keyword: str, location: str) -> list:
    """HTML fallback if API blocked"""
    jobs = []
    try:
        slug = keyword.replace(" ", "-")
        url  = (f"https://www.naukri.com/{slug}-jobs-in-{location}"
                f"?experience=0&experienceDD=6&jobAge=1")
        r = SESSION.get(url, timeout=15)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("article.jobTuple, div.jobTuple"):
            t = card.select_one("a.title")
            c = card.select_one("a.subTitle")
            l = card.select_one("li.location span")
            e = card.select_one("li.experience span")
            s = card.select_one("li.salary span")
            if not t:
                continue
            link = t.get("href", "")
            if not link.startswith("http"):
                link = "https://www.naukri.com" + link
            jobs.append({
                "_html":    True,
                "title":    t.get_text(strip=True),
                "company":  c.get_text(strip=True) if c else "",
                "location": l.get_text(strip=True) if l else location,
                "link":     link,
                "id":       link.split("?")[0].split("-")[-1],
                "exp":      e.get_text(strip=True) if e else "",
                "salary":   s.get_text(strip=True) if s else "",
            })
    except Exception as e:
        print(f"  [Naukri HTML] {e}")
    return jobs

def _normalise(raw: dict) -> dict:
    """Standardise API or HTML job into common format"""
    if raw.get("_html"):
        return {
            "id":       raw.get("id", raw.get("link", "")),
            "title":    raw["title"],
            "company":  raw["company"],
            "location": raw["location"],
            "link":     raw["link"],
            "source":   "Naukri",
            "posted":   "Today",
            "salary":   raw.get("salary", ""),
            "exp":      raw.get("exp", ""),
        }
    ph     = raw.get("placeholders", [])
    loc    = ph[0].get("label", "") if ph else ""
    salary = ph[1].get("label", "") if len(ph) > 1 else ""
    exp    = ph[2].get("label", "") if len(ph) > 2 else ""
    jd     = raw.get("jdURL", "")
    link   = (f"https://www.naukri.com{jd}"
              if jd and not jd.startswith("http") else jd)
    return {
        "id":       str(raw.get("jobId", link)),
        "title":    raw.get("title", ""),
        "company":  raw.get("companyName", ""),
        "location": loc,
        "link":     link,
        "source":   "Naukri",
        "posted":   raw.get("footerPlaceholderLabel", "Today"),
        "salary":   salary,
        "exp":      exp,
    }

def scrape_naukri() -> list:
    """
    Main entry — called every 2 hours by job_alert.py
    Searches ALL target titles × ALL locations
    jobAge=1 → only last 24h → within 2hr cycle catches fresh postings
    seen_jobs.json dedup → no duplicate alerts
    """
    print("  [Naukri] Initialising session...")
    _init_session()

    all_jobs = []
    seen_ids = set()
    total    = len(TARGET_TITLES) * len(LOCATIONS)
    done     = 0

    for title in TARGET_TITLES:
        for location in LOCATIONS:
            done += 1

            # Try API first, fallback to HTML
            raw_list = _api_search(title, location)
            if not raw_list:
                raw_list = _html_search(title, location)

            new = 0
            for raw in raw_list:
                job = _normalise(raw)
                uid = job["id"] or job["link"]
                if not uid or uid in seen_ids:
                    continue
                seen_ids.add(uid)
                all_jobs.append(job)
                new += 1

            if new > 0:
                print(f"  [Naukri] '{title}' in {location} → {new} new jobs")

            # Progress every 20 searches
            if done % 20 == 0:
                print(f"  [Naukri] {done}/{total} searches, "
                      f"{len(all_jobs)} unique jobs so far...")

            time.sleep(0.4)  # polite rate limit

    print(f"[Naukri] ✅ {len(all_jobs)} unique fresh jobs found (last 24h)")
    return all_jobs
