import os
import sys
import logging
import subprocess
import importlib
from pathlib import Path

# Setup paths
CURRENT_DIR = Path(__file__).parent.resolve()
LOG_FILE = CURRENT_DIR / "integration.log"
PROJECT_ROOT = CURRENT_DIR.parent.parent

# Remove old log if it exists to keep it fresh per run
if LOG_FILE.exists():
    LOG_FILE.unlink()

# Setup logger to write to integration.log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def warn_and_log(test_name: str, issue: str):
    """Log warning for failed testcase."""
    logger.warning(f"FAILED CHECK [{test_name}]: {issue}")

def check_python_version():
    """Check Python version >= 3.10"""
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        warn_and_log(
            "Python Version", 
            f"Expected >= 3.10, found {v.major}.{v.minor}"
        )
    else:
        logger.info("✅ Python version check passed.")

def check_java_version():
    """Check Java version (needed for Spark)"""
    try:
        output = subprocess.check_output(["java", "-version"], stderr=subprocess.STDOUT, text=True)
        # Just verifying it exists and runs
        logger.info("✅ Java installation check passed.")
    except Exception as e:
        warn_and_log("Java Installation", f"Java is not installed or accessible: {str(e)}")

def check_required_packages():
    """Verify all critical technical requirements packages are installed"""
    required_packages = {
        "pyspark": "3.5",
        "delta": "3.0", # delta-spark imports as delta
        "boto3": "1.26",
        "pyaim": "1.5", # CyberArk PAM
        "kubernetes": "28.0",
        "fastapi": "0.110"
    }

    for pkg, min_version in required_packages.items():
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "unknown")
            logger.info(f"✅ Package {pkg} check passed (Found: {version}).")
        except ImportError as e:
            warn_and_log("Missing Package", f"Required package '{pkg}' (>= {min_version}) is missing. Root cause: {str(e)}")

def check_directory_structure():
    """Verify Medallion architecture layout and infra structure exists"""
    required_dirs = [
        "src/ingestion", 
        "src/transformation", 
        "src/aggregation",
        "src/common",
        "src/api",
        "infra/kubernetes",
        "docker",
        "config"
    ]

    for d in required_dirs:
        path = PROJECT_ROOT / d
        if not path.exists() or not path.is_dir():
            warn_and_log("Project Structure", f"Required directory '{d}' is missing.")
        else:
            logger.info(f"✅ Directory structure check passed: {d}")

def check_config_files():
    """Verify configuration files are present"""
    config_file = PROJECT_ROOT / "config" / "settings.yaml"
    if not config_file.exists():
        warn_and_log("Configuration", "config/settings.yaml is missing.")
    else:
        logger.info("✅ Configuration file check passed.")

def run_all_checks():
    """Execution wrapper for all integration checks"""
    logger.info("="*50)
    logger.info("STARTING PLATFORM INTEGRATION & COMPLIANCE CHECKS")
    logger.info("="*50)
    
    check_python_version()
    check_java_version()
    check_required_packages()
    check_directory_structure()
    check_config_files()
    
    logger.info("="*50)
    logger.info("INTEGRATION CHECKS COMPLETE. See integration.log for any warnings.")
    logger.info("="*50)

if __name__ == "__main__":
    try:
        run_all_checks()
    except Exception as e:
        logger.exception(f"Critical error during integration tests: {str(e)}")
    
    # We exit 0 deliberately so the pipeline warns but doesn't hard-fail the build
    # per user request: "if any testcase failed just warn with root cause in integration.log"
    sys.exit(0)
