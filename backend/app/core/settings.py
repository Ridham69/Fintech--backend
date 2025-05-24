"""
Settings Module

This module manages all application configuration using Pydantic v2 Settings.
Includes configurations for:
- Application core settings
- Database connections
- Authentication and security
- Third-party integrations
- Feature flags
- Monitoring and logging
- Task processing
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    EmailStr,
    Field,
    PostgresDsn,
    RedisDsn,
    SecretStr,
    field_validator,
    model_validator
)
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    """Application core configuration."""
    
    TITLE: str = "AutoInvest India API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Automated Investment Platform for Indian Retail Investors"
    
    # Environment
    ENVIRONMENT: str = Field(
        default="development",
        pattern="^(development|staging|production|test)$"
    )
    DEBUG: bool = Field(default=False)
    
    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    ROOT_PATH: str = Field(default="")
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    model_config = SettingsConfigDict(
        env_prefix="APP_"
    )

class DatabaseConfig(BaseSettings):
    """Database connection configuration."""
    
    # PostgreSQL
    POSTGRES_HOST: str
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_SCHEMA: str = Field(default="public")
    
    # Connection Pool
    POSTGRES_MIN_POOL_SIZE: int = Field(default=5)
    POSTGRES_MAX_POOL_SIZE: int = Field(default=20)
    POSTGRES_POOL_RECYCLE: int = Field(default=1800)  # 30 minutes
    
    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: Optional[SecretStr] = None
    
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        """Construct PostgreSQL SYNC connection URL (for Alembic, sync SQLAlchemy)."""
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB
        )
    
    @property
    def ASYNC_DATABASE_URL(self) -> PostgresDsn:
        """Construct PostgreSQL ASYNC connection URL (for async SQLAlchemy)."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB
        )
    
    @property
    def REDIS_URL(self) -> RedisDsn:
        """Construct Redis connection URL."""
        auth = (
            f":{self.REDIS_PASSWORD.get_secret_value()}@"
            if self.REDIS_PASSWORD
            else ""
        )
        return RedisDsn.build(
            scheme="redis",
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path=str(self.REDIS_DB),
            password=self.REDIS_PASSWORD.get_secret_value() if self.REDIS_PASSWORD else None
        )
    
    model_config = SettingsConfigDict(
        env_prefix="DB_"
    )

class AuthConfig(BaseModel):
    """Authentication and authorization configuration."""
    
    # JWT Settings
    JWT_SECRET_KEY: SecretStr = SecretStr("dummy_jwt_secret_for_ci")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    
    # Password Hashing
    ARGON2_TIME_COST: int = Field(default=2)
    ARGON2_MEMORY_COST: int = Field(default=102400)
    ARGON2_PARALLELISM: int = Field(default=8)
    
    # Session Management
    SESSION_COOKIE_NAME: str = Field(default="session")
    SESSION_COOKIE_SECURE: bool = Field(default=True)
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True)
    SESSION_COOKIE_SAMESITE: str = Field(default="lax")
    
    # Login Throttling
    MAX_LOGIN_ATTEMPTS: int = Field(default=5)
    
    model_config = SettingsConfigDict(
        env_prefix="AUTH_"
    )

class CeleryConfig(BaseSettings):
    """Celery task queue configuration."""
    
    BROKER_URL: str
    RESULT_BACKEND: str
    
    # Task Settings
    TASK_SERIALIZER: str = Field(default="json")
    RESULT_SERIALIZER: str = Field(default="json")
    ACCEPT_CONTENT: List[str] = Field(default=["json"])
    TIMEZONE: str = Field(default="Asia/Kolkata")
    
    # Task Execution
    TASK_SOFT_TIME_LIMIT: int = Field(default=300)  # 5 minutes
    TASK_TIME_LIMIT: int = Field(default=360)  # 6 minutes
    WORKER_CONCURRENCY: int = Field(default=4)
    
    # Task Routing
    TASK_DEFAULT_QUEUE: str = Field(default="default")
    TASK_CREATE_MISSING_QUEUES: bool = Field(default=True)
    
    model_config = SettingsConfigDict(
        env_prefix="CELERY_"
    )

class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""
    
    ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    
    # Per-endpoint limits
    AUTH_RATE_LIMIT: int = Field(default=5)  # Auth endpoints
    INVESTMENT_RATE_LIMIT: int = Field(default=30)  # Investment endpoints
    PAYMENT_RATE_LIMIT: int = Field(default=20)  # Payment endpoints
    
    # Exclude paths from rate limiting
    RATE_LIMIT_EXCLUDE_PATHS: Set[str] = Field(
        default={"/health", "/metrics", "/docs", "/redoc"}
    )
    
    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_"
    )

class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    LEVEL: str = Field(default="INFO")
    JSON_LOGS: bool = Field(default=True)
    
    # Log file settings
    LOG_FILE_PATH: Optional[Path] = None
    LOG_ROTATION: str = Field(default="20 MB")
    LOG_RETENTION: str = Field(default="14 days")
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=1.0)
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_"
    )

