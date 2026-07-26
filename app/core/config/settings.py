"""
Configuration Settings Module
==============================

Central configuration for the entire application using Pydantic V2 BaseSettings.

**Architectural Rationale:**
- All configuration is defined in a single, typed, validated class.
- Environment variables are the source of truth (12-Factor App).
- No hardcoded secrets — everything flows through .env or environment.
- Computed properties derive complex values (URLs) from atomic settings.
- Validators ensure configuration correctness at startup, not at runtime.

**Connection to the system:**
- Imported by every layer that needs configuration (database, cache, messaging, etc.).
- The `get_settings()` function in `__init__.py` provides a cached singleton.
"""

from __future__ import annotations

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings follow the naming convention: SECTION_PROPERTY
    e.g., POSTGRES_HOST, REDIS_PORT, APP_DEBUG
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application
    # ==========================================================================
    app_name: str = Field(
        default="document-intelligence-platform",
        description="Application name used in logs and health endpoints",
    )
    app_version: str = Field(
        default="0.1.0",
        description="Semantic version of the application",
    )
    app_description: str = Field(
        default="Enterprise AI Document Intelligence Platform",
        description="Human-readable description for OpenAPI docs",
    )
    app_env: str = Field(
        default="development",
        description="Runtime environment: development | staging | production | testing",
    )
    app_debug: bool = Field(
        default=False,
        description="Enable debug mode (never True in production)",
    )
    app_host: str = Field(
        default="0.0.0.0",
        description="Host to bind the application server",
    )
    app_port: int = Field(
        default=8000,
        description="Port to bind the application server",
    )
    app_workers: int = Field(
        default=1,
        description="Number of Uvicorn worker processes",
    )

    # ==========================================================================
    # API
    # ==========================================================================
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="URL prefix for API version 1",
    )

    # ==========================================================================
    # PostgreSQL
    # ==========================================================================
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="dip_user")
    postgres_password: str = Field(default="change_me_in_production")
    postgres_db: str = Field(default="document_intelligence")
    postgres_pool_size: int = Field(
        default=20,
        description="SQLAlchemy connection pool size",
    )
    postgres_max_overflow: int = Field(
        default=10,
        description="Max connections beyond pool_size",
    )
    postgres_pool_recycle: int = Field(
        default=3600,
        description="Seconds before a connection is recycled",
    )
    postgres_echo: bool = Field(
        default=False,
        description="Echo SQL statements to logs (development only)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_sync(self) -> str:
        """Synchronous PostgreSQL URL for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: str = Field(default="")
    redis_max_connections: int = Field(default=20)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        password_part = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password_part}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ==========================================================================
    # RabbitMQ
    # ==========================================================================
    rabbitmq_host: str = Field(default="localhost")
    rabbitmq_port: int = Field(default=5672)
    rabbitmq_user: str = Field(default="dip_user")
    rabbitmq_password: str = Field(default="change_me_in_production")
    rabbitmq_vhost: str = Field(default="/")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rabbitmq_url(self) -> str:
        """AMQP connection URL for RabbitMQ."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )

    # ==========================================================================
    # Celery
    # ==========================================================================
    celery_broker_url: str = Field(
        default="amqp://dip_user:change_me_in_production@localhost:5672//",
        description="Celery broker URL (RabbitMQ)",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend (Redis)",
    )

    # ==========================================================================
    # CORS
    # ==========================================================================
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
    )
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: list[str] = Field(default=["*"])
    cors_allow_headers: list[str] = Field(default=["*"])

    # ==========================================================================
    # Logging
    # ==========================================================================
    log_level: str = Field(
        default="INFO",
        description="Global log level: DEBUG | INFO | WARNING | ERROR | CRITICAL",
    )
    log_format: str = Field(
        default="json",
        description="Log output format: json | console",
    )
    log_file: str = Field(
        default="logs/app.log",
        description="Path to the log file",
    )

    # ==========================================================================
    # Trusted Hosts
    # ==========================================================================
    trusted_hosts: list[str] = Field(
        default=["localhost", "127.0.0.1"],
    )

    # ==========================================================================
    # JWT & Authentication
    # ==========================================================================
    jwt_secret_key: str = Field(
        default="SUPER_SECRET_JWT_KEY_PLEASE_CHANGE_IN_PRODUCTION_BLACKROCK_ALADDIN",
        description="Secret key for signing JWT tokens",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Cryptographic algorithm for JWT signing",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days",
    )
    jwt_issuer: str = Field(
        default="blackrock-dip",
        description="JWT issuer claim (iss)",
    )
    jwt_audience: str = Field(
        default="blackrock-dip-api",
        description="JWT audience claim (aud)",
    )

    # ==========================================================================
    # Password & Account Security
    # ==========================================================================
    max_failed_login_attempts: int = Field(
        default=5,
        description="Maximum failed login attempts before account lockout",
    )
    account_lockout_minutes: int = Field(
        default=15,
        description="Lockout duration in minutes after maximum failed login attempts",
    )
    password_min_length: int = Field(
        default=12,
        description="Minimum password length requirement",
    )

    # ==========================================================================
    # Validators
    # ==========================================================================
    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Ensure environment is one of the known values."""
        allowed = {"development", "staging", "production", "testing"}
        if v.lower() not in allowed:
            msg = f"APP_ENV must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            msg = f"LOG_LEVEL must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v.upper()

    # ==========================================================================
    # Utility Properties
    # ==========================================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.app_env == "testing"
