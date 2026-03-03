#!/usr/bin/env python3
import json
import os
import urllib.request

STATE_FILE = "last_status.json"
SUMMARY_URL = "https://status.anthropic.com/api/v2/summary.json"
INCIDENTS_URL = "https://status.anthropic.com/api/v2/incidents/unresolved.json"
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

INDICATOR_EMOJI = {
    "none": "✅",
    "minor": "⚠️",
    "major": "🔴",
    "critical": "🚨",
}

COMPONENT_EMOJI = {
    "operational": "✅",
    "degraded_performance": "⚠️",
    "partial_outage": "🟠",
    "major_outage": "🔴",
    "under_maintenance": "🔧",
}


def fetch(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read())


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)


def format_new_incident(incident):
    emoji = INDICATOR_EMOJI.get(incident.get("impact", "minor"), "⚠️")
    status = incident["status"].replace("_", " ").title()

    lines = [
        f"{emoji} <b>Incident: {status}</b>",
        "",
        f"<b>{incident['name']}</b>",
    ]

    if incident.get("incident_updates"):
        lines.append(incident["incident_updates"][0]["body"])

    affected = incident.get("components", [])
    if affected:
        lines.append("")
        for c in affected:
            component_emoji = COMPONENT_EMOJI.get(c.get("status", ""), "⚠️")
            lines.append(f"{component_emoji} {c['name']}")

    lines += ["", f'<a href="{incident["shortlink"]}">View all updates</a>']
    return "\n".join(lines)


def format_resolved_incident(incident):
    lines = [
        "✅ <b>Incident: Resolved</b>",
        "",
        f"<b>{incident['name']}</b>",
        "This incident has been resolved.",
    ]

    affected = incident.get("components", [])
    if affected:
        lines.append("")
        for c in affected:
            lines.append(f"✅ {c['name']}")

    lines += ["", f'<a href="{incident["shortlink"]}">View incident</a>']
    return "\n".join(lines)


def main():
    summary = fetch(SUMMARY_URL)
    unresolved = fetch(INCIDENTS_URL)

    current_indicator = summary["status"]["indicator"]
    current_incidents = {i["id"]: i for i in unresolved["incidents"]}
    current_ids = set(current_incidents)

    state = load_state()
    first_run = state is None

    if first_run:
        save_state({"indicator": current_indicator, "incident_ids": list(current_ids)})
        print(f"First run. Indicator: {current_indicator}, Active incidents: {len(current_ids)}")
        return

    last_indicator = state["indicator"]
    last_ids = set(state["incident_ids"])

    new_ids = current_ids - last_ids
    resolved_ids = last_ids - current_ids

    for incident_id in new_ids:
        incident = current_incidents[incident_id]
        msg = format_new_incident(incident)
        send_telegram(msg)
        print(f"Notified new incident: {incident['name']}")

    for incident_id in resolved_ids:
        try:
            data = fetch(f"https://status.anthropic.com/api/v2/incidents/{incident_id}.json")
            msg = format_resolved_incident(data["incident"])
        except Exception:
            msg = "✅ <b>Claude API incident has been resolved.</b>"
        send_telegram(msg)
        print(f"Notified resolved incident: {incident_id}")

    # Fallback: overall status changed but no tracked incidents (edge case)
    if not new_ids and not resolved_ids and current_indicator != last_indicator:
        emoji = INDICATOR_EMOJI.get(current_indicator, "⚠️")
        components = "\n".join(
            f"{COMPONENT_EMOJI.get(c['status'], '❓')} {c['name']}"
            for c in summary["components"]
            if c["status"] != "operational"
        )
        msg = f"{emoji} <b>Claude API: {summary['status']['description']}</b>"
        if components:
            msg += f"\n\n{components}"
        send_telegram(msg)
        print(f"Notified status change: {current_indicator}")

    if not new_ids and not resolved_ids:
        print("No changes.")

    save_state({"indicator": current_indicator, "incident_ids": list(current_ids)})


if __name__ == "__main__":
    main()
