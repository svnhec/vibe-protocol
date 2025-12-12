'use client';

import { useState, useEffect } from 'react';
import { AnimatePresence } from 'framer-motion';
import PredictionCard from './components/PredictionCard';
import { usePrivy } from '@privy-io/react-auth';
import { supabase } from './lib/supabase';

interface Market {
  id: string;
  question: string;
  image_url: string;
  category: string;
  similarity?: number;
}

export default function Home() {
  const { login, authenticated, user, logout } = usePrivy();
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);

  // 1. Sync User & Fetch Smart Feed
  useEffect(() => {
    async function loadFeed() {
      setLoading(true);
      
      // A. Sync User if logged in
      let dbUserId = null;
      if (authenticated && user) {
        const { data: userData } = await supabase.from('users').upsert({
          privy_user_id: user.id,
          wallet_address: user.wallet?.address,
        }, { onConflict: 'privy_user_id' }).select('id').single();
        
        if (userData) dbUserId = userData.id;
      }

      // B. Fetch Feed (AI Recommended vs Global)
      if (dbUserId) {
        // Logged in? Use Vector Search Algorithm
        console.log("🧠 Fetching AI-curated feed for:", dbUserId);
        const { data, error } = await supabase.rpc('match_markets', {
          target_user_id: dbUserId,
          match_threshold: 0.0, // Low threshold to ensure we see content
          match_count: 10
        });
        
        if (!error && data && data.length > 0) {
          setMarkets(data);
          setLoading(false);
          return;
        }
      }

      // C. Fallback (Global Feed) - For guests or if AI finds nothing
      console.log("🌍 Fetching global feed");
      const { data, error } = await supabase
        .from('markets')
        .select('*')
        .eq('status', 'OPEN')
        .order('created_at', { ascending: false })
        .limit(10);

      if (data) setMarkets(data);
      setLoading(false);
    }

    loadFeed();
  }, [authenticated, user]);

  const removeMarket = (id: string) => {
    setMarkets((prev) => prev.filter((market) => market.id !== id));
  };

  const handleSwipe = async (marketId: string, direction: 'left' | 'right') => {
    if (!authenticated) {
      alert("Please login to place a bet!");
      return;
    }

    console.log(`User voted ${direction.toUpperCase()} on market ${marketId}`);
    
    try {
        const { data: userData } = await supabase
            .from('users')
            .select('id')
            .eq('privy_user_id', user?.id)
            .single();

        if (userData) {
             const { error } = await supabase.from('bets').insert({
                user_id: userData.id,
                market_id: marketId,
                amount: 10,
                currency: 'GOLD',
                direction: direction === 'right' ? 'YES' : 'NO',
                potential_payout: 20
            });
            if (error) console.error("Bet error:", error);
            else console.log("Bet saved successfully!");
        }
    } catch (e) {
        console.error("Error placing bet:", e);
    }

    setTimeout(() => removeMarket(marketId), 200); 
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-black text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-white border-t-transparent" />
          <p className="text-sm text-zinc-400 font-mono">Curating your vibe...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black p-4 overflow-hidden relative">
      {/* Header with Login */}
      <div className="absolute top-4 right-4 z-50">
        {authenticated ? (
            <div className="flex items-center gap-2 bg-zinc-900/80 px-4 py-2 rounded-full border border-zinc-800 backdrop-blur-md shadow-xl">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm font-medium text-white">
                {user?.email?.address || user?.wallet?.address?.slice(0, 6) + '...'}
              </span>
              <button 
                onClick={logout}
                className="ml-2 text-xs text-zinc-400 hover:text-white transition-colors"
              >
                Sign Out
              </button>
            </div>
        ) : (
          <button
            onClick={login}
            className="rounded-full bg-white px-6 py-2 text-sm font-bold text-black transition hover:scale-105 active:scale-95 shadow-lg shadow-white/10"
          >
            Login / Connect
          </button>
        )}
      </div>

      <div className="relative h-[600px] w-full max-w-sm">
        <AnimatePresence>
          {markets.length > 0 ? (
            markets.map((market) => (
              <PredictionCard
                key={market.id}
                id={market.id}
                question={market.question}
                imageUrl={market.image_url}
                category={market.category}
                odds="+100" 
                onSwipe={(dir) => handleSwipe(market.id, dir)}
              />
            ))
          ) : (
             <div className="flex flex-col items-center justify-center h-full text-center p-8 border border-zinc-800 rounded-3xl bg-zinc-900/50">
                <p className="text-xl font-bold mb-2">Caught up! 🎉</p>
                <p className="text-sm text-zinc-400">Our AI is scanning for new tea...</p>
             </div>
          )}
        </AnimatePresence>
      </div>

      <div className="mt-8 flex gap-4">
        <div className="h-2 w-2 rounded-full bg-white/20" />
        <div className="h-2 w-2 rounded-full bg-white" />
        <div className="h-2 w-2 rounded-full bg-white/20" />
      </div>
    </main>
  );
}
