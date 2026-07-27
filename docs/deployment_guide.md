# Production Deployment & Installation Guide

## 1. Environment Requirements
- **Docker**: Version 24.0+
- **Kubernetes Cluster**: Version 1.28+
- **Helm**: Version 3.12+
- **Python**: Version 3.12+
- **Poetry**: Version 1.8+

---

## 2. Docker Compose Local / Single Server Deployment

To spin up the entire production environment via Docker Compose:

```bash
# 1. Clone repository
git clone https://github.com/kalpitcode/document-intelligence-platform.git
cd document-intelligence-platform

# 2. Build production images & launch services
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Verify health probe
curl http://localhost:8000/api/v1/health
```

---

## 3. Kubernetes Deployment via Manifests

```bash
# 1. Apply namespace, secrets, and configurations
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secret.yaml
kubectl apply -f deploy/k8s/pvc.yaml

# 2. Apply deployments, services, ingress, and scaling policies
kubectl apply -f deploy/k8s/serviceaccount.yaml
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/ingress.yaml
kubectl apply -f deploy/k8s/hpa.yaml
kubectl apply -f deploy/k8s/networkpolicy.yaml
kubectl apply -f deploy/k8s/pdb.yaml
kubectl apply -f deploy/k8s/resourcequota.yaml
kubectl apply -f deploy/k8s/limitrange.yaml
```

---

## 4. Kubernetes Deployment via Helm

```bash
# 1. Install or Upgrade Helm Release
helm upgrade --install dip deploy/helm/document-intelligence-platform \
  --namespace dip-production \
  --create-namespace \
  -f deploy/helm/document-intelligence-platform/values.yaml

# 2. Verify Deployment Status
helm status dip --namespace dip-production
```

---

## 5. Security & Configuration Recommendations
- Change default secrets in `deploy/k8s/secret.yaml` and `deploy/helm/.../values.yaml`.
- Ensure TLS certificates are bound to the Ingress controller.
- Enable Prometheus monitoring scraped from `/api/v1/metrics`.
