"""
CBDT Insight — FastAPI Developer Dashboard & Orchestrator
"""

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.common.config import get_config
from src.common.spark import get_spark_session

app = FastAPI(
    title="CBDT Insight API",
    description="Development and Orchestration API for the Medallion Data Platform",
    version="1.0.0",
)

class JobResponse(BaseModel):
    job_name: str
    status: str
    message: str

@app.get("/health")
def read_health():
    """Health check endpoint."""
    return {"status": "ok", "environment": get_config().environment}

@app.get("/config")
def read_config():
    """View current active configuration."""
    cfg = get_config()
    return {
        "spark_master": cfg.spark.master,
        "storage_endpoint": cfg.storage.endpoint,
        "cyberark_url": cfg.secrets.base_url,
    }

def run_spark_health_check():
    """Trigger a local spark job in the background."""
    spark = get_spark_session()
    df = spark.range(100)
    count = df.count()
    print(f"Spark Health Check Default Count: {count}")

@app.post("/jobs/health-check", response_model=JobResponse)
def trigger_health_check(background_tasks: BackgroundTasks):
    """Trigger a background spark health check."""
    background_tasks.add_task(run_spark_health_check)
    return JobResponse(
        job_name="spark_health_check",
        status="triggered",
        message="Background Spark health check submitted."
    )

if __name__ == "__main__":
    import uvicorn
    cfg = get_config()
    uvicorn.run("src.api.main:app", host=cfg.server.host, port=cfg.server.port, reload=cfg.server.reload)
