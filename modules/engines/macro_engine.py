import requests
from bs4 import BeautifulSoup
import time
from dateutil import parser
from urllib.parse import urlparse
from modules.utils import market_utils
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime

# --- CONFIGURATION (Yahoo Macro - Grandmaster Edition) ---
MACRO_RSS_TARGETS = [
    # 1. FED (The Source)
    {
        "name": "Federal Reserve",
        "category": "FED",
        "rss_url": "https://news.google.com/rss/search?q=intitle:%22Federal+Reserve%22+OR+intitle:%22FOMC%22+OR+intitle:%22Powell%22+OR+intitle:%22Fed+Official%22+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 2. INDICATORS (The Hard Data)
    {
        "name": "Economic Indicators",
        "category": "INDICATORS",
        "rss_url": "https://news.google.com/rss/search?q=intitle:%22CPI%22+OR+intitle:%22PPI%22+OR+intitle:%22PCE%22+OR+intitle:%22Nonfarm+Payrolls%22+OR+intitle:%22Jobless+Claims%22+OR+intitle:JOLTS+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 3. TREASURY (The Bond Market)
    {
        "name": "Treasury & Bonds",
        "category": "TREASURY",
        "rss_url": "https://news.google.com/rss/search?q=intitle:%22Yield%22+OR+intitle:%2210-year%22+OR+intitle:%22Treasury+Auction%22+OR+intitle:%22Inverted+Curve%22+OR+intitle:%22Bond+Market%22+-intitle:%22How+to%22+-intitle:%22Best+Bond%22+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 4. ECONOMY_GROWTH (Soft Data & General)
    {
        "name": "Economic Growth",
        "category": "ECONOMY_GROWTH",
        "rss_url": "https://news.google.com/rss/search?q=intitle:GDP+OR+intitle:%22Retail+Sales%22+OR+intitle:ISM+OR+intitle:PMI+OR+intitle:%22Consumer+Confidence%22+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 5. ENERGY (Commodities)
    {
        "name": "Energy & Oil",
        "category": "ENERGY",
        "rss_url": "https://news.google.com/rss/search?q=intitle:Oil+OR+intitle:Crude+OR+intitle:Energy+OR+intitle:OPEC+OR+intitle:%22Natural+Gas%22+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 6. COMMODITIES (Metals & Softs)
    {
        "name": "Commodities",
        "category": "COMMODITIES",
        "rss_url": "https://news.google.com/rss/search?q=intitle:Gold+OR+intitle:Silver+OR+intitle:Copper+OR+intitle:Wheat+OR+intitle:Corn+OR+intitle:Soybeans+OR+intitle:Commodities+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 7. GEO_POLITICS (Risk)
    {
        "name": "Geopolitics",
        "category": "GEO_POLITICS",
        "rss_url": "https://news.google.com/rss/search?q=intitle:Geopolitics+OR+intitle:Biden+OR+intitle:Trump+OR+intitle:War+OR+intitle:%22White+House%22+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 8. TARIFFS (Trump Specific)
    {
        "name": "Trump Tariff Updates",
        "category": "TARIFFS",
        "rss_url": "https://news.google.com/rss/search?q=intitle:%22Trump+tariff+live+updates%22+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 9. FX (Currencies)
    {
        "name": "Currencies (FX)",
        "category": "FX",
        "rss_url": "https://news.google.com/rss/search?q=intitle:%22USD%22+OR+intitle:%22EURUSD%22+OR+intitle:%22USDJPY%22+OR+intitle:%22GBPUSD%22+OR+intitle:%22Dollar+Index%22+OR+intitle:%22DXY%22+-intitle:%22Prediction%22+-intitle:%22Forecast%22+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    },
    # 10. CRYPTO (Bitcoin & Digital Assets)
    {
        "name": "Crypto & Bitcoin",
        "category": "CRYPTO",
        "rss_url": "https://news.google.com/rss/search?q=intitle:Bitcoin+OR+intitle:Crypto+OR+intitle:Ethereum+OR+intitle:%22BTC%22+OR+intitle:%22ETH%22+OR+intitle:Coinbase+OR+intitle:Binance+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
    }
]

def build_feeds_from_events(events):
    """
    Helper: Converts a list of DB event dicts into RSS Target dicts.
    Useful for manual injection from app.py.
    """
    dynamic_feeds = []
    try:
        for ev in events:
            # Construct Strict Query
            # If Before Event: "Forecast", "Preview"
            # If After/During: "Results", "Live"
            # For simplicity, we just look for the Name + Context
            name = ev['name']
            
            # Clean Name Logic (Strip -MM, -YY suffixes that kill search results)
            search_name = name
            for suffix in [" Mm", " Yy", " M/m", " Y/y", " Qq", " Q/q"]:
                search_name = search_name.replace(suffix, "").strip() # Remove " Mm"
                search_name = search_name.replace(suffix.upper(), "").strip() # Remove " MM"
            
            # Remove parenthesis content e.g. "CPI (MoM)" -> "CPI"
            if "(" in search_name:
                search_name = search_name.split("(")[0].strip()

            # Smart Query Construction
            # e.g. "CPI Release" -> intitle:"CPI" OR intitle:"Inflation"
            # We keep it simple: intitle:"Event Name"
            # Clean name for URL
            safe_name = search_name.replace(" ", "+")
            
            rss_url = f"https://news.google.com/rss/search?q=intitle:%22{safe_name}%22+OR+%22{safe_name}+Results%22+site:finance.yahoo.com&hl=en-US&gl=US&ceid=US:en"
            
            dynamic_feeds.append({
                "name": f"🗓️ EVENT: {name}",
                "category": "EVENT_WATCH",
                "rss_url": rss_url
            })
            
    except Exception as e:
        print(f"⚠️ Event Build Error: {e}")
        
    return dynamic_feeds

def generate_event_feeds(db):
    """
    DYNAMIC HUNTER: Checks the Calendar DB for today/tomorrow's events.
    Returns a list of temporary feed targets to hunt for.
    """
    if not db: return []
    
    import datetime
    try:
        # Check Today and Tomorrow
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        
        # Get Events
        events = db.get_upcoming_events(today.isoformat(), tomorrow.isoformat())
        return build_feeds_from_events(events)

    except Exception as e:
        print(f"⚠️ Event Feed Gen Error: {e}")
        return []

def run_macro_scan(target_date, max_pages, log_callback, db=None, cache_map=None, existing_titles=None, resume_targets=None, target_subset=None, manual_event_feeds=None, headless=False, lookback_start=None):
    """
    The Yahoo Macro Hunter (Selenium Edition).
    Fetches Economy, Energy, and Geo news from Yahoo Finance.
    """
    found_reports = []
    # If existing_titles passed, we use it for checking dupes
    if existing_titles is None:
        if db:
            # 🛡️ DEDUPLICATION UPGRADE: Check 3-Day Window (Today, Yesterday, Day Before)
            seen_today = db.fetch_existing_titles(target_date)
            yesterday = target_date - datetime.timedelta(days=1)
            seen_yesterday = db.fetch_existing_titles(yesterday)
            day_before = target_date - datetime.timedelta(days=2)
            seen_day_before = db.fetch_existing_titles(day_before)
            
            # Merge (Today overrides older, but keys are normalized so it's fine)
            seen_titles = {**seen_day_before, **seen_yesterday, **seen_today}
            log_callback(f"🔍 DEDUP CONTEXT: Loaded {len(seen_today)} (T) + {len(seen_yesterday)} (T-1) + {len(seen_day_before)} (T-2).")
        else:
            seen_titles = {}
    else:
        # 🛡️ SAFETY: Convert stale Set cache to Dict
        if isinstance(existing_titles, set):
            seen_titles = {t: "?" for t in existing_titles}
        else:
            seen_titles = existing_titles.copy()
    
    # Init seen_urls from cache_map if available
    if cache_map:
        seen_urls = set(cache_map.keys())
    else:
        seen_urls = set()
    
    log_callback(f"\n📂 ACTIVATING PHASE: MACRO SCANNER (Yahoo Finance Targets)")
    if target_subset:
        log_callback(f"├── 🎯 Filtered Mode: Scanning {len(target_subset)} specific topics.")
    log_callback(f"├── 🖥️ Launching Chrome Driver...")
    
    try:
        driver = market_utils.get_selenium_driver(headless=headless)
    except Exception as e:
        log_callback(f"❌ Failed to launch Chrome: {str(e)}")
        return []

    item_limit = max_pages * 20 
    
    item_limit = max_pages * 20 
    
    # 🌟 DYNAMIC INJECT: Add Calendar Events to the Hit List
    rss_targets = list(MACRO_RSS_TARGETS) # Copy original
    
    # 1. Use Manual Feeds if provided (Granular Selection)
    if manual_event_feeds is not None:
         if manual_event_feeds:
             log_callback(f"├── 📅 CALENDAR INJECTION: {len(manual_event_feeds)} Selected Events added to Hunt.")
             rss_targets.extend(manual_event_feeds)
    
    # 2. Fallback to Auto-Detect if DB exists (Legacy/Default)
    elif db:
        event_feeds = generate_event_feeds(db)
        if event_feeds:
             log_callback(f"├── 📅 CALENDAR DETECTED: {len(event_feeds)} Upcoming Events! Injected into Hunt.")
             rss_targets.extend(event_feeds)

    # Init Progress Manager
    from modules.utils.scan_progress import ScanProgressManager
    pm = ScanProgressManager()
    
    # Map names for tracking
    # FILTER BY SUBSET FIRST (If user selected specific categories)
    if target_subset:
         # target_subset is list of NAMES (strings)
         subset_set = set(target_subset)
         rss_targets = [t for t in rss_targets if t['name'] in subset_set]
    
    target_names = [t['name'] for t in rss_targets]
    
    # 🧠 Smart Tracking Init (Heuristic)
    curr_state = pm.load_state()
    if not curr_state.get("active_scan"):
         pm.start_new_scan("MACRO", target_names, target_date.strftime("%Y-%m-%d"))
    
    # FILTER IF RESUMING
    if resume_targets:
        # Filter logic: Keep targets whose name is in resume_targets (ordered?)
        # Better: keep order of resume_targets?
        # Simpler: Filter rss_targets to keep only those within resume_targets set
        resume_set = set(resume_targets)
        rss_targets = [t for t in rss_targets if t['name'] in resume_set]
        log_callback(f"♻️ RESUMING SCAN: {len(rss_targets)} Feeds Remaining.")

    try:
        for target in rss_targets:
            feed_name = target['name']
            
            # TRACKING START
            pm.mark_target_start(feed_name)
            feed_name = target['name']
            category_tag = target['category']
            rss_url = target['rss_url']
            
            log_callback(f"├── 📡 Connecting to Feed: {feed_name}...")
            
            try:
                # RSS Fetch
                resp = requests.get(rss_url, headers=market_utils.HEADERS, timeout=10)
                soup = BeautifulSoup(resp.content, features="xml")
                items = soup.find_all("item")
                
                if not items:
                    log_callback(f"│   └── ⚠️ Feed empty. Next...")
                    continue
                    
                log_callback(f"│   ├── 📥 Received {len(items)} entries.")
                    
                processed_count = 0
                for item in items:
                    if processed_count >= item_limit: break
                    processed_count += 1
                    
                    title = item.title.text
                    pub_date_str = item.pubDate.text
                    google_link = item.link.text
                    
                    try:
                        pub_dt = parser.parse(pub_date_str)
                        pub_date_only = pub_dt.date()
                    except:
                        continue 
                    
                    # DATE/TIME CHECK (Sliding Window)
                    if lookback_start:
                        if pub_dt < lookback_start:
                            continue
                    else:
                        # Fallback to strict date if no lookback_start provided
                        if pub_date_only != target_date:
                            continue
                    
                    # URL RESOLUTION (Early for Dedupe)
                    real_url = market_utils.decode_google_news_url(google_link)
                    clean_url = real_url.split('?')[0]

                    # 🛑 GLOBAL DB CHECK (The Ultimate Truth)
                    # We must check REAL_URL because that's what we store (with params like ?oc=5)
                    found_db_id = None
                    if db:
                        # Check FULL URL first
                        found_db_id = db.article_exists(real_url, title)
                        if not found_db_id:
                            # Fallback: Check CLEAN URL
                            found_db_id = db.article_exists(clean_url, title)

                        # DEBUG: Just keep one simple log if found
                        # log_callback(f"� DEBUG: Checked {clean_url[:30]}... Result: {found_db_id}")

                    if found_db_id:
                         log_callback(f"│   └── ⏭️ Skipping '{title[:30]}...' (Found in DB Row #{found_db_id})")
                         continue 



                    # Normalize Title (Match DB behavior)
                    norm_title = market_utils.normalize_title(title).lower()
                    
                    # Local Cache Check (Fast Fail)
                    if norm_title in seen_titles: 
                        db_id = seen_titles[norm_title] if isinstance(seen_titles, dict) else "?"
                        log_callback(f"│   └── ⏭️ Skipping: '{title[:40]}...' (Found in Cache Row #{db_id})")
                        continue
    
                    # 🚫 FAST TITLE BLOCKLIST (Catch them before URL resolve)
                    t_low = title.lower()
                    if "motley fool" in t_low or "zacks" in t_low or "benzinga" in t_low:
                         log_callback(f"│   └── 🛑 SKIPPING: Blocked Keyword in Title.")
                         # SAVE AS HIDDEN
                         if db:
                            blocked_item = {
                                "title": title,
                                "url": clean_url,
                                "content": ["BLOCKED TITLE KEYWORD"],
                                "publisher": "BLOCKED",
                                "time": pub_dt.strftime("%H:%M %Z%z").strip(),
                                "published_at": pub_dt.isoformat(),
                                "source_domain": "finance.yahoo.com",
                                "category": "HIDDEN"
                            }
                            db.insert_news([blocked_item], "HIDDEN")
                            seen_titles[norm_title] = "New Session"
                         continue
                    
                    # 🌍 INSTANT FOREIGN TITLES CHECK
                    upper_title = title.upper()
                    foreign_markers = ["YAHOO FINANCE UK", "YAHOO! FINANCE CANADA", "YAHOO FINANCE AUSTRALIA", "YAHOO FINANCE SINGAPORE"]
                    is_foreign = False
                    for marker in foreign_markers:
                        if marker in upper_title:
                             log_callback(f"│   └── 🛑 Skipped Foreign Source: '{title[:40]}...' (Detected: {marker})")
                             is_foreign = True
                             break
                    if is_foreign: continue
                    
                    # 🚫 FAST BLOCKLIST (Title Scan)
                    # Check if any blocked source is the reason
                    is_blacklisted = False
                    block_reason = ""
                    for bad_src in market_utils.BLOCKED_SOURCES:
                        if bad_src in upper_title:
                            # 🛡️ EXCEPTION: Event Watch allowing ZACKS
                            if category_tag == "EVENT_WATCH" and bad_src == "ZACKS":
                                continue
                            is_blacklisted = True
                            block_reason = bad_src
                            break
                    
                    if is_blacklisted:
                        log_callback(f"│   └── 🛑 Skipped: '{title[:40]}...' (Matches Blocklist: {block_reason})")
                        continue
                    
                    log_callback(f"│   ├── 🔹 CANDIDATE: '{title}' [{category_tag}]")
                    log_callback(f"│   │   ├── 🕒 Time: {pub_dt.strftime('%Y-%m-%d %H:%M %Z%z').strip()} (Verified via RSS)")
                    
                    
                    # 🛑 STRICT PRE-FLIGHT DOMAIN CHECK
                    try:
                        d_parts = urlparse(clean_url)
                        domain = d_parts.netloc.lower()
                        if "yahoo.com" in domain:
                            if domain not in ["finance.yahoo.com", "www.finance.yahoo.com"]:
                                log_callback(f"│   │   └── 🛑 SKIPPING: Non-US Domain detected ({domain})")
                                continue
                    except:
                        pass

                    # 🚫 FAST URL BLOCKLIST (Avoid Loading Garbage)
                    u_low = clean_url.lower()
                    if "motley-fool" in u_low or "zacks" in u_low or "benzinga" in u_low:
                         log_callback(f"│   │   └── 🛑 SKIPPING: Blocked Keyword in URL.")
                         
                         # SAVE AS HIDDEN (To Skip Title Next Time)
                         if db:
                            blocked_item = {
                                "title": title,
                                "url": clean_url, # Use clean_url for uniqueness
                                "content": ["BLOCKED URL KEYWORD"],
                                "publisher": "BLOCKED",
                                "time": pub_dt.strftime("%H:%M %Z%z").strip(),
                                "published_at": pub_dt.isoformat(),
                                "source_domain": "finance.yahoo.com",
                                "category": "HIDDEN"
                            }
                            db.insert_news([blocked_item], "HIDDEN")
                            # Update Cache
                            norm_key = market_utils.normalize_title(title).lower()
                            seen_titles[norm_key] = "New Session"
                            
                         continue
                    
                    if clean_url in seen_urls: 
                        log_callback(f"│   └── ⏭️ Skipping duplicate URL (Session Cache).")
                        continue
                    # seen_urls.add(clean_url) <-- MOVED: Only add AFTER success
                    
                    # CACHE CHECK
                    if cache_map and clean_url in cache_map:
                        cached_item = cache_map[clean_url]
                        found_reports.append(cached_item)
                        log_callback(f"│   │   └── 💾 CACHE HIT. Skipping.")
                        continue

                    # BROWSER FETCH (Using shared Yahoo fetcher)
                    # We can use fetch_yahoo_selenium from market_utils because Yahoo structure is consistent
                    # SMART RETRY LOGIC
                    max_attempts = 1
                    if market_utils.is_premium_source(title, real_url):
                        max_attempts = 2
                        log_callback(f"│   │   └── 🌟 Premium Source Detected. Retries Enabled.")

                    content = None
                    
                    # 🔄 RETRY LOOP (Start)
                    for attempt in range(max_attempts):
                        try:
                            # DYNAMIC ALLOW LIST
                            allow_sources = []
                            if category_tag == "EVENT_WATCH":
                                allow_sources = ["ZACKS"]

                            content = market_utils.fetch_yahoo_selenium(driver, real_url, log_callback, allow_sources=allow_sources)
                            if content:
                                break # Success
                        except market_utils.DeadDriverException:
                            log_callback(f"│   │   └── 💀 Browser Died (Attempt {attempt+1}/{max_attempts}). Restarting...")
                            market_utils.force_quit_driver(driver)
                            try:
                                driver = market_utils.get_selenium_driver()
                                log_callback(f"│   │   └── ♻️ Driver Rebooted Successfully.")
                            except Exception as reboot_err:
                                log_callback(f"│   │   └── ❌ Reboot Failed: {reboot_err}")
                                break # Stop retrying if we can't get a driver
                        except market_utils.BlockedContentException as be:
                            log_callback(f"│   │   └── 🛑 {str(be)}")
                            # SAVE AS BLOCKED TO PREVENT RETRY
                            if db:
                                blocked_item = {
                                    "title": title,
                                    "url": clean_url, 
                                    "content": ["BLOCKED SOURCE"],
                                    "publisher": "BLOCKED",
                                    "time": pub_dt.strftime("%H:%M %Z%z").strip(),
                                    "published_at": pub_dt.isoformat(),
                                    "source_domain": "finance.yahoo.com",
                                    "category": "HIDDEN"
                                }
                                db.insert_news([blocked_item], "HIDDEN")
                                
                                # Update Cache
                                norm_key = market_utils.normalize_title(title).lower()
                                seen_titles[norm_key] = "New Session"
                                log_callback(f"│   │   └── 💾 MARKED as BLOCKED in DB.")
                            break # Don't retry blocked content
                        except Exception as e:
                            log_callback(f"│   │   └── ⚠️ Fetch Error (Attempt {attempt+1}/{max_attempts}): {e}")
                    # 🔄 RETRY LOOP (End)
                    
                    if content:
                        # 🛡️ REDUNDANT FINAL CHECK (Paranoid Mode)
                        try:
                            final_u = driver.current_url
                            f_p = urlparse(final_u)
                            f_d = f_p.netloc.lower()
                            if "yahoo.com" in f_d and f_d not in ["finance.yahoo.com", "www.finance.yahoo.com"]:
                                log_callback(f"│   │   └── 🛑 FINAL SECURITY BLOCK: Discarding non-US content from {f_d}")
                                continue
                        except:
                            pass

                        # UNPACK DICT (Handle Legacy List Return for safety)
                        if isinstance(content, list):
                            content_list = content
                            publisher = "Yahoo Finance" 
                        else:
                            content_list = content.get("content", [])
                            publisher = content.get("publisher", "Yahoo Finance")

                        report_item = {
                            "title": title,
                            "url": real_url,
                            "content": content_list,
                            "publisher": publisher,
                            "time": pub_dt.strftime("%H:%M %Z%z").strip(), # Store time for UI
                            "published_at": pub_dt.isoformat(), # Store raw time for DB
                            "source_domain": "finance.yahoo.com",
                            "category": category_tag
                        }
                        
                        # 💾 INCREMENTAL SAVE
                        if db:
                            inserted_count, dups_count = db.insert_news([report_item], category_tag)
                            if inserted_count > 0:
                                log_callback(f"│   │   └── 💾 SAVED to DB immediately.")
                            elif dups_count > 0:
                                log_callback(f"│   │   └── ⚠️ Already Exists (Ignored by DB).")
                            else:
                                log_callback(f"│   │   └── ⚠️ DB Insert Failed (No rows affected).")
                            
                        found_reports.append(report_item)
                        seen_urls.add(clean_url)
                        
                        # Update cache with normalized key
                        norm_key = market_utils.normalize_title(title).lower()
                        seen_titles[norm_key] = "New Session"
                        seen_titles[title] = "New Session"
                        log_callback(f"│   │   └── 🏆 REPORT SECURED! [Source: {publisher}]")
                    else:
                        log_callback(f"│   │   └── ⚠️ Failed to extract content.")
                    
                    log_callback(f"──────────────────────────────────────────────────")
                    
                    # 🧹 SANITIZE DRIVER (Prevent Zombie Hangs)
                    try:
                        if driver: driver.get("about:blank")
                    except:
                        pass # If this fails, the next fetch will trigger the reboot logic
                    
            except market_utils.DeadDriverException:
                log_callback(f"│   └── ❌ CRITICAL: Browser Frozen/Died. Rebooting Driver...")
                try:
                    if driver: driver.quit()
                except:
                    pass
                try:
                    driver = market_utils.get_selenium_driver()
                    log_callback(f"│   └── ♻️ Driver Rebooted Successfully.")
                except Exception as e:
                    log_callback(f"│   └── ❌ Reboot Failed: {e}")
                    # If reboot fails, we might as well stop or continue to try again (likely fail)
                    # Let's continue to let generic error catcher handle next loop if needed, 
                    # but realistically we hope get_selenium_driver works.
                
            except Exception as e:
                log_callback(f"│   └── ❌ RSS Error: {str(e)}")
                
            time.sleep(1)

            # TRACKING COMPLETE
            pm.mark_target_complete(feed_name)
            
    except Exception as e:
        log_callback(f"❌ Critical Macro Scan Error: {e}")
    finally:
        if driver: driver.quit()
        
        # 🏁 ONLY FINISH if we actually went through the targets
        # If interrupted by user/error before starting, don't kill the resume state
        if 'rss_targets' in locals() and len(rss_targets) > 0:
             # Check if we reached the end of the loop normally
             # Simple heuristic: if we are in finally and no exception was unhandled 
             # (though here we catch them). 
             # Better: mark as fully done ONLY if pm says so or we expect it.
             pm.finish_scan()
        
    return found_reports