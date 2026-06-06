# Legal Document Intelligence System — Complete Build Guide

## Step-by-Step Plan

---

### PHASE 1 — Environment Setup (Day 1)

#### 1.1 Clone / create the project structure

```bash
mkdir legal-doc-intelligence && cd legal-doc-intelligence
mkdir -p backend/{routes,services,vector_store} frontend/src/components notebooks tests
```

#### 1.2 Python backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
```

#### 1.3 Set up environment variables

```bash
cp ../.env.example .env
# Edit .env — add your OPENAI_API_KEY or ANTHROPIC_API_KEY
# Set VECTOR_STORE=chroma for local development (free, no API key)
```

#### 1.4 React frontend setup

```bash
cd ../frontend
npm create vite@latest . -- --template react
# (confirm overwrite when asked)
npm install
```

---

### PHASE 2 — Backend Implementation (Day 1–2)

#### 2.1 Copy all backend files into place

Copy the generated files:
- `backend/main.py`
- `backend/routes/upload.py`
- `backend/routes/ask.py`
- `backend/routes/clauses.py`
- `backend/routes/risk.py`
- `backend/routes/documents.py`
- `backend/services/ingestion.py`
- `backend/services/embeddings.py`
- `backend/services/retrieval.py`
- `backend/services/risk_scorer.py`
- `backend/vector_store/chroma_client.py`

#### 2.2 Create `__init__.py` files

```bash
touch backend/routes/__init__.py
touch backend/services/__init__.py
touch backend/vector_store/__init__.py
```

#### 2.3 Test the backend runs

```bash
cd backend
uvicorn main:app --reload --port 8000
# Visit http://localhost:8000/docs — you'll see the Swagger UI
```

#### 2.4 Test with curl

```bash
# Upload a PDF
curl -X POST http://localhost:8000/upload \
  -F "file=@your_contract.pdf"

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the termination conditions?"}'

# Risk score (use doc_id from upload response)
curl http://localhost:8000/risk-score/{doc_id}

# Extract all indemnity clauses
curl -X POST http://localhost:8000/extract-clauses \
  -H "Content-Type: application/json" \
  -d '{"clause_type": "indemnity"}'
```

---

### PHASE 3 — Frontend Implementation (Day 2–3)

#### 3.1 Replace the default App

```bash
# Remove default boilerplate
rm frontend/src/App.css frontend/src/index.css
# Copy App.jsx into frontend/src/App.jsx
```

#### 3.2 Update main.jsx

```jsx
// frontend/src/main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

#### 3.3 Run the frontend

```bash
cd frontend
npm run dev
# Visit http://localhost:5173
```

---

### PHASE 4 — Vector Store (Choosing Between Chroma vs Pinecone)

#### Option A: Chroma (local, free — recommended for development)

No setup needed. Chroma persists to `./chroma_db` automatically.

```env
VECTOR_STORE=chroma
CHROMA_PERSIST_DIR=./chroma_db
```

#### Option B: Pinecone (cloud — recommended for production)

```bash
pip install pinecone-client
```

Create `backend/vector_store/pinecone_client.py`:

```python
import os
import pinecone
from llama_index.vector_stores.pinecone import PineconeVectorStore

def get_vector_store():
    pc = pinecone.Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME", "legal-docs"))
    return PineconeVectorStore(pinecone_index=index)
```

Then in `.env`:
```env
VECTOR_STORE=pinecone
PINECONE_API_KEY=your-key-here
PINECONE_INDEX_NAME=legal-docs
```

And in `chroma_client.py`, add a factory at the top:
```python
def get_vector_store():
    if os.getenv("VECTOR_STORE") == "pinecone":
        from vector_store.pinecone_client import get_vector_store as pine_store
        return pine_store()
    # ... existing chroma code
```

---

### PHASE 5 — Embedding Model Choice

#### Option A: OpenAI text-embedding-3-large (recommended, paid)
```env
EMBEDDING_MODEL=text-embedding-3-large
```
Dimension: 3072 · Best accuracy · ~$0.13 per million tokens

