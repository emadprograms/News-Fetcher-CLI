import requests
import json
from bs4 import BeautifulSoup
from dateutil import parser
import datetime
import os
import sys
import signal
import time
from urllib.parse import urlparse

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global Headers
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.investing.com/"
}
BLOCKED_SOURCES = ["MOTLEY FOOL", "SIMPLY WALL ST", "BENZINGA", "ZACKS", "GLOBENEWSWIRE"]
PREMIUM_SOURCES = ["BLOOMBERG", "REUTERS", "CNBC", "WSJ", "WALL STREET JOURNAL", "FINANCIAL TIMES", "BARRON'S"]

def force_quit_driver(driver):
    """
    Terminates the Selenium driver via PID (Hard Kill) to ensure no zombie processes.
    """
    if not driver: return
    
    # 1. Try Graceful Quit first
    try:
        driver.quit()
    except:
        pass
        
    # 2. Hard Kill via PID (Unix/Mac specific)
    try:
        pid = driver.service.process.pid
        if pid:
            os.kill(pid, signal.SIGTERM) # Try polite kill first
            # time.sleep(1) 
            # os.kill(pid, signal.SIGKILL) # Force kill if needed (optional)
            print(f"🔨 Force Killed Driver PID: {pid}")
    except Exception as e:
        # print(f"⚠️ PID Kill failed (already dead?): {e}")
        pass

def is_premium_source(title, url):
    """
    Checks if the source is 'Premium' (Worth Retrying).
    """
    text_check = (title + " " + url).upper()
    for src in PREMIUM_SOURCES:
        if src in text_check:
            return True
    return False

def normalize_title(title):
    """
    Standardizes titles for deduplication.
    1. Trims whitespace.
    2. Removes common Source Suffixes (e.g. ' - Yahoo Finance').
    3. Returns CLEAN title (Case preserved). Caller should .lower() if needed.
    """
    if not title: return ""
    t = title.strip()
    # Suffixes to remove (Order matters? Longest first maybe?)
    suffixes = [" - Yahoo Finance", " - Bloomberg", " - Reuters", " - CNBC", " - MarketWatch", " - The Wall Street Journal"]
    for s in suffixes:
        if t.endswith(s):
            t = t.rsplit(s, 1)[0].strip()
    return t

# --- CHROME CONFIGURATION ---
# Auto-detect Chrome Path for stabilization on Windows/Mac
CHROME_PATH = None
if sys.platform == "win32":
    # Windows Paths
    potential_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    for p in potential_paths:
        if os.path.exists(p):
            CHROME_PATH = p
            break
elif sys.platform == "darwin":
    # Mac Path
    mac_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(mac_path):
        CHROME_PATH = mac_path

_CACHED_DRIVER_PATH = None # Optimization: Cache binary path

