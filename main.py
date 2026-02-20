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

def send_discord_report(webhook_url, message, embeds=None):
    """ Sends a notification to Discord. Supports rich embeds. """
    if not webhook_url: return
    try:
        if embeds:
            payload = {"embeds": embeds}
        else:
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

def build_discord_report(target_date, report, duration_sec, run_number=1, max_runs=3):
    """
    Builds a rich Discord embed with categorized alerting.
    Returns (message_text, embed_list).
    """
    macro = report.get("macro", 0)
    stocks = report.get("stocks", 0)
    company = report.get("company", 0)
    total = macro + stocks + company
    total_db = report.get("total_in_db", 0)
    cal_events = report.get("calendar_events", 0)
    ma_keys = report.get("marketaux_keys", 0)
    tickers_count = report.get("tickers_scanned", 0)
    errors = report.get("errors", [])
    
    minutes = int(duration_sec // 60)
    seconds = int(duration_sec % 60)
    
    # Categorize errors into warnings and criticals
    warnings = [e for e in errors if any(w in e.lower() for w in ["missing", "not found", "skipping", "sync failed"])]
    criticals = [e for e in errors if e not in warnings]
    
    # Determine embed color (Discord color codes)
    if criticals:
        color = 0xFF0000  # Red
        status_line = "🚨 CRITICAL ISSUES DETECTED"
    elif warnings:
        color = 0xFFAA00  # Orange/Yellow
        status_line = "⚠️ Completed with Warnings"
    else:
        color = 0x00FF00  # Green
        status_line = "✅ All systems nominal"
    
    # Build Description
    desc_lines = [
        f"🌍 **Macro:** {macro}  |  📈 **Stocks:** {stocks}  |  🏢 **Company:** {company}",
        f"📰 **New in Hunt:** {total} articles",
    ]
    if total_db > 0:
        desc_lines.append(f"🗄️ **Session Total:** {total_db} articles")
    if cal_events > 0:
        desc_lines.append(f"📅 **Calendar:** {cal_events} events synced")
    if tickers_count > 0:
        desc_lines.append(f"🎯 **Tickers:** {tickers_count}  |  🔑 **Keys:** {ma_keys}")
    desc_lines.append(f"⏱️ **Duration:** {minutes}m {seconds}s  |  **Run:** {run_number}/{max_runs}")
    
    embed = {
        "title": f"🦵 GRANDMASTER HUNT — {target_date}",
        "description": "\n".join(desc_lines),
        "color": color,
        "footer": {"text": status_line}
    }
    
    # Add error fields
    if criticals:
        embed["fields"] = embed.get("fields", [])
        embed["fields"].append({
            "name": f"🚨 Critical ({len(criticals)})",
            "value": "\n".join([f"❌ {e}" for e in criticals[:5]]),
            "inline": False
        })
    if warnings:
        embed["fields"] = embed.get("fields", [])
        embed["fields"].append({
            "name": f"⚠️ Warnings ({len(warnings)})",
            "value": "\n".join([f"• {w}" for w in warnings[:5]]),
            "inline": False
        })
    
    return None, [embed]

def run_automation(run_number=1, max_runs=3):
    """
    Main automation orchestrator.
    Returns a result dict: {"success": bool, "articles_found": int, "errors": list}
    """
    start_time = time.time()
    update_log("🚀 INITIATING AUTOMATED GRANDMASTER HUNT PROTOCOL (MARKET-CENTRIC DAY)")
    
    # 🕒 REF-LOGIC: MARKET-CENTRIC TRADING SESSIONS
    # ------------------------------------------------------------------
    # Anchor: 1 AM UTC | Switch-over: DST-aware (8 AM or 9 AM UTC)
    # Weekends/Holidays: Treated as extensions of the last Trading Day.
    # ------------------------------------------------------------------
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today_utc = now_utc.date()
    
    # 1. Identify the 'Logical' Trading Session we are dealing with
    current_market_day = market_utils.MarketCalendar.get_current_or_prev_trading_day(today_utc)
    
    # 2. DST-Aware Pre-market Switch Hour
    switch_hour = market_utils.MarketCalendar.get_premarket_switch_hour_utc(today_utc)
    
    # 3. Determine if we shift focus
    is_early_trading_day = (today_utc == current_market_day and now_utc.hour < switch_hour)
    
    if is_early_trading_day:
        # Before pre-market on a Trading Day: Finalize the PREVIOUS session
        target_date = market_utils.MarketCalendar.get_prev_trading_day(current_market_day)
        lookback_start = datetime.datetime.combine(target_date, datetime.time(1, 0), tzinfo=datetime.timezone.utc)
        lookback_end = datetime.datetime.combine(current_market_day, datetime.time(1, 0), tzinfo=datetime.timezone.utc)
    else:
        # After pre-market or on a Weekend/Holiday: Focus on the CURRENT/LATEST session
        target_date = current_market_day
        lookback_start = datetime.datetime.combine(target_date, datetime.time(1, 0), tzinfo=datetime.timezone.utc)
        lookback_end = now_utc
            
    update_log(f"⏰ TRADING DATE FOCUS: {target_date} (Switch Hour: {switch_hour}:00 UTC)")
    update_log(f"⏰ LOOKBACK WINDOW (UTC): {lookback_start.strftime('%Y-%m-%d %H:%M')} -> {lookback_end.strftime('%Y-%m-%d %H:%M')}")
    
    # Early Close info
    if market_utils.MarketCalendar.is_early_close(target_date):
        update_log(f"⚠️ NOTE: {target_date} is an NYSE Early Close day (1 PM EST).")
    
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
        # Range-based dedup: covers entire session window (critical for weekend leaps)
        iso_start = lookback_start.isoformat()
        iso_end = lookback_end.isoformat()
        existing_titles = db.fetch_existing_titles_range(iso_start, iso_end)
        cache = db.fetch_cache_map(target_date, None)
        macro_results = macro_engine.run_macro_scan(
            target_date, 
            max_pages=5, 
            log_callback=update_log, 
            db=db, 
            cache_map=cache, 
            existing_titles=existing_titles,
            headless=True,
            lookback_start=lookback_start,
            lookback_end=lookback_end,
            trading_session_date=target_date
        )
        report["macro"] = len(macro_results) if macro_results else 0
        update_log(f"✅ Macro Scan Complete. {report['macro']} new articles.")
    except Exception as e:
        update_log(f"❌ Macro Scan Failed: {e}")
        report["errors"].append(f"Macro scan crashed: {e}")

    # 3. Run Stocks Scan
    try:
        update_log("📈 Starting Stocks Scan...")
        # Refresh dedup context (macro may have added articles)
        existing_titles = db.fetch_existing_titles_range(iso_start, iso_end)
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
            lookback_end=lookback_end,
            trading_session_date=target_date
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
                    lookback_end=lookback_end,
                    trading_session_date=target_date
                )
                report["company"] = len(ma_results) if ma_results else 0
                update_log(f"✅ Company Scan Complete. {report['company']} new articles.")
    except Exception as e:
        update_log(f"❌ Company Scan Failed: {e}")
        report["errors"].append(f"Company scan crashed: {e}")

    # Final count: total articles in session window
    # 📝 HUNT HEARTBEAT: Log Start
    hunt_id = db.log_hunt_start(run_number, target_date, lookback_start, lookback_end)
    update_log(f"💓 Hunt Heartbeat Started (ID: {hunt_id}, Run: {run_number}/{max_runs})")

    iso_start = lookback_start.isoformat()
    iso_end = lookback_end.isoformat()
    report["total_in_db"] = db.count_news_range(iso_start, iso_end)
    update_log(f"📦 Total articles in session window: {report['total_in_db']}")

    # Final Report
    total_found = report["macro"] + report["stocks"] + report["company"]
    duration = time.time() - start_time
    update_log("🏁 GRANDMASTER HUNT COMPLETE.")
    
    msg_text, embeds = build_discord_report(target_date, report, duration, run_number, max_runs)
    send_discord_report(discord_webhook, msg_text, embeds)

    # 📝 HUNT HEARTBEAT: Log End
    hunt_status = "SUCCESS" if not report["errors"] else ("PARTIAL" if total_found > 0 else "FAILED")
    db.log_hunt_end(hunt_id, hunt_status, total_found, report["total_in_db"], duration, report["errors"] or None)
    update_log(f"💓 Hunt Heartbeat Finalized: {hunt_status}")

    # Return result for multi-run logic
    return {
        "success": not report["errors"],
        "articles_found": total_found,
        "errors": report["errors"]
    }

