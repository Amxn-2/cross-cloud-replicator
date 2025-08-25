
# 🌐 Cross-Cloud Event-Driven Storage Replicator

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-S3-orange?logo=amazon-aws)](https://aws.amazon.com/s3/)
[![GCP](https://img.shields.io/badge/GCP-Cloud%20Storage-4285F4?logo=google-cloud)](https://cloud.google.com/storage)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

A production-grade Python service for replicating files from AWS S3 to Google Cloud Storage in an event-driven and scalable manner. Built for high availability, security, and multi-cloud reliability.

---
````
## ⚡ Quick Start (2 Minutes)

git clone <your-repository-url>
cd cross-cloud-replicator
cp .env.example .env
docker-compose up -d
echo "Hello Cloud!" > test.txt
aws s3 cp test.txt s3://your-source-bucket/test.txt
curl -X POST http://localhost:8080/v1/replicate -H "Content-Type: application/json" -d '{"s3_bucket":"your-source-bucket","s3_key":"test.txt"}'
gsutil cat gs://your-target-bucket/test.txt
````


## 🚀 Features

* Event-driven HTTP endpoint to trigger replication
* Chunked streaming for large files
* Exponential backoff retries
* Idempotent uploads with existence checks
* AWS S3 → GCP Cloud Storage
* Dockerized, health checks, structured logging, monitoring-ready
* Environment-based secrets
* Tunable chunk sizes and concurrency

---

## 📑 Table of Contents

* [🏗️ Architecture](#️-architecture)
* [📋 Prerequisites](#-prerequisites)
* [🛠️ Installation](#️-installation)
* [⚙️ Configuration](#️-configuration)
* [🧾 Environment Example (.env.example)](#-environment-example-envexample)
* [🚀 Running the Application](#-running-the-application)
* [🐳 Docker Deployment](#-docker-deployment)
* [❗ Troubleshooting](#-troubleshooting)

---

## 🏗️ Architecture

### System Architecture

![System Architecture](/images/graphTD.png)

### Sequence Flow

![Sequence Diagram](/images/seq.png)

---

## 📋 Prerequisites

<details>
<summary><b>Accounts & Services</b></summary>

* AWS account with S3 access
* Google Cloud project with Cloud Storage enabled
* Python 3.11+
* Docker (optional)

</details>

<details>
<summary><b>IAM Permissions</b></summary>

**AWS (S3 Access Required):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::your-source-bucket",
        "arn:aws:s3:::your-source-bucket/*"
      ]
    }
  ]
}
```

**Google Cloud (GCS Access Required):**

* Storage Object Admin
* (Optional) Storage Legacy Bucket Reader

</details>

---

## 🛠️ Installation

```bash
mkdir project && cd project
git clone <your-repository-url>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration

<details>
<summary><b>1. AWS Credentials</b></summary>

Create an IAM user with programmatic access and attach minimal S3 read permissions, or configure via AWS CLI:

```bash
pip install awscli
aws configure
```

</details>

<details>
<summary><b>2. Google Cloud Credentials</b></summary>

Create a service account with Storage Object Admin, download the JSON key as `gcp-service-account.json`, and secure it:

```bash
chmod 600 ./gcp-service-account.json
```

</details>

<details>
<summary><b>3. Environment Variables</b></summary>

```bash
cp .env.example .env
```

</details>

<details>
<summary><b>4. Create Buckets</b></summary>

```bash
aws s3 mb s3://your-source-bucket
gsutil mb gs://your-target-bucket
```

</details>

---

## 🧾 Environment Example (.env.example)

```bash
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1

GOOGLE_APPLICATION_CREDENTIALS=./gcp-service-account.json
GCP_PROJECT_ID=your-gcp-project-id
TARGET_GCS_BUCKET=your-target-gcs-bucket

HOST=0.0.0.0
PORT=8080
DEBUG=false

MAX_RETRIES=3
RETRY_DELAY=1.0
RETRY_BACKOFF=2.0

CHUNK_SIZE=8192
```

---

## 🚀 Running the Application

### 1. Verify Configuration

```bash
python -c "import boto3; c=boto3.client('s3'); print([b['Name'] for b in c.list_buckets()['Buckets']][:5])"
python -c "from google.cloud import storage; c=storage.Client(); print([b.name for b in list(c.list_buckets())][:5])"
```

### 2. Start Application

```bash
python -m src.app
```

**Production (Gunicorn):**

```bash
gunicorn --bind 0.0.0.0:8080 --workers 4 --timeout 300 "src.app:create_app()"
```

### 3. Health Check

```bash
curl http://localhost:8080/health
```

---

## 🐳 Docker Deployment

```bash
docker build -t crosscloud-replicator .
docker-compose up -d
docker-compose logs -f
docker-compose down
```

**Test Workflow:**

```bash
echo "Hello, World!" > test.txt
aws s3 cp test.txt s3://your-source-bucket/test.txt
curl -X POST http://localhost:8080/v1/replicate -H "Content-Type: application/json" -d '{"s3_bucket":"your-source-bucket","s3_key":"test.txt"}'
gsutil cat gs://your-target-bucket/test.txt
```

---

## ❗ Troubleshooting

* Verify `.env` values
* Confirm IAM roles and permissions in AWS and GCP
* Use the verification commands to test credentials

