#!/usr/bin/env bash
set -e

echo "==================================================="
echo " CBDT Insight — Isolated Prod VM Deployment Script"
echo "==================================================="

# 0. Check for root privileges (required for system installs)
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root (e.g., sudo ./scripts/deploy_isolated_vm.sh)"
  exit 1
fi

PARAM_FILE="config/parameters.json"

if [ ! -f "$PARAM_FILE" ]; then
    echo "Error: $PARAM_FILE not found!"
    exit 1
fi

echo "1. Installing jq for JSON parsing..."
apt-get update -y && apt-get install -y jq curl wget apt-transport-https software-properties-common

# 1. Parse JSON configurations
echo "2. Parsing configurations from $PARAM_FILE..."
ENV=$(jq -r '.environment' $PARAM_FILE)
REPLICAS=$(jq -r '.deployment.replicas' $PARAM_FILE)
PORT_NODEPORT=$(jq -r '.ports.api_nodeport' $PARAM_FILE)
PORT_SPARK_UI=$(jq -r '.ports.spark_ui' $PARAM_FILE)
PORT_SPARK_HIST=$(jq -r '.ports.spark_history' $PARAM_FILE)
PORT_DYNATRACE=$(jq -r '.ports.dynatrace_activegate' $PARAM_FILE)
PYTHON_VER=$(jq -r '.versions.python_package' $PARAM_FILE)
JAVA_VER=$(jq -r '.versions.java_package' $PARAM_FILE)

echo "-> Environment: $ENV"
echo "-> Expected Replicas: $REPLICAS"
echo "-> NodePort (API): $PORT_NODEPORT"
echo "-> Spark UI Port: $PORT_SPARK_UI"

echo "3. Installing Software & Dependencies..."
# Install Java and Python
add-apt-repository ppa:deadsnakes/ppa -y || true
apt-get update -y
apt-get install -y $JAVA_VER $PYTHON_VER ${PYTHON_VER}-venv ${PYTHON_VER}-dev build-essential gettext-base

# Function to install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "-> Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
else
    echo "-> Docker already installed."
fi

# Function to install Minikube (as local k8s provider)
if ! command -v minikube &> /dev/null; then
    echo "-> Installing Minikube..."
    wget https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
    install minikube-linux-amd64 /usr/local/bin/minikube
    rm minikube-linux-amd64
else
    echo "-> Minikube already installed."
fi

# Function to install kubectl
if ! command -v kubectl &> /dev/null; then
    echo "-> Installing kubectl..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
else
    echo "-> Kubectl already installed."
fi

echo "4. Initializing Kubernetes Cluster (Minikube)..."
# Start minikube for root (docker driver usually complains, so force it or use non-root if executing normally)
minikube start --driver=docker --force

echo "5. Setting up Python Virtual Environment..."
chown -R $SUDO_USER:$SUDO_USER .
su - $SUDO_USER -c "$PYTHON_VER -m venv .venv"
su - $SUDO_USER -c ".venv/bin/pip install --upgrade pip"
su - $SUDO_USER -c ".venv/bin/pip install -r requirements.txt"

echo "6. Running Integration Verification Checks..."
su - $SUDO_USER -c ".venv/bin/python tests/integration/integration_check.py"
echo "-> View detailed test output in tests/integration/integration.log"

echo "7. Building Docker Image directly onto Kubernetes Node..."
# Point docker CLI to minikube's docker daemon
eval $(minikube docker-env)
docker build -t cbdt-insight-api:prod -f docker/Dockerfile.api .

echo "8. Applying K8s Deployments with Dynamic Parameters..."
# We use export + envsubst to dynamically inject parameters into k8s manifests
export REPLICAS=$REPLICAS
export PORT_NODEPORT=$PORT_NODEPORT
export PORT_SPARK_UI=$PORT_SPARK_UI
export PORT_SPARK_HIST=$PORT_SPARK_HIST
export PORT_DYNATRACE=$PORT_DYNATRACE

# We dynamically create a production deployment overlay using envsubst
cat <<EOF > infra/kubernetes/api-deployment-prod.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment-prod
  labels:
    app: cbdt-insight-api-prod
spec:
  replicas: ${REPLICAS}
  selector:
    matchLabels:
      app: cbdt-insight-api-prod
  template:
    metadata:
      labels:
        app: cbdt-insight-api-prod
    spec:
      containers:
      - name: api-container
        image: cbdt-insight-api:prod
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: api
        - containerPort: 4040
          name: spark-ui
        - containerPort: 18080
          name: spark-hist
        - containerPort: 9999
          name: dynatrace
        env:
        - name: APP_ENV
          value: "production"
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
EOF

cat <<EOF > infra/kubernetes/api-service-prod.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-service-prod
  labels:
    app: cbdt-insight-api-prod
spec:
  type: NodePort
  selector:
    app: cbdt-insight-api-prod
  ports:
    - name: api-ext
      protocol: TCP
      port: 8080
      targetPort: 8000
      nodePort: ${PORT_NODEPORT}
    - name: spark-ui-ext
      protocol: TCP
      port: 8081
      targetPort: 4040
      nodePort: 34040
    - name: spark-hist-ext
      protocol: TCP
      port: 8082
      targetPort: 18080
      nodePort: 31808
    - name: dynatrace-ext
      protocol: TCP
      port: 8083
      targetPort: 9999
      nodePort: 30999
EOF

kubectl apply -f infra/kubernetes/api-deployment-prod.yaml
kubectl apply -f infra/kubernetes/api-service-prod.yaml

echo "9. Verification..."
kubectl get all -l app=cbdt-insight-api-prod

echo "==================================================="
echo "✅ Deployment Process Complete!"
echo "Isolated Production Server is Active. Exposed NodePorts:"
echo " - API Dashboard:       $(minikube ip):${PORT_NODEPORT}"
echo " - Spark UI:            $(minikube ip):34040"
echo " - Spark History:       $(minikube ip):31808"
echo " - Dynatrace Trace:     $(minikube ip):30999"
echo "==================================================="
