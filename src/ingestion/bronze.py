"""
CBDT Insight — Bronze Layer Ingestion
Extract raw data into a Delta Lake Bronze layer.
"""

from src.common.spark import get_spark_session
from src.common.config import get_config

def ingest_bronze(source_path: str, table_name: str) -> None:
    """Read a JSON source and write to Bronze Delta path."""
    spark = get_spark_session()
    cfg = get_config()

    print(f"[Bronze] Ingesting {source_path} to Bronze layer: {table_name}...")

    # Dummy Bronze append
    df = spark.read.json(source_path)
    output_path = f"s3a://{cfg.storage.bronze_bucket}/{table_name}"
    
    (df.write
       .mode('append')
       .format('delta')
       .option('delta.logRetentionDuration', '90 day')
       .save(output_path))
    
    print(f"[Bronze] Success for {table_name}")

if __name__ == "__main__":
    # Example local run
    # ingest_bronze("data/raw/customers.json", "customers")
    pass
