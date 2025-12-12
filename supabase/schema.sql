-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. USERS TABLE
-- -----------------------------------------------------------------------------
create table public.users (
  id uuid primary key references auth.users(id) on delete cascade, -- Links to Supabase Auth / Privy
  privy_user_id text unique,
  username text unique,
  wallet_address text unique,
  gold_balance bigint default 1000, -- Vibe Gold (Entertainment)
  cash_balance decimal(10, 2) default 0.00, -- Vibe Cash (Redeemable)
  is_kyc_verified boolean default false,
  referral_code text unique,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- -----------------------------------------------------------------------------
-- 2. MARKETS TABLE
-- -----------------------------------------------------------------------------
create type market_status as enum ('OPEN', 'RESOLVED', 'CANCELED');

create table public.markets (
  id uuid primary key default uuid_generate_v4(),
  question text not null,
  image_url text not null,
  category text not null,
  resolution_source text not null, -- URL agent checks
  uma_assertion_id text, -- On-chain Oracle ID
  status market_status default 'OPEN',
  outcomes jsonb default '{"yes": 0.5, "no": 0.5}', -- Initial odds
  yes_pool decimal(20, 6) default 0,
  no_pool decimal(20, 6) default 0,
  expiration_date timestamptz not null,
  created_at timestamptz default now()
);

-- -----------------------------------------------------------------------------
-- 3. BETS TABLE
-- -----------------------------------------------------------------------------
create type currency_type as enum ('GOLD', 'CASH');
create type bet_direction as enum ('YES', 'NO');

create table public.bets (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references public.users(id) not null,
  market_id uuid references public.markets(id) not null,
  amount decimal(20, 6) not null,
  currency currency_type not null,
  direction bet_direction not null,
  potential_payout decimal(20, 6) not null,
  status text default 'OPEN', -- OPEN, WON, LOST
  created_at timestamptz default now()
);

-- -----------------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS) POLICIES
-- -----------------------------------------------------------------------------
alter table public.users enable row level security;
alter table public.markets enable row level security;
alter table public.bets enable row level security;

-- Users: Read public profile, Update own profile
create policy "Public profiles are viewable by everyone" 
  on public.users for select using (true);

create policy "Users can update own profile" 
  on public.users for update using (auth.uid() = id);

-- Markets: Everyone can view markets. Only service role can insert/update.
create policy "Markets are viewable by everyone" 
  on public.markets for select using (true);

-- Bets: Users can view and create their own bets.
create policy "Users can view own bets" 
  on public.bets for select using (auth.uid() = user_id);

create policy "Users can create own bets" 
  on public.bets for insert with check (auth.uid() = user_id);

-- -----------------------------------------------------------------------------
-- FUNCTIONS
-- -----------------------------------------------------------------------------
-- Auto-update updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language 'plpgsql';

create trigger update_users_updated_at
before update on public.users
for each row execute procedure update_updated_at_column();

