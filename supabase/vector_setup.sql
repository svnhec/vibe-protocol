-- Enable the pgvector extension to work with embeddings
create extension if not exists vector;

-- 1. Add embedding column to MARKETS
-- 1536 dimensions is standard for OpenAI text-embedding-3-small
alter table public.markets 
add column if not exists embedding vector(768);

-- 2. Add interest_vector to USERS
-- This represents what the user likes (updated when they swipe)
alter table public.users 
add column if not exists interest_vector vector(768);

-- 3. The Recommendation Algorithm (RPC)
-- Finds markets that are semantically similar to the user's interest_vector
-- or just returns new markets if user has no history.
create or replace function match_markets(
  target_user_id uuid,
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  question text,
  image_url text,
  category text,
  similarity float
)
language plpgsql
as $$
declare
  user_interest vector(768);
begin
  -- Get the user's interest vector
  select interest_vector into user_interest
  from public.users
  where id = target_user_id;

  -- If user has no vector (new user), just return newest markets
  if user_interest is null then
    return query
    select m.id, m.question, m.image_url, m.category, 0.0::float as similarity
    from public.markets m
    where m.status = 'OPEN'
    order by m.created_at desc
    limit match_count;
  else
    -- Vector Search: Return markets closest to user interest
    -- (1 - (m.embedding <=> user_interest)) gives cosine similarity
    return query
    select m.id, m.question, m.image_url, m.category, (1 - (m.embedding <=> user_interest))::float as similarity
    from public.markets m
    where m.status = 'OPEN'
    and 1 - (m.embedding <=> user_interest) > match_threshold
    order by similarity desc
    limit match_count;
  end if;
end;
$$;

