import datetime
import logging
import sys
import os
import time
import traceback
import requests

# Ensure the root directory is in the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.engines import macro_engine
from modules.engines import stocks_engine
from modules.engines import marketaux_engine
from modules.clients.db_client import NewsDatabase
from modules.clients.infisical_client import InfisicalManager
from modules.clients.calendar_client import CalendarPopulator

# Configure logging
LOGS_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
APP_LOGS_DIR = os.path.join(LOGS_ROOT, "app")
SYS_LOGS_DIR = os.path.join(LOGS_ROOT, "system")

for d in [APP_LOGS_DIR, SYS_LOGS_DIR]:
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join(APP_LOGS_DIR, f"automation_{timestamp}_UTC.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)

def update_log(message):
    logging.info(message)

def cleanup_logs(days_to_keep=7):
    """ Deletes log files older than X days to keep things tidy. """
    try:
        now = time.time()
        seconds_back = days_to_keep * 86400
        count = 0
        
        # Clean App Logs and System Logs
        for folder in [APP_LOGS_DIR, SYS_LOGS_DIR]:
            if not os.path.exists(folder): continue
            for f in os.listdir(folder):
                if f.endswith(".log"):
                    path = os.path.join(folder, f)
                    if os.stat(path).st_mtime < now - seconds_back:
                        os.remove(path)
                        count += 1
        if count > 0:
            update_log(f"🧹 Cleaned up {count} old log files from app/system folders.")
    except Exception as e:
        update_log(f"⚠️ Log cleanup failed: {e}")

def send_discord_report(webhook_url, message):
    """ Sends a notification to Discord. """
    if not webhook_url: return
    try:
        payload = {"content": message}
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        update_log(f"⚠️ Discord notification failed: {e}")

def count_articles_for_date(db, target_date):
    """ Counts total articles stored for a given date. """
    try:
        titles = db.fetch_existing_titles(target_date)
        return len(titles) if titles else 0
    except:
        return 0

def build_discord_report(target_date, report, duration_sec):
    """
    Builds a rich Discord message from the scan report dict.
    """
    status_emoji = "✅" if not report["errors"] else "⚠️"
    
    lines = []
    lines.append(f"🦅 **GRANDMASTER HUNT REPORT** — {target_date}")
    lines.append(f"{'─' * 30}")
    
    # Scan Results
    lines.append(f"📊 **Scan Results:**")
    
    macro = report.get("macro", 0)
    stocks = report.get("stocks", 0)
    company = report.get("company", 0)
    total = macro + stocks + company
    
    lines.append(f"  🌍 Macro News: **{macro}** articles")
    lines.append(f"  📈 Stocks News: **{stocks}** articles")
    lines.append(f"  🏢 Company News: **{company}** articles")
    lines.append(f"  📰 **New in this Hunt: {total} articles**")
    
    # Total in DB for session
    total_db = report.get("total_in_db", 0)
    if total_db > 0:
        lines.append(f"  🗄️ **Total in Trading Session Window: {total_db} articles**")
    
    # Calendar
    cal_events = report.get("calendar_events", 0)
    if cal_events > 0:
        lines.append(f"  📅 Calendar Events: **{cal_events}** synced")
    
    # MarketAux Keys
    ma_keys = report.get("marketaux_keys", 0)
    if ma_keys > 0:
        lines.append(f"  🔑 MarketAux Keys: **{ma_keys}** active")
    
    # Tickers scanned
    tickers_count = report.get("tickers_scanned", 0)
    if tickers_count > 0:
        lines.append(f"  🎯 Tickers Scanned: **{tickers_count}**")
    
    # Duration
    minutes = int(duration_sec // 60)
    seconds = int(duration_sec % 60)
    lines.append(f"  ⏱️ Duration: **{minutes}m {seconds}s**")
    
    # Errors
    if report["errors"]:
        lines.append(f"\n⚠️ **Issues ({len(report['errors'])}):**")
        for err in report["errors"]:
            lines.append(f"  ❌ {err}")
    else:
        lines.append(f"\n{status_emoji} **All systems nominal. No errors.**")
    
    return "\n".join(lines)

def run_automation():
    start_time = time.time()
    update_log("🚀 INITIATING AUTOMATED GRANDMASTER HUNT PROTOCOL (MARKET-CENTRIC DAY)")
    
    # 🕒 MARKET-CENTRIC DAY LOGIC (1 AM UTC ANCHOR, 9 AM UTC SWITCH)
    # ------------------------------------------------------------------
    # 1. News Attribution: Session begins at 1 AM UTC (Post-Market Close).
    # 2. Focus Switch: We focus on "Yesterday" until 9 AM UTC (Pre-market Open).
    # 3. Hard Cutoff: Running before 9 AM UTC enforces a strict 24H block.
    # ------------------------------------------------------------------
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    # DETERMINE TARGET DATE (What session are we reporting on?)
    if now_utc.hour < 9:
        # Before 9 AM UTC: Focus on the trading session that JUST ENDED
        target_date = (now_utc - datetime.timedelta(days=1)).date()
        # STRICTOR WINDOW: From 1 AM (Yesterday) to 1 AM (Today)
        lookback_start = datetime.datetime.combine(target_date, datetime.time(1, 0), tzinfo=datetime.timezone.utc)
        lookback_end = lookback_start + datetime.timedelta(hours=24)
    else:
        # After 9 AM UTC: Focus on the trading session that STARTED TODAY
        target_date = now_utc.date()
        # ONGOING WINDOW: From 1 AM (Today) to NOW
        lookback_start = datetime.datetime.combine(target_date, datetime.time(1, 0), tzinfo=datetime.timezone.utc)
        lookback_end = now_utc
        
    update_log(f"⏰ TRADING DATE FOCUS: {target_date}")
    update_log(f"⏰ LOOKBACK WINDOW (UTC): {lookback_start.strftime('%Y-%m-%d %H:%M')} -> {lookback_end.strftime('%Y-%m-%d %H:%M')}")
    
    # Report tracker
    report = {
        "macro": 0,
        "stocks": 0,
        "company": 0,
        "calendar_events": 0,
        "marketaux_keys": 0,
        "tickers_scanned": 0,
        "total_in_db": 0,
        "errors": []
    }
    
    infisical = InfisicalManager()
    if not infisical.is_connected:
        update_log("❌ Error: Infisical not connected. Check credentials.")
        report["errors"].append("Infisical connection failed")
        return

    # Fetch Discord Webhook
    discord_webhook = infisical.get_discord_webhook()
    
    # 0. Cleanup Old Logs
    cleanup_logs(7)

    # 1. Initialize Databases
    db = None
    analyst_db = None
    try:
        db_url, db_token = infisical.get_turso_news_credentials()
        if db_url and db_token:
            db = NewsDatabase(db_url, db_token)
            update_log("✅ News DB Online")
        else:
            update_log("⚠️ News DB Credentials Missing")
            report["errors"].append("News DB credentials missing from Infisical")
            
        a_url, a_token = infisical.get_turso_analyst_credentials()
        if a_url and a_token:
            analyst_db = NewsDatabase(a_url, a_token, init_schema=False)
            update_log("✅ Analyst DB Online")
    except Exception as e:
        update_log(f"❌ Database Initialization Failed: {e}")
        report["errors"].append(f"Database init failed: {e}")
        send_discord_report(discord_webhook, build_discord_report(target_date, report, time.time() - start_time))
        return

    if not db:
        update_log("❌ Error: News Database is required for scan result persistence.")
        report["errors"].append("News DB is required but unavailable")
        send_discord_report(discord_webhook, build_discord_report(target_date, report, time.time() - start_time))
        return

    # 1.5 Sync Calendar
    try:
        update_log("📅 Syncing Economic & Earnings Calendar...")
        cal_pop = CalendarPopulator(db, analyst_db=analyst_db)
        cal_count = cal_pop.sync_week()
        report["calendar_events"] = cal_count if cal_count else 0
        update_log("✅ Calendar Sync Complete.")
    except Exception as e:
        update_log(f"⚠️ Calendar Sync Failed: {e}")
        report["errors"].append(f"Calendar sync failed: {e}")

    # (Removed unused articles_before snapshot — each scan tracks its own before/after)

    # 2. Run Macro Scan
    try:
        update_log("🌍 Starting Macro Scan...")
        macro_results = macro_engine.run_macro_scan(
            target_date, 
            max_pages=5, 
            log_callback=update_log, 
            db=db, 
            cache_map=cache, 
            existing_titles=existing_titles,
            headless=True,
            lookback_start=lookback_start,
            lookback_end=lookback_end
        )
        report["macro"] = len(macro_results) if macro_results else 0
        update_log(f"✅ Macro Scan Complete. {report['macro']} new articles.")
    except Exception as e:
        update_log(f"❌ Macro Scan Failed: {e}")
        report["errors"].append(f"Macro scan crashed: {e}")

    # 3. Run Stocks Scan
    try:
        update_log("📈 Starting Stocks Scan...")
        existing_titles = db.fetch_existing_titles(target_date)
        cache = db.fetch_cache_map(target_date, None)
        stocks_results = stocks_engine.run_stocks_scan(
            target_date, 
            max_pages=5, 
            log_callback=update_log, 
            db=db, 
            cache_map=cache, 
            existing_titles=existing_titles,
            headless=True,
            lookback_start=lookback_start,
            lookback_end=lookback_end
        )
        report["stocks"] = len(stocks_results) if stocks_results else 0
        update_log(f"✅ Stocks Scan Complete. {report['stocks']} new articles.")
    except Exception as e:
        update_log(f"❌ Stocks Scan Failed: {e}")
        report["errors"].append(f"Stocks scan crashed: {e}")

    # 4. Run Company Specific Scan (MarketAux)
    try:
        update_log("🏢 Starting Company Specific Scan...")
        ma_keys = infisical.get_marketaux_keys()
        report["marketaux_keys"] = len(ma_keys)
        if not ma_keys:
            update_log("⚠️ MarketAux API Keys missing. Skipping company scan.")
            report["errors"].append("MarketAux API keys not found in Infisical")
        else:
            # Fetch monitored tickers from analyst DB
            tickers = []
            if analyst_db:
                tickers = analyst_db.fetch_monitored_tickers()
            
            report["tickers_scanned"] = len(tickers)
            
            if not tickers:
                update_log("ℹ️ No monitored tickers found in Analyst DB.")
                report["errors"].append("No monitored tickers in Analyst DB for MarketAux scan")
            else:
                ma_results = marketaux_engine.run_marketaux_scan(
                    ma_keys, 
                    target_date, 
                    tickers, 
                    update_log, 
                    db=db, 
                    cache_map=cache, 
                    existing_titles=existing_titles,
                    headless=True,
                    lookback_start=lookback_start,
                    lookback_end=lookback_end
                )
                report["company"] = len(ma_results) if ma_results else 0
                update_log(f"✅ Company Scan Complete. {report['company']} new articles.")
    except Exception as e:
        update_log(f"❌ Company Scan Failed: {e}")
        report["errors"].append(f"Company scan crashed: {e}")

    # Final count: total articles in session window
    iso_start = lookback_start.isoformat()
    iso_end = lookback_end.isoformat()
    report["total_in_db"] = db.count_news_range(iso_start, iso_end)
    update_log(f"📦 Total articles in session window: {report['total_in_db']}")

    # Final Report
    duration = time.time() - start_time
    update_log("🏁 GRANDMASTER HUNT COMPLETE.")
    
    discord_message = build_discord_report(target_date, report, duration)
    send_discord_report(discord_webhook, discord_message)

    # 🚪 PROPER EXIT: Close DB connections to avoid AIOHTTP warnings
    try:
        if db:
            db.client.close()
            update_log("🔌 News DB Disconnected.")
        if analyst_db:
            analyst_db.client.close()
            update_log("🔌 Analyst DB Disconnected.")
    except Exception as e:
        update_log(f"⚠️ Error during DB disconnection: {e}")

if __name__ == "__main__":
    try:
        run_automation()
    except Exception as e:
        # 🚨 EMERGENCY OVERRIDE: If the whole script crashes, try to send one last Discord alert
        error_details = traceback.format_exc()
        
        # Try to get webhook one last time if it's not set
        try:
            infisical = InfisicalManager()
            webhook = infisical.get_discord_webhook()
            if webhook:
                target_date = datetime.datetime.now(datetime.timezone.utc).date()
                emergency_msg = (
                    f"🚨 **CRITICAL SYSTEM FAILURE** — {target_date}\n"
                    f"{'─' * 30}\n"
                    f"The Grandmaster Hunt has crashed unexpectedly!\n\n"
                    f"**Error:** `{str(e)}`\n"
                    f"**Details:**\n```python\n{error_details[:500]}...\n```\n"
                    f"🔍 Please check `logs/system/automation_stderr.log` for the full trace."
                )
                requests.post(webhook, json={"content": emergency_msg}, timeout=10)
        except Exception:
            pass # Total silence if even the emergency notification fails
            
        logging.error(f"FATAL CRASH: {e}")
        logging.error(error_details)
        sys.exit(1)