class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""
    
    # Prometheus
    ENABLE_METRICS: bool = Field(default=True)
    METRICS_PORT: int = Field(default=9090)
    
    # OpenTelemetry
    ENABLE_TRACING: bool = Field(default=True)
    OTEL_SERVICE_NAME: str = Field(default="autoinvest-api")
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    
    # Health checks
    HEALTH_CHECK_INTERVAL: int = Field(default=30)  # seconds
    
    model_config = SettingsConfigDict(
        env_prefix="MONITORING_"
    )

class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    # CORS
    CORS_ORIGINS: List[AnyHttpUrl] = Field(default=[])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"])
    
    # Security Headers
    SECURITY_HEADERS: bool = Field(default=True)
    HSTS_ENABLED: bool = Field(default=True)
    HSTS_MAX_AGE: int = Field(default=31536000)  # 1 year
    
    # SSL/TLS
    SSL_KEYFILE: Optional[Path] = None
    SSL_CERTFILE: Optional[Path] = None
    
    # CSRF
    CSRF_ENABLED: bool = Field(default=True)
    CSRF_SECRET: SecretStr
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_"
    )

class FeatureFlags(BaseSettings):
    """Feature flag configuration."""
    
    # Investment Features
    ENABLE_AUTO_INVEST: bool = Field(default=False)
    ENABLE_MUTUAL_FUNDS: bool = Field(default=True)
    ENABLE_STOCKS: bool = Field(default=False)
    
    # KYC Features
    ENABLE_KYC_FLOW: bool = Field(default=True)
    ENABLE_VIDEO_KYC: bool = Field(default=False)
    ENABLE_AADHAAR_KYC: bool = Field(default=True)
    
    # Payment Features
    ENABLE_UPI: bool = Field(default=True)
    ENABLE_NETBANKING: bool = Field(default=True)
    ENABLE_CARDS: bool = Field(default=True)
    
    # Reports
    ENABLE_PDF_REPORTS: bool = Field(default=True)
    ENABLE_TAX_REPORTS: bool = Field(default=True)
    
    model_config = SettingsConfigDict(
        env_prefix="FEATURE_"
    )

class ThirdPartyConfig(BaseSettings):
    """Third-party service configuration."""
    
    # Razorpay
    RAZORPAY_KEY_ID: SecretStr
    RAZORPAY_KEY_SECRET: SecretStr
    RAZORPAY_WEBHOOK_SECRET: SecretStr
    RAZORPAY_ENVIRONMENT: str = Field(default="test")
    
    # AWS
    AWS_ACCESS_KEY_ID: SecretStr
    AWS_SECRET_ACCESS_KEY: SecretStr
    AWS_REGION: str = Field(default="ap-south-1")
    AWS_S3_BUCKET: str
    
    # SMS Gateway
    SMS_PROVIDER: str = Field(default="twilio")
    SMS_API_KEY: SecretStr
    SMS_SENDER_ID: str
    
    # Email
    SMTP_HOST: str
    SMTP_PORT: int = Field(default=587)
    SMTP_USER: str
    SMTP_PASSWORD: SecretStr
    SMTP_FROM_EMAIL: EmailStr
    
    @field_validator("AWS_REGION")
    @classmethod
    def validate_aws_region(cls, v: str) -> str:
        """Validate AWS region format."""
        valid_regions = {
            "ap-south-1",
            "ap-south-2",
            "ap-southeast-1",
            "ap-southeast-2"
        }
        if v not in valid_regions:
            raise ValueError(f"Invalid AWS region. Must be one of: {valid_regions}")
        return v
    
    model_config = SettingsConfigDict(
        env_prefix="EXTERNAL_"
    )

class AppSettings(BaseSettings):
    """Main settings class combining all configuration sections."""
    
    app: AppConfig = AppConfig()
    db: DatabaseConfig = DatabaseConfig()
    auth: AuthConfig = AuthConfig()
    celery: CeleryConfig = CeleryConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    logging: LoggingConfig = LoggingConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    security: SecurityConfig = SecurityConfig()
    features: FeatureFlags = FeatureFlags()
    external: ThirdPartyConfig = ThirdPartyConfig()
    
    @model_validator(mode="after")
    def validate_production_settings(self) -> "AppSettings":
        """Validate production environment settings."""
        if self.app.is_production:
            assert self.security.HSTS_ENABLED, "HSTS must be enabled in production"
            assert self.security.SSL_CERTFILE, "SSL certificate required in production"
            assert self.logging.SENTRY_DSN, "Sentry DSN required in production"
            assert self.security.CORS_ORIGINS, "CORS origins must be specified in production"
            assert not self.app.DEBUG, "Debug mode must be disabled in production"
        return self
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
        extra="ignore"
    )

@lru_cache()
def get_settings() -> AppSettings:
    """
    Create cached settings instance.
    
    Returns:
        Cached AppSettings instance
    """
    return AppSettings()

# Create global settings instance
settings = get_settings()
