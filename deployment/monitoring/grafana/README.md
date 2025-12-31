# Consoul Grafana Dashboard

Pre-built Grafana dashboard for monitoring Consoul API metrics exposed via Prometheus.

## Prerequisites

- Grafana 10.x or 11.x
- Prometheus datasource configured and scraping Consoul metrics (port 9090)
- Consoul running with `CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED=true`

## Quick Start

### Option 1: Grafana UI Import

1. Open Grafana and navigate to **Dashboards** > **Import**
2. Click **Upload JSON file** and select `consoul-dashboard.json`
3. Select your Prometheus datasource when prompted
4. Click **Import**

### Option 2: Grafana API Import

```bash
# Set your Grafana URL and API key
GRAFANA_URL="http://localhost:3000"
GRAFANA_API_KEY="your-api-key"

# Import the dashboard (wrapping in required API format)
jq '{dashboard: ., overwrite: true, folderId: 0}' consoul-dashboard.json | \
curl -X POST \
  -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- \
  "$GRAFANA_URL/api/dashboards/db"
```

### Option 3: Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: consoul-grafana-dashboard
  labels:
    grafana_dashboard: "1"
data:
  consoul-dashboard.json: |
    # Paste contents of consoul-dashboard.json here
```

If using the Grafana Helm chart with sidecar:

```yaml
# values.yaml
sidecar:
  dashboards:
    enabled: true
    label: grafana_dashboard
```

## Dashboard Overview

### Template Variables

| Variable | Description | Usage |
|----------|-------------|-------|
| `$endpoint` | Filter by API endpoint | Multi-select dropdown |
| `$model` | Filter by LLM model | Multi-select dropdown |
| `$interval` | Aggregation interval | Auto (recommended) or manual selection (1m, 5m, 10m, 15m, 30m, 1h) |

### Panel Rows

#### 1. Overview
Quick stats showing current system health:
- **Request Rate**: Requests per second
- **Error Rate**: Percentage with color thresholds (green <1%, yellow 1-5%, red >=5%)
- **Active Sessions**: Current concurrent sessions
- **p95 Latency**: 95th percentile response time with thresholds (green <2s, yellow 2-5s, red >=5s)

#### 2. Request Metrics
Request distribution over time:
- Request rate by endpoint (stacked area)
- Request rate by HTTP status code (2xx green, 4xx yellow, 5xx red)
- Request rate by LLM model

#### 3. Latency
Response time analysis:
- p50/p95/p99 latency percentiles with threshold lines
- Latency heatmap showing distribution across histogram buckets
- p95 latency breakdown by endpoint

#### 4. Token Usage
LLM token consumption:
- Input vs output token rate (blue/purple)
- Token usage by model
- Cumulative token count

#### 5. Tool Executions
Tool/function call metrics:
- Execution rate by tool name
- Overall success rate gauge (red <90%, yellow 90-95%, green >=95%)
- Summary table with success/failure counts per tool

#### 6. Errors
Error analysis:
- Error rate by type (validation, internal, timeout, etc.)
- Error rate by endpoint
- Recent errors table with counts

#### 7. Redis Health
Cache layer status:
- Redis status indicator (Healthy/Degraded)
- Redis recovery events over time

## Alert Thresholds

The dashboard uses color thresholds matching the operations runbook:

| Metric | Warning | Critical |
|--------|---------|----------|
| Error Rate | > 1% | > 5% |
| p95 Latency | > 2s | > 5s |
| Active Sessions | > 1000 | > 5000 |
| Tool Success Rate | < 95% | < 90% |

## Datasource Configuration

The dashboard uses a portable datasource reference (`${DS_PROMETHEUS}`). On import, Grafana will prompt you to select a Prometheus datasource.

For programmatic deployment, ensure your Prometheus datasource UID matches or update the dashboard JSON accordingly.

## Metrics Reference

| Metric | Type | Labels |
|--------|------|--------|
| `consoul_request_total` | Counter | endpoint, method, status, model |
| `consoul_request_latency_seconds` | Histogram | endpoint, method |
| `consoul_token_usage_total` | Counter | direction, model, session_id |
| `consoul_active_sessions` | Gauge | - |
| `consoul_tool_executions_total` | Counter | tool_name, status |
| `consoul_errors_total` | Counter | endpoint, error_type |
| `consoul_redis_degraded` | Gauge | - |
| `consoul_redis_recovered_total` | Counter | - |

## Prometheus Scrape Config

Example scrape configuration for Prometheus:

```yaml
scrape_configs:
  - job_name: 'consoul'
    static_configs:
      - targets: ['consoul:9090']
    scrape_interval: 15s
```

## Customization

To modify the dashboard:

1. Import into Grafana
2. Make changes via the Grafana UI
3. Export as JSON via **Dashboard settings** > **JSON Model** > **Save to file**
4. Replace `consoul-dashboard.json` with the exported file

## Troubleshooting

**No data in panels**
- Verify Prometheus is scraping Consoul metrics: `curl http://consoul:9090/metrics`
- Check Prometheus targets: Prometheus UI > Status > Targets
- Ensure `CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED=true`

**Template variables empty**
- Verify metrics exist with the expected labels
- Check Prometheus datasource connectivity in Grafana

**Import errors**
- Validate JSON: `jq empty consoul-dashboard.json`
- Ensure Grafana version is 10.x or later

## Related Documentation

- [Operations Runbook](../../../docs/operations/runbook.md) - PromQL queries and alert rules
- [Metrics Implementation](../../../src/consoul/server/observability/metrics.py) - Metric definitions
