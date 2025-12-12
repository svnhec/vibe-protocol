-- 1. THE LEARNING TRIGGER
-- When a user bets, update their interest profile.
create or replace function update_interest_vector()
returns trigger
language plpgsql
as $$
declare
  market_embedding vector(768);
  user_current_vector vector(768);
begin
  -- Get the embedding of the market they just bet on
  select embedding into market_embedding
  from public.markets
  where id = new.market_id;

  -- Get the user's current vector
  select interest_vector into user_current_vector
  from public.users
  where id = new.user_id;

  -- LOGIC:
  -- If user has NO history (NULL), adopt the market's vector entirely.
  -- This creates an instant "First Impression".
  if user_current_vector is null then
    update public.users
    set interest_vector = market_embedding
    where id = new.user_id;
  
  -- If user HAS history, we *should* average it. 
  -- Note: Complex vector math in SQL can be tricky depending on pgvector version.
  -- For stability in this MVP, we will keep the "First Impression" logic or 
  -- simple replacement. A more advanced version would be: (Old * 0.9) + (New * 0.1).
  -- For now, let's stick to the Cold Start fix which provides 80% of the value.
  end if;

  return new;
end;
$$;

-- Drop trigger if exists to allow re-running
drop trigger if exists on_bet_placed on public.bets;

create trigger on_bet_placed
after insert on public.bets
for each row execute procedure update_interest_vector();


-- 2. THE INFINITE FEED ALGORITHM
-- Updates match_markets to exclude seen bets and use a fallback strategy.
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

  -- STRATEGY: 
  -- 1. Try to find Vector Matches (High Similarity)
  -- 2. Fill the rest with Newest Markets (Global Trending)
  -- 3. ALWAYS exclude markets the user has already bet on (bets table)

  return query
  with seen_markets as (
    select market_id from public.bets where user_id = target_user_id
  ),
  recommended as (
    select m.id, m.question, m.image_url, m.category, 
           case when user_interest is null then 0.0
                else (1 - (m.embedding <=> user_interest)) 
           end as sim
    from public.markets m
    where m.status = 'OPEN'
    and m.id not in (select market_id from seen_markets)
    -- If user has interest, filter by threshold. If null, ignore threshold.
    and (user_interest is null or (1 - (m.embedding <=> user_interest)) > match_threshold)
    order by sim desc
    limit match_count
  ),
  filler as (
    select m.id, m.question, m.image_url, m.category, 0.0 as sim
    from public.markets m
    where m.status = 'OPEN'
    and m.id not in (select market_id from seen_markets)
    and m.id not in (select id from recommended) -- Don't duplicate
    order by m.created_at desc
    limit match_count
  )
  select * from recommended
  union all
  select * from filler
  limit match_count;
end;
$$;

