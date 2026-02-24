# News Fetcher (Grandmaster Hunt)

A sophisticated news aggregation and analysis system designed for financial markets, featuring a Streamlit dashboard, Discord integration, and automated scraping engines.

## Tech Stack
- **Language:** Python 3.12+
- **Frontend:** Streamlit
- **Database:** Turso (libsql)
- **Secrets:** Infisical
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
- `logs/`: Application and system logs.

## Engineering Standards
- **Modular Design:** Keep scraping logic in `engines/` and infrastructure logic in `clients/`.
- **Error Handling:** Automated runs (`main.py`) use a multi-attempt strategy (max 3 runs) with Discord alerting.
- **Session Logic:** Market sessions are resolved based on UTC time and NYSE trading hours in `modules/utils/market_utils.py`.
- **Type Safety:** Use type hints where possible for better maintainability.

## Common Commands
- **Run Dashboard:** `streamlit run streamlit_app.py`
- **Run Automation:** `python main.py`
- **Run Discord Bot:** `python discord_bot/bot.py`
- **Tests:** `pytest`

## Critical Files
- `.streamlit/secrets.toml`: Local Streamlit secrets (use Infisical for production).
- `requirements.txt`: Project dependencies.
- `modules/clients/infisical_client.py`: Core secret manager used across the app.
