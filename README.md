# 🏗️ Enterprise Big Data Platform — CBDT Insight

> **On-prem big data engineering solution for highly secure enterprise environments**
> *(Mimicked insight project — all from memory)*

![Version](https://img.shields.io/badge/version-1.0-blue)
![Status](https://img.shields.io/badge/status-In%20Development-orange)
![Classification](https://img.shields.io/badge/classification-Internal%20Use%20Only-red)
![License](https://img.shields.io/badge/license-Proprietary-lightgrey)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Environment Strategy](#environment-strategy)
- [Data Architecture — Medallion Pattern](#data-architecture--medallion-pattern)
- [High Availability & Disaster Recovery](#high-availability--disaster-recovery)
- [Security & IAM](#security--iam)
- [Monitoring & Observability](#monitoring--observability)
- [Network Architecture](#network-architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Contributing](#contributing)

---

## Overview

CBDT Insight is an **enterprise-grade data platform** designed for organizations requiring strict security, compliance (SOC2 / ISO 27001), and high availability. The platform implements a **Spark Medallion Architecture** (Bronze → Silver → Gold) on top of **Delta Lake**, orchestrated via **Kubernetes**, with full observability through **Dynatrace**.

### Key Objectives

| Objective | Target |
|---|---|
| **Uptime SLA** | 99.99% (≤ 3.6 sec downtime/week) |
| **Recovery Point Objective (RPO)** | 15 minutes |
| **Recovery Time Objective (RTO)** | 1 hour |
| **Compliance** | SOC2, ISO 27001 audit-ready |
| **Environments** | Fully isolated Dev → Test → Prod |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DMZ (10.0.0.0/22)                  │
│                   WAF  ·  Load Balancer  ·  TLS 1.2+               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐   ┌──────────────────────────────────────────┐   │
│  │  BASTION HOST │   │        APPLICATION ZONE (10.0.5.0/24)    │   │
│  │ (10.0.4.0/25)│──▶│  Kubernetes Cluster (3+ CP, 5+ Workers)  │   │
│  │  SSH + PAM   │   │  ┌────────┐ ┌────────┐ ┌────────┐       │   │
│  └──────────────┘   │  │ Spark  │ │  API   │ │ CI/CD  │       │   │
│                      │  │ Jobs   │ │Services│ │Jenkins │       │   │
│                      │  └───┬────┘ └───┬────┘ └────────┘       │   │
│                      └─────┼──────────┼────────────────────────┘   │
│                            │          │                             │
│  ┌─────────────────────────▼──────────▼────────────────────────┐   │
│  │              DATA ZONE (10.0.6.0/24) — Encrypted            │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌───────────────────────┐  │   │
│  │  │PostgreSQL│  │ S3-Compatible│  │     Delta Lake         │  │   │
│  │  │HA Primary│  │ Object Store │  │ Bronze→Silver→Gold     │  │   │
│  │  │+ Standby │  │ (3x Replicas)│  │ (ACID Transactions)   │  │   │
│  │  └──────────┘  └──────────────┘  └───────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           MONITORING ZONE (10.0.7.0/25) — Isolated          │   │
│  │           Dynatrace  ·  Fluent-bit  ·  Alerting             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Infrastructure

| Component | Tool | Version | Purpose |
|---|---|---|---|
| Containerization | Docker | 20.10+ | Package apps with dependencies |
| Orchestration | Kubernetes | 1.28+ | Manage containers at scale |
| Compute Engine | Apache Spark | 3.5+ | Distributed data processing |
| Data Lake Format | Delta Lake | 3.0+ | ACID transactions on data lake |
| Object Storage | S3-compatible | API v4 | Distributed immutable storage |
| Version Control | Git | 2.40+ | Code and config management |
| CI/CD | Jenkins HA | 2.387+ | Build, test, deploy pipelines |
| Secrets Management | CyberArk PAM | Latest | Privileged access & credential management |
| Monitoring | Dynatrace | Latest | APM & infrastructure monitoring |

### Programming Languages

| Language | Version | Use Case |
|---|---|---|
| Python | 3.10+ | Data processing, Spark jobs, orchestration |
| SQL | ANSI SQL-2016 | Data querying, ETL transformations |
| Bash | 4.0+ (POSIX) | Infrastructure scripts, CI/CD pipelines |

### Python Libraries

| Library | Version | Function |
|---|---|---|
| `pyspark` | 3.5+ | Spark API in Python |
| `delta-spark` | 3.0+ | Delta Lake ACID operations |
| `boto3` | 1.26+ | S3-compatible storage SDK |
| `great_expectations` | 0.17+ | Data quality validation framework |

---

## Environment Strategy

The platform enforces **strict environment isolation** with a unidirectional promotion model:

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│   DEV    │────▶│   TEST   │────▶│  PRODUCTION  │
│          │     │          │     │              │
│ Isolated │     │ Pre-prod │     │ HA/DR Config │
│ VM       │     │ Parity   │     │ Multi-AZ     │
└──────────┘     └──────────┘     └──────────────┘
     ❌ No backflow from Prod to Dev
```

### Promotion Gates

| Transition | Required Approvals | Automated Checks |
|---|---|---|
| Dev → Test | Developer + Peer Review | Unit tests, linting, security scan |
| Test → Prod | Lead + QA + Ops | Integration tests, perf benchmarks, DR validation |
| Emergency Patch | 2 of 3: Lead + Ops + Manager | Same as Test→Prod (accelerated) |

### Environment Isolation Rules

- **Separate credentials** per environment (service accounts, DB passwords, SSH keys, API tokens)
- **Isolated network subnets** — no cross-environment traffic
- **Dedicated Kubernetes clusters** for production; Dev/Test may share with strict namespace isolation

| Property | Development | Test | Production |
|---|---|---|---|
| Control Plane Nodes | 1 (non-HA) | 1 (non-HA) | 3+ (etcd quorum) |
| Worker Nodes (min) | 2 | 3 | 5+ |
| Cluster Sharing | Combined with Test | Shared with Dev | **Dedicated only** |
| Network Policy | Namespace isolation | Namespace isolation | Fine-grained RBAC + NetworkPolicy |

---

## Data Architecture — Medallion Pattern

Data flows through three progressively refined layers:

```
  ┌─────────────────────────────────────────────────────┐
  │                   SOURCE SYSTEMS                     │
  └───────────┬─────────────────────────────────────────┘
              │
              ▼
  ┌─────────────────────┐
  │   🥉 BRONZE LAYER   │  Raw, immutable ingestion
  │   (Append-only)      │  • No transformation
  │   AES-256 encrypted  │  • Explicit schema on read
  │   90-day retention   │  • Partitioned by load_date
  └──────────┬──────────┘
             │
             ▼
  ┌─────────────────────┐
  │   🥈 SILVER LAYER   │  Cleaned & validated
  │   (Business logic)   │  • Deduplication
  │   PII masked         │  • PII masking (SHA-256)
  │   Great Expectations │  • Surrogate key generation
  └──────────┬──────────┘  • Rejects quarantined
             │
             ▼
  ┌─────────────────────┐
  │   🥇 GOLD LAYER     │  Business-ready aggregates
  │   (Curated)          │  • Fact & Dimension tables
  │   Column-encrypted   │  • Pre-aggregated cubes
  │   RBAC-restricted    │  • Optimized for analytics
  └─────────────────────┘
```

### Spark Configuration

```properties
spark.dynamicAllocation.enabled       = true
spark.dynamicAllocation.minExecutors  = 2
spark.dynamicAllocation.maxExecutors  = 50
spark.dynamicAllocation.executorIdleTimeout = 60s
```

---

## High Availability & Disaster Recovery

### HA Strategy

| Strategy | Mechanism | Use Case |
|---|---|---|
| Rolling Deployment | Sequential pod replacement | Non-breaking changes (default) |
| Blue/Green | Two full versions, switch traffic | High-risk changes, instant rollback |
| Canary | 5–10% traffic to new version | Error monitoring, gradual ramp-up |

### Multi-AZ Distribution

| Component | Requirement | Rationale |
|---|---|---|
| Kubernetes nodes | Distributed across 3 AZs | Survive 1 full AZ failure |
| Database replicas | Primary AZ-1, replicas AZ-2 & AZ-3 | Active-passive auto-failover |
| Object storage | 3-way replication, regional bucket | Erasure coding (10× fault tolerance) |

### Database HA

| Topology | Description | RPO / RTO |
|---|---|---|
| Primary-Standby (Sync) | Writes wait for standby ACK | **RPO = 0** (no data loss), RTO = 30 sec |
| Primary-Standby (Async) | Writes confirmed on primary | RPO < 1 sec, RTO = 30 sec |

### Disaster Recovery

| DR Aspect | Specification |
|---|---|
| **Backup cadence** | Daily snapshots (35-day retention) + incremental every 4 hours |
| **Encryption** | AES-256 at rest, TLS in transit |
| **Immutability** | WORM — backups cannot be modified/deleted within retention window |
| **Cross-region** | Primary (Region-1), Standby (Region-2, >100 km), Archive (Region-3, >500 km) |
| **DR drills** | Quarterly — simulate full data center failure |

---

## Security & IAM

### Core Principles

| Principle | Implementation |
|---|---|
| **Least Privilege** | Deny by default, explicitly allow |
| **Separation of Duties** | Approval chain: peer review → lead → ops |
| **Privilege Escalation** | Request via CyberArk PAM + Jira approval + auto-expire |

### RBAC Model

| Role | Permissions | Environments |
|---|---|---|
| Developer | Read/Write code, Deploy to Dev/Test | Dev, Test |
| SRE | Deploy to Prod, modify configs, SSH Bastion | All |
| Data Engineer | Deploy Spark jobs, modify Bronze/Silver | Dev, Test, Prod (read-only Gold) |
| DBA | Database admin, backups, failover | All |
| Analyst | Read Gold tables only | Prod (read-only) |

### MFA Requirements

| Access Type | MFA Method | Requirement |
|---|---|---|
| SSH to Bastion | TOTP + SSH key | Mandatory |
| Console Login | TOTP or Yubikey | Mandatory |
| Git commit signing | GPG key | Prod changes only |
| CyberArk PAM session | LDAP + TOTP | Every interaction |

### Threat Modeling (STRIDE)

| Threat | Likelihood | Impact | Key Mitigation |
|---|---|---|---|
| Spoofing | Medium | Critical | MFA, mTLS, strong auth |
| Tampering | Low | Critical | Encryption, audit logs, RBAC |
| Repudiation | Medium | High | Immutable audit logs, signatures |
| Info Disclosure | Medium | Critical | Encryption, access control, masking |
| DoS | High | High | Rate limiting, autoscaling, WAF |
| Privilege Escalation | Low | Critical | Least privilege, PAM, monitoring |

---

## Monitoring & Observability

All monitoring flows through **Dynatrace** (deployed in an isolated observability zone).

### Metrics Collection

| Category | Examples | Interval |
|---|---|---|
| Node CPU | Usage %, context switches, load avg | 10 sec |
| Node Memory | Used/Available GB, swap, OOM kills | 10 sec |
| JVM (Spark) | Heap, GC pauses, thread count | 30 sec |
| Kubernetes | Pod restarts, node status, API latency | 30 sec |
| Application | Request/error rate, latency p50/p95/p99 | 1 min |

### Alert Severity Mapping

| Condition | Severity | Action |
|---|---|---|
| CPU > 80% for 5 min | ⚠️ Warning | Page on-call, trigger autoscale |
| Memory > 90% for 2 min | 🔴 Critical | Page critical, drain node |
| Pod restarts > 3 in 1h | ⚠️ Warning | Investigate crash logs |
| DB replication lag > 10s | 🔴 Critical | Page DBAs, check network |
| Request latency p99 > 5s | ⚠️ Warning | Review slow query logs |

### Log Management

| Level | Retention |
|---|---|
| DEBUG | 7 days |
| INFO | 30 days |
| WARN | 90 days |
| ERROR | 1 year (with sampling) |
| CRITICAL | 2 years (immutable) |

---

## Network Architecture

### Security Zones

| Zone | Purpose | CIDR |
|---|---|---|
| External DMZ | Public-facing LB, WAF | `10.0.0.0/22` |
| Bastion Host | SSH jump server for Ops | `10.0.4.0/25` |
| Application Zone | API services, microservices | `10.0.5.0/24` |
| Data Zone | Databases, object storage | `10.0.6.0/24` |
| Monitoring Zone | Dynatrace, alerting, logging | `10.0.7.0/25` |
| CI/CD Zone | Jenkins, artifact repo, GitLab | `10.0.7.128/25` |

### TLS & Mutual TLS

| Communication Type | Protocol | Certificate Authority |
|---|---|---|
| Service-to-Service | TLS 1.3 + mTLS | Internal CA (CyberArk PKI) |
| Client-to-LB | TLS 1.2+ | Public CA (Let's Encrypt / DigiCert) |
| Database Connection | TLS 1.2+ | CyberArk CA or DB native certs |

### Firewall Policy

- **Default deny** — all traffic blocked unless explicitly allowed
- **Dev → Prod: DENIED** — prevents credential leakage from compromising production
- All allow/deny decisions logged with timestamp, source IP, destination, port, protocol, and action
- Logs archived for **1 year**

---

## Project Structure

```
cbdt-insight/
├── README.md                          # This file
├── docs/
│   └── requirements/
│       └── Enterprise_Data_Platform_Technical_Requirements.docx
├── src/                               # Application source code (planned)
│   ├── ingestion/                     # Bronze layer ingestion jobs
│   ├── transformation/                # Silver layer cleaning & validation
│   ├── aggregation/                   # Gold layer curated aggregates
│   └── common/                        # Shared utilities & configs
├── infra/                             # Infrastructure-as-Code (planned)
│   ├── kubernetes/                    # K8s manifests & Helm charts
│   ├── docker/                        # Dockerfiles
│   └── terraform/                     # IaC for cloud/on-prem provisioning
├── pipelines/                         # CI/CD pipeline definitions (planned)
├── tests/                             # Unit & integration tests (planned)
└── runbooks/                          # DR playbooks & operational docs (planned)
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Docker 20.10+
- Kubernetes 1.28+ (or Minikube for local dev)
- Apache Spark 3.5+
- CyberArk PAM (Privileged Access Manager)
- Git 2.40+

### Clone the Repository

```bash
git clone https://github.com/datawarior-06/enterprise-big-data.git
cd enterprise-big-data
```

### Set Up Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyspark delta-spark boto3 great_expectations
```

---

## Contributing

1. **Branch** off `main` with a descriptive name (`feature/bronze-ingestion`)
2. **Follow** the Dev → Test → Prod promotion model
3. **All commits** must pass: unit tests, linting, and security scans
4. **Prod changes** require GPG-signed commits
5. **Submit a PR** with peer review before merging

---

## Next Steps (Roadmap)

| Phase | Milestone | Timeline |
|---|---|---|
| 1 | Architecture review & approval | Month 1 |
| 2 | Detailed implementation roadmap (12-month plan) | Month 1–2 |
| 3 | Infrastructure provisioning (K8s, CyberArk PAM, Dynatrace) | Month 2–4 |
| 4 | Bronze layer ingestion pipelines | Month 3–5 |
| 5 | Silver layer transformation & data quality | Month 5–7 |
| 6 | Gold layer aggregates & BI integration | Month 7–9 |
| 7 | DR runbooks & quarterly drill schedule | Month 9–10 |
| 8 | Monitoring baselines & SLA target establishment | Month 10–11 |
| 9 | SOC2 / ISO 27001 audit readiness review | Month 11–12 |

---

<p align="center">
  <b>Version 1.0</b> · March 2025 · Internal Use Only<br>
  Enterprise Data Platform — CBDT Insight
</p>
