# SRE Observability, Prometheus Metrics & Alerting Guide

## 1. Metrics Stack Configuration
- **Prometheus Exporter**: Scrapes OpenMetrics from `/api/v1/metrics` every 15 seconds.
- **OpenTelemetry Collector**: Receives OTLP gRPC (`:4317`) and HTTP (`:4318`) traces and exports to tracing backends.
- **Grafana**: Pre-configured dashboards for API throughput, Celery task latency, PostgreSQL connection pool, and Qdrant search performance.

---

## 2. Core Alert Rules & Thresholds

| Alert Name | Condition | Severity | Action / Runbook |
| :--- | :--- | :--- | :--- |
| `APIHighErrorRate` | HTTP 5xx errors $> 5\%$ over 5 min | Critical | Scale replicas, check Postgres pool |
| `HighRequestLatency` | p99 latency $> 1000$ms | Warning | Inspect slow Qdrant queries & DB locks |
| `WorkerQueueBacklog` | RabbitMQ depth $> 500$ tasks | High | Autoscale Celery worker pods |
| `CircuitBreakerTripped` | CircuitBreaker state = `OPEN` | High | Investigate downstream dependency failure |
