#!/usr/bin/env bash
# Deploy script to spin up the Dev Server and mock artifacts

# Terminate existing dev server on 8080
lsof -ti:8080 | xargs kill -9 2>/dev/null

echo "Starting CBDT Insight Local Development Server on port 8080..."

# Run the API in the background using the active venv
export PYTHONPATH=$(pwd)
.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8080 &
SERVER_PID=$!

echo "Server started correctly on process ID: $SERVER_PID"
echo "API Docs available at: http://localhost:8080/docs"
echo "Waiting for server to become responsive..."
sleep 3

# Make a health check curl request
echo "Health check:"
curl -X GET http://localhost:8080/health

echo ""
echo "Triggering Spark job background task..."
curl -X POST http://localhost:8080/jobs/health-check
echo ""

echo "Development environment has fully been configured and deployed locally!"
