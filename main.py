import datetime
import logging
import sys
import os

# Ensure the root directory is in the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.engines import macro_engine
from modules.engines import stocks_engine
from modules.engines import marketaux_engine
from modules.clients.db_client import NewsDatabase
from modules.clients.infisical_client import InfisicalManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("automation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def update_log(message):
    logging.info(message)

def run_automation():
    update_log("🚀 INITIATING AUTOMATED GRANDMASTER HUNT PROTOCOL")
    target_date = datetime.date.today()
    update_log(f"🎯 TARGET DATE: {target_date}")
    
    infisical = InfisicalManager()
    if not infisical.is_connected:
        update_log("❌ Error: Infisical not connected. Check credentials.")
        return

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
            
        a_url, a_token = infisical.get_turso_analyst_credentials()
        if a_url and a_token:
            analyst_db = NewsDatabase(a_url, a_token, init_schema=False)
            update_log("✅ Analyst DB Online")
    except Exception as e:
        update_log(f"❌ Database Initialization Failed: {e}")
        return

    if not db:
        update_log("❌ Error: News Database is required for scan result persistence.")
        return

    # 2. Run Macro Scan
    try:
        update_log("🌍 Starting Macro Scan...")
        existing_titles = db.fetch_existing_titles(target_date)
        cache = db.fetch_cache_map(target_date, None)
        macro_engine.run_macro_scan(
            target_date, 
            max_pages=5, 
            log_callback=update_log, 
            db=db, 
            cache_map=cache, 
            existing_titles=existing_titles,
            headless=True
        )
    except Exception as e:
        update_log(f"❌ Macro Scan Failed: {e}")

    # 3. Run Stocks Scan
    try:
        update_log("📈 Starting Stocks Scan...")
        existing_titles = db.fetch_existing_titles(target_date)
        cache = db.fetch_cache_map(target_date, None)
        stocks_engine.run_stocks_scan(
            target_date, 
            max_pages=5, 
            log_callback=update_log, 
            db=db, 
            cache_map=cache, 
            existing_titles=existing_titles,
            headless=True
        )
    except Exception as e:
        update_log(f"❌ Stocks Scan Failed: {e}")

    # 4. Run Company Specific Scan (MarketAux)
    try:
        update_log("🏢 Starting Company Specific Scan...")
        ma_keys = infisical.get_marketaux_keys()
        if not ma_keys:
            update_log("⚠️ MarketAux API Keys missing. Skipping company scan.")
        else:
            # Fetch monitored tickers from analyst DB
            tickers = []
            if analyst_db:
                tickers = analyst_db.fetch_monitored_tickers()
            
            if not tickers:
                update_log("ℹ️ No monitored tickers found in Analyst DB.")
            else:
                existing_titles = db.fetch_existing_titles(target_date)
                cache = db.fetch_cache_map(target_date, None)
                marketaux_engine.run_marketaux_scan(
                    ma_keys, 
                    target_date, 
                    tickers, 
                    update_log, 
                    db=db, 
                    cache_map=cache, 
                    existing_titles=existing_titles,
                    headless=True
                )
    except Exception as e:
        update_log(f"❌ Company Scan Failed: {e}")

    update_log("🏁 AUTOMATED MISSION ACCOMPLISHED.")

if __name__ == "__main__":
    run_automation()
