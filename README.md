# 🦅 News-Fetcher (Automation + Dashboard)

A professional-grade market intelligence tool designed to scrape, aggregate, and analyze financial news from multiple sources (Yahoo Finance, Google News, MarketAux). Built for reliability, background automation, and granular control.

This repository focuses on the core **engines** and **automated background runner**.

## 🚀 Key Features

### 🔍 Grandmaster Hunt (CLI)
- **Automated Scheduling**: Runs daily via macOS `launchd` (08:00 AM by default).
- **Deep Scanning**: Fetches full article content, not just headlines.
- **Micro & Macro**: Segregates "Macro" economic news from "Micro" company-specific catalysts.
- **Auto-Sync Calendar**: Automatically fetches Economic and Earnings calendars before every scan.

### 🔒 Centralized Security (Infisical)
- **Machine Identity Auth**: Managed via Infisical Universal Auth.
- **Dynamic Discovery**: Automatically finds all MarketAux and Turso credentials in your project.
- **Zero-Trust**: No keys stored in code; strictly uses `.env` for Infisical access.

### 📋 Real-time Logging
- **Timestamped Logs**: Every run generates a unique log file in the `logs/` directory.
- **Live Streaming**: Logs are flushed to disk in real-time for immediate monitoring.

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
    Create a `.env` file with your Infisical Machine Identity credentials:
    ```env
    INFISICAL_CLIENT_ID="your_client_id"
    INFISICAL_CLIENT_SECRET="your_client_secret"
    INFISICAL_PROJECT_ID="your_project_id"
    ```

## 🖥️ Usage

### Run Manually
```bash
python3 main.py
```

### Setup Automation (macOS)
Run the configuration script to schedule daily scans:
```bash
chmod +x setup_automation.sh
./setup_automation.sh
```

---
*Built for the Alpha Hunter.*
