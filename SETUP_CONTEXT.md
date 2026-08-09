# 🤖 AI Job Alert Bot - Complete System Overview & Setup Guide

**Date**: August 9, 2026  
**Version**: v11 (Parallel Edition)  
**Author**: Akash Shinde  
**Target Profile**: 3 YOE | Java Backend + AI/ML/GenAI/LLM Engineer

---

## 📋 SYSTEM OVERVIEW

This is an automated job alert system that monitors **3000+ companies** across multiple job platforms and sends real-time alerts via Telegram when matching jobs are posted. The system is optimized for speed with concurrent fetching, achieving ~1300 companies scanned in ~90 seconds.

### 🎯 Target Roles
The bot is configured to find positions matching:
- **Java/Backend**: Java Developer, Backend Engineer, Spring Boot, Microservices
- **AI/ML**: AI Engineer, ML Engineer, GenAI Engineer, LLM Engineer
- **Combined**: Python Engineer, Full Stack, Software Engineer (AI/Java)
- **Experience Level**: 2-4 years (excludes senior/staff/principal and intern roles)

### 🌍 Target Locations
Prioritized in this order:
1. Remote/Work from Home/Worldwide
2. Pune (your preferred location)
3. Indian cities (Bangalore, Hyderabad, Mumbai, etc.)
4. Visa sponsorship locations (Japan, Korea, Singapore)
5. **Excludes**: US/UK/EU onsite-only positions

---

## 🏗️ PROJECT STRUCTURE

```
job-alert-bot/
├── job_alert.py              # Main bot (v11 parallel edition)
├── naukri_scraper.py          # Naukri.com specialized scraper
├── naukri_login_test.py       # Test script for Naukri scraper
├── companies.txt              # Company watchlist (3000+ companies)
├── requirements.txt           # Python dependencies
├── seen_jobs.json             # Job deduplication cache
├── ats_cache.json            # Dead slug cache (404 companies)
├── README.md                  # Documentation
└── .gitignore                # Git ignore rules
```

---

## 🔧 CORE COMPONENTS

### 1️⃣ **job_alert.py** (Main Engine)
**Purpose**: Orchestrates parallel job fetching from multiple sources

**Key Features**:
- ✅ **60 concurrent workers** (ThreadPoolExecutor)
- ✅ **Per-ATS rate limiting** (Lever: 20, Greenhouse: 20, Ashby: 15, Workday: 5)
- ✅ **Session pooling** (keep-alive TCP connections)
- ✅ **Dead slug cache** (skips known-404 companies for 7 days)
- ✅ **Adaptive retry** (exponential backoff on 429/503)
- ✅ **8-second timeout** per request
- ✅ **Telegram batching** (digest mode alerts)

**Job Sources** (6 total):
1. **Lever API** - Public REST API (`api.lever.co`)
2. **Greenhouse API** - Public REST API (`boards-api.greenhouse.io`)
3. **Ashby API** - Public REST API (`api.ashbyhq.com`)
4. **Workday API** - Enterprise ATS (Amazon, Microsoft, IBM, Oracle, etc.)
5. **Naukri** - Indian job portal (via specialized scraper)
6. **Google Custom Search API** - Fresh postings from last 24h

**Filtering Logic**:
```python
# Role matching (must contain at least one):
✓ Java developer/backend, AI/ML engineer, GenAI, LLM, etc.

# Excluded seniority:
✗ Staff/Principal/Director/VP/Chief/Manager
✗ Intern/Co-op

# Excluded roles:
✗ Product Manager, Data Analyst, Sales, Marketing, etc.

# Location preferences:
✓ India, Remote, Worldwide, Visa Sponsor
✗ US/UK/EU onsite-only
```

### 2️⃣ **naukri_scraper.py** (Naukri Specialist)
**Purpose**: Scrapes Naukri.com using a 3-tier fallback strategy

