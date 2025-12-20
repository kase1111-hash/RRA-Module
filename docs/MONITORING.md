# RRA Module - Monitoring & Alerting Guide

**Version:** 1.0.0
**Last Updated:** 2025-12-20

This guide covers production monitoring, alerting, and observability best practices for the RRA Module.

---

## Table of Contents

1. [Overview](#overview)
2. [Security Logging](#security-logging)
3. [Metrics Collection](#metrics-collection)
4. [Alerting Rules](#alerting-rules)
5. [Dashboard Recommendations](#dashboard-recommendations)
6. [Integration Examples](#integration-examples)

---

## Overview

The RRA Module provides structured logging and metrics collection that integrates with standard observability stacks:

- **Logging:** JSON-formatted security events compatible with SIEM systems
- **Metrics:** Prometheus-compatible metrics for operational monitoring
- **Tracing:** OpenTelemetry support for distributed tracing (optional)

### Recommended Stack

| Component | Recommended Tools |
|-----------|-------------------|
| Log Aggregation | ELK Stack, Splunk, Datadog, CloudWatch |
| Metrics | Prometheus + Grafana, Datadog, CloudWatch |
| Alerting | PagerDuty, OpsGenie, Slack, Email |
| APM | Datadog APM, New Relic, Jaeger |

---

## Security Logging

### Log Format

All security events are logged in JSON format with the following structure:

```json
{
  "timestamp": "2025-12-20T10:30:00.000Z",
  "service": "rra-module",
  "environment": "production",
  "event_type": "auth.failure",
  "severity": "warning",
  "message": "Authentication failed: Invalid API key",
  "source_ip": "192.0.2.1",
  "user_id": "user_abc123",
  "agent_id": "repo_xyz789",
  "request_id": "req_123456",
  "details": {
    "reason": "invalid_key",
    "attempts": 3
  },
  "tags": ["security", "auth"]
}
```

### Event Types

| Event Type | Severity | Description |
|------------|----------|-------------|
| `auth.success` | info | Successful authentication |
| `auth.failure` | warning | Failed authentication attempt |
| `auth.token_expired` | info | Expired token used |
| `rate_limit.exceeded` | warning | Rate limit exceeded |
| `webhook.signature_invalid` | warning | Invalid webhook signature |
| `ssrf.blocked` | warning | SSRF attempt blocked |
| `injection.blocked` | warning | Injection attempt blocked |
| `suspicious.pattern` | warning | Suspicious activity detected |
| `suspicious.brute_force` | error | Brute force attack detected |
| `contract.license_issued` | info | License NFT minted |
| `contract.payment_received` | info | Payment received |

### Enabling Security Logs

```bash
# Set environment variables
export RRA_SECURITY_LOG_FILE=true
export RRA_SERVICE_NAME=rra-production
export RRA_ENVIRONMENT=production

# Logs will be written to logs/security.log
```

### Log Rotation

Configure log rotation using logrotate:

```
/var/log/rra/security.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 rra rra
}
```

---

## Metrics Collection

### Key Metrics to Monitor

#### API Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rra_api_requests_total` | Counter | method, endpoint, status | Total API requests |
| `rra_api_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `rra_api_errors_total` | Counter | method, endpoint, error_type | API errors |

#### Security Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rra_auth_attempts_total` | Counter | result, method | Authentication attempts |
| `rra_rate_limit_hits_total` | Counter | agent_id | Rate limit events |
| `rra_security_events_total` | Counter | event_type, severity | Security events |

#### Blockchain Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rra_licenses_issued_total` | Counter | chain, license_type | Licenses issued |
| `rra_payments_received_total` | Counter | chain, token | Payments received |
| `rra_gas_used_total` | Counter | chain, operation | Gas consumed |

#### Agent Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `rra_negotiations_total` | Counter | agent_id, outcome | Negotiations completed |
| `rra_negotiation_duration_seconds` | Histogram | agent_id | Negotiation duration |
| `rra_active_agents` | Gauge | - | Currently active agents |

### Prometheus Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'rra-module'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## Alerting Rules

### Critical Alerts (Immediate Response Required)

```yaml
# Critical: Service Down
- alert: RRAServiceDown
  expr: up{job="rra-module"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "RRA Module is down"
    description: "RRA Module has been unreachable for more than 1 minute"

# Critical: High Error Rate
- alert: RRAHighErrorRate
  expr: rate(rra_api_errors_total[5m]) > 10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High API error rate detected"
    description: "Error rate is {{ $value }} errors per second"

# Critical: Brute Force Attack
- alert: RRABruteForceDetected
  expr: increase(rra_auth_attempts_total{result="failure"}[5m]) > 50
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Possible brute force attack detected"
    description: "{{ $value }} failed auth attempts in 5 minutes"
```

### Warning Alerts (Investigate Within 1 Hour)

```yaml
# Warning: High Latency
- alert: RRAHighLatency
  expr: histogram_quantile(0.95, rate(rra_api_request_duration_seconds_bucket[5m])) > 2
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High API latency detected"
    description: "95th percentile latency is {{ $value }}s"

# Warning: Rate Limit Exhaustion
- alert: RRARateLimitExhaustion
  expr: increase(rra_rate_limit_hits_total[1h]) > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High rate limit usage"
    description: "{{ $value }} rate limit events in the last hour"

# Warning: SSRF Attempts
- alert: RRASSRFAttempts
  expr: increase(rra_security_events_total{event_type="ssrf.blocked"}[1h]) > 5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "SSRF attempts detected"
    description: "{{ $value }} SSRF attempts blocked in the last hour"
```

### Info Alerts (Review Daily)

```yaml
# Info: Low Transaction Volume
- alert: RRALowTransactionVolume
  expr: increase(rra_licenses_issued_total[24h]) < 1
  for: 24h
  labels:
    severity: info
  annotations:
    summary: "No licenses issued in 24 hours"
    description: "Consider investigating if this is unexpected"

# Info: Certificate Expiry
- alert: RRACertificateExpiry
  expr: (rra_tls_certificate_expiry_seconds - time()) < 604800
  for: 1h
  labels:
    severity: info
  annotations:
    summary: "TLS certificate expiring soon"
    description: "Certificate expires in {{ $value | humanizeDuration }}"
```

---

## Dashboard Recommendations

### Overview Dashboard

Create a high-level dashboard with:

1. **Service Health**
   - Uptime percentage (target: 99.9%)
   - Current request rate
   - Error rate (target: <1%)
   - Active connections

2. **Security Status**
   - Auth success/failure ratio
   - Rate limit utilization
   - Security events by type
   - Blocked attack attempts

3. **Business Metrics**
   - Licenses issued (daily/weekly/monthly)
   - Revenue by chain
   - Active agents
   - Average negotiation time

### Security Dashboard

Create a security-focused dashboard with:

1. **Authentication**
   - Login attempts over time
   - Failed logins by IP
   - Token usage patterns

2. **Attack Detection**
   - SSRF attempts
   - Injection attempts
   - Brute force indicators
   - Unusual traffic patterns

3. **Rate Limiting**
   - Rate limit utilization by agent
   - Top rate-limited IPs
   - Trending toward limits

### Blockchain Dashboard

Create a blockchain-focused dashboard with:

1. **Transaction Activity**
   - Licenses issued by chain
   - Gas costs over time
   - Payment volume

2. **Contract Health**
   - Failed transactions
   - Pending transactions
   - Gas price trends

---

## Integration Examples

### ELK Stack (Elasticsearch, Logstash, Kibana)

```ruby
# logstash.conf
input {
  file {
    path => "/var/log/rra/security.log"
    codec => json
    type => "rra-security"
  }
}

filter {
  if [type] == "rra-security" {
    date {
      match => ["timestamp", "ISO8601"]
      target => "@timestamp"
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "rra-security-%{+YYYY.MM.dd}"
  }
}
```

### CloudWatch (AWS)

```python
# cloudwatch_handler.py
import boto3
import json

logs_client = boto3.client('logs')

def send_to_cloudwatch(event: dict):
    logs_client.put_log_events(
        logGroupName='/rra-module/security',
        logStreamName='production',
        logEvents=[{
            'timestamp': int(time.time() * 1000),
            'message': json.dumps(event)
        }]
    )
```

### Datadog

```yaml
# datadog.yaml
logs:
  - type: file
    path: /var/log/rra/security.log
    service: rra-module
    source: python
    sourcecategory: security

init_config:

instances:
  - prometheus_url: http://localhost:8000/metrics
    namespace: rra
    metrics:
      - rra_*
```

### PagerDuty Integration

```python
# pagerduty_alert.py
import requests

def send_pagerduty_alert(event: dict):
    if event.get('severity') in ['critical', 'error']:
        requests.post(
            'https://events.pagerduty.com/v2/enqueue',
            json={
                'routing_key': 'YOUR_ROUTING_KEY',
                'event_action': 'trigger',
                'payload': {
                    'summary': event['message'],
                    'severity': event['severity'],
                    'source': event['service'],
                    'custom_details': event.get('details', {})
                }
            }
        )
```

---

## Quick Setup Checklist

- [ ] Enable security logging (`RRA_SECURITY_LOG_FILE=true`)
- [ ] Configure log rotation
- [ ] Set up log aggregation (ELK/Splunk/CloudWatch)
- [ ] Configure Prometheus metrics scraping
- [ ] Create Grafana dashboards
- [ ] Set up alerting rules
- [ ] Configure PagerDuty/OpsGenie integration
- [ ] Test alert delivery
- [ ] Document runbooks for each alert
- [ ] Schedule regular monitoring review

---

## License

This documentation is licensed under FSL-1.1-ALv2.

Copyright 2025 Kase Branham
