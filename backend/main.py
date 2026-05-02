import os
import json
import asyncio
import anthropic
import pdfplumber

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional

from rag.chunker   import chunk_text
from rag.embedder  import embed_texts
from rag.retriever import retrieve, build_context
from db.client     import get_client


app = FastAPI(title="AI Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # tighten to your GitHub Pages URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a helpful AI agent assisting users with their questions.
When context from documents is provided, base your answer on that context.
If the context doesn't contain enough information, say so clearly.
Always cite which source you used (e.g. "According to Source 1...").
Be concise and precise."""


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Document upload ───────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Accept one or more files, chunk and embed them, then store in Supabase.
    Supports: .txt, .pdf, .md
    """
    results = []

    for file in files:
        raw = await file.read()
        text = _extract_text(raw, file.filename)

        if not text.strip():
            results.append({"filename": file.filename, "status": "skipped – empty content"})
            continue

        chunks  = chunk_text(text, file.filename)
        vectors = embed_texts([c["content"] for c in chunks])

        rows = [
            {
                "content":   c["content"],
                "embedding": v,
                "metadata":  c["metadata"],
            }
            for c, v in zip(chunks, vectors)
        ]

        get_client().table("documents").insert(rows).execute()
        results.append({"filename": file.filename, "chunks": len(chunks), "status": "ok"})

    return {"results": results}


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

    # Stream Claude's answer token by token
    with claude.messages.stream(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for token in stream.text_stream:
            event = {"type": "text", "content": token}
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0)

    yield "data: [DONE]\n\n"
