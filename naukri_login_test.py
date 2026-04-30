"""
Quick local test for Naukri browser-based job search (no login required).
Usage: python naukri_login_test.py
"""
import sys
sys.path.insert(0, ".")
from naukri_scraper import _ensure_browser, _fetch_browser, _close_naukri_browser

print("=== Testing stealth browser launch ===")
page = _ensure_browser()
print("Page:", page)

if page:
    print("\n=== Testing browser job search (AI Engineer, India) ===")
    jobs = _fetch_browser("ai-engineer", "india")
    print(f"Jobs found: {len(jobs)}")
    for j in jobs[:5]:
        print(f"  - {j['title']} @ {j['company']} | {j['location']} | {j['posted']}")
        print(f"    {j['link']}")

_close_naukri_browser()
print("\nDone.")

