# 🎯 Your Personal Setup Checklist

**Date Started**: _______________  
**Goal**: Get job alerts running by: _______________

---

## 📋 PHASE 1: INITIAL SETUP (Target: 15 minutes)

### Telegram Bot Configuration
- [ ] Opened Telegram app
- [ ] Messaged @BotFather
- [ ] Created new bot (name: _______________)
- [ ] Saved bot token: `________________________` (keep secret!)
- [ ] Messaged @userinfobot
- [ ] Saved chat ID: `________________________`
- [ ] Clicked "Start" on my new bot

### Environment Setup
- [ ] Created `.env` file in project folder
- [ ] Added `TELEGRAM_BOT_TOKEN` to `.env`
- [ ] Added `TELEGRAM_CHAT_ID` to `.env`
- [ ] Saved `.env` file

### Install Dependencies
- [ ] Ran `pip install -r requirements.txt`
- [ ] Ran `playwright install chromium`
- [ ] No errors during installation

### First Test
- [ ] Ran `python job_alert.py`
- [ ] Bot completed without errors
- [ ] `seen_jobs.json` file created
- [ ] `ats_cache.json` file created
- [ ] Execution time: _______ seconds

**✅ Phase 1 Status**: _____ / 12 completed

---

## 📋 PHASE 2: CUSTOMIZATION (Target: 20 minutes)

### Customize Job Preferences
- [ ] Opened `job_alert.py` in editor
- [ ] Reviewed `TARGET_ROLES` (lines 118-148)
- [ ] Added roles I want: _______________________________
- [ ] Removed roles I don't want: _______________________________
- [ ] Reviewed `EXCLUDE_SENIORITY` (lines 151-165)
- [ ] Reviewed `ACCEPT_LOCATIONS` (lines 169-184)
- [ ] Changed to my preferred city: _______________________________
- [ ] Added remote preference: YES / NO
- [ ] Saved `job_alert.py`

### Customize Companies
- [ ] Opened `companies.txt`
- [ ] Reviewed current companies list
- [ ] Added companies I'm interested in: _______________________________
- [ ] Removed companies I'm NOT interested in: _______________________________
- [ ] Total companies in my list: _______
- [ ] Saved `companies.txt`

### Test Customization
- [ ] Deleted `seen_jobs.json` (to test filters)
- [ ] Ran `python job_alert.py` again
- [ ] Checked output for my target roles
- [ ] Verified locations match my preferences
- [ ] Received Telegram alerts (if new jobs exist)
- [ ] Alert quality is good: YES / NEEDS_TUNING

**✅ Phase 2 Status**: _____ / 16 completed

---

## 📋 PHASE 3: AUTOMATION (Target: 15 minutes)

### Choose Automation Method
**I will use** (check one):
- [ ] **GitHub Actions** (Recommended - Free, 24/7)
- [ ] **Windows Task Scheduler** (Requires PC on)
- [ ] **Linux Cron** (Local server)
- [ ] **Cloud Server** (AWS/GCP/DO)

### GitHub Actions Setup (if chosen)
- [ ] Created GitHub account (username: _______________)
- [ ] Created new **private** repository
- [ ] Pushed code to GitHub
- [ ] Added secret: `TELEGRAM_BOT_TOKEN`
- [ ] Added secret: `TELEGRAM_CHAT_ID`
- [ ] Created `.github/workflows/job_alert.yml`
- [ ] Verified workflow file is correct
- [ ] Triggered manual run (Actions tab)
- [ ] Workflow completed successfully
- [ ] Checked GitHub Actions schedule is set (every hour)

### Windows Task Scheduler Setup (if chosen)
- [ ] Opened Task Scheduler
- [ ] Created new basic task
- [ ] Set name: "Job Alert Bot"
- [ ] Set trigger: Daily, repeat every 1 hour
- [ ] Set action: `python`
- [ ] Set arguments: full path to `job_alert.py`
- [ ] Set "Start in": full path to project folder
- [ ] Tested task runs manually
- [ ] Verified task is enabled

### Linux Cron Setup (if chosen)
- [ ] Opened terminal
- [ ] Edited crontab: `crontab -e`
- [ ] Added cron line: `0 * * * * ...`
- [ ] Saved crontab
- [ ] Verified cron syntax: `crontab -l`
- [ ] Checked cron service running: `systemctl status cron`

**✅ Phase 3 Status**: _____ / 10 completed (varies by method)

---

## 📋 PHASE 4: MONITORING & TUNING (Ongoing)

### Week 1: Monitor Quality
- [ ] **Day 1**: Received first real alerts
      - Number of alerts: _______
      - Quality (relevant?): _____ / 10
      - False positives: _______