#### Option B: legal-BERT (free, local, slower)
```env
EMBEDDING_MODEL=legal-bert
```
```bash
pip install sentence-transformers
# Model downloads automatically on first run (~400MB)
```

#### Option C: Ollama (free, fully local LLM + embeddings)
```bash
# Install Ollama: https://ollama.ai
ollama pull nomic-embed-text   # for embeddings
ollama pull llama3             # for LLM
```

---

### PHASE 6 — Running the Full Demo (5-Minute Walkthrough)

#### Prepare sample contracts
Download free NDA samples from:
- https://www.lawinsider.com/documents/nda
- https://docracy.com

Use 2 contracts: one NDA + one Service Agreement.

#### Demo script

**Moment 1 — Multi-doc Q&A with citations**
1. Upload both contracts via the Upload Zone
2. Leave "All Documents" selected
3. Ask: "Which contract has a longer non-compete clause?"
4. System returns exact clause text from each doc with page citations

**Moment 2 — Clause extraction**
1. Click "Clause Extractor" tab
2. Select "Indemnity" from dropdown
3. Click "Extract Clauses"
4. All indemnification clauses appear from both docs, with source + page

**Moment 3 — Risk scoring**
1. Upload a one-sided liability contract
2. Select it in the sidebar
3. Click "Risk Analyzer" tab
4. Click "Analyze Risk"
5. See score (e.g. 74/100), flagged clauses highlighted, recommendations

---

### PHASE 7 — Production Checklist

#### Security
- [ ] Add API authentication (JWT or API key middleware)
- [ ] Rate limit the `/ask` endpoint (expensive LLM calls)
- [ ] Sanitize file uploads (validate PDF headers, not just extension)
- [ ] Store API keys in proper secrets manager (not .env in prod)

#### Performance
- [ ] Cache embeddings in Redis to avoid re-embedding on restart
- [ ] Add background task queue (Celery/RQ) for PDF ingestion
- [ ] Stream LLM responses via SSE for real-time chat feel

#### Deployment
- [ ] Dockerize: `docker-compose up` should start both services
- [ ] Use Nginx to proxy `/api/*` → FastAPI, `/*` → Vite build
- [ ] Set `CHROMA_PERSIST_DIR` to a mounted volume (not ephemeral storage)

---

### Project File Structure (Final)

```
legal-doc-intelligence/
├── requirements.txt
├── .env.example
├── README.md
│
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py              # POST /upload
│   │   ├── ask.py                 # POST /ask
│   │   ├── clauses.py             # POST /extract-clauses
│   │   ├── risk.py                # GET /risk-score
│   │   └── documents.py           # GET /documents
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ingestion.py           # PDF → clause chunks → vectors
│   │   ├── embeddings.py          # OpenAI / legal-BERT wrapper
│   │   ├── retrieval.py           # Hybrid BM25 + vector RAG
│   │   └── risk_scorer.py         # Clause risk rules engine
│   └── vector_store/
│       ├── __init__.py
│       ├── chroma_client.py       # Local ChromaDB
│       └── pinecone_client.py     # Cloud Pinecone (optional)
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       └── App.jsx                # Full UI (upload + chat + clauses + risk)
│
└── notebooks/
    ├── 01_chunking_experiments.ipynb
    ├── 02_embedding_eval.ipynb
    └── 03_retrieval_eval.ipynb
```

---

### Key Design Decisions (Interview Talking Points)

| Decision | Why It Matters |
|---|---|
| Clause-boundary chunking | Each chunk = one legal unit. Retrieval is semantically precise. |
| Hybrid BM25 + vector search | Vector search misses "Force Majeure"; BM25 catches it. Best of both worlds. |
| Metadata-enriched embeddings | Filter by `clause_type` without re-reading documents. |
| Citation grounding in system prompt | Prevents hallucination. Every answer is traceable to a page. |
| Rule-based risk scorer | Explainable, auditable, fast. No black-box ML needed for first version. |
| Chroma for dev, Pinecone for prod | Zero-cost local dev; seamless swap to cloud via env var. |
