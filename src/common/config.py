"""
CBDT Insight — Configuration Manager
Centralises all application configuration with environment-based overrides.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env file (if present) for local development
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Data class based configuration
# ---------------------------------------------------------------------------
@dataclass
class SparkConfig:
    """Spark cluster & session settings."""
    app_name: str = "cbdt-insight"
    master: str = "local[*]"
    executor_memory: str = "2g"
    driver_memory: str = "1g"
    dynamic_allocation: bool = True
    min_executors: int = 2
    max_executors: int = 50
    executor_idle_timeout: str = "60s"
    delta_extensions: str = "io.delta.sql.DeltaSparkSessionExtension"
    delta_catalog: str = "org.apache.spark.sql.delta.catalog.DeltaCatalog"


@dataclass
class StorageConfig:
    """S3 / Object Storage settings."""
    endpoint: str = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    access_key: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    secret_key: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    region: str = os.getenv("S3_REGION", "us-east-1")
    bronze_bucket: str = os.getenv("S3_BRONZE_BUCKET", "bronze")
    silver_bucket: str = os.getenv("S3_SILVER_BUCKET", "silver")
    gold_bucket: str = os.getenv("S3_GOLD_BUCKET", "gold")


@dataclass
class SecretsConfig:
    """CyberArk PAM settings."""
    app_id: str = os.getenv("CYBERARK_APP_ID", "cbdt-insight-dev")
    base_url: str = os.getenv("CYBERARK_BASE_URL", "https://cyberark.local")
    safe: str = os.getenv("CYBERARK_SAFE", "DEV-Safe")
    verify_ssl: bool = os.getenv("CYBERARK_VERIFY_SSL", "false").lower() == "true"


@dataclass
class MonitoringConfig:
    """Dynatrace monitoring settings."""
    api_url: str = os.getenv("DYNATRACE_API_URL", "https://dynatrace.local/api")
    api_token: str = os.getenv("DYNATRACE_API_TOKEN", "")
    environment_id: str = os.getenv("DYNATRACE_ENV_ID", "dev")


@dataclass
class ServerConfig:
    """FastAPI dev server settings."""
    host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    port: int = int(os.getenv("SERVER_PORT", "8000"))
    reload: bool = os.getenv("SERVER_RELOAD", "true").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "info")


@dataclass
class AppConfig:
    """Master configuration container."""
    environment: str = os.getenv("APP_ENV", "development")
    project_root: Path = _PROJECT_ROOT
    spark: SparkConfig = field(default_factory=SparkConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    secrets: SecretsConfig = field(default_factory=SecretsConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def from_yaml(cls, path: Optional[str] = None) -> "AppConfig":
        """Load configuration from a YAML file with env overrides."""
        if path is None:
            path = os.getenv("CONFIG_PATH", str(_PROJECT_ROOT / "config" / "settings.yaml"))
        cfg = cls()
        config_file = Path(path)
        if config_file.exists():
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
            # Apply YAML values (env vars still take priority via dataclass defaults)
            if "spark" in data:
                for k, v in data["spark"].items():
                    if hasattr(cfg.spark, k):
                        setattr(cfg.spark, k, v)
            if "storage" in data:
                for k, v in data["storage"].items():
                    if hasattr(cfg.storage, k):
                        setattr(cfg.storage, k, v)
        return cfg


# ---------------------------------------------------------------------------
# Singleton access
# ---------------------------------------------------------------------------
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Return the singleton AppConfig instance."""
    global _config
    if _config is None:
        _config = AppConfig.from_yaml()
    return _config
