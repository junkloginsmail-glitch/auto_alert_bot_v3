"""
🤖 AI Job Alert Bot v2 — Lever + Greenhouse (ALL Companies)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Author  : Akash Shinde (SpiDo)
Strategy:
  SOURCE 1 → Google Custom Search API  (finds ANY company, real-time)
  SOURCE 2 → Known company APIs        (Lever + Greenhouse, fast backup)
Notify  : Telegram (instant) + Email (backup)
Schedule: Every 1 hour via GitHub Actions (FREE)
"""

import os, json, time, hashlib, smtplib, requests, re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from groq import Groq

# ──────────────────────────────────────────────────────
# CONFIG — All values come from GitHub Secrets
# ──────────────────────────────────────────────────────
GROQ_API_KEY          = os.environ["GROQ_API_KEY"]
TELEGRAM_BOT_TOKEN    = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID      = os.environ["TELEGRAM_CHAT_ID"]
GOOGLE_API_KEY        = os.environ["GOOGLE_API_KEY"]        # Google Custom Search API key
GOOGLE_CSE_ID         = os.environ["GOOGLE_CSE_ID"]         # Custom Search Engine ID
EMAIL_SENDER          = os.environ.get("EMAIL_SENDER", "")
EMAIL_PASSWORD        = os.environ.get("EMAIL_APP_PASSWORD", "")
EMAIL_RECEIVER        = os.environ.get("EMAIL_RECEIVER", "akash.shinde@myyahoo.com")

SEEN_JOBS_FILE = "seen_jobs.json"

# ──────────────────────────────────────────────────────
# YOUR PROFILE — AI uses this for relevance scoring
# ──────────────────────────────────────────────────────
MY_PROFILE = """
Name: Akash Shinde | Experience: 3 years | Location: Pune, India
Open to: Remote India, Pune onsite, Bangalore onsite, visa sponsorship abroad

Skills: Java (Spring Boot), Python (FastAPI), LLMs, RAG pipelines,
LangChain, LangGraph, ChromaDB, FAISS, Sentence-Transformers,
Groq/OpenAI/Anthropic APIs, prompt engineering, LLM evaluation,
MLOps, AWS, Docker, Kubernetes, Jenkins CI/CD

Target roles: AI Engineer, GenAI Engineer, ML Backend Engineer,
LLM Engineer, Applied AI Engineer, NLP Engineer

Projects: AI Change Risk Predictor (XGBoost+FAISS+FastAPI),
RAG Document Intelligence (LangChain+FAISS), AI Code Reviewer (FastAPI+Groq)
"""

# ──────────────────────────────────────────────────────
# GOOGLE SEARCH QUERIES
# These find ANY company on Lever/Greenhouse posting
# AI/ML jobs for India — even posted 30 minutes ago!
# ──────────────────────────────────────────────────────
GOOGLE_QUERIES = [
    # Lever — India / Remote
    'site:jobs.lever.co "AI engineer" "India"',
    'site:jobs.lever.co "GenAI" OR "LLM" "India" OR "remote"',
    'site:jobs.lever.co "machine learning engineer" "India"',
    'site:jobs.lever.co "applied AI" OR "NLP engineer" "India"',
    'site:jobs.lever.co "backend engineer" "AI" OR "LLM" "India"',
    # Greenhouse — India / Remote
    'site:job-boards.greenhouse.io "AI engineer" "India"',
    'site:job-boards.greenhouse.io "GenAI" OR "LLM" "India" OR "remote India"',
    'site:job-boards.greenhouse.io "machine learning engineer" "India"',
    'site:job-boards.greenhouse.io "applied AI" "India"',
    'site:job-boards.greenhouse.io "backend" "LLM" OR "RAG" "India"',
]

# ──────────────────────────────────────────────────────
# KNOWN COMPANIES — fast API polling as backup
# ──────────────────────────────────────────────────────
LEVER_COMPANIES = [
    "databricks", "scale", "huggingface", "anthropic", "mistral",
    "wandb", "cohere", "together", "perplexity", "anyscale",
    "runwayml", "stability", "adept", "emi-labs", "weekdayworks",
    "smart-working-solutions", "boldbusiness", "cognite", "thinkahead",
]

GREENHOUSE_COMPANIES = [
    "databricks", "coinbase", "particle41llc", "bswiftindia", "builtin",
    "gitlab", "apolloio", "samsara", "clarifai", "boldbusiness",
    "airslate", "asapp-2", "levelai", "pay2dc", "degreed",
    "clickup", "welocalize",
]

