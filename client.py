"""
Discovery Client
Demonstrates service discovery and calling a random service instance.

Flow:
  1. Ask the registry for all active instances of quote-service
  2. Pick one at random
  3. Call GET /quote on that instance
  4. Print the result (including which instance served it)
  5. Repeat N times

Usage:
  python client.py          # makes 6 calls (default)
  python client.py 10       # makes 10 calls
"""

import random
import sys
import time

import requests

REGISTRY_URL = "http://localhost:5001"
SERVICE_NAME = "quote-service"


def discover_instances():
    """Ask the registry for all active instances of the service."""
    try:
        r = requests.get(f"{REGISTRY_URL}/discover/{SERVICE_NAME}", timeout=5)
        if r.status_code == 200:
            return r.json().get('instances', [])
        print(f"Discovery failed: {r.status_code}")
        return []
    except requests.exceptions.ConnectionError:
        print("Cannot reach registry. Is registry.py running?")
        return []


def call_service(address):
    """Call the /quote endpoint on a specific instance."""
    r = requests.get(f"{address}/quote", timeout=5)
    return r.json()


def main():
    total_calls = int(sys.argv[1]) if len(sys.argv) > 1 else 6

    print("=" * 55)
    print("  Service Discovery Client")
    print("=" * 55)

    # Show what's currently registered
    instances = discover_instances()
    if not instances:
        print("No instances of quote-service found. Start quote_service.py first.")
        sys.exit(1)

    print(f"\nFound {len(instances)} instance(s) of '{SERVICE_NAME}':")
    for inst in instances:
        print(f"  - {inst['address']}  (uptime: {inst['uptime_seconds']}s)")

    print(f"\nMaking {total_calls} calls (random instance each time)...\n")

    for i in range(1, total_calls + 1):
        # Re-discover each time — in production a service could come up/go down
        instances = discover_instances()
        if not instances:
            print("All instances disappeared.")
            break

        # Pick a random instance
        chosen = random.choice(instances)
        address = chosen['address']

        result = call_service(address)

        print(f"Call {i}/{total_calls}")
        print(f"  Instance  : {result['served_by']}")
        print(f"  Quote     : {result['quote']}")
        print()

        time.sleep(0.5)

    print("Done.")


if __name__ == '__main__':
    main()
