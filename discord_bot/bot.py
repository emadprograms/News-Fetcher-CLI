import os
import discord
from discord.ext import commands
import aiohttp
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load local environment variables if present
load_dotenv()

# Configuration from Environment Variables
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_PAT")
GITHUB_REPO = os.getenv("GITHUB_REPO", "emadprograms/news-fetcher")
# Workflows
FETCH_WORKFLOW = "newsfetcher.yml"
CHECK_WORKFLOW = "news_checker.yml"

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
async def check_raw_news(ctx, target_date: str = None):
    """Triggers a session status check via GitHub Actions. Optional: !checkrawnews YYYY-MM-DD"""
    
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

    if target_date:
        status_msg = await ctx.send(f"📡 **Connecting to News Grid...** Dispatching status check signal for `{target_date}`.")
    else:
        status_msg = await ctx.send("📡 **Connecting to News Grid...** Dispatching status check signal.")
    
    # Prepare GitHub API request
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{CHECK_WORKFLOW}/dispatches"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # Trigger the workflow
    data = {
        "ref": "main",
        "inputs": {}
    }

    # Add optional target_date input if provided
    if target_date:
        data["inputs"]["target_date"] = target_date
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 204:
                    await status_msg.edit(content="💠 **Check Dispatched!**\n> GitHub is now querying the session status... Fetching live link... 📡")
                    
                    # Try up to 3 times with 4s wait each to get the live link
                    live_url = None
                    for attempt in range(1, 4):
                        await asyncio.sleep(4)
                        runs_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{CHECK_WORKFLOW}/runs"
                        async with session.get(runs_url, headers=headers) as runs_resp:
                            if runs_resp.status == 200:
                                runs_data = await runs_resp.json()
                                if runs_data.get("workflow_runs"):
                                    live_url = runs_data["workflow_runs"][0]["html_url"]
                                    break
                    
                    if live_url:
                        await status_msg.edit(content=f"💠 **Check Dispatched!**\n> GitHub is now querying the session status.\n> 🔗 **[Watch Live Status Check on GitHub](<{live_url}>)**\n\n> The report will be delivered via webhook shortly. 📡")
                    else:
                        await status_msg.edit(content="💠 **Check Dispatched!**\n> GitHub is now querying the session status. (Live link could not be retrieved - check GitHub Actions manually)\n\n> The report will be delivered via webhook shortly. 📡")
                else:
                    try:
                        response_json = await response.json()
                        error_details = response_json.get("message", "No error message provided")
                    except:
                        error_details = await response.text()
                    
                    await status_msg.edit(content=f"❌ **Failed to trigger check.**\nGitHub API Error ({response.status}): `{error_details}`\n> **Workflow:** `{CHECK_WORKFLOW}`\n> **Repo:** `{GITHUB_REPO}`")
                    print(f"Failed to trigger: {response.status} - {error_details}")
    except Exception as e:
        await status_msg.edit(content=f"⚠️ **Internal Error:** Could not reach GitHub.\n`{str(e)}`")

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
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{FETCH_WORKFLOW}/dispatches"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    # We trigger the workflow on the 'main' branch
    data = {
        "ref": "main",
        "inputs": {}
    }
    
    # Add optional target_date input if provided
    if target_date:
        data["inputs"]["target_date"] = target_date
    
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
                        
                        runs_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{FETCH_WORKFLOW}/runs"
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
                        await status_msg.edit(content=f"💠 **Transmission Successful!**{date_note}\n> **NewsFetcher** is now initializing the background runner.\n> 🔗 **[Watch Live Updates on GitHub](<{live_url}>)**\n\n> A typical run takes **10-15 minutes**. The final report will be delivered here once complete. 📰")
                    else:
                        await status_msg.edit(content="💠 **Transmission Successful!**\n> **NewsFetcher** is now initializing the background runner. (Live link could not be retrieved - check GitHub Actions manually)\n\n> A typical run takes **10-15 minutes**. The final report will be delivered here once complete. 📰")
                else:
                    try:
                        response_json = await response.json()
                        error_details = response_json.get("message", "No error message provided")
                    except:
                        error_details = await response.text()
                    
                    await status_msg.edit(content=f"❌ **Failed to trigger workflow.**\nGitHub API Error ({response.status}): `{error_details}`\n> **Workflow:** `{FETCH_WORKFLOW}`\n> **Repo:** `{GITHUB_REPO}`")
                    print(f"Failed to trigger: {response.status} - {error_details}")
            
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