# ──────────────────────────────────────────────────────
# SEEN JOBS — prevents duplicate Telegram alerts
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
# SOURCE 1 — Google Custom Search API
# Finds ANY company posting on Lever or Greenhouse
# 100 free queries/day, each returns 10 results = 1000 jobs/day
# dateRestrict=d1 means only last 24 hours → catches fresh postings!
# ──────────────────────────────────────────────────────
def scrape_via_google() -> list:
    jobs = []
    seen_urls = set()

    for query in GOOGLE_QUERIES:
        try:
            res = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key":          GOOGLE_API_KEY,
                    "cx":           GOOGLE_CSE_ID,
                    "q":            query,
                    "num":          10,
                    "dateRestrict": "d1",  # ← ONLY last 24 hours
                },
                timeout=10
            )
            if res.status_code != 200:
                print(f"[Google] HTTP {res.status_code} → {query[:50]}")
                continue

            items = res.json().get("items", [])
            print(f"[Google] {len(items):2d} results → {query[:60]}")

            for item in items:
                link    = item.get("link", "")
                title   = item.get("title", "")
                snippet = item.get("snippet", "")

                if not link or link in seen_urls:
                    continue
                if "jobs.lever.co" not in link and "job-boards.greenhouse.io" not in link:
                    continue

                # Clean title
                title = re.sub(r"\s*[-|]\s*(Lever|Greenhouse).*$", "", title).strip()

                # Extract company name from URL
                if "jobs.lever.co" in link:
                    slug    = link.split("jobs.lever.co/")[-1].split("/")[0]
                    source  = "Lever"
                else:
                    slug    = link.split("job-boards.greenhouse.io/")[-1].split("/")[0]
                    source  = "Greenhouse"
                company = slug.replace("-", " ").title()

                seen_urls.add(link)
                jobs.append({
                    "title":       title,
                    "company":     company,
                    "location":    "Check posting",
                    "link":        link,
                    "description": snippet,
                    "source":      f"{source} via Google",
                    "posted_at":   "< 24 hours ago"
                })

            time.sleep(0.5)

        except Exception as e:
            print(f"[Google] Error: {e}")

    print(f"[Google] Total: {len(jobs)} unique fresh jobs found")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 2A — Lever Known Companies API
# ──────────────────────────────────────────────────────
def scrape_lever_known() -> list:
    jobs = []
    for company in LEVER_COMPANIES:
        try:
            res = requests.get(
                f"https://api.lever.co/v0/postings/{company}?mode=json&limit=50",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=8
            )
            if res.status_code != 200:
                continue
            for job in res.json():
                posted = job.get("createdAt", 0)
                jobs.append({
                    "title":       job.get("text", ""),
                    "company":     company.replace("-", " ").title(),
                    "location":    job.get("categories", {}).get("location", ""),
                    "link":        job.get("hostedUrl", ""),
                    "description": job.get("descriptionPlain", "")[:600],
                    "source":      "Lever",
                    "posted_at":   datetime.fromtimestamp(posted/1000).strftime("%d %b %Y") if posted else "N/A"
                })
        except Exception as e:
            print(f"[Lever] {company}: {e}")
        time.sleep(0.2)
    print(f"[Lever Known] {len(jobs)} jobs fetched")
    return jobs

# ──────────────────────────────────────────────────────
# SOURCE 2B — Greenhouse Known Companies API
# ──────────────────────────────────────────────────────
def scrape_greenhouse_known() -> list:
    jobs = []
    for company in GREENHOUSE_COMPANIES:
        try:
            res = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=8
            )
            if res.status_code != 200:
                continue
            for job in res.json().get("jobs", []):
                jobs.append({
                    "title":       job.get("title", ""),
                    "company":     company.replace("-", " ").title(),
                    "location":    job.get("location", {}).get("name", ""),
                    "link":        job.get("absolute_url", ""),
                    "description": job.get("content", "")[:600],
                    "source":      "Greenhouse",
                    "posted_at":   job.get("updated_at", "")[:10]
                })
        except Exception as e:
            print(f"[Greenhouse] {company}: {e}")
        time.sleep(0.3)
    print(f"[Greenhouse Known] {len(jobs)} jobs fetched")
    return jobs

