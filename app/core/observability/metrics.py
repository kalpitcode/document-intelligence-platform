"""
Prometheus Metrics Engine Module
=================================

Thread-safe, enterprise-grade Prometheus metrics registry for platform observability.

**Architectural Rationale:**
- Pure Python OpenMetrics implementation guaranteeing high-performance metric collection
  without external binary runtime dependencies.
- Collects counters, gauges, and latency histograms for HTTP requests, worker queues,
  OCR processing, vector embeddings, hybrid search, RAG queries, workflow execution,
  database operations, Redis, Qdrant, MinIO, and LLM token usage.
- Exposes text output compliant with Prometheus / OpenMetrics scraping standards.

**Connection to the system:**
- Recorded by middleware (`TimingMiddleware`, `RequestIDMiddleware`), services, and workers.
- Formatted and served via `GET /api/v1/metrics` and `GET /metrics`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
import math
import threading
import time
from typing import Any


class Counter:
    """Thread-safe Prometheus Counter metric."""

    def __init__(self, name: str, documentation: str, labelnames: tuple[str, ...] = ()) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames
        self._values: dict[tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, value: float = 1.0, **labels: Any) -> None:
        if value < 0:
            raise ValueError("Counter value increment must be non-negative.")
        key = tuple(str(labels.get(lbl, "")) for lbl in self.labelnames)
        with self._lock:
            self._values[key] += value

    def collect(self) -> list[str]:
        lines = [
            f"# HELP {self.name} {self.documentation}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            for key, val in self._values.items():
                if self.labelnames:
                    label_str = ",".join(
                        f'{name}="{v}"' for name, v in zip(self.labelnames, key, strict=False)
                    )
                    lines.append(f"{self.name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{self.name} {val}")
        return lines


class Gauge:
    """Thread-safe Prometheus Gauge metric."""

    def __init__(self, name: str, documentation: str, labelnames: tuple[str, ...] = ()) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames
        self._values: dict[tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, value: float, **labels: Any) -> None:
        key = tuple(str(labels.get(lbl, "")) for lbl in self.labelnames)
        with self._lock:
            self._values[key] = float(value)

    def inc(self, value: float = 1.0, **labels: Any) -> None:
        key = tuple(str(labels.get(lbl, "")) for lbl in self.labelnames)
        with self._lock:
            self._values[key] += value

    def dec(self, value: float = 1.0, **labels: Any) -> None:
        key = tuple(str(labels.get(lbl, "")) for lbl in self.labelnames)
        with self._lock:
            self._values[key] -= value

    def collect(self) -> list[str]:
        lines = [
            f"# HELP {self.name} {self.documentation}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            for key, val in self._values.items():
                if self.labelnames:
                    label_str = ",".join(
                        f'{name}="{v}"' for name, v in zip(self.labelnames, key, strict=False)
                    )
                    lines.append(f"{self.name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{self.name} {val}")
        return lines


class Histogram:
    """Thread-safe Prometheus Histogram metric with default or custom latency buckets."""

    DEFAULT_BUCKETS = (
        0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 30.0, float("inf")
    )

    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: tuple[str, ...] = (),
        buckets: tuple[float, ...] | None = None,
    ) -> None:
        self.name = name
        self.documentation = documentation
        self.labelnames = labelnames
        self.buckets = tuple(sorted(buckets)) if buckets else self.DEFAULT_BUCKETS
        if float("inf") not in self.buckets:
            self.buckets = (*self.buckets, float("inf"))

        self._counts: dict[tuple[str, ...], dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )
        self._sums: dict[tuple[str, ...], float] = defaultdict(float)
        self._total_counts: dict[tuple[str, ...], int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, amount: float, **labels: Any) -> None:
        key = tuple(str(labels.get(lbl, "")) for lbl in self.labelnames)
        with self._lock:
            self._sums[key] += amount
            self._total_counts[key] += 1
            b_dict = self._counts[key]
            for b in self.buckets:
                if amount <= b:
                    b_dict[b] += 1

    def collect(self) -> list[str]:
        lines = [
            f"# HELP {self.name} {self.documentation}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            for key, b_dict in self._counts.items():
                cumulative = 0
                label_base = (
                    ",".join(f'{name}="{v}"' for name, v in zip(self.labelnames, key, strict=False))
                    if self.labelnames
                    else ""
                )

                for b in self.buckets:
                    cumulative += b_dict[b]
                    le_str = "+Inf" if math.isinf(b) else str(b)
                    lbl_full = f'{label_base},le="{le_str}"' if label_base else f'le="{le_str}"'
                    lines.append(f"{self.name}_bucket{{{lbl_full}}} {cumulative}")

                lbl_wrap = f"{{{label_base}}}" if label_base else ""
                lines.append(f"{self.name}_sum{lbl_wrap} {self._sums[key]}")
                lines.append(f"{self.name}_count{lbl_wrap} {self._total_counts[key]}")
        return lines


class MetricsRegistry:
    """Central registry tracking all operational metrics."""

    def __init__(self) -> None:
        # HTTP Metrics
        self.http_requests_total = Counter(
            "blackrock_dip_http_requests_total",
            "Total count of HTTP requests processed",
            ("method", "endpoint", "status_code"),
        )
        self.http_request_duration_seconds = Histogram(
            "blackrock_dip_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ("method", "endpoint"),
        )
        self.http_response_status_total = Counter(
            "blackrock_dip_http_response_status_total",
            "HTTP response status code count",
            ("status_code",),
        )

        # Operational Latencies
        self.ocr_duration_seconds = Histogram(
            "blackrock_dip_ocr_duration_seconds",
            "OCR processing duration in seconds",
            ("engine",),
        )
        self.embedding_duration_seconds = Histogram(
            "blackrock_dip_embedding_duration_seconds",
            "Vector embedding generation duration in seconds",
            ("model",),
        )
        self.search_latency_seconds = Histogram(
            "blackrock_dip_search_latency_seconds",
            "Hybrid search latency in seconds",
            ("strategy",),
        )
        self.rag_latency_seconds = Histogram(
            "blackrock_dip_rag_latency_seconds",
            "RAG generation latency in seconds",
            ("llm_model",),
        )
        self.workflow_duration_seconds = Histogram(
            "blackrock_dip_workflow_duration_seconds",
            "Workflow execution duration in seconds",
            ("workflow_id", "status"),
        )
        self.ai_feature_duration_seconds = Histogram(
            "blackrock_dip_ai_feature_duration_seconds",
            "AI feature execution duration in seconds",
            ("feature_type",),
        )

        # Component Infrastructure Latencies
        self.database_query_time_seconds = Histogram(
            "blackrock_dip_database_query_time_seconds",
            "Database query execution duration in seconds",
            ("operation",),
        )
        self.redis_latency_seconds = Histogram(
            "blackrock_dip_redis_latency_seconds",
            "Redis cache command latency in seconds",
            ("command",),
        )
        self.qdrant_latency_seconds = Histogram(
            "blackrock_dip_qdrant_latency_seconds",
            "Qdrant vector database query latency in seconds",
            ("operation",),
        )
        self.storage_latency_seconds = Histogram(
            "blackrock_dip_storage_latency_seconds",
            "MinIO object storage request latency in seconds",
            ("operation",),
        )
        self.llm_latency_seconds = Histogram(
            "blackrock_dip_llm_latency_seconds",
            "LLM API provider request latency in seconds",
            ("provider", "model"),
        )

        # Counters & Gauges
        self.token_usage_total = Counter(
            "blackrock_dip_token_usage_total",
            "Total LLM token consumption count",
            ("token_type", "model"),
        )
        self.worker_queue_size = Gauge(
            "blackrock_dip_worker_queue_size",
            "Current pending task count in Celery worker queues",
            ("queue_name",),
        )
        self.circuit_breaker_tripped_total = Counter(
            "blackrock_dip_circuit_breaker_tripped_total",
            "Total circuit breaker trip events",
            ("service_name",),
        )
        self.rate_limit_exceeded_total = Counter(
            "blackrock_dip_rate_limit_exceeded_total",
            "Total rate limit exceeded occurrences",
            ("client_ip",),
        )

    def generate_prometheus_text(self) -> str:
        """Render all registered metrics in standard Prometheus exposition text format."""
        all_metrics: list[Counter | Gauge | Histogram] = [
            self.http_requests_total,
            self.http_request_duration_seconds,
            self.http_response_status_total,
            self.ocr_duration_seconds,
            self.embedding_duration_seconds,
            self.search_latency_seconds,
            self.rag_latency_seconds,
            self.workflow_duration_seconds,
            self.ai_feature_duration_seconds,
            self.database_query_time_seconds,
            self.redis_latency_seconds,
            self.qdrant_latency_seconds,
            self.storage_latency_seconds,
            self.llm_latency_seconds,
            self.token_usage_total,
            self.worker_queue_size,
            self.circuit_breaker_tripped_total,
            self.rate_limit_exceeded_total,
        ]
        output_lines: list[str] = []
        for m in all_metrics:
            output_lines.extend(m.collect())
            output_lines.append("")
        return "\n".join(output_lines)


# Global singleton instance
metrics_registry = MetricsRegistry()


def track_time(histogram: Histogram, **labels: Any) -> Callable:
    """Decorator / Context manager helper to measure execution latency."""

    class TimerContextManager:
        def __enter__(self) -> TimerContextManager:
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args: Any) -> None:
            duration = time.perf_counter() - self.start
            histogram.observe(duration, **labels)

    return TimerContextManager()
