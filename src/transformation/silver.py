"""
CBDT Insight — Silver Layer Transformation
Clean, deduplicate, and validate data.
"""

from src.common.spark import get_spark_session
from src.common.config import get_config
from pyspark.sql.functions import row_number, col
from pyspark.sql.window import Window

def transform_to_silver(table_name: str, key_column: str) -> None:
    """Read from Bronze, deduplicate, and write to Silver Delta path."""
    spark = get_spark_session()
    cfg = get_config()

    print(f"[Silver] Transforming {table_name}...")
    
    input_path = f"s3a://{cfg.storage.bronze_bucket}/{table_name}"
    output_path = f"s3a://{cfg.storage.silver_bucket}/{table_name}"
    
    # Read Bronze
    df = spark.read.format("delta").load(input_path)
    
    # Simple Deduplication via Window Function
    windowSpec = Window.partitionBy(key_column).orderBy("load_date")
    dedup_df = (df.withColumn("rn", row_number().over(windowSpec))
                  .filter(col("rn") == 1)
                  .drop("rn"))
    
    # Write to Silver (Overwrite for simplicity in this stub)
    (dedup_df.write
       .mode("overwrite")
       .format("delta")
       .save(output_path))
       
    print(f"[Silver] Success for {table_name}")