# ──────────────────────────────────────────────────────
# AI RELEVANCE SCORER — Groq llama-3.3-70b
# ──────────────────────────────────────────────────────
def is_relevant(job: dict) -> tuple[bool, str]:
    try:
        r = Groq(api_key=GROQ_API_KEY).chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"""You are a job relevance evaluator.

CANDIDATE:
{MY_PROFILE}

JOB:
Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Description: {job['description'][:500]}

Is this job relevant to the candidate?
Check: (1) AI/ML/GenAI/LLM/NLP backend role (2) India/India-remote/worldwide remote (3) 1-6 years exp

Reply ONLY as JSON, no extra text:
{{"relevant": true/false, "score": 1-10, "reason": "one line"}}"""}],
            temperature=0.1, max_tokens=120
        )
        raw    = re.sub(r"```json|```", "", r.choices[0].message.content).strip()
        result = json.loads(raw)
        return result.get("relevant", False) and result.get("score", 0) >= 6, result.get("reason", "")
    except Exception as e:
        print(f"[AI] {e}")
        return False, ""

# ──────────────────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────────────────
def send_telegram(job: dict, reason: str):
    icon = "🟡" if "Lever" in job["source"] else "🟢"
    msg  = f"""{icon} *New AI Job Alert!*

📌 *{job['title']}*
🏢 {job['company']}
📍 {job['location']}
📅 {job['posted_at']}
🔍 {job['source']}

🤖 _{reason}_

🔗 [Apply Now]({job['link']})"""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg.strip(),
                  "parse_mode": "Markdown", "disable_web_page_preview": False},
            timeout=10
        )
        print(f"[Telegram] {'✅' if r.status_code==200 else '❌'} {job['title']} @ {job['company']}")
    except Exception as e:
        print(f"[Telegram] {e}")

# ──────────────────────────────────────────────────────
# EMAIL (backup)
# ──────────────────────────────────────────────────────
def send_email(job: dict, reason: str):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🤖 {job['title']} @ {job['company']}"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = EMAIL_RECEIVER
        msg.attach(MIMEText(f"""<html><body style="font-family:sans-serif;max-width:580px;margin:auto;padding:20px">
          <div style="background:#4F46E5;padding:16px;border-radius:8px 8px 0 0">
            <h2 style="color:white;margin:0">🤖 New AI Job Alert</h2></div>
          <div style="border:1px solid #e5e7eb;border-top:none;padding:20px;border-radius:0 0 8px 8px">
            <h3>{job['title']}</h3>
            <p><b>🏢</b> {job['company']}</p>
            <p><b>📍</b> {job['location']}</p>
            <p><b>📅</b> {job['posted_at']}</p>
            <p><b>🔍</b> {job['source']}</p>
            <p><b>🤖</b> <i>{reason}</i></p><br>
            <a href="{job['link']}" style="background:#4F46E5;color:white;padding:12px 24px;
               border-radius:6px;text-decoration:none;font-weight:bold">Apply Now →</a>
          </div></body></html>""", "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        print(f"[Email] ✅ {job['title']}")
    except Exception as e:
        print(f"[Email] {e}")

# ──────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────
def main():
    print(f"\n{'━'*56}")
    print(f"🤖 AI Job Alert Bot v2 — {datetime.now().strftime('%d %b %Y %H:%M')}")
    print(f"{'━'*56}\n")

    seen = load_seen()
    new_count = 0

    # Collect from all 3 sources
    all_jobs = []
    print("🌐 SOURCE 1: Google Search (ANY company, last 24h)...")
    all_jobs += scrape_via_google()
    print("\n📡 SOURCE 2A: Lever Known Companies...")
    all_jobs += scrape_lever_known()
    print("\n📡 SOURCE 2B: Greenhouse Known Companies...")
    all_jobs += scrape_greenhouse_known()

    # Deduplicate by URL
    seen_urls, unique = set(), []
    for j in all_jobs:
        if j["link"] and j["link"] not in seen_urls:
            seen_urls.add(j["link"])
            unique.append(j)

    print(f"\n{'━'*56}")
    print(f"📊 {len(unique)} unique jobs to evaluate")
    print(f"🧠 AI scoring...\n")

    for job in unique:
        if not job["link"]:
            continue
        jid = make_id(job["link"])
        if jid in seen:
            continue

        relevant, reason = is_relevant(job)
        if relevant:
            print(f"✅ MATCH → {job['title']} @ {job['company']} | {job['location']}")
            send_telegram(job, reason)
            send_email(job, reason)
            new_count += 1
            time.sleep(1.5)
        else:
            print(f"⏭️  Skip → {job['title']} @ {job['company']}")

        seen.add(jid)

    save_seen(seen)
    print(f"\n{'━'*56}")
    print(f"✅ Done! {new_count} new alerts sent.")
    print(f"{'━'*56}\n")

if __name__ == "__main__":
    main()
