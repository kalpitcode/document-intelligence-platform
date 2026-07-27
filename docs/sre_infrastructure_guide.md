# Google SRE Production Infrastructure & Topology Guide

## Overview
This document outlines the cloud infrastructure topology, Kubernetes resource declarations, and storage provisions for the **Enterprise AI Document Intelligence Platform**.

---

## 1. Kubernetes Namespace & RBAC Security Model
- **Namespace**: `dip-production`
- **ServiceAccount**: `dip-sre-service-account` bound to `dip-sre-role` enforcing principle of least privilege.
- **ResourceQuota**: Hard ceiling of 40 CPU cores, 80GB RAM, and 50 maximum pods.
- **LimitRange**: Enforces default request (250m CPU / 256Mi RAM) and limit (1000m CPU / 1Gi RAM).

---

## 2. Stateful Services Architecture

| Service | Architecture | Persistent Volume | Storage Class |
| :--- | :--- | :--- | :--- |
| **PostgreSQL 16** | StatefulSet (`dip-postgres`) | `50Gi` | `dip-fast-nvme` (pd-ssd) |
| **Redis 7** | StatefulSet (`dip-redis`) | `10Gi` | `dip-fast-nvme` |
| **RabbitMQ 3.13** | StatefulSet (`dip-rabbitmq`) | `20Gi` | `dip-fast-nvme` |
| **MinIO Object Store** | StatefulSet (`dip-minio`) | `100Gi` | `dip-fast-nvme` |
| **Qdrant Vector DB** | StatefulSet (`dip-qdrant`) | `50Gi` | `dip-fast-nvme` |

---

## 3. StorageClass & Dynamic Volume Provisioning
Utilizes high-throughput SSD storage (`pd-ssd` via `StorageClass/dip-fast-nvme`) with `volumeBindingMode: WaitForFirstConsumer` and `allowVolumeExpansion: true`.
