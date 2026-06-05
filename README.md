# EcoWaste Sorting Assistant

EcoWaste Sorting Assistant is a secure cloud-based AI SaaS prototype for waste-object detection and recycling guidance. The system uses a custom YOLO model trained on TACO-style waste images (`best.pt`) to detect waste objects such as cans, plastic items, paper/carton, cups, foam/styrofoam, and other litter. It then combines rule-based EcoWaste recommendations with a BitNet LLM interpretation layer to provide user-friendly waste sorting guidance.

The prototype is designed to run on a Debian 12 Google Cloud VM using Docker Compose. It includes FastAPI, a custom YOLO image inference service, Microsoft BitNet LLM inference, PostgreSQL request history, Firebase Authentication, Firestore storage, RabbitMQ post-processing, Prometheus/Grafana monitoring, security hardening, and a complete test suite.

---

## 1. What the system does

The main product workflow is:

```text
User uploads a waste image
        ↓
Firebase Authentication verifies the user
        ↓
FastAPI receives the request
        ↓
Custom YOLO model (`models/yolo/best.pt`) detects waste objects
        ↓
Raw request and output are stored in PostgreSQL and Firestore
        ↓
RabbitMQ sends the detection output to a worker
        ↓
The worker applies EcoWaste sorting rules
        ↓
BitNet interprets the YOLO + rule-based output in natural language
        ↓
The final post-processed result is stored in Firestore
        ↓
Prometheus and Grafana monitor the API
```

Example output:

```json
{
  "model": "ecowaste-yolo-taco-best",
  "predictions": [
    {
      "label": "can",
      "confidence": 0.99,
      "bbox": {
        "x1": 1665.82,
        "y1": 1048.27,
        "x2": 2346.98,
        "y2": 2247.62
      }
    }
  ],
  "firebase_output_id": "...",
  "postprocess_job_id": "..."
}
```

The post-processing result includes:

```json
{
  "processed_output": {
    "type": "ecowaste_image_postprocessing",
    "label_counts": {
      "can": 2,
      "other_litter": 1
    },
    "ecowaste_recommendations": [
      {
        "label": "can",
        "waste_category": "metal_recyclable",
        "recommended_bin": "metal recycling bin",
        "handling_note": "Empty and rinse cans before recycling."
      }
    ],
    "bitnet_interpretation": "The image contains two cans that should be placed in the metal recycling bin if empty and clean. One uncertain item should be manually reviewed.",
    "interpretation_model": "bitnet-b1.58-2B-4T"
  }
}
```

---

## 2. Main technologies

- **Google Cloud Compute Engine** — Debian 12 VM deployment
- **Docker and Docker Compose** — service orchestration
- **FastAPI** — REST API
- **Ultralytics YOLO** — custom EcoWaste object detection using `best.pt`
- **Microsoft BitNet / bitnet.cpp** — CPU-based LLM interpretation service
- **PostgreSQL** — request history and audit log
- **Firebase Authentication** — protected API access with Firebase ID tokens
- **Firebase Firestore** — model outputs and post-processed results
- **RabbitMQ** — asynchronous post-processing queue
- **Prometheus** — API metrics collection
- **Grafana** — monitoring dashboard
- **pytest + pytest-cov** — complete test suite and coverage

---

## 3. Repository structure

```text
ai-saas-gcp/
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── database.py
│   ├── models.py
│   ├── crud.py
│   ├── monitoring.py
│   ├── security.py
│   ├── worker.py
│   └── services/
│       ├── auth.py
│       ├── ecowaste_llm.py
│       ├── ecowaste_rules.py
│       ├── firebase_store.py
│       ├── inference.py
│       ├── llm_client.py
│       ├── postprocess.py
│       └── rabbitmq_client.py
├── docs/
│   ├── cost_estimation.md
│   ├── monitoring.md
│   ├── product_scenario.md
│   ├── security.md
│   └── testing.md
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
├── scripts/
│   ├── cost_estimator.py
│   └── run_tests.sh
├── tests/
├── Dockerfile
├── Dockerfile.bitnet
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── .env.example
└── README.txt
```

The custom YOLO model is expected at:

```text
models/yolo/best.pt
```

The `models/` directory is intentionally ignored by Git because model files are large binary artifacts.

---

## 4. Requirements

Recommended VM specification:

```text
OS: Debian 12
CPU: 4 vCPU
RAM: 16 GB
Disk: 80 GB or more
GPU: Not required
```

Required software:

```bash
sudo apt update
sudo apt install -y git curl jq file python3 python3-pip python3-venv
```

Docker and Docker Compose plugin must also be installed.

Check Docker:

```bash
docker --version
docker compose version
```

---

## 5. Firebase and GCP requirements

Before running the system, prepare Firebase:

1. Open Firebase Console.
2. Attach Firebase to the existing Google Cloud project.
3. Enable **Firestore Database**.
4. Enable **Firebase Authentication**.
5. Enable **Email/Password** sign-in provider.
6. Create a test user.
7. Create/register a Firebase Web App to obtain the **Web API Key**.

