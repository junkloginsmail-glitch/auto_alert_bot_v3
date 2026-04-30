# 🤖 AI Job Alert Bot v2
**Catches ANY company's AI job on Lever or Greenhouse — even posted 30 min ago**

---

## 🏗️ How It Works

```
Every 1 hour (GitHub Actions, FREE):
│
├── SOURCE 1: Google Custom Search API  ← finds ANY company, real-time
│     └── "site:jobs.lever.co AI engineer India" (last 24h only)
│     └── "site:job-boards.greenhouse.io LLM engineer India" (last 24h only)
│
├── SOURCE 2: Known Company APIs        ← fast, no quota used
│     └── Lever API for 19 known AI companies
│     └── Greenhouse API for 17 known AI companies
│
├── AI Relevance Scorer (Groq llama-3.3-70b)
│     └── "Is this job relevant for Akash's profile?"
│     └── Scores 1-10, only alerts if score >= 6
│
└── Notifications
      ├── Telegram → instant push to phone 📱
      └── Email → Gmail backup 📧
```

---

## 🚀 Setup (20 minutes, completely FREE)

### Step 1 — Create Telegram Bot
1. Open Telegram → search **@BotFather** → send `/newbot`
2. Name it anything, e.g. `AkashJobAlertBot`
3. Copy the **Bot Token**: `7123456789:AAFxyz...`
4. Search your bot name → press **Start**
5. Get your Chat ID:
   - Open: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Send any message to your bot first
   - Look for `"id"` inside `"chat"` → that's your Chat ID

---

### Step 2 — Get Google Custom Search API (FREE — 100 queries/day)
1. Go to: https://console.cloud.google.com
2. Create a new project → **Enable "Custom Search API"**
3. Go to **Credentials → Create API Key** → copy it

4. Go to: https://programmablesearchengine.google.com
5. Click **Add** → Search the entire web → Create
6. Copy the **Search Engine ID (cx)**

> 💡 100 free queries/day × 10 results = 1000 jobs/day scanned. More than enough!

---

### Step 3 — Create GitHub Repo
1. Go to github.com → **New Repository** → name it `job-alert-bot`
2. Upload ALL files from this folder (keep folder structure)

---

### Step 4 — Add GitHub Secrets
Go to: Repo → **Settings → Secrets and Variables → Actions → New secret**

| Secret Name | Value |
|---|---|
| `GROQ_API_KEY` | From [console.groq.com](https://console.groq.com) |
| `TELEGRAM_BOT_TOKEN` | From BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |
| `GOOGLE_API_KEY` | From Google Cloud Console |
| `GOOGLE_CSE_ID` | From Programmable Search Engine |
| `EMAIL_SENDER` | Your Gmail (optional) |
| `EMAIL_APP_PASSWORD` | Gmail App Password (optional) |
| `EMAIL_RECEIVER` | `akash.shinde@myyahoo.com` |
| `NAUKRI_EMAIL` | Your Naukri login email (**recommended** — bypasses IP blocks) |
| `NAUKRI_PASSWORD` | Your Naukri login password |

> For Gmail App Password: Google Account → Security → 2FA on → App Passwords

---

### Step 5 — Enable GitHub Actions
1. Go to your repo → **Actions tab**
2. Click **"I understand my workflows, enable them"**
3. ✅ Bot now runs every hour, forever, FREE!

---

### Step 6 — Test Manually
1. Go to **Actions → 🤖 AI Job Alert Bot → Run workflow**
2. Check Telegram within 2 minutes!

---

## 📱 Telegram Alert Preview

```
🟢 New AI Job Alert!

📌 AI Engineer
🏢 Particle41
📍 India - Remote
📅 < 24 hours ago
🔍 Greenhouse via Google

🤖 RAG + LangChain + 3 YOE match, India remote ✅

🔗 Apply Now → https://job-boards.greenhouse.io/...
```

---

## 📁 File Structure

```
job-alert-bot/
├── job_alert.py              ← Main bot script
├── seen_jobs.json            ← Tracks alerted jobs (auto-updated)
├── requirements.txt
├── README.md
└── .github/
    └── workflows/
        └── job_alert.yml     ← GitHub Actions cron (every 1 hour)
```

---

## ⚙️ Customise

In `job_alert.py`:
- **Stricter/looser matching** → change `score >= 6` (higher = stricter)
- **Add known companies** → add slugs to `LEVER_COMPANIES` / `GREENHOUSE_COMPANIES`
- **More search queries** → add to `GOOGLE_QUERIES`
- **Your profile** → update `MY_PROFILE` block

---

## 🆓 Cost Breakdown

| Service | Cost |
|---|---|
| GitHub Actions (cron) | FREE (2000 min/month) |
| Google Custom Search | FREE (100 queries/day) |
| Groq API | FREE tier |
| Telegram Bot | FREE |
| Total | **$0/month** ✅ |
