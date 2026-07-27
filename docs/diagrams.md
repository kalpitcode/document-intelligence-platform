# Enterprise System Diagrams

This document contains 8 Mermaid architecture diagrams illustrating the design of the **Enterprise AI Document Intelligence Platform**.

---

## 1. System Architecture

```mermaid
graph TD
    Client[Client Applications] -->|HTTPS REST| Ingress[NGINX Ingress Controller]
    Ingress --> API[FastAPI Cluster]

    subgraph Infrastructure Core
        API --> DB[(PostgreSQL 16)]
        API --> Cache[(Redis 7)]
        API --> Queue[(RabbitMQ Broker)]
    end

    subgraph Workers & Compute
        Queue --> Worker[Celery Worker Cluster]
        Worker --> MinIO[(MinIO S3 Storage)]
        Worker --> OCR[OCR Pipeline]
        Worker --> Embed[Embedding Model]
        Embed --> Qdrant[(Qdrant Vector DB)]
    end

    subgraph Observability
        API --> Prom[Prometheus /metrics]
        API --> OTEL[OpenTelemetry Context]
    end
```

---

## 2. Container Diagram

```mermaid
graph TB
    subgraph Host Network / Kubernetes Node
        C1[FastAPI Application Container :8000]
        C2[Celery Worker Container]
        C3[PostgreSQL Container :5432]
        C4[Redis Container :6379]
        C5[RabbitMQ Container :5672]
        C6[MinIO Container :9000]
        C7[Qdrant Container :6333]
    end

    C1 --> C3
    C1 --> C4
    C1 --> C5
    C2 --> C5
    C2 --> C6
    C2 --> C7
```

---

## 3. Synchronous Request Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant MW as Security Middleware
    participant API as FastAPI Router
    participant Service as Business Service
    participant Repo as Repository
    participant DB as PostgreSQL DB

    Client->>MW: HTTP POST /api/v1/search
    MW->>MW: Check Rate Limit & Security Headers
    MW->>API: Forward Authorized Request
    API->>Service: Call execute_search()
    Service->>Repo: Query Database / Vector Store
    Repo->>DB: Execute Query
    DB-->>Repo: Data Result
    Repo-->>Service: Return Entities
    Service-->>API: Return Domain Models
    API-->>Client: HTTP 200 OK (JSON APIResponse)
```

---

## 4. Asynchronous OCR Processing Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Gateway as FastAPI Endpoint
    participant Storage as MinIO S3
    participant Broker as RabbitMQ
    participant Worker as Celery Worker
    participant DB as Postgres DB

    User->>Gateway: POST /api/v1/documents (Upload PDF)
    Gateway->>Storage: Store raw binary file
    Gateway->>DB: Save Document Record (Status: PENDING)
    Gateway->>Broker: Enqueue 'process_document' task
    Gateway-->>User: HTTP 202 Accepted (Document ID)

    Broker->>Worker: Dispatch task
    Worker->>Storage: Fetch raw binary file
    Worker->>Worker: Run PyMuPDF & Tesseract OCR
    Worker->>DB: Update Document (Status: COMPLETED, Text Chunks)
```

---

## 5. Enterprise RAG Pipeline Flow

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as FastAPI Chat Endpoint
    participant Embed as Sentence Transformer Model
    participant Vector as Qdrant Vector DB
    participant LLM as LiteLLM Model Provider

    User->>API: POST /api/v1/chat/query (Question)
    API->>Embed: Embed query string to 384d vector
    Embed-->>API: Query Dense Vector
    API->>Vector: Perform Hybrid Vector + BM25 Search
    Vector-->>API: Top-K Context Chunks
    API->>LLM: Formulate System Prompt + Context
    LLM-->>API: Generated Answer with Citations
    API-->>User: Structured Response JSON
```

---

## 6. Workflow DAG Execution Flow

```mermaid
graph TD
    Start([Trigger Workflow]) --> Step1[Step 1: Document OCR]
    Step1 --> Step2[Step 2: Table Extraction]
    Step2 --> Step3[Step 3: Chunking & Embeddings]
    Step3 --> Step4[Step 4: Vector Indexing]
    Step4 --> End([Workflow Completed])
```

---

## 7. Kubernetes Deployment Architecture

```mermaid
graph TB
    subgraph Namespace: dip-production
        Ingress[NGINX Ingress Controller]
        HPA[HorizontalPodAutoscaler]
        
        subgraph Pods Deployment
            Pod1[API Pod 1]
            Pod2[API Pod 2]
            Pod3[API Pod 3]
        end
        
        Ingress --> Pod1
        Ingress --> Pod2
        Ingress --> Pod3
        HPA -. Scales .-> Pods Deployment
    end
```

---

## 8. Authentication Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Auth as Auth Router
    participant Service as PasswordService
    participant Token as TokenService
    participant DB as User Repository

    Client->>Auth: POST /api/v1/auth/login (email, password)
    Auth->>DB: Get User by Email
    DB-->>Auth: UserModel
    Auth->>Service: Verify Password (Argon2id)
    Service-->>Auth: Password Valid (True)
    Auth->>Token: Create JWT Access & Refresh Tokens
    Token-->>Auth: Token Pair
    Auth-->>Client: HTTP 200 OK (access_token, refresh_token)
```