The GCP VM service account must have Firestore access. The recommended role is:

```text
Cloud Datastore User
```

The VM should also have sufficient OAuth access scope, preferably:

```text
https://www.googleapis.com/auth/cloud-platform
```

This project uses Google Application Default Credentials from the VM. No Firebase service account JSON file is required.

---

## 6. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/ai-saas-gcp.git
cd ai-saas-gcp
```

Replace `YOUR_USERNAME` with the GitHub account or organization name.

---

## 7. Add the custom YOLO model

Create the model directory:

```bash
mkdir -p models/yolo
```

Copy your trained model into the project:

```bash
cp /path/to/best.pt models/yolo/best.pt
```

Example if the model was uploaded to the VM home directory:

```bash
cp ~/best.pt models/yolo/best.pt
chmod 644 models/yolo/best.pt
```

Check that the model exists:

```bash
ls -lh models/yolo/best.pt
```

---

## 8. Configure environment variables

Create `.env` from the example:

```bash
cp .env.example .env
nano .env
```

Minimum required values:

```env
FIREBASE_PROJECT_ID=your-gcp-project-id
FIREBASE_WEB_API_KEY=your-firebase-web-api-key
FIREBASE_OUTPUT_COLLECTION=model_outputs
FIREBASE_POSTPROCESS_COLLECTION=postprocessed_outputs

POSTGRES_USER=ai_user
POSTGRES_PASSWORD=change-this-postgres-password
POSTGRES_DB=ai_saas

RABBITMQ_DEFAULT_USER=ai_user
RABBITMQ_DEFAULT_PASS=change-this-rabbitmq-password
RABBITMQ_QUEUE=postprocess_jobs

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change-this-grafana-password

YOLO_MODEL_PATH=/app/models/yolo/best.pt
YOLO_DISPLAY_NAME=ecowaste-yolo-taco-best
YOLO_CONF_THRESHOLD=0.30
YOLO_IMAGE_SIZE=640

ENABLE_BITNET_IMAGE_INTERPRETATION=true

ALLOWED_HOSTS=localhost,127.0.0.1,api,testserver
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
MAX_REQUEST_BYTES=10485760
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
ALLOWED_IMAGE_CONTENT_TYPES=image/jpeg,image/png,image/webp
```

Do not commit `.env` to GitHub.

---

## 9. Build the system

```bash
docker compose build
```

The BitNet image may take a long time to build because it downloads the model and compiles the inference server.

---

## 10. Run the system

```bash
docker compose up -d
```

Check services:

```bash
docker compose ps
```

Expected services:

```text
ai-saas-api
ai-saas-worker
ai-saas-bitnet
ai-saas-postgres
ai-saas-rabbitmq
ai-saas-prometheus
ai-saas-grafana
```

Health check:

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected output:

```json
{
  "status": "ok",
  "service": "ai-saas-api",
  "version": "1.0.0"
}
```

---

## 11. Get a Firebase ID token

Set environment variables:

```bash
set -a
source .env
set +a
```

Login with a Firebase test user:

```bash
curl -s -X POST \
  "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${FIREBASE_WEB_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "TestPassword123!",
    "returnSecureToken": true
  }' | tee firebase-login-response.json | python3 -m json.tool
```

Store the ID token:

```bash
TOKEN=$(cat firebase-login-response.json | jq -r '.idToken')
echo ${#TOKEN}
```

If the output is a long number such as `900+`, the token is ready.

Test authentication:

```bash
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

Firebase ID tokens expire. To get a new token, run the login command again.

---

## 12. Test the image endpoint

Use any waste image uploaded to the VM. Example:

```bash
IMG="$HOME/67_000088.JPG"
MIME=$(file --mime-type -b "$IMG")

curl -s -X POST http://localhost:8000/api/v1/image/predict \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@${IMG};type=${MIME}" \
  | tee ecowaste-response.json \
  | python3 -m json.tool
```

The response should include:

```text
model
predictions
firebase_output_id
postprocess_job_id
```

---

## 13. Get the post-processing result

```bash
JOB_ID=$(cat ecowaste-response.json | jq -r '.postprocess_job_id')

sleep 10

curl -s "http://localhost:8000/api/v1/postprocess/results/${JOB_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

The result should include:

```text
ecowaste_recommendations
bitnet_interpretation
interpretation_model
```

---

## 14. Test the BitNet text endpoint

```bash
curl -s -X POST http://localhost:8000/api/v1/text/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain how this EcoWaste system helps users sort waste."}' \
  | python3 -m json.tool
```

---

## 15. Request history

List recent interactions:

```bash
curl -s "http://localhost:8000/api/v1/history?limit=5" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

Filter image requests:

```bash
curl -s "http://localhost:8000/api/v1/history?request_type=image&limit=5" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

---

## 16. Firebase Firestore CRUD endpoints

Create a manual Firestore output:

```bash
curl -s -X POST http://localhost:8000/api/v1/firebase/outputs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "request_type": "manual",
    "input_summary": "Manual Firestore test",
    "model": "manual-test",
    "output": {"message": "Created through the API"},
    "metadata": {"source": "README test"}
  }' | tee firebase-output.json | python3 -m json.tool
