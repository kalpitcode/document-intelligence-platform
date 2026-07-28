"""
Enterprise Dashboard Web UI Module
====================================
Provides a flagship, glassmorphism dark-mode Single Page Application (SPA) dashboard
for interactive document parsing, hybrid search, RAG chat, DAG workflows, and telemetry.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Web UI"])

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise AI Document Intelligence Platform</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <script type="module" src="/static/js/main.js"></script>
</head>
<body>

    <header>
        <div class="brand">
            <div class="logo-icon">A</div>
            <div>
                <div class="brand-title">ALADDIN AI PLATFORM</div>
                <div class="brand-subtitle">Document Intelligence</div>
            </div>
        </div>
        <div class="header-actions">
            <div class="status-pill"><div class="status-dot"></div> SYSTEM ONLINE</div>
            <a href="/api/v1/docs" target="_blank" class="btn-action btn-action-sm">API Docs ↗</a>
        </div>
    </header>

    <main>
        <!-- Navigation Tabs -->
        <nav class="tabs-nav">
            <button class="tab-btn active" id="tab-btn-dashboard" data-tab="dashboard">📊 Overview Telemetry</button>
            <button class="tab-btn" id="tab-btn-ocr" data-tab="ocr">📄 Document OCR Parsing</button>
            <button class="tab-btn" id="tab-btn-search" data-tab="search">🔍 Hybrid Vector Search</button>
            <button class="tab-btn" id="tab-btn-rag" data-tab="rag">🤖 Enterprise RAG Chat</button>
            <button class="tab-btn" id="tab-btn-workflows" data-tab="workflows">⚡ DAG Workflows</button>
            <button class="tab-btn" id="tab-btn-specs" data-tab="specs">📘 API Specifications</button>
        </nav>

        <!-- TAB 1: OVERVIEW TELEMETRY -->
        <div id="tab-dashboard" class="tab-content active">
            <div class="metrics-grid">
                <div class="card">
                    <div class="card-header"><span class="card-title">Documents Ingested</span><span class="card-icon">📚</span></div>
                    <div class="card-value">1,248</div>
                    <div class="card-subtext">↑ 14% this week</div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">Vector Embeddings</span><span class="card-icon">🧬</span></div>
                    <div class="card-value">48,920</div>
                    <div class="card-subtext">384d Dense Vectors in Qdrant</div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">Hybrid Query SLA</span><span class="card-icon">⚡</span></div>
                    <div class="card-value">18.2 ms</div>
                    <div class="card-subtext">RRF (Dense Vector + BM25)</div>
                </div>
                <div class="card">
                    <div class="card-header"><span class="card-title">Active Celery Workers</span><span class="card-icon">⚙️</span></div>
                    <div class="card-value">8 Workers</div>
                    <div class="card-subtext">100% Processing Queue Health</div>
                </div>
            </div>

            <div class="section-box">
                <div class="section-header">
                    <div class="section-title">💚 Live Component Health Diagnostics</div>
                    <button class="btn-action btn-action-xs" id="btn-refresh-health">Refresh Health</button>
                </div>
                <div class="console-box" id="health-console">[SYSTEM] Querying live diagnostic status from /api/v1/health...</div>
            </div>
        </div>

        <!-- TAB 2: DOCUMENT OCR PARSING -->
        <div id="tab-ocr" class="tab-content">
            <div class="section-box">
                <div class="section-header">
                    <div class="section-title">📄 Asynchronous Document Ingestion & OCR</div>
                </div>
                <div class="dropzone" id="dropzone-ocr">
                    <input type="file" id="ocr-file-input" class="file-input-hidden" accept=".pdf,.docx,.txt,.csv,.xlsx,.png,.jpg,.jpeg">
                    <div class="upload-icon">📤</div>
                    <div class="dropzone-title">Click to Process Financial PDF / DOCX</div>
                    <div class="dropzone-subtitle">Supports PyMuPDF Layout Parsing, Tesseract OCR & Table Bounding Box Detection</div>
                </div>
                <div class="console-box" id="ocr-console">Ready to receive document for processing...</div>
            </div>
        </div>

        <!-- TAB 3: HYBRID VECTOR SEARCH -->
        <div id="tab-search" class="tab-content">
            <div class="section-box">
                <div class="section-header">
                    <div class="section-title">🔍 Reciprocal Rank Fusion (RRF) Hybrid Search</div>
                </div>
                <div class="input-group">
                    <input type="text" id="search-input" class="input-field" placeholder="Enter query (e.g. Q4 revenue margin growth or risk factors)..." value="Q4 revenue growth financial summary">
                    <button class="btn-action" id="btn-run-search">Execute Search</button>
                </div>
                <div class="chip-group">
                    <div class="chip" data-query="Q4 revenue growth financial summary">Q4 revenue growth</div>
                    <div class="chip" data-query="Operating margin and profitability analysis">Operating margin</div>
                    <div class="chip" data-query="Risk management factors and credit exposure">Risk management</div>
                </div>
                <div class="console-box" id="search-console">Enter search term above to execute RRF Hybrid Query...</div>
            </div>
        </div>

        <!-- TAB 4: ENTERPRISE RAG CHAT -->
        <div id="tab-rag" class="tab-content">
            <div class="section-box">
                <div class="section-header">
                    <div class="section-title">🤖 Enterprise Retrieval-Augmented Generation (RAG)</div>
                </div>
                <div class="console-box chat-console-box" id="chat-box">
                    <div class="chat-bubble ai-bubble">
                        👋 Hello! I am your Enterprise AI Financial & Document Assistant. Ask me any question regarding ingested documents or portfolio analytics.
                    </div>
                </div>
                <div class="input-group">
                    <input type="text" id="rag-input" class="input-field" placeholder="Ask a question about your documents..." value="What were the primary revenue drivers in Q4?">
                    <button class="btn-action" id="btn-send-rag">Ask RAG AI</button>
                </div>
            </div>
        </div>

        <!-- TAB 5: DAG WORKFLOWS -->
        <div id="tab-workflows" class="tab-content">
            <div class="section-box">
                <div class="section-header">
                    <div class="section-title">⚡ Distributed DAG Workflow Orchestration</div>
                </div>
                <p class="text-muted">Execute multi-step asynchronous processing pipelines (Ingestion ➔ Layout Analysis ➔ Embedding Generation ➔ Qdrant Indexing ➔ Notification).</p>
                <button class="btn-action btn-fit" id="btn-run-workflow">Trigger Standard Ingestion DAG Pipeline</button>
                <div class="console-box" id="workflow-console">Workflow Engine Ready. Select a pipeline to execute.</div>
            </div>
        </div>

        <!-- TAB 6: API SPECIFICATIONS -->
        <div id="tab-specs" class="tab-content">
            <div class="section-box">
                <div class="section-header">
                    <div class="section-title">📘 Interactive API Documentation & Specs</div>
                </div>
                <p class="text-muted">Explore live REST API specs, schema definitions, and execute requests directly.</p>
                <div class="input-group">
                    <a href="/api/v1/docs" target="_blank" class="btn-action">🚀 Open Swagger UI Interactive Console</a>
                    <a href="/api/v1/redoc" target="_blank" class="btn-action btn-secondary">📘 Open ReDoc Specs</a>
                    <a href="/api/v1/metrics" target="_blank" class="btn-action btn-secondary">📊 Open Metrics</a>
                </div>
            </div>
        </div>
    </main>

    <footer>
        Enterprise AI Document Intelligence Platform &bull; Built on Aladdin Architecture Principles &bull; Version 0.1.0
    </footer>

</body>
</html>"""

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def get_dashboard():
    """Render the flagship Enterprise AI Platform Dashboard Web UI."""
    return HTMLResponse(content=DASHBOARD_HTML)
