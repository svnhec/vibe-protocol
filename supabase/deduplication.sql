-- Function to check if a similar market already exists
-- Returns TRUE if a duplicate is found (Similarity > threshold)
create or replace function check_duplicate_market(
  new_embedding vector(768),
  match_threshold float
)
returns boolean
language plpgsql
as $$
declare
  is_duplicate boolean;
begin
  select exists (
    select 1
    from public.markets
    where status = 'OPEN'
    and 1 - (embedding <=> new_embedding) > match_threshold
  ) into is_duplicate;

  return is_duplicate;
end;
$$;

