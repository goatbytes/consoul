# Consoul Load Testing Guide

Comprehensive guide for validating Consoul performance before production deployment, including test scripts, baseline benchmarks, and monitoring integration.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Load Testing Tools](#load-testing-tools)
- [Test Scenarios](#test-scenarios)
- [HTTP Load Testing](#http-load-testing)
- [WebSocket Load Testing](#websocket-load-testing)
- [Baseline Benchmarks](#baseline-benchmarks)
- [Monitoring During Tests](#monitoring-during-tests)
- [Running Tests](#running-tests)
- [Interpreting Results](#interpreting-results)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)
- [Related Documentation](#related-documentation)

---

## Overview

### Purpose

Load testing Consoul before production deployment helps you:

1. **Establish Baselines** - Measure expected latency and throughput under normal load
2. **Identify Bottlenecks** - Find connection pool limits, memory leaks, or configuration issues
3. **Validate Scaling** - Confirm horizontal scaling behavior with Redis
4. **Compare Configurations** - Benchmark different tuning parameters

### Architecture Under Test

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Load Testing Architecture                            │
│                                                                             │
│  Load Generator                                                             │
│  (k6/Locust)                                                                │
│      │                                                                      │
│      ├──── HTTP POST /chat ──────────────────────┐                          │
│      │                                           ▼                          │
│      │                                    ┌──────────────┐                  │
│      │                                    │   Consoul    │                  │
│      │                                    │   Server     │                  │
│      │                                    └──────┬───────┘                  │
│      │                                           │                          │
│      ├──── WebSocket /ws/chat/{session} ─────────┤                          │
│      │                                           │                          │
│      │                           ┌───────────────┼───────────────┐          │
│      │                           ▼               ▼               ▼          │
│      │                    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│      │                    │  Redis   │    │Prometheus│    │   LLM    │      │
│      │                    │ (state)  │    │ (metrics)│    │ Provider │      │
│      │                    └──────────┘    └──────────┘    └──────────┘      │
│      │                                                                      │
│      └──── Scrape :9090/metrics ─────────────────────────────────────────   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Metrics to Measure

| Metric | Target | Description |
|--------|--------|-------------|
| Request Rate | Varies by deployment | Requests processed per second |
| P50 Latency | < 200ms | Median response time (excluding LLM) |
| P95 Latency | < 1s | 95th percentile response time |
| P99 Latency | < 2s | 99th percentile response time |
| Error Rate | < 1% | Percentage of failed requests |
| Concurrent Connections | 100+ | Maximum simultaneous connections |

---

## Prerequisites

### Required Components

1. **Consoul Server** - Running instance with endpoints accessible
2. **Redis** - Required for distributed session storage and rate limiting
3. **Prometheus** - For metrics collection during tests (port 9090)

### Environment Setup

```bash
# Start Consoul with Prometheus metrics enabled
CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED=true \
CONSOUL_OBSERVABILITY_METRICS_PORT=9090 \
CONSOUL_SESSION_REDIS_URL=redis://localhost:6379/0 \
CONSOUL_RATE_LIMIT_REDIS_URL=redis://localhost:6379/1 \
python -m consoul.server

# Verify endpoints
curl http://localhost:8000/health    # Should return 200
curl http://localhost:8000/ready     # Should return 200 if Redis healthy
curl http://localhost:9090/metrics   # Prometheus metrics
```

### Test Account Setup

For authenticated testing, create test API keys:

```bash
# Set test API key in environment
export CONSOUL_API_KEY="test-load-key-12345"

# Or configure tier-based keys for rate limit testing
export CONSOUL_TIER_KEYS='{
  "basic-key": "basic",
  "premium-key": "premium"
}'
```

---

## Load Testing Tools

### k6 (Recommended)

JavaScript-based load testing tool with excellent HTTP and WebSocket support.

**Installation:**

```bash
# macOS
brew install k6

# Linux (Debian/Ubuntu)
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
    --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
    sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6

# Docker
docker pull grafana/k6
```

**Quick Test:**

```bash
# Basic HTTP test
k6 run --vus 10 --duration 30s script.js

# With environment variables
k6 run -e API_KEY=your-key -e BASE_URL=http://localhost:8000 script.js
```

### Locust (Python Alternative)

Python-based load testing with a web UI for real-time monitoring.

**Installation:**

```bash
pip install locust
```

**Quick Test:**

```bash
# Start with web UI
locust -f locustfile.py --host=http://localhost:8000

# Headless mode
locust -f locustfile.py --host=http://localhost:8000 \
    --headless -u 50 -r 10 --run-time 5m
```

### hey (Simple HTTP)

Lightweight tool for quick baseline checks.

**Installation:**

```bash
# macOS
brew install hey

# Go install
go install github.com/rakyll/hey@latest
```

**Quick Test:**

```bash
# 1000 requests with 50 concurrent connections
hey -n 1000 -c 50 -m POST \
    -H "Content-Type: application/json" \
    -d '{"session_id":"test","message":"hello"}' \
    http://localhost:8000/chat
```

---

## Test Scenarios

### 1. Baseline Test

**Purpose:** Measure performance floor with minimal load.

**Configuration:**
- Virtual Users (VUs): 1-5
- Duration: 1-2 minutes
- Ramp-up: None

**What to Measure:**
- Minimum achievable latency
- Single-user throughput
- Memory baseline

```javascript
// k6 baseline test
export const options = {
  vus: 1,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<500'],
  },
};
```

### 2. Soak Test

**Purpose:** Detect memory leaks and resource exhaustion over time.

**Configuration:**
- Virtual Users: 50 (sustained)
- Duration: 30+ minutes (ideally 2-4 hours)
- Ramp-up: 2 minutes

**What to Measure:**
- Memory growth over time
- Session accumulation
- Connection pool exhaustion
- Garbage collection pauses

```javascript
// k6 soak test
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up
    { duration: '30m', target: 50 },  // Sustained load
    { duration: '2m', target: 0 },    // Ramp down
  ],
};
```

### 3. Spike Test

**Purpose:** Validate behavior under sudden traffic surges.

**Configuration:**
- Virtual Users: 10 → 100 → 10
- Duration: 10 minutes
- Spike duration: 2-3 minutes

**What to Measure:**
- Error rate during spike
- Recovery time after spike
- Rate limiter behavior
- Circuit breaker activation

```javascript
// k6 spike test
export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Normal load
    { duration: '30s', target: 100 }, // Spike up
    { duration: '2m', target: 100 },  // Sustained spike
    { duration: '30s', target: 10 },  // Spike down
    { duration: '2m', target: 10 },   // Recovery
  ],
};
```

### 4. Stress Test

**Purpose:** Find the breaking point and maximum capacity.

**Configuration:**
- Virtual Users: Progressive increase until failure
- Duration: Until errors exceed threshold
- Step: Increase 20 VUs every 2 minutes

**What to Measure:**
- Maximum sustainable throughput
- Error threshold (when errors > 5%)
- Resource limits hit first (CPU, memory, connections)
- Recovery behavior after overload

```javascript
// k6 stress test
export const options = {
  stages: [
    { duration: '2m', target: 20 },
    { duration: '2m', target: 40 },
    { duration: '2m', target: 60 },
    { duration: '2m', target: 80 },
    { duration: '2m', target: 100 },
    { duration: '2m', target: 120 },
    { duration: '5m', target: 0 },    // Recovery
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],   // Stop if >5% errors
  },
};
```

---

## HTTP Load Testing

### k6 Script for `/chat` Endpoint

```javascript
// load_test_chat.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const chatLatency = new Trend('chat_latency');

// Configuration from environment
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || '';

export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 50 },   // Sustained load at 50 users
    { duration: '1m', target: 100 },  // Spike to 100 users
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2s
    errors: ['rate<0.01'],             // Error rate under 1%
    chat_latency: ['p(99)<3000'],      // 99% of chat requests under 3s
  },
};

export default function () {
  // Generate unique session ID per VU and iteration
  const sessionId = `load-test-${__VU}-${__ITER}`;

  const payload = JSON.stringify({
    session_id: sessionId,
    message: 'Hello, this is a load test message. Please respond briefly.',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: '30s',
  };

  // Add API key if provided
  if (API_KEY) {
    params.headers['X-API-Key'] = API_KEY;
  }

  const startTime = Date.now();
  const res = http.post(`${BASE_URL}/chat`, payload, params);
  const duration = Date.now() - startTime;

  // Record custom latency metric
  chatLatency.add(duration);

  // Validate response
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response has content': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.response !== undefined;
      } catch {
        return false;
      }
    },
    'no error in response': (r) => {
      try {
        const body = JSON.parse(r.body);
        return !body.error;
      } catch {
        return false;
      }
    },
  });

  // Track error rate
  errorRate.add(!success);

  // Log errors for debugging
  if (!success) {
    console.log(`Error: VU=${__VU}, Status=${res.status}, Body=${res.body}`);
  }

  // Simulate user think time
  sleep(1);
}

// Optional: Setup and teardown
export function setup() {
  // Verify server is healthy
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'server is healthy': (r) => r.status === 200,
  });

  console.log(`Starting load test against ${BASE_URL}`);
}

export function teardown(data) {
  console.log('Load test complete');
}
```

### Running HTTP Load Test

```bash
# Basic run
k6 run load_test_chat.js

# With custom configuration
k6 run -e BASE_URL=http://localhost:8000 -e API_KEY=your-key load_test_chat.js

# Output results to JSON
k6 run --out json=results.json load_test_chat.js

# Output to InfluxDB for Grafana dashboards
k6 run --out influxdb=http://localhost:8086/k6 load_test_chat.js
```

### Locust Script for `/chat` Endpoint

```python
# locustfile_chat.py
from locust import HttpUser, task, between
import json
import os

class ConsoulUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Initialize user session."""
        self.session_id = f"load-test-{self.environment.runner.user_count}"
        self.api_key = os.environ.get('API_KEY', '')

    @task
    def chat(self):
        """Send a chat message."""
        headers = {'Content-Type': 'application/json'}

        if self.api_key:
            headers['X-API-Key'] = self.api_key

        payload = {
            'session_id': self.session_id,
            'message': 'Hello, this is a load test message.',
        }

        with self.client.post(
            '/chat',
            json=payload,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'response' in data:
                        response.success()
                    else:
                        response.failure('Missing response field')
                except json.JSONDecodeError:
                    response.failure('Invalid JSON response')
            elif response.status_code == 429:
                response.failure('Rate limited')
            else:
                response.failure(f'Status {response.status_code}')
```

---

## WebSocket Load Testing

### k6 Script for WebSocket Endpoint

```javascript
// load_test_websocket.js
import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';

// Custom metrics
const wsErrors = new Rate('ws_errors');
const wsMessages = new Counter('ws_messages_received');
const wsLatency = new Trend('ws_message_latency');

const BASE_URL = __ENV.BASE_URL || 'ws://localhost:8000';
const API_KEY = __ENV.API_KEY || '';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '2m', target: 30 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    ws_errors: ['rate<0.05'],
    ws_message_latency: ['p(95)<5000'],
  },
};

export default function () {
  const sessionId = `ws-load-test-${__VU}-${__ITER}`;
  let url = `${BASE_URL}/ws/chat/${sessionId}`;

  // Add API key as query parameter if provided
  if (API_KEY) {
    url += `?api_key=${API_KEY}`;
  }

  const messageStartTime = Date.now();
  let receivedDone = false;
  let tokenCount = 0;

  const res = ws.connect(url, {}, function (socket) {
    socket.on('open', function () {
      console.log(`VU ${__VU}: WebSocket connected`);

      // Send chat message
      socket.send(JSON.stringify({
        type: 'message',
        content: 'Hello from WebSocket load test. Please respond briefly.',
      }));
    });

    socket.on('message', function (data) {
      wsMessages.add(1);

      try {
        const msg = JSON.parse(data);

        if (msg.type === 'token') {
          tokenCount++;
        } else if (msg.type === 'done') {
          const latency = Date.now() - messageStartTime;
          wsLatency.add(latency);
          receivedDone = true;
          console.log(`VU ${__VU}: Received done after ${tokenCount} tokens in ${latency}ms`);
          socket.close();
        } else if (msg.type === 'error') {
          console.log(`VU ${__VU}: Error: ${msg.data?.message || 'Unknown error'}`);
          wsErrors.add(1);
          socket.close();
        }
      } catch (e) {
        console.log(`VU ${__VU}: Failed to parse message: ${data}`);
      }
    });

    socket.on('error', function (e) {
      console.log(`VU ${__VU}: WebSocket error: ${e.error()}`);
      wsErrors.add(1);
    });

    socket.on('close', function () {
      console.log(`VU ${__VU}: WebSocket closed`);
    });

    // Timeout after 30 seconds
    socket.setTimeout(function () {
      if (!receivedDone) {
        console.log(`VU ${__VU}: Timeout waiting for response`);
        wsErrors.add(1);
        socket.close();
      }
    }, 30000);
  });

  check(res, {
    'WebSocket connection successful': (r) => r && r.status === 101,
  });

  // Wait before next iteration
  sleep(2);
}
```

### Running WebSocket Load Test

```bash
# Basic run
k6 run load_test_websocket.js

# With configuration
k6 run -e BASE_URL=ws://localhost:8000 -e API_KEY=your-key load_test_websocket.js
```

---

## Baseline Benchmarks

### Expected Performance by Deployment Size

These benchmarks assume:
- LLM provider latency not included (mocked or cached responses)
- Redis available and healthy
- Default configuration settings

| Deployment | Requests/sec | P50 Latency | P95 Latency | P99 Latency | Max VUs |
|------------|--------------|-------------|-------------|-------------|---------|
| Single Instance (2 CPU, 4GB) | 50-100 | <50ms | <200ms | <500ms | 100 |
| Single Instance (4 CPU, 8GB) | 100-200 | <50ms | <150ms | <300ms | 200 |
| 3 Instances + Redis | 200-400 | <50ms | <200ms | <500ms | 400 |
| 5 Instances + Redis | 400-700 | <50ms | <200ms | <500ms | 700 |

### With LLM Provider Latency

When testing with real LLM providers, expect significantly higher latencies:

| Provider | Typical Latency | Impact on P95 |
|----------|-----------------|---------------|
| OpenAI GPT-4 | 2-10s | +3-10s |
| OpenAI GPT-3.5 | 0.5-3s | +1-3s |
| Anthropic Claude | 1-8s | +2-8s |
| Local Ollama | 0.5-5s | +1-5s (depends on model) |

### Resource Utilization Targets

| Resource | Normal | Warning | Critical |
|----------|--------|---------|----------|
| CPU | <70% | 70-85% | >85% |
| Memory | <75% | 75-90% | >90% |
| Redis Connections | <50% pool | 50-80% | >80% |
| HTTP Pool | <50% pool | 50-80% | >80% |

---

## Monitoring During Tests

### Prometheus Metrics

Consoul exposes metrics on port 9090. Use these queries to monitor during load tests.

#### Request Rate

```promql
# Requests per second by endpoint
rate(consoul_request_total[1m])

# Requests per second by status code
sum by (status) (rate(consoul_request_total[1m]))

# Total request rate
sum(rate(consoul_request_total[1m]))
```

#### Latency Percentiles

```promql
# P50 latency
histogram_quantile(0.50, sum by (le) (rate(consoul_request_latency_seconds_bucket[5m])))

# P95 latency
histogram_quantile(0.95, sum by (le) (rate(consoul_request_latency_seconds_bucket[5m])))

# P99 latency
histogram_quantile(0.99, sum by (le) (rate(consoul_request_latency_seconds_bucket[5m])))

# Average latency
sum(rate(consoul_request_latency_seconds_sum[5m])) / sum(rate(consoul_request_latency_seconds_count[5m]))
```

#### Error Rate

```promql
# Error rate percentage
100 * sum(rate(consoul_errors_total[1m])) / sum(rate(consoul_request_total[1m]))

# Errors by type
sum by (error_type) (rate(consoul_errors_total[1m]))
```

#### Active Sessions

```promql
# Current active sessions
consoul_active_sessions

# Session creation rate
rate(consoul_active_sessions[1m])
```

#### Circuit Breaker Status

```promql
# Circuit breaker state (0=closed, 1=half-open, 2=open)
consoul_circuit_breaker_state

# Circuit breaker trips
rate(consoul_circuit_breaker_trips_total[5m])

# Rejected requests due to open circuit
rate(consoul_circuit_breaker_rejections_total[5m])
```

#### Token Usage

```promql
# Input tokens per second
sum by (model) (rate(consoul_token_usage_total{direction="input"}[1m]))

# Output tokens per second
sum by (model) (rate(consoul_token_usage_total{direction="output"}[1m]))
```

#### Redis Health

```promql
# Redis degraded state (1 = degraded, 0 = healthy)
consoul_redis_degraded

# Redis recovery events
rate(consoul_redis_recovered_total[5m])
```

### Grafana Dashboard Queries

For a comprehensive load testing dashboard, combine these panels:

```yaml
# Panel 1: Request Rate
- title: "Request Rate"
  query: sum(rate(consoul_request_total[1m]))
  type: timeseries

# Panel 2: Latency Percentiles
- title: "Latency Percentiles"
  queries:
    - label: "P50"
      query: histogram_quantile(0.50, sum by (le) (rate(consoul_request_latency_seconds_bucket[5m])))
    - label: "P95"
      query: histogram_quantile(0.95, sum by (le) (rate(consoul_request_latency_seconds_bucket[5m])))
    - label: "P99"
      query: histogram_quantile(0.99, sum by (le) (rate(consoul_request_latency_seconds_bucket[5m])))
  type: timeseries

# Panel 3: Error Rate
- title: "Error Rate %"
  query: 100 * sum(rate(consoul_errors_total[1m])) / sum(rate(consoul_request_total[1m]))
  type: gauge
  thresholds: [1, 5]  # Warning at 1%, Critical at 5%

# Panel 4: Active Sessions
- title: "Active Sessions"
  query: consoul_active_sessions
  type: stat
```

---

## Running Tests

### Step-by-Step Process

#### 1. Pre-Test Verification

```bash
# Verify Consoul is running and healthy
curl -s http://localhost:8000/health | jq
# Expected: {"status": "healthy"}

# Verify readiness (Redis connection)
curl -s http://localhost:8000/ready | jq
# Expected: {"status": "ready"}

# Verify metrics endpoint
curl -s http://localhost:9090/metrics | head -20
```

#### 2. Baseline Test

```bash
# Run baseline test (1-5 VUs for 2 minutes)
k6 run --vus 5 --duration 2m load_test_chat.js

# Record results
# - P50 latency: ___ms
# - P95 latency: ___ms
# - Requests/sec: ___
# - Error rate: ___%
```

#### 3. Load Test

```bash
# Run staged load test
k6 run load_test_chat.js

# Monitor in separate terminal
watch -n 5 'curl -s http://localhost:9090/metrics | grep consoul_'
```

#### 4. Stress Test

```bash
# Run stress test to find limits
k6 run --vus 200 --duration 10m load_test_chat.js

# Stop when:
# - Error rate exceeds 5%
# - P99 latency exceeds 10s
# - Server becomes unresponsive
```

#### 5. Collect Results

```bash
# Export k6 results to JSON
k6 run --out json=results.json load_test_chat.js

# Parse results
cat results.json | jq '.metrics.http_req_duration.values'
```

### Continuous Load Testing

For CI/CD integration:

```bash
#!/bin/bash
# run_load_test.sh

set -e

# Configuration
THRESHOLD_P95=2000  # ms
THRESHOLD_ERROR=1   # percent

# Run test
k6 run --out json=results.json load_test_chat.js

# Parse results
P95=$(cat results.json | jq -r '.metrics.http_req_duration.values.p95 // 0')
ERROR_RATE=$(cat results.json | jq -r '.metrics.errors.values.rate // 0')

# Check thresholds
if (( $(echo "$P95 > $THRESHOLD_P95" | bc -l) )); then
    echo "FAIL: P95 latency ${P95}ms exceeds threshold ${THRESHOLD_P95}ms"
    exit 1
fi

if (( $(echo "$ERROR_RATE > $THRESHOLD_ERROR" | bc -l) )); then
    echo "FAIL: Error rate ${ERROR_RATE}% exceeds threshold ${THRESHOLD_ERROR}%"
    exit 1
fi

echo "PASS: All thresholds met"
```

---

## Interpreting Results

### Good Results

A successful load test shows:

- **Flat latency curve** - Latency remains stable as load increases
- **Linear throughput** - Requests/sec scales with VUs until saturation
- **Low error rate** - Errors remain under 1% throughout
- **Stable memory** - No memory growth over time (soak test)
- **Quick recovery** - Latency returns to baseline after load decreases

### Warning Signs

| Symptom | Possible Cause | Investigation |
|---------|----------------|---------------|
| Latency spikes at low load | Cold start, GC pauses | Check memory metrics, enable GC logging |
| Gradual latency increase | Connection pool exhaustion | Check Redis/HTTP pool utilization |
| Sudden error spikes | Rate limiting, circuit breaker | Check `consoul_circuit_breaker_state` |
| Timeout errors | Slow LLM responses, network issues | Check LLM provider health |
| Memory growth | Session accumulation, leaks | Check session GC, enable profiling |

### Identifying Bottlenecks

```
┌─────────────────────────────────────────────────────────────────┐
│                    Bottleneck Decision Tree                     │
│                                                                 │
│  High latency?                                                  │
│      │                                                          │
│      ├─── CPU > 80%? ──► Scale vertically or add workers        │
│      │                                                          │
│      ├─── Redis slow? ──► Check pool size, network latency      │
│      │                                                          │
│      ├─── LLM timeout? ──► Check provider status, timeouts      │
│      │                                                          │
│      └─── Memory high? ──► Session GC, reduce history size      │
│                                                                 │
│  High error rate?                                               │
│      │                                                          │
│      ├─── 429 errors? ──► Rate limits hit, increase tiers       │
│      │                                                          │
│      ├─── 503 errors? ──► Circuit breaker open, check LLM       │
│      │                                                          │
│      ├─── 500 errors? ──► Check logs, debug specific errors     │
│      │                                                          │
│      └─── Timeouts? ──► Increase timeouts, check network        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Scaling Decisions

Based on test results:

| Finding | Recommendation |
|---------|----------------|
| CPU saturated before connection limits | Add Uvicorn workers or scale vertically |
| Connection pools exhausted | Increase pool sizes in configuration |
| Memory growing over time | Tune session GC, reduce context size |
| Error rate spikes during load | Add instances (horizontal scaling) |
| Single instance meets requirements | Deploy with Redis for redundancy |

---

## Troubleshooting

### Connection Refused Errors

**Symptoms:**
- `ECONNREFUSED` errors in k6
- `Connection refused` in logs

**Causes and Solutions:**

```bash
# 1. Server not running
curl http://localhost:8000/health
# Fix: Start Consoul server

# 2. Redis not available
curl http://localhost:8000/ready
# Fix: Start Redis, check CONSOUL_SESSION_REDIS_URL

# 3. Port conflict
lsof -i :8000
# Fix: Kill conflicting process or use different port

# 4. Firewall blocking
sudo ufw status
# Fix: Allow port 8000
```

### High P99 Latency

**Symptoms:**
- P99 latency significantly higher than P50
- Occasional slow responses

**Causes and Solutions:**

```bash
# 1. Check connection pool settings
# In configuration:
CONSOUL_REDIS_MAX_CONNECTIONS=100  # Increase if needed
HTTPX_MAX_CONNECTIONS=100          # Increase for more concurrent LLM calls

# 2. Check garbage collection
# Enable GC logging to identify pauses
PYTHONGC_DEBUG=1 python -m consoul.server

# 3. Check slow queries
# In Prometheus:
histogram_quantile(0.99, rate(consoul_request_latency_seconds_bucket[5m]))
# Compare with P50 to identify outliers
```

### Increasing Error Rate Under Load

**Symptoms:**
- Error rate climbs as VUs increase
- Rate limit (429) or circuit breaker (503) errors

**Causes and Solutions:**

```bash
# 1. Rate limiting
# Check current limits
curl -H "X-API-Key: your-key" http://localhost:8000/chat

# Increase limits for testing
CONSOUL_DEFAULT_LIMITS="1000/minute"
CONSOUL_TIER_LIMITS='{"premium": "5000/minute"}'

# 2. Circuit breaker tripping
# Check status
curl http://localhost:9090/metrics | grep circuit_breaker

# Increase threshold for testing
CONSOUL_CIRCUIT_BREAKER_FAILURE_THRESHOLD=20

# 3. LLM provider rate limits
# Use mock responses for testing throughput
# Or test against local Ollama
```

### Memory Growth During Soak Tests

**Symptoms:**
- Memory usage increases over time
- Server eventually runs out of memory

**Causes and Solutions:**

```bash
# 1. Session accumulation
# Check session count
curl http://localhost:9090/metrics | grep active_sessions

# Reduce session TTL for testing
CONSOUL_SESSION_TTL=300  # 5 minutes

# Increase GC frequency
CONSOUL_SESSION_GC_INTERVAL=60

# 2. Context/history growth
# Limit conversation history
CONSOUL_MAX_HISTORY_MESSAGES=50

# 3. Memory profiling
# Enable memory profiler
pip install memory_profiler
python -m memory_profiler -m consoul.server
```

### WebSocket Disconnections

**Symptoms:**
- WebSocket connections closing unexpectedly
- `1008 Policy Violation` close codes

**Causes and Solutions:**

```bash
# 1. Slow client detection
# Consoul disconnects slow clients to prevent backpressure
# In load test, ensure message processing is fast

# 2. Timeout configuration
# Increase WebSocket timeout
CONSOUL_WS_TIMEOUT=60

# 3. Check for message buffer overflow
# Monitor logs for "slow client" messages
# Reduce message rate or increase buffer
```

---

## Quick Reference

### Environment Variables for Load Testing

```bash
# Server Configuration
CONSOUL_HOST=0.0.0.0
CONSOUL_PORT=8000
CONSOUL_WORKERS=4

# Redis
CONSOUL_SESSION_REDIS_URL=redis://localhost:6379/0
CONSOUL_RATE_LIMIT_REDIS_URL=redis://localhost:6379/1
CONSOUL_REDIS_MAX_CONNECTIONS=100

# Rate Limiting (relaxed for testing)
CONSOUL_RATE_LIMIT_ENABLED=true
CONSOUL_DEFAULT_LIMITS="1000/minute"

# Session Management
CONSOUL_SESSION_TTL=3600
CONSOUL_SESSION_GC_INTERVAL=300

# Circuit Breaker
CONSOUL_CIRCUIT_BREAKER_ENABLED=true
CONSOUL_CIRCUIT_BREAKER_FAILURE_THRESHOLD=10

# Prometheus Metrics
CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED=true
CONSOUL_OBSERVABILITY_METRICS_PORT=9090
```

### k6 Command Cheat Sheet

```bash
# Basic run
k6 run script.js

# Specify VUs and duration
k6 run --vus 50 --duration 5m script.js

# Environment variables
k6 run -e BASE_URL=http://example.com -e API_KEY=secret script.js

# Output formats
k6 run --out json=results.json script.js
k6 run --out csv=results.csv script.js
k6 run --out influxdb=http://localhost:8086/k6 script.js

# Cloud execution (k6 cloud account required)
k6 cloud script.js

# Multiple outputs
k6 run --out json=results.json --out influxdb=http://localhost:8086/k6 script.js
```

### Prometheus Query Cheat Sheet

```promql
# Request rate
rate(consoul_request_total[1m])

# Latency percentiles
histogram_quantile(0.95, rate(consoul_request_latency_seconds_bucket[5m]))

# Error rate percentage
100 * sum(rate(consoul_errors_total[1m])) / sum(rate(consoul_request_total[1m]))

# Active sessions
consoul_active_sessions

# Circuit breaker state
consoul_circuit_breaker_state

# Redis health
consoul_redis_degraded
```

### Quick Test Commands

```bash
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready

# Single request test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","message":"hello"}'

# Quick load test with hey
hey -n 100 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","message":"hello"}' \
  http://localhost:8000/chat

# Metrics snapshot
curl http://localhost:9090/metrics | grep consoul_
```

---

## Related Documentation

- [Performance Tuning Guide](../deployment/performance-tuning.md) - Connection pool sizing, server parameters
- [Scaling Guide](scaling-guide.md) - Horizontal and vertical scaling procedures
- [Multi-Tenancy Guide](../deployment/multi-tenancy.md) - Tenant isolation and rate limiting
- [API Key Rotation](api-key-rotation.md) - Managing API keys and per-key metrics
- [Runbook](runbook.md) - Operational procedures and incident response

---

**Last Updated**: December 2024
**Version**: 1.0
**Ticket**: SOUL-345