def get_selenium_driver(headless=False):
    """ Launches a Chrome browser. Optimized for speed. """
    global _CACHED_DRIVER_PATH
    
    options = Options()
    
    # Common options
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-extensions") # Speedup
    options.add_argument("--no-first-run") # Speedup
    
    if headless:
        options.add_argument("--headless=new")
        
    options.page_load_strategy = 'eager' # ⚡ Do not wait for full ads/images to load. DOM access is enough.
    
    # User Agent (Legacy/Previous Working)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    if CHROME_PATH and os.path.exists(CHROME_PATH):
         options.binary_location = CHROME_PATH
    
    try:
        # FAST LAUNCH OPTIMIZATION
        if _CACHED_DRIVER_PATH and os.path.exists(_CACHED_DRIVER_PATH):
            service_path = _CACHED_DRIVER_PATH
        else:
            # Only hit the network/check version if not cached
            service_path = ChromeDriverManager().install()
            _CACHED_DRIVER_PATH = service_path
            
        service = Service(service_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(6) # ⏳ Prevent Headless Hanging/Freezing (Optimized)
        return driver
    except Exception as e:
        error_msg = str(e)
        if "cannot find Chrome binary" in error_msg:
            raise Exception("❌ Selenium cannot find Chrome. Set CHROME_PATH in market_utils.py.")
        raise e

def decode_google_news_url(google_url):
    """ 
    LEGACY MODE: Pass-through.
    We let Selenium handle the redirect because 'requests' decoding was unstable/stuck.
    """
    return google_url

class DeadDriverException(Exception):
    pass

class BlockedContentException(Exception):
    pass

def fetch_yahoo_selenium(driver, url, log_callback, allow_sources=None):
    """
    Fetches Yahoo content using a REAL BROWSER to render JavaScript.
    allow_sources: List of uppercase strings (e.g. ["ZACKS"]) to bypass the blocklist.
    """
    try:
        # 0. DOMAIN VALIDATION (No International Yahoo)
        from urllib.parse import urlparse
        import urllib3
        import socket
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if "yahoo.com" in domain:
            if domain not in ["finance.yahoo.com", "www.finance.yahoo.com"]:
                if log_callback: log_callback(f"│   │   │   └── 🛑 Skipped Non-US Domain: {domain}")
                raise BlockedContentException(f"Non-US Domain: {domain}")

        if log_callback: log_callback(f"│   │   │   ├── 🔍 Visiting Article Source...")
        
        if not driver: return None
            
        try:
            # Set Script Timeout too (just in case)
            if log_callback: log_callback(f"│   │   │   ├── 🚦 Visiting: {domain} ...")
            driver.set_script_timeout(5)
            driver.set_page_load_timeout(5) # Enforce stricter timeout (5s)
            driver.get(url)
        except Exception as te:
            # Catch ALL Fetch Errors (Timeout, Connection Refused, Zombie Driver)
            # If it's a timeout or freeze, we return headline only.
            # If it's a 'death' error (no session), we let DeadDriverException bubble via check below?
            # No, if driver is dead, driver.current_url will fail.
            
            err_str = str(te).lower()
            if "timeout" in err_str or "timed out" in err_str:
                if log_callback: log_callback(f"│   │   │   └── ⚠️ Page Load Timeout (5s). Returning Headline Only.")
                return {"text": f"[Content Timeout] Link: {url}", "publisher": "Unknown (Timeout)"}
            else:
                # If it's not a timeout, it might be a crash.
                # Let's verify driver aliveness.
                try: 
                    _ = driver.current_url
                except:
                    raise DeadDriverException("Driver Died during Fetch")
                
                # If driver is alive but fetch failed (e.g. 404, DNS):
                if log_callback: log_callback(f"│   │   │   └── ⚠️ Fetch Failed ({err_str[:50]}...). Returning Headline.")
                return {"text": f"[Fetch Failed: {err_str}] Link: {url}", "publisher": "Unknown (Error)"}

        # ... (Processing Loop) ...
        
           # 1. HANDLE CONSENT POPUPS (Try to click 'Maybe Later' or 'Reject')
        try:
            # Wait briefly to see if a popup appears
            WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Maybe later') or contains(text(), 'Reject')]"))
            ).click()
            log_callback(f"│   │   │   │   └── 🍪 Dismissed Cookie/Consent Popup.")
        except:
            pass # No popup, continue
        
        # 2. WAIT FOR CONTENT LOAD & MONITOR URL (The Firewall Loop)
        # We loop for up to 5 seconds. If stuck on Google, we try to click content links.
        valid_us_yahoo = False
        
        for i in range(10): # 10 * 0.5s = 5 seconds max wait
            time.sleep(0.5)
            
            curr = driver.current_url
            p = urlparse(curr)
            d = p.netloc.lower()
            
            # If we are on a Yahoo domain, it MUST be the US one.
            if "yahoo.com" in d:
                if d in ["finance.yahoo.com", "www.finance.yahoo.com"]:
                    valid_us_yahoo = True
                    break # Success!
                else:
                    # Detected UK/CA/SG/etc.
                    if log_callback: log_callback(f"│   │   │   └── 🛑 BLOCKED Non-US Domain: {d}")
                    raise BlockedContentException(f"Redirected to Non-US Domain: {d}")
            
            # If still on Google, try to help it along
            if "google.com" in d:
                # Check for "Redirect Notice" link
                if i > 2: 
                    try:
                        # 1. Try generic "Redirect Notice" link (often just the displayed URL)
                        links = driver.find_elements(By.TAG_NAME, "a")
                        for l in links:
                            # If it looks like a meaningful link (not a footer/nav)
                            # Google Redirect page usually has one big link in the middle
                            if "yahoo.com" in l.text or "https://" in l.text:
                                l.click()
                                break
                    except:
                        pass
                    
                    # Check for Consent again (Persistent)
                    try:
                        btns = driver.find_elements(By.TAG_NAME, "button")
                        for b in btns:
                            txt = b.text.lower()
                            if "accept" in txt or "agree" in txt or "consent" in txt:
                                b.click()
                                break
                    except:
                        pass
        
        # 3. FINAL DOMAIN VERIFICATION
        final_url = driver.current_url
        p_final = urlparse(final_url)
        d_final = p_final.netloc.lower()
        
        if "yahoo.com" in d_final:
             if d_final not in ["finance.yahoo.com", "www.finance.yahoo.com"]:
                 if log_callback: log_callback(f"│   │   │   └── 🛑 BLOCKED Final Non-US Domain: {d_final}")
                 raise BlockedContentException(f"Final URL is Non-US Domain: {d_final}")
        elif "google.com" in d_final:
             # If we are STILL on google, the redirect failed or didn't happen.
             # We probably don't have the article.
             if log_callback: 
                 title_safe = driver.title.strip()[:50]
                 log_callback(f"│   │   │   └── ⚠️ Stuck on Google. Returning Headline Only.")
             return {"text": f"[Stuck on Google] Link: {url}", "publisher": "Google RSS"}
        
        # 4. PARSE RENDERED HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 2. Extract Text
        content_div = soup.find("div", class_="caas-body") or \
                      soup.find("div", class_="article-body") or \
                      soup.find("article") or soup.body
            
        if not content_div:
            if log_callback: log_callback(f"│   │   │   └── ⚠️ No content body found. Returning Headline Only.")
            return {"text": f"[No Content Found] Link: {url}", "publisher": "Unknown"}

        all_tags = content_div.find_all(['p', 'li', 'h2', 'h3'])
        
        clean_text = []
        for tag in all_tags:
            text = tag.get_text().strip()
            if len(text) > 20: 
                lower = text.lower()
                if "click here" in lower: continue
                if "read more" in lower: continue
                clean_text.append(text)
        
        if log_callback: log_callback(f"│   │   │   └── ✅ Extracted {len(clean_text)} lines.")
        
        # 3. Extract Publisher
        publisher = "Yahoo Finance"
        try:
            # Strategy -1: JSON-LD (Golden Source)
            ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in ld_scripts:
                try:
                    data = json.loads(script.string)
                    # Check for Provider (The actual source)
                    if "provider" in data and "name" in data["provider"]:
                        publisher = data["provider"]["name"]
                        break
                    # Fallback to Creator/Author if provider missing (e.g. "Maurie Backman, The Motley Fool")
                    if "author" in data and "name" in data["author"]:
                        auth_name = data["author"]["name"]
                        if "," in auth_name:
                             # "Name, Publisher" format common on Yahoo
                             publisher = auth_name.split(",")[-1].strip()
                        break
                except:
                    continue
            
            # Use HTML Fallbacks only if JSON-LD failed
            if publisher == "Yahoo Finance":
                # Strategy 0: Syndicated Provider Logo (Most Reliable)
                # Try <a> tag wrapper first (often contains the name in aria-label)
                provider_link = soup.select_one("div.caas-logo-provider a")
                if provider_link:
                    if provider_link.get('aria-label'):
                        publisher = provider_link.get('aria-label').strip()
                    elif provider_link.get('title'):
                        publisher = provider_link.get('title').strip()
                
                # If <a> failed or didn't exist, try <img> alt inside provider div
                if publisher == "Yahoo Finance":
                    logo_img = soup.select_one("div.caas-logo-provider img")
                    if logo_img and logo_img.get('alt'):
                        publisher = logo_img.get('alt').strip()

                # Strategy 1: Explicit Text Author (Fallback)
                if publisher == "Yahoo Finance":
                    pub_elem = soup.select_one(".caas-attr-item-author, .caas-author-byline-org, .caas-metadata span")
                    if pub_elem:
                        publisher = pub_elem.get_text().strip()
                    else:
                        # Strategy 2: Check for "By " prefix in metadata text
                        meta_div = soup.find("div", class_="caas-metadata")
                        if meta_div:
                            txt = meta_div.get_text().strip()
                            # Clean messy text like "Matches query • 5 min read"
                            if "Matches" not in txt: 
                                parts = txt.split("•")
                                if len(parts) > 0:
                                    publisher = parts[0].strip()
        except:
            pass

        # Cleanup Publisher String
        publisher = publisher.replace("By ", "").strip()
        # Remove common "rss" suffixes or time info if leaked
        if " min read" in publisher: publisher = publisher.split(" min read")[0].strip()
        
        if len(publisher) > 50 or len(publisher) < 2: 
            publisher = "Yahoo Finance" # Safety Check
        
        # --- 🛡️ SOURCE FILTERING (User Request) ---
        pub_upper = publisher.upper()
        
        # 1. BLOCKLIST (Noise Filters)
        # Uses Global BLOCKED_SOURCES defined at top of file
        # Check if explicitly allowed (Whitelisted for this specific run)

        if pub_upper in BLOCKED_SOURCES:
                if log_callback: log_callback(f"│   │   │   └── 🛑 BLOCKED Source: {publisher}")
                raise BlockedContentException(f"Blocked Source: {publisher}")
        
        # 2. PRIORITIZATION (Quality Highlight)
        PRIORITY_SOURCES = ["REUTERS", "BLOOMBERG", "CNBC"]
        is_priority = False
        for good_src in PRIORITY_SOURCES:
            if good_src in pub_upper:
                publisher = f"⭐ {publisher}" # Visual Tag
                is_priority = True
                break

        if log_callback: 
            if is_priority:
                log_callback(f"│   │   │   └── 🌟 PREMIER SOURCE: {publisher}")
            elif publisher != "Yahoo Finance":
                log_callback(f"│   │   │   └── 🏢 Publisher: {publisher}")

        return {
            "content": clean_text,
            "publisher": publisher
        } if clean_text else None

    except Exception as e:
        # ⚠️ CRITICAL: Propagate DeadDriverException to Engine
        if isinstance(e, DeadDriverException):
            raise e
        if isinstance(e, BlockedContentException):
            raise e
            
        err_str = str(e).lower()
        # DETECT CRITICAL DRIVER DEATH
        # "read timed out", "pool is closed", "connection refused", "max retries exceeded"
        fatal_triggers = ["timed out", "timeout", "connection refused", "connection reset", "httpconnectionpool", "maxretryerror", "invalid session"]
        if any(trigger in err_str for trigger in fatal_triggers):
            if log_callback: log_callback(f"│   │   │   └── ❌ CRITICAL DRIVER FAILURE: {str(e)}")
            raise DeadDriverException("Browser Died")
            
        if log_callback: log_callback(f"│   │   │   └── ❌ Browser Error: {str(e)}")
        return None

