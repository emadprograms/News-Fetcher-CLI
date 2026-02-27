# News Fetcher (Grandmaster Hunt)

A sophisticated news aggregation and analysis system designed for financial markets, featuring a Streamlit dashboard, Discord integration, and automated scraping engines.

## Tech Stack
- **Language:** Python 3.12+
- **Frontend:** Streamlit
- **Database:** Turso (libsql)
- **Secrets:** Infisical (infisicalsdk)
- **Automation:** Selenium (Headless Chrome), GitHub Actions
- **Data Sources:** Yahoo Finance, MarketAux, InvestPy, various RSS feeds
- **Messaging:** Discord (Webhooks & Bot)

## Project Structure
- `main.py`: Entry point for automated "Grandmaster Hunt" sessions.
- `streamlit_app.py`: Interactive dashboard for visualizing news and managing scans.
- `modules/`:
  - `engines/`: Scrapers for Macro, Stocks, and Company-specific news.
  - `clients/`: API clients for Database (Turso), Secrets (Infisical), and Calendars.
  - `utils/`: Market calendar logic and scan progress management.
- `discord_bot/`: Separate Discord bot service.
- `tools/`: Internal folder for scripts, experimentation, and debugging tools (e.g., `test_infisical.py`).
- `logs/`: Application and system logs.

## Architectural Decisions & Evolution

- **Lightweight Discord Bot:** To prevent server load and hanging, the Discord bot acts solely as a communication bridge. Commands like `!checkrawnews` and `!rawnews` do not query the database directly; they trigger GitHub Actions, which then perform the work and return results via Discord Webhooks.
- **Infisical SDK v3 Fixes:** Resolved `BaseSecret` attribute errors caused by the v3 SDK's nested secret structure. Implemented a robust `_extract_value` and `_extract_key_name` helper to handle both snake_case and camelCase attributes across SDK versions.
- **Dynamic Key Discovery:** MarketAux keys are discovered dynamically using a prefix search (`marketaux-` and `marketaux_`). The legacy `MARKETAUX_API_KEYS` list check was removed to eliminate unnecessary 404 errors during discovery.
- **Session-Aware Queries:** GitHub Actions and bot commands respect the `target_date` argument, ensuring queries for past sessions resolve to the correct historical windows.

## Engineering Standards
- **Tools Usage:** Always use the `tools/` folder for any new scripts, debugging, or investigative code. This keeps the root directory clean and provides a centralized place for project utilities.
- **Modular Design:** Keep scraping logic in `engines/` and infrastructure logic in `clients/`.

## Common Commands
- **Run Dashboard:** `streamlit run streamlit_app.py`
- **Run Automation:** `python main.py`
- **Run Discord Bot:** `python discord_bot/bot.py`
- **Run Status Check (Manual):** `MODE=CHECK python main.py`
- **Tests:** `pytest`

## Discord Bot Commands
- `!rawnews [YYYY-MM-DD]`: Triggers the GitHub Actions workflow to run a full news hunt for the specified or current trading session.
- `!checkrawnews [YYYY-MM-DD]`: Triggers a lightweight GitHub Action that queries the database for the session window and article count, then delivers the result via webhook. Wrap links in `<>` to avoid Discord banners.

## Critical Files
- `.streamlit/secrets.toml`: Local Streamlit secrets (use Infisical for production).
- `requirements.txt`: Project dependencies.
- `modules/clients/infisical_client.py`: Core secret manager used across the app.
