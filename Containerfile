# Containerfile — Podman-compatible multi-stage build
# Stage 1: Builder
FROM registry.access.redhat.com/ubi9/python-311:latest AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --target /install -r requirements.txt

# Stage 2: Runtime
FROM registry.access.redhat.com/ubi9/ubi:latest AS runtime
LABEL maintainer="data-engineering@company.com"
LABEL version="1.0.0"

# ── System packages (JDK 21, wget, curl)
RUN dnf install -y java-21-openjdk-headless wget curl procps && dnf clean all

# ── Environment
ENV JAVA_HOME=/usr/lib/jvm/jre-21-openjdk
ENV SPARK_VERSION=3.5.1
ENV SPARK_HOME=/opt/spark
ENV DELTA_VERSION=3.2.0
ENV PATH=$SPARK_HOME/bin:$JAVA_HOME/bin:$PATH
ENV PYSPARK_PYTHON=python3
ENV PYTHONPATH=/opt/pipeline

# ── Apache Spark
RUN wget -q https://downloads.apache.org/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz \
    -O /tmp/spark.tgz && tar -xzf /tmp/spark.tgz -C /opt/ && \
    ln -s /opt/spark-${SPARK_VERSION}-bin-hadoop3 /opt/spark && rm /tmp/spark.tgz

# ── JARs: Delta Lake, S3A, PostgreSQL JDBC
RUN wget -q https://repo1.maven.org/maven2/io/delta/delta-spark_2.12/${DELTA_VERSION}/delta-spark_2.12-${DELTA_VERSION}.jar -P $SPARK_HOME/jars/ && \
    wget -q https://repo1.maven.org/maven2/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar -P $SPARK_HOME/jars/ && \
    wget -q https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar -P $SPARK_HOME/jars/ && \
    wget -q https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar -P $SPARK_HOME/jars/ && \
    wget -q https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar -P $SPARK_HOME/jars/

# ── Python packages
COPY --from=builder /install /install
ENV PYTHONPATH=$PYTHONPATH:/install

# ── Pipeline source
COPY _commons/   /opt/pipeline/_commons/
COPY config/     /opt/pipeline/config/
COPY logs/       /opt/pipeline/logs/
COPY vault/      /opt/pipeline/vault/
COPY module1/    /opt/pipeline/module1/
COPY module2/    /opt/pipeline/module2/
COPY module3/    /opt/pipeline/module3/
COPY main.py     /opt/pipeline/main.py

# ── Spark config
COPY config/spark_defaults.conf $SPARK_HOME/conf/spark-defaults.conf
COPY config/log4j2.properties   $SPARK_HOME/conf/log4j2.properties

# ── Dynatrace OneAgent (injected via volume at runtime)
ENV LD_PRELOAD=/opt/dynatrace/oneagent/agent/lib64/liboneagentproc.so

WORKDIR /opt/pipeline
CMD ["spark-submit", "--master", "local[*]", "main.py"]
