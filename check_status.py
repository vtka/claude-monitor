#!/usr/bin/env python3
import json
import os
import urllib.request

STATUS_FILE = "last_status.txt"
STATUS_URL = "https://status.anthropic.com/api/v2/status.json"
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

MESSAGES = {
    "none": "✅ Claude API is back to normal — all systems operational.",
    "minor": "⚠️ Claude API has a minor incident.",
    "major": "🔴 Claude API is experiencing a major outage!",
    "critical": "🚨 Claude API is down — critical incident!",
}


def fetch_status():
    with urllib.request.urlopen(STATUS_URL, timeout=10) as response:
        data = json.loads(response.read())
    return data["status"]["indicator"], data["status"]["description"]


def load_last_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE) as f:
            return f.read().strip()
    return None


def save_status(status):
    with open(STATUS_FILE, "w") as f:
        f.write(status)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    urllib.request.urlopen(req, timeout=10)


def main():
    indicator, description = fetch_status()
    last = load_last_status()

    print(f"Current: {indicator} | Last: {last} | {description}")

    if indicator != last:
        # Skip notification on the very first run (no previous state)
        if last is not None:
            message = MESSAGES.get(indicator, f"⚠️ Claude API status changed: {description}")
            send_telegram(message)
            print(f"Sent: {message}")

        save_status(indicator)
    else:
        print("No change.")


if __name__ == "__main__":
    main()
