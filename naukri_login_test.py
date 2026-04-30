"""
Quick local test for Naukri Playwright login + job search.
Usage:
  set NAUKRI_EMAIL=your@email.com
  set NAUKRI_PASSWORD=yourpassword
  python naukri_login_test.py
"""
import os, sys

if not os.environ.get("NAUKRI_EMAIL"):
    print("Set NAUKRI_EMAIL and NAUKRI_PASSWORD env vars before running this test.")
    sys.exit(1)

sys.path.insert(0, ".")
from naukri_scraper import _ensure_naukri_page, _fetch_authenticated, _close_naukri_browser

print("=== Testing Playwright stealth login ===")
page = _ensure_naukri_page()
print("Page:", page)

if page:
    print(f"\nPost-login URL: {page.url}")

    print("\n=== Testing in-browser job search (AI Engineer, India) ===")
    jobs = _fetch_authenticated("ai-engineer", "india")
    print(f"Jobs found: {len(jobs)}")
    for j in jobs[:5]:
        print(f"  - {j['title']} @ {j['company']} | {j['location']} | {j['posted']}")
        print(f"    {j['link']}")

_close_naukri_browser()
print("\nDone.")

