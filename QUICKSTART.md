# 🚀 Quick Start Guide - Job Alert Bot Setup

**Goal**: Get your personalized job alert bot running in 15 minutes

---

## ⚡ STEP-BY-STEP SETUP

### Step 1: Get Your Telegram Bot Token (5 minutes)

1. **Open Telegram** on your phone or desktop

2. **Create a bot**:
   - Search for `@BotFather`
   - Send `/newbot`
   - Choose a name: "My Job Alert Bot"
   - Choose a username: "yourname_job_bot" (must end with 'bot')
   - **Copy the token** (looks like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

3. **Get your Chat ID**:
   - Search for `@userinfobot`
   - Send any message
   - **Copy your ID** (looks like: `123456789`)

4. **Start your bot**:
   - Search for your bot username in Telegram
   - Click "Start" button

---

### Step 2: Install Dependencies (3 minutes)

Open terminal in project folder and run:

```powershell
# Install Python packages
pip install -r requirements.txt

# Install Playwright browser (needed for Naukri scraper)
playwright install chromium
```

**Note**: If you get an error on `playwright install`, run:
```powershell
pip install playwright
playwright install --with-deps chromium
```

---

### Step 3: Create Environment File (2 minutes)

Create a file named `.env` in the project folder:

```bash
# Required - Your Telegram credentials
TELEGRAM_BOT_TOKEN=paste_your_token_here
TELEGRAM_CHAT_ID=paste_your_chat_id_here

# Optional - Google Custom Search (for ultra-fresh jobs)
GOOGLE_API_KEY=
GOOGLE_CSE_ID=

# Optional - If Naukri blocks your IP
SCRAPER_API_KEY=
```

**Replace** the token and chat ID with values from Step 1.

---

### Step 4: First Test Run (2 minutes)

```powershell
# Run the bot
python job_alert.py
```

**What to expect**:
```
🤖 AI Job Alert Bot v11 — 09 Aug 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Fetching 3000+ companies...

[LEVER] anthropic → 12 jobs
[GREENHOUSE] stripe → 8 jobs
...

✅ Done! 0 new alerts sent (first run = all marked as seen)
Total time: 127s
```

**First run**: 0 alerts (expected - all jobs marked as "seen")  
**Next runs**: Only NEW jobs will trigger Telegram alerts

---

### Step 5: Customize for Your Preferences (3 minutes)

**Edit `job_alert.py`** to match your preferences:

#### Your Target Roles (line 118-148)
```python
TARGET_ROLES = [
    # Customize - keep what interests you, remove others
    "java developer",
    "backend engineer",
    "ai engineer",
    "ml engineer",
    # Add more...
]
```

#### Your Location Preferences (line 169-184)
```python
ACCEPT_LOCATIONS = [
    "pune",        # ⬅️ Add YOUR city here
    "remote",
    "bangalore",
    # Add more...
]

BLOCK_LOCATIONS = [
    # Keep this - blocks US/UK onsite-only jobs
    "san francisco, ca",
    "new york, ny",
    # Add more locations you DON'T want
]
```

#### Your Companies (edit `companies.txt`)
- **Keep**: Companies you want to track
- **Remove**: Companies you're not interested in
- **Add**: New companies (one per line)

---

### Step 6: Second Test Run (2 minutes)

```powershell
# Run again after customization
python job_alert.py
```

**Now you should see**:
- Bot fetches jobs faster (skips companies from cache)
- Filters apply (only your target roles/locations)
- Any **new jobs** (posted since last run) → Telegram alert! 📱

---

## 🤖 AUTOMATION OPTIONS

### Option A: GitHub Actions (Recommended - Free)

**Why**: Free, runs every hour, no local machine needed

**Steps**:
1. Create GitHub account (if you don't have)
2. Create new **private** repository
3. Push this code to GitHub
4. Add secrets in repo settings:
   - `TELEGRAM_BOT_TOKEN` = your token
   - `TELEGRAM_CHAT_ID` = your chat ID
5. Create `.github/workflows/job_alert.yml`:

```yaml
name: Job Alert Bot

on:
  schedule:
    - cron: '0 * * * *'  # Every hour
  workflow_dispatch:  # Manual trigger

jobs:
  run-bot:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install --with-deps chromium
      
      - name: Run bot
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python job_alert.py
      
      - name: Commit state files
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add seen_jobs.json ats_cache.json
          git diff --quiet && git diff --staged --quiet || git commit -m "Update job cache [skip ci]"
          git push
```

6. Done! Bot runs every hour automatically

---

### Option B: Windows Task Scheduler (Local)

**Why**: Runs on your PC, works even without internet hosting

**Steps**:
1. Open Task Scheduler (search in Start menu)
2. Create Basic Task
   - Name: "Job Alert Bot"
   - Trigger: Daily, repeat every 1 hour
   - Action: Start a program
   - Program: `python`
   - Arguments: `D:\AI\AI_Projects\job-alert-bot\job_alert.py`
   - Start in: `D:\AI\AI_Projects\job-alert-bot`
3. Done! Runs every hour when PC is on

**Note**: Requires your PC to be on. Use GitHub Actions if you want 24/7 operation.

---

### Option C: Cloud Server (Advanced)

Deploy to AWS EC2 / Google Cloud / Digital Ocean:

```bash
# SSH into server
ssh your-server

# Clone repo
git clone https://github.com/yourusername/job-alert-bot.git
cd job-alert-bot

# Install
pip install -r requirements.txt
playwright install chromium

# Add to crontab
crontab -e
# Add line:
0 * * * * cd /path/to/job-alert-bot && python job_alert.py >> bot.log 2>&1
```

---

## ✅ VERIFICATION CHECKLIST

After setup, verify everything works:

- [ ] Telegram bot responds to /start command
- [ ] First run completes without errors
- [ ] `seen_jobs.json` and `ats_cache.json` files created
- [ ] Second run shows new jobs (if any posted since first run)
- [ ] Telegram alert received for new jobs
- [ ] Jobs match your target roles/locations
- [ ] Automation scheduled (GitHub Actions / Task Scheduler / Cron)

---

## 🎯 WHAT HAPPENS NEXT?

### Daily Operation:
1. **Bot runs every hour** (automated)
2. **Checks 3000+ companies** across Lever/Greenhouse/Ashby/Workday/Naukri
3. **Filters** by your roles/locations/experience
4. **Sends Telegram alert** for NEW matching jobs only
5. **You apply** early (competitive advantage!)

### Expected Alerts:
- **Day 1**: 0 alerts (all marked as seen)
- **Day 2+**: 5-20 alerts/day (varies by market activity)
- **Monday mornings**: More alerts (companies post over weekend)

---

## 🛠️ TROUBLESHOOTING

### "No Telegram alerts"
1. Check token/chat ID in `.env` are correct
2. Send `/start` to your bot
3. Test manually:
   ```python
   import requests, os
   token = os.environ["TELEGRAM_BOT_TOKEN"]
   chat_id = os.environ["TELEGRAM_CHAT_ID"]
   requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                 json={"chat_id": chat_id, "text": "Test works!"})
   ```

### "Playwright error"
```powershell
# Reinstall
pip uninstall playwright playwright-stealth
pip install playwright playwright-stealth
playwright install --with-deps chromium
```

### "Naukri returns 0 jobs"
- **Normal on first run** - Naukri has strict rate limits
- **Check**: `python naukri_login_test.py` for detailed logs
- **Solution**: Get ScraperAPI key (1000 free requests/month)

### "Too many alerts (spam)"
Edit `job_alert.py`:
- Add more keywords to `EXCLUDE_ROLES`
- Remove broad titles from `TARGET_ROLES`
- Make location filter stricter

---

## 📊 MONITORING YOUR BOT

### Check bot is running:
```powershell
# View last run output
tail job_alert.log   # Linux/Mac
Get-Content job_alert.log -Tail 50   # Windows PowerShell
```

### Performance metrics to track:
- **Alert quality**: Are jobs relevant? Tune filters if not
- **Alert volume**: Too many? Add exclusions. Too few? Broaden search
- **Execution time**: Should be 90-150s. Slower = network issues

---

## 🎓 PRO TIPS

### Get More Relevant Jobs:
1. **Review Telegram alerts weekly** - note patterns
2. **Add emerging keywords** - "agentic ai", "rag engineer", etc.
3. **Remove noise** - if "full stack" gives too many frontend jobs, remove it
4. **Location tuning** - add specific cities you'd relocate to

### Maximize Coverage:
1. **Add companies regularly** - check Y Combinator, TechCrunch for new startups
2. **Enable Google CSE** - catches jobs on custom ATSs
3. **Check GitHub Actions logs** - ensure bot runs every hour

### Save Time:
1. **Create application templates** - reuse cover letters
2. **Set up job tracker** - Notion/Airtable with columns: Company, Role, Applied, Status
3. **Apply within 24h** - bot gives you early-bird advantage, use it!

---

## 📞 NEED HELP?

### Common Issues:
- See `SETUP_CONTEXT.md` (detailed guide)
- Check logs in terminal output
- Test individual components:
  - Naukri: `python naukri_login_test.py`
  - Telegram: `python -c "import requests; print('test')"`

### Resources:
- Telegram Bot docs: https://core.telegram.org/bots
- Playwright docs: https://playwright.dev/python/
- ATS APIs: See company career page for API docs

---

## 🎯 READY TO GO LIVE?

**Final Checklist**:
1. ✅ `.env` file created with your tokens
2. ✅ Dependencies installed
3. ✅ Test run successful
4. ✅ Telegram alerts working
5. ✅ Customized roles/locations/companies
6. ✅ Automation scheduled

**Start monitoring**: Your bot will now alert you the moment a matching job is posted! 🎉

**Good luck with your job hunt!** 💼🚀
