# Legal Document Intelligence System

An AI-powered legal document analysis platform that enables users to upload contracts, ask natural language questions, extract legal clauses, and assess contractual risk using Retrieval-Augmented Generation (RAG).

---

## Features

- 📄 Upload and process legal PDF documents
- 🤖 Ask questions about contracts using RAG
- 🔍 Hybrid retrieval using BM25 + vector search
- 📋 Automated clause extraction
- ⚠️ Rule-based risk scoring engine
- 📚 Source-grounded responses with citations
- 🔄 Support for ChromaDB (local) and Pinecone (cloud)
- 🧠 Multiple embedding model support (OpenAI, Legal-BERT, Ollama)

---

## Tech Stack

### Backend
- FastAPI
- Python
- Uvicorn

### Frontend
- React
- Vite

### Vector Databases
- ChromaDB
- Pinecone

### Embedding Models
- OpenAI text-embedding-3-large
- Legal-BERT
- Ollama (nomic-embed-text)

### LLM Providers
- OpenAI
- Anthropic
- Ollama

### Additional Tools
- BM25 Retrieval
- RAG Architecture
- Rule-based Risk Analysis

---

## System Architecture

```text
PDF Upload
     ↓
Document Parsing
     ↓
Clause Boundary Chunking
     ↓
Embedding Generation
     ↓
ChromaDB / Pinecone
     ↓
Hybrid Retrieval (BM25 + Vector Search)
     ↓
LLM (OpenAI / Anthropic / Ollama)
     ↓
Answer Generation with Citations
     ↓
Clause Extraction & Risk Analysis
```

---

## Installation

### Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/legal-doc-intelligence.git
cd legal-doc-intelligence
```

---

## Backend Setup

Create a virtual environment:

```bash
cd backend
python -m venv venv
```

Activate it:

### Windows

```bash
venv\Scripts\activate
```

### macOS/Linux

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r ../requirements.txt
```

---

## Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Example configuration:

```env
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

VECTOR_STORE=chroma

CHROMA_PERSIST_DIR=./chroma_db

EMBEDDING_MODEL=text-embedding-3-large
```

---

## Frontend Setup

Navigate to frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Run the frontend:

```bash
npm run dev
```

Frontend will be available at:

```
http://localhost:5173
```

---

## Running the Backend

Navigate to backend:

```bash
cd backend
```

Start the FastAPI server:

```bash
uvicorn main:app --reload --port 8000
```

Backend API documentation:

```
http://localhost:8000/docs
```

---

## API Usage Examples

### Upload a Legal Document

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@contract.pdf"
```

### Ask Questions About Contracts

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the termination conditions?"}'
```

### Risk Analysis

```bash
curl http://localhost:8000/risk-score/{doc_id}
```

### Extract Clauses

```bash
curl -X POST http://localhost:8000/extract-clauses \
  -H "Content-Type: application/json" \
  -d '{"clause_type":"indemnity"}'
```

---

## Vector Store Options

### ChromaDB (Recommended for Development)

No additional setup required.

```env
VECTOR_STORE=chroma
CHROMA_PERSIST_DIR=./chroma_db
```

### Pinecone (Recommended for Production)

Install Pinecone:

```bash
pip install pinecone-client
```

Environment configuration:

```env
VECTOR_STORE=pinecone

PINECONE_API_KEY=your_key_here

PINECONE_INDEX_NAME=legal-docs
```

---

## Embedding Model Options

### OpenAI Embeddings

```env
EMBEDDING_MODEL=text-embedding-3-large
```

- Dimension: 3072
- High retrieval accuracy

### Legal-BERT

```env
EMBEDDING_MODEL=legal-bert
```

Install:

```bash
pip install sentence-transformers
```

Advantages:

- Free
- Domain-specific legal understanding

### Ollama (Fully Local)

Install Ollama and pull models:

```bash
ollama pull nomic-embed-text
ollama pull llama3
```

Advantages:

- No API costs
- Complete privacy

---

## Demo Workflow

### Multi-Document Q&A

1. Upload multiple contracts.
2. Select "All Documents".
3. Ask:

```text
Which contract has a longer non-compete clause?
```

4. The system returns answers with source citations.

### Clause Extraction

1. Open the Clause Extractor.
2. Select clause type:

```text
Indemnity
```

3. View extracted clauses with document references.

### Risk Analysis

1. Upload a contract.
2. Open Risk Analyzer.
3. Generate a risk report.
4. Review flagged clauses and recommendations.

---

## Production Checklist

### Security

- [ ] Add JWT authentication
- [ ] Implement API rate limiting
- [ ] Validate uploaded PDF headers
- [ ] Store secrets using a secure secrets manager

### Performance

- [ ] Cache embeddings using Redis
- [ ] Add Celery/RQ for background processing
- [ ] Stream LLM responses using Server-Sent Events (SSE)

### Deployment

- [ ] Dockerize the application
- [ ] Configure Nginx reverse proxy
- [ ] Mount persistent storage for ChromaDB

---

## Project Structure

```text
legal-doc-intelligence/
├── requirements.txt
├── .env.example
├── README.md
│
├── backend/
│   ├── main.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── upload.py
│   │   ├── ask.py
│   │   ├── clauses.py
│   │   ├── risk.py
│   │   └── documents.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ingestion.py
│   │   ├── embeddings.py
│   │   ├── retrieval.py
│   │   └── risk_scorer.py
│   │
│   └── vector_store/
│       ├── __init__.py
│       ├── chroma_client.py
│       └── pinecone_client.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       └── App.jsx
│
├── notebooks/
│   ├── 01_chunking_experiments.ipynb
│   ├── 02_embedding_eval.ipynb
│   └── 03_retrieval_eval.ipynb
```

---

## Key Design Decisions

| Decision | Why It Matters |
|-----------|----------------|
| Clause-boundary chunking | Each chunk represents a complete legal clause, improving retrieval precision. |
| Hybrid BM25 + vector search | Combines keyword matching with semantic understanding for better results. |
| Metadata-enriched embeddings | Enables filtering by clause type without reprocessing documents. |
| Citation-grounded prompting | Reduces hallucinations by ensuring answers reference source documents. |
| Rule-based risk scoring | Provides explainable and auditable legal risk assessments. |
| Chroma for development, Pinecone for production | Allows cost-effective development with scalable deployment options. |

---

## Future Improvements

- Fine-tune Legal-BERT for contract classification
- Add support for DOCX contracts
- Implement multilingual legal document analysis
- Add real-time collaborative contract review
- Introduce contract comparison functionality
- Deploy using Kubernetes

---

## License

This project is licensed under the MIT License.

---

## Author

**Your Name**

GitHub: https://github.com/YOUR_USERNAME

LinkedIn: https://linkedin.com/in/YOUR_PROFILE