MAX_HUNT_RUNS = 3
COOLDOWN_BETWEEN_RUNS = 30  # seconds

if __name__ == "__main__":
    for run_num in range(1, MAX_HUNT_RUNS + 1):
        try:
            update_log(f"\n{'='*50}")
            update_log(f"🔁 HUNT ATTEMPT {run_num}/{MAX_HUNT_RUNS}")
            update_log(f"{'='*50}")
            
            result = run_automation(run_number=run_num, max_runs=MAX_HUNT_RUNS)
            
            if result and result.get("success"):
                update_log(f"✅ Run {run_num} completed successfully. No need to retry.")
                break
            else:
                errors = result.get("errors", []) if result else ["Unknown failure"]
                update_log(f"⚠️ Run {run_num} completed with {len(errors)} error(s).")
                if run_num < MAX_HUNT_RUNS:
                    update_log(f"⏳ Cooling down {COOLDOWN_BETWEEN_RUNS}s before next attempt...")
                    time.sleep(COOLDOWN_BETWEEN_RUNS)
                    
        except Exception as e:
            error_details = traceback.format_exc()
            update_log(f"🚨 Run {run_num} CRASHED: {e}")
            
            if run_num == MAX_HUNT_RUNS:
                # Final attempt failed — send emergency Discord alert
                try:
                    infisical = InfisicalManager()
                    webhook = infisical.get_discord_webhook()
                    if webhook:
                        target_date = datetime.datetime.now(datetime.timezone.utc).date()
                        emergency_embed = {
                            "title": f"🚨 CRITICAL SYSTEM FAILURE — {target_date}",
                            "description": (
                                f"The Grandmaster Hunt has crashed on **all {MAX_HUNT_RUNS} attempts**!\n\n"
                                f"**Error:** `{str(e)}`\n"
                                f"**Details:**\n```python\n{error_details[:500]}...\n```\n"
                                f"🔍 Check `logs/app/` for the full trace."
                            ),
                            "color": 0xFF0000  # Red
                        }
                        requests.post(webhook, json={"embeds": [emergency_embed]}, timeout=10)
                except Exception:
                    pass
                
                logging.error(f"FATAL CRASH (All {MAX_HUNT_RUNS} attempts): {e}")
                logging.error(error_details)
                sys.exit(1)
            else:
                update_log(f"⏳ Cooling down {COOLDOWN_BETWEEN_RUNS}s before retry...")
                time.sleep(COOLDOWN_BETWEEN_RUNS)
    
    update_log("🎬 ALL HUNT ATTEMPTS FINISHED.")
