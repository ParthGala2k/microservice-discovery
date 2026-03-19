"""
Service Registry
Maintains a list of available service instances.
Services register on startup, send heartbeats to stay alive,
and deregister on shutdown. Stale instances are auto-removed.
"""

from flask import Flask, request, jsonify
from datetime import datetime
import threading
import time

app = Flask(__name__)

# { service_name: [ { address, registered_at, last_heartbeat } ] }
registry = {}
registry_lock = threading.Lock()

HEARTBEAT_TIMEOUT = 30   # seconds before an instance is considered dead
CLEANUP_INTERVAL  = 10   # how often the cleanup thread runs


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'service' not in data or 'address' not in data:
        return jsonify({"status": "error", "message": "Missing service or address"}), 400

    service = data['service']
    address = data['address']

    with registry_lock:
        if service not in registry:
            registry[service] = []

        existing = next((s for s in registry[service] if s['address'] == address), None)
        if existing:
            existing['last_heartbeat'] = datetime.now()
            return jsonify({"status": "updated", "message": f"{service} @ {address} refreshed"})

        registry[service].append({
            'address':        address,
            'registered_at':  datetime.now(),
            'last_heartbeat': datetime.now(),
        })
        print(f"[REGISTRY] Registered  {service} @ {address}")
        return jsonify({"status": "registered", "message": f"{service} @ {address} registered"}), 201


@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    if not data or 'service' not in data or 'address' not in data:
        return jsonify({"status": "error", "message": "Missing service or address"}), 400

    service = data['service']
    address = data['address']

    with registry_lock:
        if service in registry:
            instance = next((s for s in registry[service] if s['address'] == address), None)
            if instance:
                instance['last_heartbeat'] = datetime.now()
                return jsonify({"status": "ok"})
        return jsonify({"status": "not_found"}), 404


@app.route('/deregister', methods=['POST'])
def deregister():
    data = request.json
    if not data or 'service' not in data or 'address' not in data:
        return jsonify({"status": "error", "message": "Missing service or address"}), 400

    service = data['service']
    address = data['address']

    with registry_lock:
        if service in registry:
            registry[service] = [s for s in registry[service] if s['address'] != address]
            if not registry[service]:
                del registry[service]
            print(f"[REGISTRY] Deregistered {service} @ {address}")
            return jsonify({"status": "deregistered"})
        return jsonify({"status": "not_found"}), 404


@app.route('/discover/<service>', methods=['GET'])
def discover(service):
    with registry_lock:
        if service not in registry:
            return jsonify({"service": service, "instances": [], "count": 0}), 404

        now = datetime.now()
        active = [
            {
                'address':        s['address'],
                'uptime_seconds': round((now - s['registered_at']).total_seconds(), 1),
            }
            for s in registry[service]
            if (now - s['last_heartbeat']).total_seconds() < HEARTBEAT_TIMEOUT
        ]
        return jsonify({"service": service, "instances": active, "count": len(active)})


@app.route('/services', methods=['GET'])
def list_services():
    with registry_lock:
        now = datetime.now()
        info = {
            svc: {
                'total_instances':  len(instances),
                'active_instances': sum(
                    1 for s in instances
                    if (now - s['last_heartbeat']).total_seconds() < HEARTBEAT_TIMEOUT
                ),
            }
            for svc, instances in registry.items()
        }
        return jsonify({"services": info, "total_services": len(info)})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


def cleanup_stale():
    while True:
        time.sleep(CLEANUP_INTERVAL)
        with registry_lock:
            now = datetime.now()
            to_remove = []
            for service, instances in registry.items():
                active = [s for s in instances
                          if (now - s['last_heartbeat']).total_seconds() < HEARTBEAT_TIMEOUT]
                if active:
                    registry[service] = active
                else:
                    to_remove.append(service)
            for service in to_remove:
                del registry[service]
                print(f"[REGISTRY] Removed stale service: {service}")


if __name__ == '__main__':
    threading.Thread(target=cleanup_stale, daemon=True).start()
    print("Service Registry running on http://localhost:5001")
    print(f"  Heartbeat timeout : {HEARTBEAT_TIMEOUT}s")
    print(f"  Cleanup interval  : {CLEANUP_INTERVAL}s\n")
    app.run(host='0.0.0.0', port=5001, debug=False)
