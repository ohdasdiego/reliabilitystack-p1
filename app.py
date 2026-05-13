"""
Flask demo service with three health-style endpoints for Azure Monitor scenarios:

- /health/healthy   — fast 200 (availability / success-rate baselines)
- /health/unhealthy — 5xx (failed requests, failed URL ping tests)
- /health/slow      — delayed 200 (request duration, timeout if delay exceeds test timeout)
"""

import os
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

# Cap slow endpoint so accidental huge values do not hang the process forever
_MAX_SLOW_DELAY_SEC = float(os.environ.get("MAX_SLOW_DELAY_SEC", "120"))


@app.get("/")
def index():
    return jsonify(
        service="reliabilitystack-p1",
        endpoints={
            "healthy": "/health/healthy",
            "unhealthy": "/health/unhealthy",
            "slow": "/health/slow?delay_seconds=5",
        },
        notes={
            "azure_monitor": (
                "Point Standard tests or Application Insights availability tests at these URLs; "
                "use metric alerts on HttpStatusCode / failed requests for unhealthy; "
                "use server response time or test duration for slow."
            )
        },
    )


@app.get("/health/healthy")
def health_healthy():
    return jsonify(status="healthy", http_status=200), 200


@app.get("/health/unhealthy")
def health_unhealthy():
    # 503 is typical for “dependency down” / circuit-open style failures
    return (
        jsonify(
            status="unhealthy",
            http_status=503,
            reason="simulated_failure_for_monitoring",
        ),
        503,
    )


@app.get("/health/slow")
def health_slow():
    try:
        delay = float(request.args.get("delay_seconds", "5"))
    except ValueError:
        return jsonify(error="delay_seconds must be a number"), 400

    delay = max(0.0, min(delay, _MAX_SLOW_DELAY_SEC))
    time.sleep(delay)
    return (
        jsonify(
            status="slow_but_success",
            http_status=200,
            delay_seconds=delay,
        ),
        200,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