- [ ] **Day 2**: Checked alert volume
      - Number of alerts: _______
      - Applied to: _______

- [ ] **Day 3**: Mid-week check
      - Number of alerts: _______
      - Need to adjust filters: YES / NO

- [ ] **Day 7**: Week review
      - Total alerts received: _______
      - Total jobs applied to: _______
      - Alert quality: _____ / 10
      - Need tuning: YES / NO

### Tuning Actions (if needed)
- [ ] Added keywords to `EXCLUDE_ROLES`: _______________________________
- [ ] Removed broad titles from `TARGET_ROLES`: _______________________________
- [ ] Adjusted location preferences: _______________________________
- [ ] Added/removed companies: _______________________________
- [ ] Tested changes: `python job_alert.py`
- [ ] Quality improved: YES / NO

### Week 2-4: Optimization
- [ ] **Week 2**: Alert volume stable
      - Avg alerts/day: _______
      - Application rate: _______

- [ ] **Week 3**: Fine-tuned filters
      - Changes made: _______________________________
      - Result: _______________________________

- [ ] **Week 4**: System stable
      - Automation working: YES / NO
      - Alert quality: _____ / 10
      - Ready for long-term use: YES / NO

**✅ Phase 4 Status**: Ongoing monitoring

---

## 🎯 ADVANCED FEATURES (Optional)

### Google Custom Search Setup
- [ ] Created Google Cloud project
- [ ] Enabled Custom Search API
- [ ] Created API key
- [ ] Created Custom Search Engine
- [ ] Added search sites (lever.co, greenhouse.io, etc.)
- [ ] Added `GOOGLE_API_KEY` to `.env`
- [ ] Added `GOOGLE_CSE_ID` to `.env`
- [ ] Tested: more fresh jobs found: YES / NO

### ScraperAPI Setup (for Naukri)
- [ ] Signed up at scraperapi.com
- [ ] Got API key (free tier: 1000 req/month)
- [ ] Added `SCRAPER_API_KEY` to `.env`
- [ ] Tested: `python naukri_login_test.py`
- [ ] Naukri scraping working: YES / NO

### Performance Optimization
- [ ] Measured execution time: _______ seconds
- [ ] Adjusted `MAX_WORKERS` (if needed): _______
- [ ] Adjusted semaphore limits (if needed): _______
- [ ] Cleaned `seen_jobs.json` (if >10MB)
- [ ] Performance improved: YES / NO

**✅ Advanced Features Status**: _____ / 15 completed

---

## 📊 SUCCESS METRICS

### Technical Metrics
- **Bot uptime**: _____ % (check GitHub Actions / logs)
- **Execution time**: _____ seconds average
- **Companies checked**: _______
- **Jobs scraped per run**: _______
- **Alert rate**: _____ alerts/day average

### Job Hunt Metrics
- **Applications submitted**: _______
- **Interviews scheduled**: _______
- **Offers received**: _______
- **Time saved** (early alerts): _____ hours
- **Success rate**: _____ %

### Quality Metrics
- **Alert relevance**: _____ / 10
- **False positive rate**: _____ %
- **Missed jobs** (found manually): _______
- **User satisfaction**: _____ / 10

---

## 🎉 MILESTONES

- [ ] **🚀 First run successful** (Date: ______)
- [ ] **📱 First Telegram alert** (Date: ______)
- [ ] **✅ Automation working** (Date: ______)
- [ ] **📝 First application via bot** (Date: ______)
- [ ] **📞 First interview via bot** (Date: ______)
- [ ] **🎊 First offer via bot** (Date: ______)

---

## 🐛 ISSUES ENCOUNTERED

| Date | Issue | Solution | Status |
|------|-------|----------|--------|
| ____ | _____ | ________ | ______ |
| ____ | _____ | ________ | ______ |
| ____ | _____ | ________ | ______ |

---

## 📝 NOTES & IDEAS

### Things to Try:
- 
- 
- 

### Companies to Add:
- 
- 
- 

### Filter Adjustments Needed:
- 
- 
- 

### Questions to Research:
- 
- 
- 

---

## ✅ FINAL STATUS

**Overall Setup Progress**: _____ / 53 completed

**System Status**:
- [ ] Fully operational
- [ ] Needs tuning
- [ ] Has issues (see above)

**My Rating**: _____ / 10

**Ready for Long-term Use**: YES / NO

**Date Completed**: _______________

---

**🎯 Next Review Date**: _______________

**🎊 Congratulations on setting up your AI Job Alert Bot!**
