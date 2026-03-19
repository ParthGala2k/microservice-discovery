"""
Quote Service
A microservice that returns random programming quotes.

Each instance:
  - Registers itself with the Service Registry on startup
  - Exposes GET /quote  →  returns a random quote + which instance served it
  - Sends a heartbeat to the registry every 10 seconds
  - Deregisters itself cleanly on Ctrl+C

Usage:
  python quote_service.py 8001
  python quote_service.py 8002
"""

import argparse
import random
import signal
import sys
import threading
import time

import requests
from flask import Flask, jsonify

# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------
QUOTES = [
    "Any fool can write code that a computer can understand. Good programmers write code that humans can understand. — Martin Fowler",
    "First, solve the problem. Then, write the code. — John Johnson",
    "Simplicity is the soul of efficiency. — Austin Freeman",
    "Make it work, make it right, make it fast. — Kent Beck",
    "Code is like humor. When you have to explain it, it's bad. — Cory House",
    "Fix the cause, not the symptom. — Steve Maguire",
    "Premature optimization is the root of all evil. — Donald Knuth",
    "The best code is no code at all. — Jeff Atwood",
    "Talk is cheap. Show me the code. — Linus Torvalds",
    "Always code as if the person who ends up maintaining your code is a violent psychopath who knows where you live. — John Woods",
]

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Set by argparse at startup
SERVICE_NAME    = "quote-service"
service_address = None
registry_url    = None
stop_event      = threading.Event()


@app.route('/quote', methods=['GET'])
def get_quote():
    return jsonify({
        "quote":     random.choice(QUOTES),
        "served_by": service_address,   # lets the client see which instance replied
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "instance": service_address})


# ---------------------------------------------------------------------------
# Registry interaction
# ---------------------------------------------------------------------------
def register():
    try:
        r = requests.post(
            f"{registry_url}/register",
            json={"service": SERVICE_NAME, "address": service_address},
            timeout=5,
        )
        if r.status_code in (200, 201):
            print(f"[{service_address}] Registered with registry")
            return True
        print(f"[{service_address}] Registration failed: {r.text}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"[{service_address}] Cannot reach registry at {registry_url}")
        print("  Make sure registry.py is running first.")
        return False


def deregister():
    try:
        requests.post(
            f"{registry_url}/deregister",
            json={"service": SERVICE_NAME, "address": service_address},
            timeout=5,
        )
        print(f"[{service_address}] Deregistered from registry")
    except Exception:
        pass   # best-effort on shutdown


def heartbeat_loop():
    while not stop_event.is_set():
        try:
            requests.post(
                f"{registry_url}/heartbeat",
                json={"service": SERVICE_NAME, "address": service_address},
                timeout=5,
            )
            print(f"[{service_address}] Heartbeat sent")
        except Exception as e:
            print(f"[{service_address}] Heartbeat error: {e}")
        stop_event.wait(10)   # send every 10 seconds


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Quote microservice")
    parser.add_argument('port', type=int, help='Port this instance listens on (e.g. 8001)')
    parser.add_argument('--registry', default='http://localhost:5001', help='Registry URL')
    args = parser.parse_args()

    service_address = f"http://localhost:{args.port}"
    registry_url    = args.registry

    # Register before starting the server
    if not register():
        sys.exit(1)

    # Start heartbeat in background
    threading.Thread(target=heartbeat_loop, daemon=True).start()

    # Graceful shutdown on Ctrl+C
    def shutdown(sig, frame):
        print(f"\n[{service_address}] Shutting down...")
        stop_event.set()
        deregister()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    print(f"[{service_address}] Quote service running — GET /quote")
    app.run(host='0.0.0.0', port=args.port, debug=False)
