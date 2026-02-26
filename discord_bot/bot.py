import os
import sys
import discord
from discord.ext import commands
import aiohttp
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Ensure the root directory is in the path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.clients.db_client import NewsDatabase
from modules.clients.infisical_client import InfisicalManager
import modules.utils.market_utils as market_utils

# Load local environment variables if present
load_dotenv()

# Configuration from Environment Variables
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_PAT")
GITHUB_REPO = os.getenv("GITHUB_REPO", "emadprograms/News-Fetcher-CLI")
WORKFLOW_FILENAME = os.getenv("WORKFLOW_FILENAME", "manual_run.yml")

# Setup intents for message reading
intents = discord.Intents.default()
intents.message_content = True

# Initialize Bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('Bot is ready to receive commands.')

@bot.command(name="checkrawnews")
async def check_raw_news(ctx):
    """Shows the current session window and how many articles are in the database for it."""
    try:
        status_msg = await ctx.send("🔍 **Checking database...**")
        
        # 🕒 Resolve Current Session
        now_utc = datetime.now(timezone.utc)
        target_date, lookback_start, lookback_end = market_utils.MarketCalendar.resolve_trading_session(now_utc)
        
        # 🔗 Connect to Database
        infisical = InfisicalManager()
        if not infisical.is_connected:
            await status_msg.edit(content="❌ **Error:** Could not connect to Infisical.")
            return

        db_url, db_token = infisical.get_turso_news_credentials()
        if not db_url or not db_token:
            await status_msg.edit(content="❌ **Error:** Database credentials missing in Infisical.")
            return
            
        db = NewsDatabase(db_url, db_token, init_schema=False)
        
        # 📊 Count Articles
        iso_start = lookback_start.isoformat()
        iso_end = lookback_end.isoformat()
        total_in_db = db.count_news_range(iso_start, iso_end)
        
        # Build Response
        start_str = lookback_start.strftime("%a %b %d, %H:%M UTC")
        end_str = lookback_end.strftime("%a %b %d, %H:%M UTC")
        
        embed = discord.Embed(
            title=f"📊 Session Status: {target_date}",
            description=(
                f"🗓️ **Start:** `{start_str}`\n"
                f"🗓️ **End:** `{end_str}`\n\n"
                f"📰 **Articles in DB:** `{total_in_db}`"
            ),
            color=0x3498db, # Blue
            timestamp=now_utc
        )
        embed.set_footer(text="NewsFetcher Live Grid")
        
        await status_msg.edit(content=None, embed=embed)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in !checkrawnews: {error_details}")
        await ctx.send(f"⚠️ **Internal Error:** `{str(e)}`")

@bot.command(name="rawnews")
async def trigger_fetch(ctx, target_date: str = None):
    """Triggers the GitHub Actions News-Fetcher workflow. Optional: !rawnews YYYY-MM-DD"""
    
    # 🛡️ Validate date format BEFORE dispatching
    if target_date:
        try:
            parsed = datetime.strptime(target_date, "%Y-%m-%d")
            
            # Allow targeting upcoming trading days (up to 5 days ahead) for weekends/holidays
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            max_future = today + timedelta(days=5)
            
            if parsed > max_future:
                await ctx.send(
                    f"❌ **Invalid date:** `{target_date}` is too far in the future.\n"
                    f"> You can target dates up to 5 days ahead to prepare for the next trading session."
                )
                return
                
            target_date = parsed.strftime("%Y-%m-%d")  # Normalize to clean format
        except ValueError:
            await ctx.send(
                f"❌ **Invalid date format:** `{target_date}`\n"
                f"> Expected format: **YYYY-MM-DD** (e.g. `2026-02-18`)\n"
                f"> Please try again with a valid date."
            )
            return
    
    # Visual feedback focused on News-Fetcher identity
    if target_date:
        status_msg = await ctx.send(f"📡 **Connecting to News Grid...** Dispatching signal for date: `{target_date}`")
    else:
        status_msg = await ctx.send("📡 **Connecting to News Grid...** Dispatching signal to GitHub.")
    
    # Prepare GitHub API request
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILENAME}/dispatches"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # We trigger the workflow on the 'main' branch
    data = {
        "ref": "main"
    }
    
    # Add optional target_date input if provided
    if target_date:
        data["inputs"] = {
            "target_date": target_date
        }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                # GitHub returns 204 No Content on a successful dispatch
                if response.status == 204:
                    await status_msg.edit(content="💠 **Transmission Successful!**\n> **NewsFetcher** is initializing... Fetching live link... 📡")
                    print(f"Triggered fetch via Discord user: {ctx.author}")
                    
                    # Try up to 3 times with 4s wait each (total 12s)
                    live_url = None
                    for attempt in range(1, 4):
                        await asyncio.sleep(4)
                        print(f"Attempt {attempt} to fetch live link...")
                        
                        runs_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILENAME}/runs"
                        async with session.get(runs_url, headers=headers) as runs_resp:
                            if runs_resp.status == 200:
                                runs_data = await runs_resp.json()
                                if runs_data.get("workflow_runs"):
                                    live_url = runs_data["workflow_runs"][0]["html_url"]
                                    break
                            else:
                                print(f"Failed to fetch runs on attempt {attempt}: {runs_resp.status}")
                    
                    if live_url:
                        date_note = f" for `{target_date}`" if target_date else ""
                        await status_msg.edit(content=f"💠 **Transmission Successful!**{date_note}\n> **NewsFetcher** is now initializing the background runner.\n> 🔗 **[Watch Live Updates on GitHub]({live_url})**\n\n> A typical run takes **10-15 minutes**. The final report will be delivered here once complete. 📰")
                    else:
                        await status_msg.edit(content="💠 **Transmission Successful!**\n> **NewsFetcher** is now initializing the background runner. (Live link could not be retrieved - check GitHub Actions manually)\n\n> A typical run takes **10-15 minutes**. The final report will be delivered here once complete. 📰")
                else:
                    response_json = await response.json() if response.content_type == 'application/json' else {}
                    error_details = response_json.get("message", await response.text())
                    await status_msg.edit(content=f"❌ **Failed to trigger workflow.**\nGitHub API Error ({response.status}): `{error_details}`")
                    print(f"Failed to trigger: {response.status} - {await response.text()}")
            
    except Exception as e:
        await status_msg.edit(content=f"⚠️ **Internal Error:** Could not reach GitHub.\n`{str(e)}`")
        print(f"Exception triggering workflow: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("CRITICAL: DISCORD_BOT_TOKEN is missing.")
        exit(1)
    if not GITHUB_TOKEN:
        print("CRITICAL: GITHUB_PAT is missing.")
        exit(1)
        
    print("Starting bot...")
    bot.run(DISCORD_TOKEN)
