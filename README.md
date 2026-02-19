# 🦅 News-Fetcher: The Grandmaster Edition

A professional-grade market intelligence tool designed to scrape, aggregate, and analyze financial news from multiple sources (Yahoo Finance, Google News, MarketAux). Built for reliability, speed, and granular control.

## 🚀 Key Features

### 🔍 Grandmaster Hunt
- **Deep Scanning**: Fetches full article content, not just headlines.
- **Micro & Macro**: Segregates "Macro" economic news from "Micro" company-specific catalysts.
- **Granular Control**: Select specific sectors (Earnings, IPOs, Insider Trades) and filter daily earnings by specific companies (e.g., "Scan Nike only").

### 🔒 Centralized Security (Infisical)
- **Machine Identity Auth**: All API keys and credentials are managed via Infisical.
- **Universal Auth**: Seamless authentication using Client IDs and Secrets, with auto-rotation for API keys.
- **Zero-Trust**: No sensitive keys are stored in the codebase.

## 🛠️ Setup

1.  **Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Secrets (Infisical)**:
    Create a `.streamlit/secrets.toml` file with your Infisical Machine Identity credentials:
    ```toml
    [infisical]
    client_id = "..."
    client_secret = "..."
    project_id = "..."
    ```

## 🖥️ Usage

Run the dashboard:
```bash
streamlit run app.py
```

### Marketplace Settings
- **Enable Market Scan**: Toggles the macro-level scan.
- **Select Market Categories**: Filter for specific news types (e.g., "Earnings & Results", "Mergers & Acquisitions").
- **Target Specific Companies**: (Visible when "Earnings" is enabled) meticulously select which reporting companies to scan today.

### Company Watchlist
- **Enable Specific Company Scan**: Force-scan your personal watchlist.
- **Select Companies**: Defaults to ALL your monitored tickers.

---
*Built for the Alpha Hunter.*
