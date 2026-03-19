# Microservice Discovery

## Demo

<video src="video1733810299.mp4" controls width="800"></video>

A working demonstration of **Service Discovery** in a distributed system.
Two instances of a microservice register with a central registry. A client discovers them dynamically and calls a random instance on every request — without hardcoding any addresses.

---

## What This Project Demonstrates

| Concept | Where It Happens |
|---|---|
| Service Registration | `quote_service.py` registers itself with the registry on startup |
| Heartbeating | `quote_service.py` sends a ping to the registry every 10 seconds |
| Stale Instance Cleanup | `registry.py` removes instances that stop heartbeating |
| Graceful Deregistration | `quote_service.py` deregisters itself on Ctrl+C |
| Service Discovery | `client.py` asks the registry for all active instances |
| Random Load Distribution | `client.py` picks a random instance on every call |

---

## Architecture

```
                        ┌──────────────────────┐
                        │    Service Registry   │
                        │    (registry.py)      │
                        │    localhost:5001     │
                        └──────────────────────┘
                          ▲         ▲        ▲
               register / │         │        │ discover
               heartbeat  │         │        │
                          │         │        │
          ┌───────────────┘  ┌──────┘        └────────────────┐
          │                  │                                 │
┌─────────────────┐  ┌─────────────────┐            ┌─────────────────┐
│  Quote Service  │  │  Quote Service  │            │     Client      │
│   Instance 1    │  │   Instance 2    │            │   (client.py)   │
│  localhost:8001 │  │  localhost:8002 │            │                 │
│                 │  │                 │            │ 1. discover()   │
│  GET /quote     │  │  GET /quote     │◀───call────│ 2. random pick  │
└─────────────────┘  └─────────────────┘            │ 3. call /quote  │
                                                     └─────────────────┘
```

**Flow:**
1. Both service instances start and register their address with the registry
2. Both send a heartbeat every 10 seconds so the registry knows they are alive
3. The client calls `/discover/quote-service` on the registry
4. The registry returns the list of active instances
5. The client picks one at random and calls its `/quote` endpoint
6. Steps 3–5 repeat for every call — if an instance goes down, it disappears from the list automatically

---

## Project Structure

```
MicroserviceDiscovery/
├── registry.py        # The service registry (stores and serves instance locations)
├── quote_service.py   # The microservice (returns quotes, registers itself)
├── client.py          # The discovery client (finds and calls a random instance)
└── requirements.txt
```

---

## Setup

**Prerequisites:** Python 3.8+

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Demo

You need **4 terminals**, all with the virtual environment activated.

### Terminal 1 — Start the Registry

```bash
python registry.py
```

Expected output:
```
Service Registry running on http://localhost:5001
  Heartbeat timeout : 30s
  Cleanup interval  : 10s
```

### Terminal 2 — Start Instance 1

```bash
python quote_service.py 8001
```

Expected output:
```
[http://localhost:8001] Registered with registry
[http://localhost:8001] Quote service running — GET /quote
[http://localhost:8001] Heartbeat sent        ← repeats every 10s
```

### Terminal 3 — Start Instance 2

```bash
python quote_service.py 8002
```

Expected output:
```
[http://localhost:8002] Registered with registry
[http://localhost:8002] Quote service running — GET /quote
[http://localhost:8002] Heartbeat sent
```

### Terminal 4 — Run the Client

```bash
python client.py 10
```

Expected output:
```
=======================================================
  Service Discovery Client
=======================================================

Found 2 instance(s) of 'quote-service':
  - http://localhost:8001  (uptime: 12.3s)
  - http://localhost:8002  (uptime: 8.1s)

Making 10 calls (random instance each time)...

Call 1/10
  Instance  : http://localhost:8002
  Quote     : Talk is cheap. Show me the code. — Linus Torvalds

Call 2/10
  Instance  : http://localhost:8001
  Quote     : Make it work, make it right, make it fast. — Kent Beck

Call 3/10
  Instance  : http://localhost:8002
  Quote     : Premature optimization is the root of all evil. — Donald Knuth
...
```

The `Instance` line changing between `8001` and `8002` confirms that the client is discovering both instances and distributing calls randomly across them.

---

## Observing Key Behaviors

### What happens when an instance goes down?

Stop Instance 1 with Ctrl+C in Terminal 2. You will see:
```
[http://localhost:8001] Deregistered from registry   ← graceful deregistration
```
Run the client again — it will only find and call Instance 2.

### What happens if an instance crashes (no graceful shutdown)?

Kill Terminal 2 without Ctrl+C (force close). The registry does not know immediately.
After **30 seconds** (heartbeat timeout), the registry's cleanup thread removes it automatically:
```
[REGISTRY] Removed stale service: quote-service   ← printed by registry.py
```
The next client call will only see Instance 2 in the discovered list.

### Verifying registry state at any time

```bash
# See all registered services
curl http://localhost:5001/services

# See all active instances of quote-service
curl http://localhost:5001/discover/quote-service
```

---

## How Service Discovery Solves a Real Problem

Without a registry, you would hardcode service addresses:
```python
# Fragile — breaks if the service moves or scales
response = requests.get("http://localhost:8001/quote")
```

With discovery, the client never needs to know where services live:
```python
# Resilient — works regardless of how many instances exist or where they run
instances = discover("quote-service")
chosen    = random.choice(instances)
response  = requests.get(f"{chosen['address']}/quote")
```

This is the foundation of how systems like **Netflix Eureka**, **HashiCorp Consul**, and **Kubernetes DNS** work at scale.
