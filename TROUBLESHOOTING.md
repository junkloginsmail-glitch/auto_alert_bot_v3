# 🔧 Troubleshooting Guide - Job Alert Bot

**Complete solutions for common issues**

---

## 📑 TABLE OF CONTENTS

1. [Telegram Issues](#telegram-issues)
2. [Installation Problems](#installation-problems)
3. [Naukri Scraper Issues](#naukri-scraper-issues)
4. [Network & API Errors](#network--api-errors)
5. [Automation Issues](#automation-issues)
6. [Performance Problems](#performance-problems)
7. [Alert Quality Issues](#alert-quality-issues)
8. [File & Permission Errors](#file--permission-errors)

---

## 🤖 TELEGRAM ISSUES

### Issue: No Telegram alerts received

**Symptoms**: Bot runs successfully but no messages on phone

**Check #1**: Token and Chat ID correct?
```powershell
# View your .env file
Get-Content .env

# Should show:
# TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
# TELEGRAM_CHAT_ID=123456789
```

**Check #2**: Bot started?
1. Open Telegram app
2. Search for your bot username
3. Click "START" button

**Check #3**: Test manually
```python
# test_telegram.py
import requests
import os

token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")

if not token or not chat_id:
    print("ERROR: Environment variables not set")
    print("Set them first: set TELEGRAM_BOT_TOKEN=...")
else:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, json={
        "chat_id": chat_id,
        "text": "✅ Test message - Bot is working!"
    })
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
```

**Run test**:
```powershell
python test_telegram.py
```

**Expected output**:
```json
Status: 200
Response: {"ok": true, "result": {...}}
```

**Common Errors**:

**Error**: `{"ok": false, "error_code": 401, "description": "Unauthorized"}`  
**Fix**: Wrong bot token. Get new token from @BotFather

**Error**: `{"ok": false, "error_code": 400, "description": "Bad Request: chat not found"}`  
**Fix**: Wrong chat ID. Get correct ID from @userinfobot

**Error**: `{"ok": false, "error_code": 403, "description": "Forbidden: bot was blocked by the user"}`  
**Fix**: Unblock bot in Telegram, send /start

---

### Issue: Environment variables not found

**Symptoms**: `KeyError: 'TELEGRAM_BOT_TOKEN'`

**Fix #1**: Create `.env` file
```bash
# Create file: .env
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**Fix #2**: Load environment variables manually
```powershell
# Windows PowerShell
$env:TELEGRAM_BOT_TOKEN="your_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"
python job_alert.py
```

**Fix #3**: Use python-dotenv
```bash
pip install python-dotenv
```

Add to top of `job_alert.py`:
```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file
```

---

### Issue: Telegram rate limit exceeded

**Symptoms**: `{"ok": false, "error_code": 429, "description": "Too Many Requests"}`

**Cause**: Sending >30 messages/second

**Fix**: Bot already includes 0.5s delay between messages. If still happening:

Edit `job_alert.py` (line ~800):
```python
def send_telegram(job):
    # ...
    time.sleep(1.0)  # Increase from 0.5 to 1.0 second
```

---

## 📦 INSTALLATION PROBLEMS

### Issue: `pip install` fails

**Error**: `ERROR: Could not install packages due to an OSError`

**Fix #1**: Run as administrator
```powershell
# Windows PowerShell (Run as Administrator)
pip install -r requirements.txt
```

**Fix #2**: Use user install
```powershell
pip install --user -r requirements.txt
```

**Fix #3**: Upgrade pip
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Issue: Playwright install fails

**Error**: `playwright install` not found

**Fix #1**: Install playwright first
```powershell
pip install playwright
playwright install chromium
```

**Fix #2**: Install with dependencies (Linux/Mac)
```bash
playwright install --with-deps chromium
```

**Fix #3**: Manual browser download (Windows)
```powershell
# If auto-install fails, specify exact version
pip install playwright==1.44.0
python -m playwright install chromium
```

**Still failing?**
```powershell
# Check Python version (need 3.8+)
python --version

# Check pip version
pip --version

# Reinstall from scratch
pip uninstall playwright playwright-stealth
pip install playwright==1.44.0 playwright-stealth
python -m playwright install chromium
```

---

### Issue: Import errors

**Error**: `ModuleNotFoundError: No module named 'playwright'`

**Fix**: Verify installation
```powershell
# Check installed packages
pip list | Select-String playwright

# Should show:
# playwright    1.44.0
# playwright-stealth    2.0.0

# If missing, install
pip install playwright playwright-stealth
```

---

## 🌐 NAUKRI SCRAPER ISSUES

### Issue: Naukri returns 0 jobs

**Symptoms**: `[Naukri] Total: 0 unique jobs found`

**Cause #1**: IP blocked by Akamai

**Fix**: Use ScraperAPI
1. Sign up: https://www.scraperapi.com (free tier)
2. Get API key from dashboard
3. Add to `.env`:
   ```bash
   SCRAPER_API_KEY=your_key_here
   ```
4. Run again: `python job_alert.py`

**Cause #2**: Playwright browser failed

**Debug**:
```powershell
# Test Naukri scraper alone
python naukri_login_test.py
```

**Expected output**:
```
=== Testing stealth browser launch ===
Page: <Page ...>

=== Testing browser job search ===
Jobs found: 15
  - AI Engineer @ TCS | Bangalore | 2 days ago
  - Java Developer @ Infosys | Pune | 1 day ago
  ...
```

**If browser fails**:
```powershell
# Reinstall Playwright
pip uninstall playwright playwright-stealth
pip install playwright playwright-stealth
playwright install --with-deps chromium
```

**Cause #3**: Search terms too restrictive

**Fix**: Edit `naukri_scraper.py` (line ~160)
```python
# Change jobAge from 3 to 7 (last 7 days)
"jobAge": 7,  # was 3
```

---

### Issue: Browser crashes on GitHub Actions

**Symptoms**: Naukri works locally but fails on GitHub Actions

**Fix**: Add dependencies to workflow

Edit `.github/workflows/job_alert.yml`:
```yaml
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    playwright install --with-deps chromium  # ← Important!
```

The `--with-deps` flag installs system libraries needed by Chromium on Linux.

---

### Issue: Slow Naukri scraping (>2 minutes)

**Cause**: Browser mode is slow (20-30s for 160 searches)

**Fix #1**: Reduce search coverage
Edit `naukri_scraper.py` (line ~90):
```python
# Keep only high-priority locations
LOCATIONS = ["work-from-home", "pune"]  # Remove bangalore, india
```

**Fix #2**: Increase timeout risk
Edit `naukri_scraper.py` (line ~370):
```python
# Reduce wait time after page load
page.wait_for_timeout(1000)  # was 3000 (faster but might miss jobs)
```

---

## 🌍 NETWORK & API ERRORS

### Issue: HTTP 429 (Too Many Requests)

**Symptoms**: `[LEVER] company → Failed (429)`

**Cause**: Too many concurrent requests

**Fix**: Reduce workers or increase semaphore delay

Edit `job_alert.py`:
```python
# Option 1: Reduce max workers (line 42)
MAX_WORKERS = 30  # was 60

# Option 2: Reduce per-ATS concurrency (line 47-52)
_SEM = {
    "lever":      threading.Semaphore(10),  # was 20
    "greenhouse": threading.Semaphore(10),  # was 20
    "ashby":      threading.Semaphore(8),   # was 15
    "workday":    threading.Semaphore(3),   # was 5
}
```

---

### Issue: Timeout errors

**Symptoms**: `requests.exceptions.Timeout`

**Cause**: Network slow or API down

**Fix**: Increase timeout

Edit `job_alert.py` (line 43):
```python
REQUEST_TIMEOUT = 15  # was 8 seconds
```

**Trade-off**: Slower execution (90s → 180s) but fewer failures

---

### Issue: Google CSE quota exceeded

**Symptoms**: `[Google] Quota exceeded`

**Cause**: Free tier = 100 queries/day

**Fix #1**: Disable Google CSE
Edit `job_alert.py` (line ~15):
```python
GOOGLE_API_KEY = ""  # Set to empty string
GOOGLE_CSE_ID  = ""
```

**Fix #2**: Upgrade to paid plan
- $5 per 1000 queries
- https://console.cloud.google.com

**Fix #3**: Reduce search queries
Edit `job_alert.py` (line ~410):
```python
GOOGLE_QUERIES = [
    "ai engineer india",  # Keep only 1-2 searches
]
```

---

### Issue: SSL certificate errors

**Symptoms**: `SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]`

**Fix #1**: Update certifi
```powershell
pip install --upgrade certifi requests
```

**Fix #2**: Disable SSL verification (NOT recommended for production)
Edit `job_alert.py`:
```python
r = session.get(url, timeout=8, verify=False)
```

**Fix #3**: Install system certificates (Windows)
```powershell
# Download and install: https://curl.se/docs/caextract.html
# Or use:
python -m pip install --upgrade certifi
```

---

## ⚙️ AUTOMATION ISSUES

### Issue: GitHub Actions not running

**Check #1**: Workflow file exists
```
.github/workflows/job_alert.yml  ← Must be this exact path
```

**Check #2**: Cron syntax correct
```yaml
schedule:
  - cron: '0 * * * *'  # Every hour at minute 0
```

**Check #3**: Secrets added
1. Go to repo Settings → Secrets → Actions
2. Should see:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

**Check #4**: Actions enabled
1. Repo Settings → Actions → General
2. "Allow all actions" selected
3. Workflow permissions: "Read and write"

**Debug**:
1. Go to Actions tab in GitHub
2. Click on workflow run
3. Click on job → View logs
4. Look for errors

---

### Issue: Windows Task Scheduler not running

**Check #1**: Task created
1. Open Task Scheduler
2. Task Scheduler Library → "Job Alert Bot"
3. Should show "Ready" status

**Check #2**: Trigger configured
1. Right-click task → Properties
2. Triggers tab → Should show "Daily, repeat every 1 hour"

**Check #3**: Action configured
1. Properties → Actions tab
2. Program: `python` or `C:\Python311\python.exe`
3. Arguments: `D:\AI\AI_Projects\job-alert-bot\job_alert.py`
4. Start in: `D:\AI\AI_Projects\job-alert-bot`

**Check #4**: Run manually
1. Right-click task → Run
2. Check if it executes
3. View History tab for errors

**Common fix**: Use full Python path
```
# Instead of "python"
C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe
```

---

### Issue: Cron job not running (Linux/Mac)

**Check #1**: Cron service running
```bash
# Linux
systemctl status cron

# Mac
sudo launchctl list | grep cron
```

**Check #2**: Crontab correct
```bash
crontab -l

# Should show:
# 0 * * * * cd /path/to/job-alert-bot && python job_alert.py >> bot.log 2>&1
```

**Check #3**: Environment variables
Cron doesn't load .bashrc/.profile. Must set vars in crontab:
```bash
# Edit crontab
crontab -e

# Add these lines:
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
0 * * * * cd /path/to/job-alert-bot && python job_alert.py >> bot.log 2>&1
```

**Check #4**: Python path
```bash
# Use full Python path
0 * * * * cd /path/to/job-alert-bot && /usr/bin/python3 job_alert.py >> bot.log 2>&1
```

**Debug**:
```bash
# Check cron logs
cat /var/log/cron    # Linux
cat /var/log/syslog | grep CRON  # Ubuntu

# Check bot logs
tail -f /path/to/job-alert-bot/bot.log
```

---

## 🐌 PERFORMANCE PROBLEMS

### Issue: Bot takes >5 minutes to run

**Cause #1**: Dead slug cache not working

**Fix**: Delete cache and rebuild
```powershell
Remove-Item ats_cache.json
python job_alert.py  # Will rebuild cache
```

**Cause #2**: Too many workers (network bottleneck)

**Fix**: Reduce workers
Edit `job_alert.py` (line 42):
```python
MAX_WORKERS = 30  # was 60
```

**Cause #3**: Slow internet connection

**Fix**: Increase timeout
Edit `job_alert.py` (line 43):
```python
REQUEST_TIMEOUT = 15  # was 8
```

---

### Issue: High CPU usage

**Cause**: Too many threads

**Fix**: Reduce workers
```python
MAX_WORKERS = 20  # was 60
```

---

### Issue: High memory usage

**Cause**: Large seen_jobs.json (>10MB)

**Fix**: Clean old entries
```python
# clean_seen_jobs.py
import json

# Keep only recent 5000 jobs
with open("seen_jobs.json") as f:
    seen = json.load(f)

recent = seen[-5000:]  # Keep last 5000

with open("seen_jobs.json", "w") as f:
    json.dump(recent, f)
```

**Run**:
```powershell
python clean_seen_jobs.py
```

---

## 📊 ALERT QUALITY ISSUES

### Issue: Too many alerts (spam)

**Fix #1**: Add more exclusions
Edit `job_alert.py` (line 165):
```python
EXCLUDE_ROLES = [
    # Add more non-target roles
    "data analyst",
    "qa engineer",
    "devops engineer",
    "frontend developer",
    "mobile developer",
]
```

**Fix #2**: Stricter role matching
Edit `job_alert.py` (line 118):
```python
# Remove broad titles
TARGET_ROLES = [
    # "software engineer",  # Too broad - remove
    "java backend engineer",  # More specific
    "ai engineer",
]
```

**Fix #3**: Stricter location filter
Edit `job_alert.py` (line 186):
```python
BLOCK_LOCATIONS = [
    # Block more locations you don't want
    "california",
    "texas",
    "uk",
    "canada",
]
```

---

### Issue: Missing relevant jobs

**Fix #1**: Add more keywords
Edit `job_alert.py` (line 118):
```python
TARGET_ROLES = [
    # Add emerging titles
    "agentic ai",
    "rag engineer",
    "mlops",
]
```

**Fix #2**: Broader location acceptance
Edit `job_alert.py` (line 169):
```python
ACCEPT_LOCATIONS = [
    # Add more cities
    "hyderabad",
    "delhi",
    "gurgaon",
    # Add countries with visa sponsor
    "singapore",
    "dubai",
]
```

**Fix #3**: Check dead cache
```powershell
# View ats_cache.json
Get-Content ats_cache.json

# If good company is marked dead, remove entry
# Or delete entire file
Remove-Item ats_cache.json
```

---

### Issue: Old jobs showing as "new"

**Cause**: seen_jobs.json deleted or corrupted

**Fix**: Keep seen_jobs.json
- Don't delete this file
- If corrupted, rename it: `mv seen_jobs.json seen_jobs_backup.json`
- Run bot once - will create fresh file
- Expect many "new" alerts on first run after reset

---

## 📁 FILE & PERMISSION ERRORS

### Issue: `FileNotFoundError: companies.txt`

**Fix**: Ensure file exists
```powershell
# Check if file exists
Test-Path companies.txt

# If False, download from GitHub or create
New-Item companies.txt -ItemType File
```

---

### Issue: `PermissionError: [Errno 13] Permission denied`

**Fix**: Run with proper permissions
```powershell
# Windows: Run as Administrator

# Linux/Mac:
sudo python job_alert.py
```

---

### Issue: `JSONDecodeError: Expecting value`

**Cause**: Corrupted JSON file

**Fix**: Rebuild state files
```powershell
# Backup current files
Copy-Item seen_jobs.json seen_jobs_backup.json
Copy-Item ats_cache.json ats_cache_backup.json

# Delete corrupted files
Remove-Item seen_jobs.json
Remove-Item ats_cache.json

# Run bot - will create fresh files
python job_alert.py
```

---

## 🆘 EMERGENCY FIXES

### Nuclear option: Fresh start

If nothing works, reset everything:

```powershell
# 1. Backup state
Copy-Item seen_jobs.json seen_jobs_backup.json -ErrorAction SilentlyContinue
Copy-Item ats_cache.json ats_cache_backup.json -ErrorAction SilentlyContinue

# 2. Uninstall all
pip uninstall -y requests playwright playwright-stealth

# 3. Delete Python cache
Remove-Item -Recurse -Force __pycache__

# 4. Fresh install
pip install -r requirements.txt
playwright install --with-deps chromium

# 5. Test
python naukri_login_test.py
python job_alert.py
```

---

## 📞 GETTING MORE HELP

### Enable debug mode

Edit `job_alert.py` (add at top):
```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

Run again:
```powershell
python job_alert.py > debug.log 2>&1
```

Share `debug.log` when asking for help.

---

### Collect system info

```powershell
# System info
python --version
pip --version
pip list | Select-String "requests|playwright"

# Test network
Test-NetConnection api.lever.co -Port 443
Test-NetConnection boards-api.greenhouse.io -Port 443

# Test APIs manually
curl "https://api.lever.co/v0/postings/stripe?mode=json"
```

---

### Contact options

- **GitHub Issues**: Open issue on project repo
- **Stack Overflow**: Tag `python`, `playwright`, `telegram-bot`
- **Documentation**: See `SETUP_CONTEXT.md` and `ARCHITECTURE.md`

---

## ✅ QUICK DIAGNOSTIC CHECKLIST

Run through this checklist when troubleshooting:

- [ ] Python 3.8+ installed: `python --version`
- [ ] Dependencies installed: `pip list | grep playwright`
- [ ] `.env` file exists with correct tokens
- [ ] Telegram bot started (sent /start)
- [ ] Test Telegram: `python test_telegram.py`
- [ ] Test Naukri: `python naukri_login_test.py`
- [ ] `companies.txt` exists
- [ ] Files writable (not read-only)
- [ ] Internet connection working
- [ ] No firewall blocking Python
- [ ] Environment variables loaded
- [ ] Working directory correct

If all checked, bot should work! ✅

---

**🎯 Still stuck? Create `debug.log` and review carefully.**
**💡 Most issues are: wrong tokens, missing .env, or Playwright not installed.**