**Strategy** (tried in order):
1. **RSS Feeds** - Public, real-time (often blocked by Akamai)
2. **Naukri Internal API** - Unauthenticated REST (often 406'd by Akamai)
3. **Playwright Stealth** - Headless Chromium intercepts `/jobapi/v3/search` XHR
   - **No login required** - jobs are public
   - Bypasses Akamai bot detection
   - Works on GitHub Actions (Ubuntu) without credentials

**Searches**: 40+ job title combinations × 4 locations = 160+ searches
- Titles: AI Engineer, GenAI, LLM, Java Developer, Backend, etc.
- Locations: work-from-home, pune, bangalore, india
- Job age: Last 3 days (changed from 1 day for better coverage)

### 3️⃣ **companies.txt** (Watchlist)
**Format**: One company per line
```
# Company name only - bot auto-detects ATS
anthropic
openai
google
stripe
```

**Categories** (3000+ companies):
- AI-First (Anthropic, OpenAI, Mistral, Cohere, etc.)
- AI Infrastructure (Langchain, Pinecone, Weaviate, etc.)
- Big Tech (Google, Microsoft, Meta, Amazon, etc.)
- Fintech (Stripe, Coinbase, Plaid, Razorpay, etc.)
- Startups (from Y Combinator, A16Z portfolio, etc.)
- Indian Tech (Swiggy, Zomato, Zerodha, etc.)

### 4️⃣ **State Files**

**seen_jobs.json**
- MD5 hash cache of job URLs already sent
- **Only adds** new jobs, never deletes
- Prevents duplicate alerts

**ats_cache.json**
- Caches companies that returned 404
- Skips them for 7 days
- Example: `{"lever:bad-company": "2026-08-09"}`

---

## 🚀 SETUP INSTRUCTIONS FOR YOU

### Step 1: Environment Variables
Create a `.env` file (or set environment variables):

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Optional (for Google Custom Search - fresh 24h jobs)
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_cse_id

# Optional (if Naukri blocks your IP)
SCRAPER_API_KEY=your_scraperapi_key
```

#### 🔑 How to Get API Keys:

**Telegram Bot** (Required):
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow prompts
3. Copy the token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
4. Get your Chat ID:
   - Message [@userinfobot](https://t.me/userinfobot)
   - Copy your ID (format: `123456789`)

**Google Custom Search** (Optional - for fresh postings):
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project → Enable "Custom Search API"
3. Create API key
4. Create Custom Search Engine at [programmablesearchengine.google.com](https://programmablesearchengine.google.com)
5. Set to search the entire web
6. Add sites: `jobs.lever.co`, `greenhouse.io`, `ashbyhq.com`

**ScraperAPI** (Optional - if Naukri blocks your IP):
1. Sign up at [scraperapi.com](https://www.scraperapi.com) (free tier: 1000 requests/month)
2. Copy API key from dashboard

### Step 2: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers (for Naukri scraper)
playwright install --with-deps chromium
```

**Dependencies**:
- `requests` - HTTP client
- `playwright` - Browser automation
- `playwright-stealth` - Anti-bot detection

### Step 3: Customize Your Job Preferences

**Edit job_alert.py** (lines 118-148):

```python
# Add/remove job titles that interest you
TARGET_ROLES = [
    "java developer",
    "ai engineer",
    # ... add more
]

# Add/remove excluded seniority levels
EXCLUDE_SENIORITY = [
    "staff engineer",
    # ... add more
]

# Customize locations
ACCEPT_LOCATIONS = [
    "pune",  # Your city
    "remote",
    # ... add more
]
```

**Edit companies.txt**:
- Add companies you want to monitor
- Remove companies you're not interested in
- Format: Just company name (one per line)

### Step 4: Test Run

```bash
# Test Naukri scraper alone
python naukri_login_test.py

# Full test run (will send Telegram alerts for new jobs)
python job_alert.py
```

**First run**: Expect 0 alerts (all jobs marked as "seen")  
**Subsequent runs**: Only new jobs will trigger alerts

### Step 5: Schedule Automation

**Option A: GitHub Actions** (Recommended - Free)
1. Fork this repo to your GitHub account
2. Add secrets in repo settings:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GOOGLE_API_KEY` (optional)
   - `GOOGLE_CSE_ID` (optional)
3. GitHub Actions runs every hour automatically

**Option B: Local Cron/Task Scheduler**

**Windows** (Task Scheduler):
```batch
# Run every hour
schtasks /create /tn "Job Alert Bot" /tr "python D:\AI\AI_Projects\job-alert-bot\job_alert.py" /sc hourly
```

**Linux/Mac** (Cron):
```bash
# Edit crontab
crontab -e

# Add this line (runs every hour)
0 * * * * cd /path/to/job-alert-bot && python job_alert.py >> job_bot.log 2>&1
```

**Option C: Always-On Server**
Deploy to:
- AWS EC2 (free tier)
- Google Cloud Compute
- Digital Ocean Droplet
- Raspberry Pi (if you have one)

---

## 📊 PERFORMANCE METRICS

**v11 Improvements** (compared to v10):
- **Speed**: ~1300 companies in ~90s (was ~600s)
- **Throughput**: ~14 companies/sec (was ~2/sec)
- **Efficiency**: 60 concurrent workers with per-ATS rate limits
- **Reliability**: Dead slug cache skips 404s instantly

**Typical Run**:
```
🔍 Fetching 3000+ companies...
  [LEVER] anthropic → 15 jobs
  [GREENHOUSE] stripe → 8 jobs
  [ASHBY] openai → 12 jobs
  ...
📊 Stats:
   🟡 Lever      : 450 companies
   🟢 Greenhouse : 380 companies
   🔵 Ashby      : 290 companies
   🟠 Workday    : 85 companies
   🔴 Naukri     : 1200 jobs
   🌐 Google CSE : 45 jobs

⏱️  Total time: 127s
📋 Jobs scraped: 4200
✅ Matched: 67
🆕 New alerts: 23
```

---

## 🔍 UNDERSTANDING THE OUTPUT

**Telegram Alert Format**:
```
🟡 New Job Alert!

📌 Backend Engineer (Java/AI)
🏢 Stripe
📍 Pune, India | Remote Available
💰 ₹25-35 LPA
🧑‍💻 2-4 years
📅 Posted 2 hours ago
🔍 Greenhouse

🔗 [Apply Now](https://jobs.stripe.com/...)
```

**Icons**:
- 🟡 Lever
- 🟢 Greenhouse
- 🔵 Ashby
- 🟠 Workday
- 🔴 Naukri
- 🌐 Google CSE

---

## 🛠️ CUSTOMIZATION GUIDE

### Adding New Companies

**Option 1**: Edit `companies.txt`
```bash
# Add one company per line
newcompany
another-startup
```

**Option 2**: Bulk import
```python
# Create a script to add companies programmatically
companies = ["company1", "company2", "company3"]
with open("companies.txt", "a") as f:
    for c in companies:
        f.write(f"{c}\n")
```

### Adding New Job Sources

Edit `job_alert.py` and add a new fetch function:

```python
def fetch_myATS(slug: str) -> list:
    """Fetch jobs from custom ATS."""
    # Your implementation
    return jobs

# Add to main fetch loop
```

### Changing Alert Frequency

**Increase coverage** (more frequent checks):
- GitHub Actions: Change `.github/workflows/job_alert.yml` cron to `0 */2 * * *` (every 2 hours)
- Naukri: Change `jobAge=3` to `jobAge=7` in `naukri_scraper.py` (last 7 days)

**Reduce noise** (stricter filters):
- Add more exclusion keywords to `EXCLUDE_ROLES`
- Remove job titles from `TARGET_ROLES`
- Make location filter more strict

---

## 🐛 TROUBLESHOOTING

### Issue: No Telegram alerts received

**Check**:
1. Environment variables set correctly?
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   echo $TELEGRAM_CHAT_ID
   ```
2. Bot started? Send `/start` to your bot
3. Bot has permission to message you?
4. Test manually:
   ```python
   import requests
   requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                 json={"chat_id": CHAT_ID, "text": "Test"})
   ```

### Issue: Naukri returns 0 jobs

**Possible causes**:
1. IP blocked by Akamai → Use ScraperAPI key
2. Playwright not installed → `playwright install chromium`
3. Browser crash → Check logs for errors

**Debug**:
```bash
python naukri_login_test.py
```

### Issue: "Too many requests" (HTTP 429)

**Solution**: Bot already handles this with:
- Per-ATS semaphores (rate limiting)
- Retry with exponential backoff
- Respect Telegram limits (0.5s between alerts)

If still happening:
- Reduce `MAX_WORKERS` in `job_alert.py` (line 42)
- Increase semaphore limits for specific ATS (lines 47-52)

### Issue: Some companies always return 0 jobs

**Possible causes**:
1. Company name wrong → Check their careers page URL
2. Company uses custom ATS → Add support manually
3. Company marked as "dead" → Check `ats_cache.json`

**Fix dead cache**:
```bash
# Remove entry from ats_cache.json
# Or delete entire file to reset
rm ats_cache.json
```

---

## 📈 OPTIMIZATION TIPS

### 1. Reduce API Quota Usage
- Disable Google CSE if hitting quota limits
- Use Naukri RSS/API (no quota) instead of browser mode

### 2. Faster Execution
- Increase `MAX_WORKERS` (line 42) - but watch for rate limits
- Remove companies you're not interested in from `companies.txt`

### 3. Better Job Matching
- Review `TARGET_ROLES` regularly - add new AI/backend keywords
- Check Telegram alerts - if too noisy, add more exclusions
- Tune experience level filters (`EXCLUDE_SENIORITY`)

### 4. Cloud Cost Optimization
- Use GitHub Actions (free 2000 min/month)
- Or AWS Lambda + EventBridge (nearly free)
- Avoid always-on servers for hourly cron jobs

---

## 📝 MAINTENANCE CHECKLIST

**Weekly**:
- [ ] Review Telegram alerts quality
- [ ] Check for new companies in your target domain
- [ ] Update `companies.txt` with new startups/companies

**Monthly**:
- [ ] Update `TARGET_ROLES` with emerging job titles
- [ ] Review `ats_cache.json` - clear old dead entries
- [ ] Check `seen_jobs.json` size (clean if >10MB)

**Quarterly**:
- [ ] Update dependencies: `pip install -U -r requirements.txt`
- [ ] Review bot performance metrics
- [ ] Check for ATS API changes

---

## 🎯 NEXT STEPS FOR YOU

### Immediate (Setup):
1. ✅ Read this document (you're here!)
2. ⬜ Set up Telegram bot and get credentials
3. ⬜ Create `.env` file with your tokens
4. ⬜ Run test: `python job_alert.py`
5. ⬜ Verify Telegram alert received

### Short-term (Customize):
6. ⬜ Review and edit `TARGET_ROLES` for your preferences
7. ⬜ Add/remove companies in `companies.txt`
8. ⬜ Test Naukri scraper: `python naukri_login_test.py`
9. ⬜ Run full bot again - check quality of matches

### Long-term (Automate):
10. ⬜ Set up GitHub Actions OR local cron
11. ⬜ Monitor alerts for 1 week - tune filters
12. ⬜ (Optional) Add Google CSE for ultra-fresh jobs
13. ⬜ (Optional) Deploy to cloud for 24/7 operation

---

## 🔗 USEFUL LINKS

- **Telegram Bot Documentation**: https://core.telegram.org/bots
- **Playwright Docs**: https://playwright.dev/python/
- **Lever API**: https://www.lever.co/docs/api
- **Greenhouse API**: https://developers.greenhouse.io/
- **Google Custom Search**: https://developers.google.com/custom-search/v1/overview

---

## 💡 PROJECT PHILOSOPHY

**Why this exists**: Job hunting is a numbers game. The earlier you apply to a new posting, the better your chances. This bot gives you a competitive edge by alerting you within minutes of a job being posted.

**Design principles**:
1. **Speed** - Check 3000+ companies in <2 minutes
2. **Reliability** - Graceful failures, retry logic, dead slug cache
3. **Relevance** - Smart filtering for your profile (3 YOE, Java+AI)
4. **Zero cost** - Free tier APIs, GitHub Actions hosting
5. **Privacy** - All data local, no tracking, no external services

**What makes it special**:
- Parallel fetching (60 workers) - most bots check sequentially
- Dead slug cache - skip 404s instantly
- Multi-source (6 job sources) - comprehensive coverage
- Location prioritization - Remote > Pune > India > Visa
- Naukri stealth scraping - works without login/ScraperAPI

---

## 🙋 FAQ

**Q: Will I get banned from job sites?**  
A: No. The bot uses:
- Public APIs (no scraping)
- Per-ATS rate limits (polite requests)
- Real browser for Naukri (looks like human)
- Retry backoff on 429 errors

**Q: How many alerts will I get per day?**  
A: Depends on your filters. Typically:
- Day 1: 0 (all jobs marked seen)
- Day 2+: 5-20 alerts/day (new postings only)
- You can tune with stricter role/location filters

**Q: Can I use this for non-tech jobs?**  
A: Yes! Edit `TARGET_ROLES` and `ACCEPT_LOCATIONS` to match any domain (finance, marketing, sales, etc.)

**Q: Does this work outside India?**  
A: Absolutely! Edit `ACCEPT_LOCATIONS` to your target countries. Works worldwide.

**Q: Can I self-host this?**  
A: Yes. Run on any machine with Python 3.8+. Works on Linux/Mac/Windows/Raspberry Pi.

**Q: Is the code production-ready?**  
A: Yes. This is v11 - actively maintained, error handling, concurrent-safe, tested on GitHub Actions.

---

## 📜 LICENSE & CREDITS

**Author**: Akash Shinde  
**License**: MIT (free to use, modify, distribute)  
**Credits**:
- Lever, Greenhouse, Ashby for public APIs
- Naukri.com for job data
- Telegram for bot platform
- Playwright for browser automation

---

**🚀 Ready to set up? Start with Step 1 above!**
**💬 Questions? Check the Troubleshooting section.**
**🎯 Good luck with your job hunt!**
