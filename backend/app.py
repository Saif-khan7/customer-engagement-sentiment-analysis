import os, requests
from flask import Flask, request, jsonify
from transformers import pipeline
from dotenv import load_dotenv          #  <-- add this

load_dotenv()                           #  <-- and call it immediately

# ─── Environment ──────────────────────────────────────────────────────────
TOKEN                 = os.getenv("HUBSPOT_PRIVATE_TOKEN")
PORTAL_ID             = os.getenv("HUBSPOT_PORTAL_ID")
FREE_TEXT_PROPERTY    = os.getenv("FREE_TEXT_PROPERTY", "content")
AI_SENTIMENT_PROPERTY = os.getenv("AI_SENTIMENT_PROPERTY", "ai_sentiment")

if not TOKEN:
    raise RuntimeError("HUBSPOT_PRIVATE_TOKEN missing!")

HS_API  = "https://api.hubapi.com"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# ─── Load model once at start-up ──────────────────────────────────────────
sentiment_pipe = pipeline(
    task="text-classification",
    model="tabularisai/multilingual-sentiment-analysis",
    device=-1,               # CPU.  Use 0 if you have a CUDA GPU.
)

# ─── Helper functions ─────────────────────────────────────────────────────
def get_ticket(ticket_id: str) -> dict | None:
    """Fetch just the free-text property from HubSpot."""
    url     = f"{HS_API}/crm/v3/objects/tickets/{ticket_id}"
    params  = {"properties": FREE_TEXT_PROPERTY}
    resp    = requests.get(url, params=params, headers=HEADERS, timeout=10)
    return resp.json() if resp.ok else None


def patch_ticket(ticket_id: str, sentiment: str) -> None:
    """Write the sentiment back into the ticket."""
    url  = f"{HS_API}/crm/v3/objects/tickets/{ticket_id}"
    data = {"properties": {AI_SENTIMENT_PROPERTY: sentiment}}
    requests.patch(url, json=data, headers=HEADERS, timeout=10)


# ─── Flask app ────────────────────────────────────────────────────────────
app = Flask(__name__)


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # — HubSpot handshake —
    challenge = request.args.get("hub.challenge")
    if challenge:
        return challenge, 200

    events = request.json or []
    for ev in events:                       # HubSpot batches events
        if ev.get("object") != "ticket":
            continue

        ticket_id = ev.get("objectId") or ev.get("object_id")
        if not ticket_id:
            continue

        ticket = get_ticket(ticket_id)
        if not ticket:
            continue

        text = (ticket["properties"] or {}).get(FREE_TEXT_PROPERTY, "")
        if not text.strip():
            continue

        # ─ Run model ─
        label = sentiment_pipe(text[:512])[0]["label"]   # e.g. "Positive"
        patch_ticket(ticket_id, label)

    return jsonify(status="ok"), 200


if __name__ == "__main__":
    # Dev server – fine for local + ngrok
    app.run(host="0.0.0.0", port=5000, debug=True)
