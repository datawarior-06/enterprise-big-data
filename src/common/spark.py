"""
CBDT Insight — Spark Session Management
"""

from typing import Optional
from pyspark.sql import SparkSession
from src.common.config import get_config

_spark: Optional[SparkSession] = None

def get_spark_session() -> SparkSession:
    """Initialize and retrieve the SparkSession."""
    global _spark
    if _spark is None:
        cfg = get_config().spark
        builder = (
            SparkSession.builder
            .appName(cfg.app_name)
            .master(cfg.master)
            .config("spark.executor.memory", cfg.executor_memory)
            .config("spark.driver.memory", cfg.driver_memory)
            .config("spark.sql.extensions", cfg.delta_extensions)
            .config("spark.sql.catalog.spark_catalog", cfg.delta_catalog)
        )
        _spark = builder.getOrCreate()
        _spark.sparkContext.setLogLevel("WARN")
    return _spark

def stop_spark_session() -> None:
    """Stop the global Spark session if active."""
    global _spark
    if _spark is not None:
        _spark.stop()
        _spark = None
