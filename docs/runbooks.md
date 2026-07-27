# Operational Runbooks & Incident Response Guide

## Incident Severity Definitions

| Severity | Impact Description | Response SLA | Escalate To |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Core API outage, Database down, total service unreachability | $< 15$ mins | On-Call Lead & Platform Architect |
| **SEV-2 (High)** | Degradation in OCR processing, high error rate ($>5\%$), worker backlog | $< 30$ mins | Platform Senior Engineer |
| **SEV-3 (Medium)** | Non-critical background task failures, minor latency increase | $< 2$ hours | DevOps Engineer |

---

## Standard Runbooks

### Runbook 1: High API Error Rate Alert (`HIGH_ERROR_RATE`)
1. Check overall system status:
   ```bash
   curl -s http://localhost:8000/api/v1/system/status | jq .
   ```
2. Query error logs for HTTP 500 status codes:
   ```bash
   kubectl logs -l app.kubernetes.io/component=api -n dip-production --tail=200 | grep '"http_status":500'
   ```
3. Verify database pool availability via `GET /api/v1/system/status`.

### Runbook 2: Celery Worker Queue Backlog (`WORKER_BACKLOG`)
1. Inspect active tasks and queue depth in Redis:
   ```bash
   redis-cli -h redis.dip-production llen celery
   ```
2. Scale worker deployment replicas horizontally:
   ```bash
   kubectl scale deployment dip-worker-deployment -n dip-production --replicas=8
   ```

### Runbook 3: Emergency Application Rollback
1. Revert to previous Helm revision:
   ```bash
   helm rollback dip --namespace dip-production
   ```
2. Verify system readiness:
   ```bash
   curl -f http://dip.blackrock.com/api/v1/health/ready
   ```
