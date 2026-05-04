import os
import json
import asyncio
import traceback
import groq
from dotenv import load_dotenv

load_dotenv()  # reads backend/.env when running locally

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from rag.chunker   import chunk_text
from rag.embedder  import embed_texts
from rag.retriever import retrieve, build_context
from db.client     import get_client
from auth          import create_token, verify_token, check_credentials


app = FastAPI(title="AI Agent Backend")

# ── Email module (toggle via EMAIL_ENABLED env var) ───────────────────────────
if os.getenv("EMAIL_ENABLED", "false").lower() == "true":
    from email_module.router import router as email_router
    app.include_router(email_router)
# To disable: set EMAIL_ENABLED=false (or remove the env var entirely)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # tighten to your GitHub Pages URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = groq.Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are a helpful AI agent assisting users with their questions.
When context from documents is provided, base your answer strictly on that context.
If the context doesn't contain enough information to answer the question, say clearly: "I don't have enough information to answer this."
Never make up facts, figures, or details that are not explicitly stated in the provided context.
Always cite which source you used (e.g. "According to Source 1...").
Be concise and precise."""


# ── Debug (remove after fixing) ───────────────────────────────────────────────

@app.get("/debug/supabase")
def debug_supabase():
    import traceback
    try:
        result = get_client().table("documents").select("id").limit(1).execute()
        return {"status": "ok", "rows": len(result.data)}
    except Exception as e:
        return {"status": "error", "error": str(e), "trace": traceback.format_exc()}

@app.get("/debug/embedding")
def debug_embedding():
    import traceback
    try:
        from rag.embedder import embed_query
        vec = embed_query("test")
        return {"status": "ok", "dimensions": len(vec)}
    except Exception as e:
        return {"status": "error", "error": str(e), "trace": traceback.format_exc()}

@app.get("/debug/upload-pipeline")
def debug_upload_pipeline():
    """Step-by-step test of the full upload pipeline."""
    import traceback
    results = {}
    try:
        # Step 1: chunk
        from rag.chunker import chunk_text
        chunks = chunk_text("This is a test document for debugging.", "test.txt")
        results["step1_chunk"] = f"ok – {len(chunks)} chunks"

        # Step 2: embed
        from rag.embedder import embed_texts
        vectors = embed_texts([c["content"] for c in chunks])
        results["step2_embed"] = f"ok – {len(vectors)} vectors, dim={len(vectors[0])}"

        # Step 3: insert into Supabase
        rows = [{"content": c["content"], "embedding": v, "metadata": c["metadata"]}
                for c, v in zip(chunks, vectors)]
        get_client().table("documents").insert(rows).execute()
        results["step3_insert"] = "ok"

        return {"status": "ok", "steps": results}
    except Exception as e:
        results["error"] = str(e)
        results["trace"] = traceback.format_exc()
        return {"status": "error", "steps": results}


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginRequest):
    if not check_credentials(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(body.username)}


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Document upload (admin protected) ─────────────────────────────────────────

MAX_FILE_BYTES = 10 * 1024 * 1024   # 10 MB hard limit
EMBED_BATCH    = 5                   # embed 5 chunks at a time to stay under memory


def _process_upload(job_id: str, raw: bytes, filename: str):
    """Background task: extract → chunk → embed → insert, then update job status."""
    from supabase import create_client
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    try:
        text = _extract_text(raw, filename)
        del raw
        if not text.strip():
            db.table("upload_jobs").update({"status": "error", "updated_at": "now()"}).eq("id", job_id).execute()
            return

        chunks = chunk_text(text, filename)
        del text
        total = 0

        for i in range(0, len(chunks), EMBED_BATCH):
            batch   = chunks[i : i + EMBED_BATCH]
            vectors = embed_texts([c["content"] for c in batch])
            rows    = [
                {"content": c["content"], "embedding": v, "metadata": c["metadata"]}
                for c, v in zip(batch, vectors)
            ]
            db.table("documents").insert(rows).execute()
            total += len(batch)

        db.table("upload_jobs").update({
            "status": "done",
            "chunks": total,
            "updated_at": "now()"
        }).eq("id", job_id).execute()

    except Exception as e:
        print(f"[UPLOAD ERROR] {filename}: {e}")
        traceback.print_exc()
        db.table("upload_jobs").update({"status": "error", "updated_at": "now()"}).eq("id", job_id).execute()


@app.post("/api/upload", status_code=202)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    _: str = Depends(verify_token),
):
    """
    Accept files, create a job record, then process in background.
    Returns job IDs immediately for status polling.
    """
    results = []

    for file in files:
        raw = await file.read()

        if len(raw) > MAX_FILE_BYTES:
            results.append({"filename": file.filename, "status": "skipped – file too large (max 10 MB)"})
            continue

        # Create job record first
        job = get_client().table("upload_jobs").insert({
            "filename": file.filename,
            "status": "processing",
        }).execute().data[0]

        background_tasks.add_task(_process_upload, job["id"], raw, file.filename)
        results.append({"filename": file.filename, "job_id": job["id"], "status": "processing"})

    return {"results": results}


@app.get("/api/upload-jobs")
def get_upload_jobs(_: str = Depends(verify_token)):
    """Return all upload jobs with their status."""
    rows = (
        get_client()
        .table("upload_jobs")
        .select("*")
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return {"jobs": rows}


@app.delete("/api/upload-jobs/{job_id}")
def delete_upload_job(job_id: str, _: str = Depends(verify_token)):
    """Delete a job record and its associated document chunks."""
    job = get_client().table("upload_jobs").select("filename").eq("id", job_id).execute().data
    if job:
        filename = job[0]["filename"]
        get_client().table("documents").delete().eq("metadata->>filename", filename).execute()
    get_client().table("upload_jobs").delete().eq("id", job_id).execute()
    return {"status": "deleted", "job_id": job_id}


# ── Chat (SSE streaming) ──────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(
    message: str = Form(...),
    conversation_id: Optional[str] = Form(None),
):
    """
    RAG chat endpoint — retrieves relevant chunks then streams Claude's response.
    Returns Server-Sent Events.
    """
    chunks  = retrieve(message)
    context = build_context(chunks)

    user_message = _build_user_message(message, context)

    return StreamingResponse(
        _stream_response(user_message, chunks),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_text(raw: bytes, filename: str) -> str:
    """Extract plain text from uploaded file."""
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        import io
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)

    # .txt / .md and anything else — decode as UTF-8
    return raw.decode("utf-8", errors="ignore")


def _build_user_message(question: str, context: str) -> str:
    if context:
        return (
            f"Use the following document context to answer the question.\n\n"
            f"<context>\n{context}\n</context>\n\n"
            f"Question: {question}"
        )
    return question


async def _stream_response(user_message: str, source_chunks: list):
    """Yield SSE events: tool_call card first, then streamed text tokens."""

    # Show which sources were found
    if source_chunks:
        for chunk in source_chunks:
            filename = chunk.get("metadata", {}).get("filename", "unknown")
            event = {
                "type":   "tool_call",
                "tool":   "vector_search",
                "input":  {"source": filename, "similarity": round(chunk.get("similarity", 0), 3)},
            }
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0)

    # Stream Groq's answer token by token
    stream = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=1024,
        stream=True,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            event = {"type": "text", "content": token}
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0)

    yield "data: [DONE]\n\n"


# ── Document management (admin protected) ─────────────────────────────────────

@app.get("/api/documents")
def list_documents(_: str = Depends(verify_token)):
    """Return all uploaded documents grouped by filename."""
    rows = (
        get_client()
        .table("documents")
        .select("metadata, created_at")
        .execute()
        .data
    )

    # Group by filename and count chunks
    summary: dict = {}
    for row in rows:
        name = row["metadata"].get("filename", "unknown")
        if name not in summary:
            summary[name] = {"filename": name, "chunks": 0, "uploaded_at": row["created_at"]}
        summary[name]["chunks"] += 1

    return {"documents": sorted(summary.values(), key=lambda d: d["uploaded_at"], reverse=True)}


@app.delete("/api/documents/{filename}")
def delete_document(filename: str, _: str = Depends(verify_token)):
    """Delete all chunks belonging to a given filename."""
    get_client().table("documents").delete().eq("metadata->>filename", filename).execute()
    return {"status": "deleted", "filename": filename}
