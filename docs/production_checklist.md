# Pre-Flight Production Launch & Rollback Checklist

## Pre-Flight Checklist
- [x] **Configuration Validation**: All default passwords and JWT secret keys replaced with production-grade credentials.
- [x] **Container Optimization**: Multi-stage `Dockerfile` verified, non-root user `dipuser` configured.
- [x] **Health Probes**: `/api/v1/health`, `/api/v1/health/live`, and `/api/v1/health/ready` verified.
- [x] **Kubernetes Manifests**: K8s ResourceQuotas, LimitRanges, NetworkPolicies, and PDBs deployed.
- [x] **Helm Verification**: Chart syntax checked via `helm lint`.
- [x] **Security Scan**: `python scripts/security_scan.py` passes with zero secret leakage.
- [x] **Database Migration**: Database schema updated to latest migration state.
- [x] **Backup Validation**: Database backup and restore verified via `scripts/db_backup.py` and `scripts/db_restore.py`.
- [x] **Load Testing**: Locust load test suite executed with zero request drops.

---

## Release & Deployment Checklist
1. Execute continuous integration pipeline tests in GitHub Actions.
2. Build and tag container image in container registry.
3. Apply database migration (`alembic upgrade head`).
4. Execute rolling deployment via Helm or Kubernetes kubectl.
5. Perform post-deployment smoke test (`GET /api/v1/health`).

---

## Emergency Rollback Checklist
1. Execute `helm rollback dip`.
2. Restore database state from pre-deployment snapshot if schema breaking changes occurred.
3. Validate API readiness and client metrics.
