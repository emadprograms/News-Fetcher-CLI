#!/bin/bash

# Configuration
PROJECT_DIR="$(pwd)"
PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python"
RUNNER_SCRIPT="$PROJECT_DIR/main.py"
PLIST_NAME="com.emad.newsfetcher.cli.automation"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# Default run time (8:00 AM)
HOUR=8
MINUTE=0

echo "🦅 News-Fetcher CLI Automation Setup"
echo "--------------------------------------"

# Check if .venv exists
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "Installing requirements..."
    $PYTHON_EXEC -m pip install -r requirements.txt
fi

# Ask for time
read -p "What hour should the automation run? (0-23, default: 8): " user_hour
read -p "What minute should the automation run? (0-59, default: 0): " user_minute

HOUR=${user_hour:-$HOUR}
MINUTE=${user_minute:-$MINUTE}

echo "📝 Generating launchd plist at $PLIST_PATH..."

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_EXEC</string>
        <string>$RUNNER_SCRIPT</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>$HOUR</integer>
        <key>Minute</key>
        <integer>$MINUTE</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/automation_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/automation_stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin</string>
    </dict>
</dict>
</plist>
EOF

echo "🚀 Loading the automation job..."
launchctl unload "$PLIST_PATH" 2>/dev/null
launchctl load "$PLIST_PATH"

echo "✅ Automation scheduled daily at $HOUR:$MINUTE."
echo "📜 Logs will be available at:"
echo "   - $PROJECT_DIR/automation.log (App logs)"
echo "   - $PROJECT_DIR/automation_stdout.log (System output)"
echo "   - $PROJECT_DIR/automation_stderr.log (System errors)"
echo "--------------------------------------"
echo "To disable, run: launchctl unload $PLIST_PATH"
