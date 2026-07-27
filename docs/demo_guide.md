# Step-by-Step Interactive Demo Walkthrough

Follow this 9-step guided walkthrough to demonstrate the full capabilities of the platform during technical interviews or system live demos.

---

## Step 1: User Registration & Login Authentication
Obtain JWT bearer access token for secure authorization.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=analyst@blackrock.com&password=Password123!"
```
*Save the `access_token` returned in the JSON response.*

---

## Step 2: Upload Financial Document
Upload raw PDF document to MinIO S3 object storage.

```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@sample_q4_report.pdf"
```

---

## Step 3: OCR Processing & Layout Extraction
Verify document status transition from `PENDING` -> `COMPLETED`.

```bash
curl "http://localhost:8000/api/v1/documents/doc-123/status" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Step 4: Execute Hybrid Semantic Vector Search
Perform Reciprocal Rank Fusion query against Qdrant vector store.

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly operating margin growth", "search_type": "hybrid"}'
```

---

## Step 5: Ask RAG Conversational Question
Query LLM provider augmented with extracted document context chunks.

```bash
curl -X POST "http://localhost:8000/api/v1/chat/query" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What were key risk drivers?"}'
```

---

## Step 6: Generate AI Document Summary
Extract structural summary.

```bash
curl -X POST "http://localhost:8000/api/v1/ai/summary/doc-123" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Step 7: Run DAG Workflow Automation
Trigger asynchronous multi-step processing DAG.

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/execute" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "Standard Ingestion DAG", "document_id": "doc-123"}'
```

---

## Step 8: View Monitoring & Observability Metrics
Inspect OpenMetrics status.

```bash
curl http://localhost:8000/api/v1/metrics
```

---

## Step 9: Validate System Health Probes
Confirm platform Liveness and Readiness.

```bash
curl http://localhost:8000/api/v1/health/ready
```
