"""
Production Deployment Readiness & Verification Test Suite
==========================================================
"""

from __future__ import annotations

import os
import pytest

from scripts.db_backup import run_backup
from scripts.db_restore import restore_backup
from scripts.security_scan import scan_secrets


def test_dockerfile_production_readiness() -> None:
    assert os.path.exists("Dockerfile")
    with open("Dockerfile", encoding="utf-8") as f:
        content = f.read()

    assert "AS builder" in content
    assert "AS runner" in content
    assert "useradd" in content
    assert "dipuser" in content
    assert "HEALTHCHECK" in content


def test_docker_compose_prod_exists() -> None:
    assert os.path.exists("docker-compose.prod.yml")
    with open("docker-compose.prod.yml", encoding="utf-8") as f:
        content = f.read()

    assert "postgres:" in content
    assert "redis:" in content
    assert "rabbitmq:" in content
    assert "minio:" in content
    assert "qdrant:" in content
    assert "api:" in content
    assert "worker:" in content


def test_kubernetes_manifests_exist() -> None:
    k8s_dir = os.path.join("deploy", "k8s")
    assert os.path.isdir(k8s_dir)

    expected_manifests = [
        "namespace.yaml",
        "configmap.yaml",
        "secret.yaml",
        "deployment.yaml",
        "service.yaml",
        "ingress.yaml",
        "hpa.yaml",
        "pvc.yaml",
        "networkpolicy.yaml",
        "pdb.yaml",
        "serviceaccount.yaml",
        "resourcequota.yaml",
        "limitrange.yaml",
    ]

    for manifest in expected_manifests:
        filepath = os.path.join(k8s_dir, manifest)
        assert os.path.exists(filepath), f"Missing K8s manifest: {manifest}"


def test_helm_chart_exists() -> None:
    helm_dir = os.path.join("deploy", "helm", "document-intelligence-platform")
    assert os.path.exists(os.path.join(helm_dir, "Chart.yaml"))
    assert os.path.exists(os.path.join(helm_dir, "values.yaml"))
    assert os.path.isdir(os.path.join(helm_dir, "templates"))


def test_ci_cd_workflows_exist() -> None:
    github_dir = os.path.join(".github", "workflows")
    assert os.path.exists(os.path.join(github_dir, "ci.yml"))
    assert os.path.exists(os.path.join(github_dir, "cd.yml"))


def test_security_scanner_execution() -> None:
    secrets = scan_secrets()
    assert len(secrets) == 0, f"Found secrets: {secrets}"


def test_db_backup_and_restore_scripts() -> None:
    backup_file = run_backup("tmp/test_backups")
    assert os.path.exists(backup_file)
    restored = restore_backup(backup_file)
    assert restored is True
    if os.path.exists(backup_file):
        os.remove(backup_file)
