# Enterprise API Reference & Code Examples

## Base URL
- Local: `http://localhost:8000/api/v1`
- Production: `https://dip.blackrock.com/api/v1`

---

## 1. Authentication

### Register User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "analyst@blackrock.com",
    "username": "analyst_john",
    "password": "Password123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### Login & Obtain JWT Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=analyst@blackrock.com&password=Password123!"
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## 2. Document Upload & Ingestion

```bash
curl -X POST "http://localhost:8000/api/v1/documents" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@sample_financial_report.pdf" \
  -F "title=Q4 Financial Analysis"
```

**Response (202 Accepted):**
```json
{
  "data": {
    "id": "doc-9f82a1b4",
    "filename": "sample_financial_report.pdf",
    "status": "processing",
    "created_at": "2026-07-27T12:00:00Z"
  },
  "message": "Document accepted for processing"
}
```

---

## 3. Hybrid Vector Search

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "net profit revenue margin growth",
    "search_type": "hybrid",
    "limit": 3
  }'
```

**Response (200 OK):**
```json
{
  "data": {
    "total": 3,
    "results": [
      {
        "document_id": "doc-9f82a1b4",
        "score": 0.942,
        "content": "Net profit margin increased by 14.2% YoY during Q4...",
        "page_number": 4
      }
    ]
  }
}
```

---

## 4. Ask RAG Questions

```bash
curl -X POST "http://localhost:8000/api/v1/chat/query" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What were the primary revenue drivers in Q4?",
    "top_k": 5
  }'
```

---

## 5. AI Document Summarization

```bash
curl -X POST "http://localhost:8000/api/v1/ai/summary/doc-9f82a1b4" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

## 6. Run Workflow DAG Execution

```bash
curl -X POST "http://localhost:8000/api/v1/workflows/execute" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "Standard Ingestion DAG",
    "document_id": "doc-9f82a1b4"
  }'
```

---

## 7. System Health & Probes

```bash
# 1. Health Check
curl http://localhost:8000/api/v1/health

# 2. Liveness Probe
curl http://localhost:8000/api/v1/health/live

# 3. Readiness Probe
curl http://localhost:8000/api/v1/health/ready
```
