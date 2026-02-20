import os
import discord
from discord.ext import commands
import aiohttp
import asyncio
from dotenv import load_dotenv

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
    print(f'✅ Logged in as {bot.user.name} ({bot.user.id})')
    print('Bot is ready to receive commands.')

@bot.command(name="fetch")
async def trigger_fetch(ctx):
    """Triggers the GitHub Actions News-Fetcher workflow."""
    
    # Visual feedback focused on News-Fetcher identity
    status_msg = await ctx.send("� **Connecting to News Grid...** Dispatching signal to GitHub.")
    
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
                        await status_msg.edit(content=f"💠 **Transmission Successful!**\n> **NewsFetcher** is now initializing the background runner.\n> 🔗 **[Watch Live Updates on GitHub]({live_url})**\n\n> A typical run takes **10-15 minutes**. The final report will be delivered here once complete. 📰")
                        print(f"Triggered fetch via Discord user: {ctx.author}")
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
        print("❌ CRITICAL: DISCORD_BOT_TOKEN is missing.")
        exit(1)
    if not GITHUB_TOKEN:
        print("❌ CRITICAL: GITHUB_PAT is missing.")
        exit(1)
        
    print("Starting bot...")
    bot.run(DISCORD_TOKEN)
