# ReliabilityStack — P1: Azure Monitor Integration

## Overview

A production-style observability pipeline built on Azure. A Flask web service with three
health-state endpoints is deployed to Azure App Service, instrumented with Azure Monitor,
and wired to PagerDuty via webhook. When the app returns HTTP 5xx errors above a defined
threshold, Azure Monitor fires an alert that creates a PagerDuty incident automatically —
and resolves it when the error rate drops back to zero.

This project demonstrates the full alerting lifecycle: signal generation → metric collection
→ threshold evaluation → incident creation → auto-resolution.

---

## Stack

| Layer | Technology |
|---|---|
| Application | Python / Flask |
| Hosting | Azure App Service (Linux, B1) |
| Monitoring | Azure Monitor (Http Server Errors metric) |
| Alerting | Azure Monitor Alert Rule + Action Group (Webhook) |
| Incident Management | PagerDuty |

---

## Application Endpoints

The Flask app exposes three endpoints, each simulating a distinct health state:

| Endpoint | HTTP Status | Purpose |
|---|---|---|
| `GET /` | 200 | Index — lists all endpoints and usage notes |
| `GET /health/healthy` | 200 | Baseline availability check |
| `GET /health/unhealthy` | 503 | Simulates a failing dependency (triggers alerts) |
| `GET /health/slow?delay_seconds=N` | 200 | Simulates latency degradation |

The `/health/slow` endpoint accepts an optional `delay_seconds` query parameter (default: 5).
Delay is clamped between 0 and `MAX_SLOW_DELAY_SEC` (default: 120) to prevent runaway hangs.

---

## Alerting Pipeline

```
Flask App (Azure App Service)
        │
        │  HTTP 503 responses
        ▼
Azure Monitor — Http Server Errors metric
        │
        │  Count > 1 within 5-minute window
        ▼
Alert Rule — http-5xx-alert (Sev 2 - Warning)
        │
        │  Threshold breached
        ▼
Action Group — pagerduty-webhook
        │
        │  POST to PagerDuty Events API
        ▼
PagerDuty Incident (auto-resolves when error rate clears)
```

### Alert Rule Configuration

| Setting | Value |
|---|---|
| Signal | Http Server Errors |
| Aggregation | Count |
| Operator | Greater than |
| Threshold | 1 |
| Lookback period | 5 minutes |
| Evaluation frequency | Every 1 minute |
| Auto-resolve | Enabled |
| Severity | Sev 2 — Warning |

---

## Infrastructure

| Resource | Name |
|---|---|
| Resource Group | `reliability-stack-rg` |
| App Service Plan | `reliability-stack-plan` (Linux, B1) |
| Web App | `reliabilitystack-p1` |
| Log Analytics Workspace | `reliability-stack-logs` |
| Alert Rule | `http-5xx-alert` |
| Action Group | `pagerduty-webhook` |

**Live URL:** `https://reliabilitystack-p1.azurewebsites.net`

---

## How to Trigger an Alert

Hit the unhealthy endpoint repeatedly to breach the threshold:

```bash
for i in {1..15}; do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" \
    https://reliabilitystack-p1.azurewebsites.net/health/unhealthy
done
```

Expected output: 15 lines each returning `503`. Within 5 minutes, Azure Monitor will
evaluate the rule, the action group will fire the webhook, and a PagerDuty incident
will be created. Once requests stop, the incident auto-resolves.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Port the Flask app listens on |
| `MAX_SLOW_DELAY_SEC` | `120` | Upper bound for `/health/slow` delay |
| `FLASK_DEBUG` | `0` | Set to `1` to enable Flask debug mode |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Enables pip install on Azure deploy |

---

## Local Development

```bash
# Clone and navigate to project
cd reliabilitystack-p1

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Test endpoints
curl http://localhost:5000/health/healthy
curl http://localhost:5000/health/unhealthy
curl "http://localhost:5000/health/slow?delay_seconds=3"
```

> **Local vs. production server:** `python app.py` uses Flask's built-in dev server and is fine for local testing. In production, Azure App Service requires an explicit startup command to run the app through Gunicorn. The startup command `gunicorn --bind=0.0.0.0:8000 app:app` is set via the Azure CLI, which is why `gunicorn` is listed in `requirements.txt`.

---

## Key Concepts Demonstrated

- **Azure App Service** — managed Linux hosting for Python web apps
- **Azure Monitor metrics** — platform-level HTTP error tracking without code instrumentation
- **Alert rules** — static threshold evaluation on time-series metrics
- **Action groups** — reusable notification targets (webhook, email, SMS, etc.)
- **PagerDuty Events API v2** — webhook-based incident creation and auto-resolution
- **Diagnostic settings** — routing App Service logs and metrics to Log Analytics
- **Alerting lifecycle** — fire → acknowledge → resolve, end to end