def parse_iso_datetime(iso_str):
    try: return parser.parse(iso_str)
    except: return None

class MarketCalendar:
    """
    Utility for NYSE Trading Days, Market Sessions, and DST-aware switchovers.
    """
    # NYSE Full-Day Holidays for 2026
    HOLIDAYS_2026 = {
        datetime.date(2026, 1, 1),   # New Year's Day
        datetime.date(2026, 1, 19),  # MLK Jr. Day
        datetime.date(2026, 2, 16),  # Presidents Day
        datetime.date(2026, 4, 3),   # Good Friday
        datetime.date(2026, 5, 25),  # Memorial Day
        datetime.date(2026, 6, 19),  # Juneteenth
        datetime.date(2026, 7, 3),   # Independence Day (Observed)
        datetime.date(2026, 9, 7),   # Labor Day
        datetime.date(2026, 11, 26), # Thanksgiving
        datetime.date(2026, 12, 25), # Christmas
    }

    # NYSE Early Close Days (1 PM EST / 6 PM UTC or 5 PM UTC in DST)
    EARLY_CLOSE_2026 = {
        datetime.date(2026, 7, 2),   # Day Before Independence Day
        datetime.date(2026, 11, 27), # Day After Thanksgiving
        datetime.date(2026, 12, 24), # Christmas Eve
    }

    # --- DST BOUNDARIES (US Eastern) ---
    # 2026: DST starts Mar 8, ends Nov 1
    # Pre-market opens at 4 AM EST = 9 AM UTC (Standard) / 8 AM UTC (Daylight)
    DST_START_2026 = datetime.date(2026, 3, 8)
    DST_END_2026 = datetime.date(2026, 11, 1)

    @staticmethod
    def is_us_dst(dt):
        """ Returns True if the given date falls within US Daylight Saving Time. """
        if isinstance(dt, datetime.datetime):
            dt = dt.date()
        return MarketCalendar.DST_START_2026 <= dt < MarketCalendar.DST_END_2026

    @staticmethod
    def get_premarket_switch_hour_utc(dt):
        """
        Returns the UTC hour at which pre-market opens (focus switch).
        Standard Time: 9 AM UTC (4 AM EST)
        Daylight Time: 8 AM UTC (4 AM EDT)
        """
        return 8 if MarketCalendar.is_us_dst(dt) else 9

    @staticmethod
    def is_trading_day(dt):
        """ Checks if a given date is a NYSE trading day. """
        if isinstance(dt, datetime.datetime):
            dt = dt.date()
        if dt.weekday() >= 5: # Saturday/Sunday
            return False
        if dt in MarketCalendar.HOLIDAYS_2026:
            return False
        return True

    @staticmethod
    def is_early_close(dt):
        """ Returns True if the given date is an NYSE early close day. """
        if isinstance(dt, datetime.datetime):
            dt = dt.date()
        return dt in MarketCalendar.EARLY_CLOSE_2026

    @staticmethod
    def get_prev_trading_day(dt):
        """ Returns the most recent trading day before the given date. """
        if isinstance(dt, datetime.datetime):
            dt = dt.date()
        curr = dt - datetime.timedelta(days=1)
        while not MarketCalendar.is_trading_day(curr):
            curr -= datetime.timedelta(days=1)
        return curr

    @staticmethod
    def get_next_trading_day(dt):
        """ Returns the next trading day after the given date. """
        if isinstance(dt, datetime.datetime):
            dt = dt.date()
        curr = dt + datetime.timedelta(days=1)
        while not MarketCalendar.is_trading_day(curr):
            curr += datetime.timedelta(days=1)
        return curr

    @staticmethod
    def get_current_or_prev_trading_day(dt):
        """ If today is a trading day, returns today. Otherwise, returns the last trading day. """
        if isinstance(dt, datetime.datetime):
            dt = dt.date()
        curr = dt
        while not MarketCalendar.is_trading_day(curr):
            curr -= datetime.timedelta(days=1)
        return curr