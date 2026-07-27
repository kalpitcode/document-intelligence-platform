# SRE Troubleshooting & Incident Response Runbook

## Incident Playbooks

### Playbook 1: PostgreSQL Connection Pool Exhaustion
1. **Diagnosis**: Check `/api/v1/system/status` or Prometheus metric `db_pool_active_connections`.
2. **Remediation**:
   - Restart failing API pods to clear unreleased connections:
     ```bash
     kubectl rollout restart deployment/dip-api-deployment -n dip-production
     ```
   - Scale database connection pool limit in `app/core/config/settings.py` via ConfigMap.

### Playbook 2: Celery Task Backlog & OCR Bottleneck
1. **Diagnosis**: Task queue depth exceeding SLA threshold.
2. **Remediation**:
   - Scale up worker replicas horizontally:
     ```bash
     kubectl scale deployment dip-worker-deployment -n dip-production --replicas=12
     ```
   - Verify RabbitMQ health: `kubectl exec -it dip-rabbitmq-0 -n dip-production -- rabbitmq-diagnostics ping`.

### Playbook 3: Vector Store Out of Memory (OOM)
1. **Diagnosis**: `dip-qdrant-0` pod status `OOMKilled`.
2. **Remediation**:
   - Increase Qdrant memory limit to 16Gi in StatefulSet spec.
