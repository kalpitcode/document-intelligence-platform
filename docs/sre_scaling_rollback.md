# Capacity Planning, Horizontal Scaling & Emergency Rollback Guide

## 1. Autoscaling Configuration
- **API Server Scaling**: Controlled by `HorizontalPodAutoscaler` (`dip-api-hpa`), scaling between 3 and 25 replicas based on CPU ($75\%$) and Memory ($80\%$) utilization.
- **Worker Scaling**: Dynamic scaling based on RabbitMQ queue backlog depth.

---

## 2. Emergency Deployment Rollback Procedure
If a production release exhibits regressions:

```bash
# 1. Rollback Helm release to previous revision
helm rollback dip -n dip-production

# 2. Verify status of rolled-back deployment
helm status dip -n dip-production

# 3. Check health probe endpoints
curl -f http://dip.blackrock.com/api/v1/health/ready
```
