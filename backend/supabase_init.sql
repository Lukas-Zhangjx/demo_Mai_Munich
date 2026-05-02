-- Run this once in Supabase SQL Editor

-- 1. Enable pgvector extension
create extension if not exists vector;

-- 2. Documents table (stores chunks + embeddings)
create table if not exists documents (
  id          uuid    default gen_random_uuid() primary key,
  content     text    not null,
  embedding   vector(512),          -- voyage-3-lite dimension
  metadata    jsonb   default '{}',
  created_at  timestamptz default now()
);

-- 3. Vector similarity index (cosine distance)
create index if not exists documents_embedding_idx
  on documents using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- 4. Match function used by retriever.py
create or replace function match_documents(
  query_embedding vector(512),
  match_threshold float,
  match_count     int
)
returns table (
  id         uuid,
  content    text,
  metadata   jsonb,
  similarity float
)
language sql stable
as $$
  select
    id,
    content,
    metadata,
    1 - (embedding <=> query_embedding) as similarity
  from documents
  where 1 - (embedding <=> query_embedding) > match_threshold
  order by embedding <=> query_embedding
  limit match_count;
$$;