```

List outputs:

```bash
curl -s "http://localhost:8000/api/v1/firebase/outputs?limit=5" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool
```

Update output:

```bash
DOC_ID=$(cat firebase-output.json | jq -r '.id')

curl -s -X PATCH "http://localhost:8000/api/v1/firebase/outputs/${DOC_ID}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"reviewed": true}}' \
  | python3 -m json.tool
```

Delete output:

```bash
curl -i -X DELETE "http://localhost:8000/api/v1/firebase/outputs/${DOC_ID}" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 17. Monitoring

Metrics endpoint:

```bash
curl -s http://localhost:8000/metrics | head -40
```

Prometheus readiness:

```bash
curl -s http://localhost:9090/-/ready
```

Prometheus query:

```bash
curl -s "http://localhost:9090/api/v1/query?query=sum(ai_saas_http_requests_total)" \
  | python3 -m json.tool
```

Grafana is available inside the VM at:

```text
http://localhost:3000
```

Default development login:

```text
username: admin
password: value of GRAFANA_ADMIN_PASSWORD in .env
```

If you want to access Grafana from your local machine, use SSH tunnelling. This is optional.

---

## 18. RabbitMQ

RabbitMQ management UI is available inside the VM at:

```text
http://localhost:15672
```

Development login:

```text
username: value of RABBITMQ_DEFAULT_USER in .env
password: value of RABBITMQ_DEFAULT_PASS in .env
```

Check queues from terminal:

```bash
docker compose exec rabbitmq rabbitmqctl list_queues
```

---

## 19. Run the test suite

Run all tests with coverage:

```bash
./scripts/run_tests.sh
```

Alternative:

```bash
docker compose run --rm api python -m pytest --cov=app --cov=scripts --cov-report=term-missing
```

The test suite covers:

- API endpoints
- Firebase Authentication checks
- YOLO inference wrapper
- BitNet client
- Firebase Firestore storage logic
- RabbitMQ publisher
- Worker post-processing
- EcoWaste rule mapping
- Monitoring metrics endpoint
- Security headers, rate limiting, and upload validation
- Cost estimator script

---

## 20. Cost estimation

Run the Stage 8 cost estimator:

```bash
python3 scripts/cost_estimator.py
```

Or inside Docker:

```bash
docker compose run --rm api python scripts/cost_estimator.py
```

Example:

```bash
python3 scripts/cost_estimator.py \
  --yolo-users 100 \
  --llm-users 100 \
  --worker-users 100000 \
  --yolo-capacity 100 \
  --llm-capacity 100 \
  --worker-capacity 5000 \
  --firebase-f-cost 0
```

The formula used is:

```text
Total = H * sum(instance_count_i * hourly_price_i) + Disk + Network + F
```

where `F` is the Firebase constant cost.

---

## 21. Security design

Implemented security features:

- Firebase Authentication for protected endpoints
- Firestore access through GCP Application Default Credentials
- IAM-based access to Firestore
- No committed Firebase private key
- Local-only service binding with `127.0.0.1`
- Security headers
- CORS configuration
- Trusted Host middleware
- Request size limit
- Image content-type validation
- Lightweight rate limiting
- Non-root API/worker Docker runtime user
- `.env` and token files excluded from Git

Public endpoints:

```text
/health
/metrics
/docs
/openapi.json
```

Protected endpoints require:

```text
Authorization: Bearer <Firebase_ID_TOKEN>
```

---

## 22. Stop the system

```bash
docker compose down
```

To remove volumes as well:

```bash
docker compose down -v
```

Use `-v` carefully because it removes PostgreSQL, Prometheus, and Grafana persisted data.

---

## 23. Troubleshooting

### Token expired

If you see:

```text
Invalid or expired Firebase ID token
```

Get a new token by running the Firebase login command again.

### Firestore 403 permission error

Check that the VM service account has:

```text
Cloud Datastore User
```

Also check that the VM has sufficient access scope:

```text
https://www.googleapis.com/auth/cloud-platform
```

### Model file not found

Check:

```bash
ls -lh models/yolo/best.pt
```

and verify `.env`:

```env
YOLO_MODEL_PATH=/app/models/yolo/best.pt
```

### Invalid image upload

Check the file MIME type:

```bash
file --mime-type -b your_image.jpg
```

Allowed types:

```text
image/jpeg
image/png
image/webp
```

### Grafana UI not accessible from laptop

Grafana is bound to VM localhost only. Either test with terminal commands inside the VM or use SSH tunnelling.

---

## 24. Product summary

EcoWaste Sorting Assistant is an end-to-end AI SaaS prototype that demonstrates how cloud technologies can support a practical sustainability use case. It combines custom waste-object detection, LLM-based explanation, secure API access, persistent storage, message-queue-based post-processing, monitoring, cost estimation, and security hardening in one deployable system.
