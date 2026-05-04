# AI Agent – RAG Document Q&A Platform

A production-ready AI agent demo built for **Hack the Mittelstand – Agentic AI in Action** (Munich, May 2026).  
Upload your company documents, then let users ask questions in natural language — the agent retrieves the most relevant passages and answers strictly from your content.

🌐 **Live demo:** [lukas-zhangjx.github.io/demo_Mai_Munich](https://lukas-zhangjx.github.io/demo_Mai_Munich)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (GitHub Pages)                   │
│                                                                  │
│   index.html          admin.html                                 │
│   Chat UI             Admin Panel                                │
│   (EN / DE)           Upload · Status · Delete                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS (ngrok tunnel for local demo)
┌────────────────────────────▼────────────────────────────────────┐
│                     Backend  (FastAPI + uvicorn)                 │
│                                                                  │
│  POST /api/chat          RAG pipeline                            │
│  ├─ embed_query()        Gemini → 768-dim vector                 │
│  ├─ match_documents()    Supabase pgvector cosine search         │
│  └─ stream answer        Groq LLaMA-3.1-8B  (SSE)               │
│                                                                  │
│  POST /api/upload        Background task (returns 202)           │
│  ├─ extract text         pdfplumber / UTF-8                      │
│  ├─ chunk_text()         Sliding window, 400 chars, 80 overlap   │
│  ├─ embed_texts()        Gemini sequential (rate-limit safe)     │
│  └─ insert → documents   Supabase                                │
│                                                                  │
│  GET  /api/upload-jobs   Job status polling                      │
│  DELETE /api/upload-jobs/{id}  Remove job + chunks               │
│  POST /api/auth/login    JWT (12 h expiry)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ Supabase REST + RPC
┌────────────────────────────▼────────────────────────────────────┐
│                     Supabase (PostgreSQL + pgvector)             │
│                                                                  │
│  documents      id · content · embedding vector(768) · metadata  │
│  upload_jobs    id · filename · status · chunks · created_at     │
│                                                                  │
│  match_documents()  cosine similarity search via <=> operator    │
│  HNSW index         fast approximate nearest-neighbour search    │
└─────────────────────────────────────────────────────────────────┘
```

### RAG Flow (step by step)

1. **Upload** — admin uploads a PDF/TXT/MD file via the admin panel
2. **Extract** — raw text is extracted (pdfplumber for PDF, UTF-8 for text)
3. **Chunk** — text is split into overlapping 400-character windows
4. **Embed** — each chunk is embedded with Gemini `gemini-embedding-001` (768 dims)
5. **Store** — chunk + vector + metadata are inserted into Supabase
6. **Query** — user message is embedded with the same model
7. **Retrieve** — pgvector finds the top-5 most similar chunks (cosine similarity ≥ 0.3)
8. **Generate** — Groq streams the answer token-by-token over SSE, citing sources

---

## Message Flow (Q&A Information Path)

How a single user question travels through the system and comes back as a streamed answer:

```
  USER
   │
   │  "What is the return policy?"
   │
   ▼
┌──────────────────────────────────────────────────────────────────┐
│  Frontend  (index.html + app.js)                                 │
│                                                                  │
│  POST /api/chat                                                  │
│  body: message = "What is the return policy?"                    │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  Backend  (FastAPI)                                              │
│                                                                  │
│  Step 1 – Embed the question                                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  embed_query("What is the return policy?")              │    │
│  │       │                                                 │    │
│  │       ▼  Google Gemini API                              │    │
│  │  query_vector = [0.031, -0.044, 0.019, …]  (768 dims)  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Step 2 – Retrieve relevant chunks                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  match_documents(query_vector, threshold=0.3, top_k=5)  │    │
│  │       │                                                 │    │
│  │       ▼  Supabase pgvector (HNSW cosine search)         │    │
│  │  chunks = [                                             │    │
│  │    { source: "policy.pdf",  similarity: 0.81,           │    │
│  │      content: "Returns accepted within 30 days…" },     │    │
│  │    { source: "faq.txt",     similarity: 0.74,           │    │
│  │      content: "Refunds are processed in 5 days…" },     │    │
│  │    …                                                    │    │
│  │  ]                                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Step 3 – Build the prompt                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  SYSTEM:  "Answer strictly from the context provided.   │    │
│  │            Cite your source. Say 'I don't know' if      │    │
│  │            the context is insufficient."                │    │
│  │                                                         │    │
│  │  USER:    "Use the following document context…          │    │
│  │            <context>                                    │    │
│  │              [Source 1 – policy.pdf]                    │    │
│  │              Returns accepted within 30 days…           │    │
│  │              [Source 2 – faq.txt]                       │    │
│  │              Refunds are processed in 5 days…           │    │
│  │            </context>                                   │    │
│  │                                                         │    │
│  │            Question: What is the return policy?"        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Step 4 – Stream the answer                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Groq API  (llama-3.1-8b-instant, stream=True)          │    │
│  │       │                                                 │    │
│  │       ▼  token by token                                 │    │
│  │  "According" → " to" → " Source" → " 1" → "," → …      │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────────┬──────────────────────────────────┘
                                │  Server-Sent Events (SSE)
                                │
                                │  data: {"type":"tool_call", "input":{"source":"policy.pdf","similarity":0.81}}
                                │  data: {"type":"text", "content":"According"}
                                │  data: {"type":"text", "content":" to"}
                                │  data: {"type":"text", "content":" Source 1…"}
                                │  data: [DONE]
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  Frontend  (app.js)                                              │
│                                                                  │
│  • Renders source cards (filename + similarity score)            │
│  • Appends each text token in real time                          │
│  • Closes stream on [DONE]                                       │
└──────────────────────────────────────────────────────────────────┘
   │
   ▼
  USER sees:
  ┌─────────────────────────────────────────┐
  │ 🔍 policy.pdf  (0.81)                   │
  │ 🔍 faq.txt     (0.74)                   │
  │                                         │
  │ According to Source 1 (policy.pdf),     │
  │ returns are accepted within 30 days of  │
  │ purchase. Refunds are processed within  │
  │ 5 business days (Source 2).             │
  └─────────────────────────────────────────┘
```

### Two AI Models, One Pipeline

| Model | Provider | Role | Called when |
|---|---|---|---|
| `gemini-embedding-001` | Google Gemini | Converts text → 768-dim vector | Every question + every uploaded chunk |
| `llama-3.1-8b-instant` | Groq | Reads context, generates answer | Every question |

> **Gemini finds. LLaMA answers.**  
> Without Gemini the system cannot locate relevant documents.  
> Without LLaMA it cannot turn those documents into a natural language response.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Frontend** | Vanilla JS, HTML/CSS | No framework, hosted on GitHub Pages |
| **i18n** | Custom `i18n.js` | English / German toggle, localStorage |
| **Backend** | FastAPI + uvicorn | Python 3.11, async background tasks |
| **LLM** | Groq `llama-3.1-8b-instant` | Free tier, streaming via SSE |
| **Embeddings** | Google Gemini `gemini-embedding-001` | 768 dimensions, free tier |
| **Vector DB** | Supabase (PostgreSQL + pgvector) | HNSW index, cosine similarity |
| **Auth** | PyJWT | HS256, 12-hour expiry |
| **Tunnel** | ngrok | Local backend exposed for demo |
| **PDF parsing** | pdfplumber | Lazy import to save memory |

All LLM and embedding services used are on **free tiers**.

---

## Project Structure

```
demo_Mai_Munich/
├── index.html              # Chat UI
├── admin.html              # Admin panel (upload, manage documents)
├── config.js               # Single place to set the API base URL
├── css/
│   ├── style.css           # Main styles
│   └── admin.css           # Admin panel styles
├── js/
│   ├── app.js              # Chat logic (SSE streaming, message rendering)
│   ├── admin.js            # Admin logic (upload, job polling, delete)
│   └── i18n.js             # EN/DE translations + language toggle
└── backend/
    ├── main.py             # FastAPI app, all endpoints
    ├── auth.py             # JWT create / verify
    ├── requirements.txt
    ├── supabase_init.sql   # DB schema + match_documents function
    ├── .env.example
    ├── db/
    │   └── client.py       # Supabase client (lru_cache singleton)
    └── rag/
        ├── chunker.py      # Sliding-window text splitter
        ├── embedder.py     # Gemini embedding API wrapper
        └── retriever.py    # pgvector similarity search
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project with pgvector enabled
- A [Groq](https://console.groq.com) API key (free)
- A [Google AI Studio](https://aistudio.google.com) API key for Gemini (free)
- [ngrok](https://ngrok.com) (for local demo with public URL)

### 1. Database Setup

Run `backend/supabase_init.sql` once in your **Supabase SQL Editor**:

```sql
-- Creates: documents table, upload_jobs table,
--          match_documents() function, HNSW index
```

> **Note:** If you previously used a different vector dimension, drop and recreate the `documents` table before running.

### 2. Backend Setup

```bash
cd backend
cp .env.example .env
# Fill in your keys in .env

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Your `.env` file:

```env
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-strong-password
JWT_SECRET=your-random-secret-string
```

### 3. Expose Backend (for demo)

```bash
ngrok http 8000
# Copy the https://xxxx.ngrok-free.app URL
```

### 4. Frontend Setup

Edit `config.js` to point to your backend:

```js
const API_BASE = 'https://xxxx.ngrok-free.app';          // ngrok (local demo)
// const API_BASE = 'https://your-backend.onrender.com'; // production
```

Open `index.html` in a browser, or deploy the repo root to GitHub Pages.

### 5. Upload Documents

1. Go to `admin.html`
2. Log in with the credentials from your `.env`
3. Drag & drop PDF, TXT, or MD files
4. Click **Upload** — processing happens in the background
5. Watch the status badge change: 🔄 *AI learning…* → ✅ *AI learned ✓*

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | — | Returns JWT token |
| `POST` | `/api/chat` | — | RAG chat, streams SSE |
| `POST` | `/api/upload` | Bearer | Upload files (202 async) |
| `GET` | `/api/upload-jobs` | Bearer | List all upload jobs |
| `DELETE` | `/api/upload-jobs/{id}` | Bearer | Delete job + its chunks |
| `GET` | `/health` | — | Health check |

### SSE Event Format (`/api/chat`)

```jsonc
// Source citation (one per retrieved chunk)
{ "type": "tool_call", "tool": "vector_search", "input": { "source": "report.pdf", "similarity": 0.712 } }

// Text token (one per LLM token)
{ "type": "text", "content": "According to Source 1…" }

// End of stream
[DONE]
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `DEBUG_ENDPOINTS` | `false` | Set `true` to enable `/debug/*` routes |
| `EMAIL_ENABLED` | `false` | Set `true` to activate the email module |
| `EMBED_BATCH` | `5` | Chunks embedded per batch (memory limit) |
| `MAX_FILE_BYTES` | `10 MB` | Maximum upload file size |
| `CHUNK_SIZE` | `400` | Characters per chunk |
| `CHUNK_OVERLAP` | `80` | Overlap between consecutive chunks |
| `SIMILARITY_THRESHOLD` | `0.3` | Minimum cosine similarity for retrieval |
| `TOP_K` | `5` | Maximum chunks returned per query |

---

## Key Design Decisions

**Why local backend + ngrok instead of cloud hosting?**  
Free-tier cloud hosts (Render 512 MB) run out of memory when embedding large documents. Running locally eliminates that constraint for demo purposes.

**Why sequential embedding instead of concurrent?**  
Gemini free tier enforces strict rate limits. Concurrent calls caused 429 errors and thread-pool deadlocks. Sequential calls are slower but reliable.

**Why HNSW index instead of IVFFlat?**  
IVFFlat requires at least `100 × lists` rows to build meaningful clusters. With a small document set, it returns no results. HNSW works correctly at any dataset size.

**Why SSE instead of WebSockets?**  
SSE is simpler (one-directional, plain HTTP), works through ngrok without extra config, and is sufficient for token-by-token streaming.

---

## License

MIT
