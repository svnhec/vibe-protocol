'use client';

import { useState } from 'react';
import { motion, useMotionValue, useTransform, PanInfo, AnimatePresence } from 'framer-motion';
import { Haptics, ImpactStyle } from '@capacitor/haptics';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

interface PredictionCardProps {
  id: string;
  question: string;
  imageUrl: string;
  odds: string;
  category: string;
  onSwipe: (direction: 'left' | 'right') => void;
}

export default function PredictionCard({
  question,
  imageUrl,
  odds,
  category,
  onSwipe,
}: PredictionCardProps) {
  const [exitX, setExitX] = useState<number>(0);

  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-25, 25]);
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0, 1, 1, 1, 0]);

  // Visual feedback stamps opacity
  const yesOpacity = useTransform(x, [0, 100], [0, 1]);
  const noOpacity = useTransform(x, [-100, 0], [1, 0]);

  const handleDragEnd = async (event: any, info: PanInfo) => {
    const threshold = 100;
    
    if (info.offset.x > threshold) {
      // Swiped Right (YES)
      setExitX(1000);
      await Haptics.impact({ style: ImpactStyle.Heavy });
      onSwipe('right');
    } else if (info.offset.x < -threshold) {
      // Swiped Left (NO)
      setExitX(-1000);
      await Haptics.impact({ style: ImpactStyle.Heavy });
      onSwipe('left');
    }
  };

  return (
    <motion.div
      style={{ x, rotate, opacity }}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      onDragEnd={handleDragEnd}
      className="absolute top-0 h-[600px] w-full max-w-sm cursor-grab active:cursor-grabbing"
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ x: exitX, opacity: 0, transition: { duration: 0.2 } }}
    >
      <div className="relative h-full w-full overflow-hidden rounded-3xl bg-black shadow-2xl border border-zinc-800">
        {/* Background Image */}
        <div 
          className="absolute inset-0 bg-cover bg-center opacity-60"
          style={{ backgroundImage: `url(${imageUrl})` }}
        />
        
        {/* Gradient Overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent" />

        {/* Stamps Overlay */}
        <motion.div 
          style={{ opacity: yesOpacity }}
          className="absolute top-10 left-10 rounded-xl border-4 border-green-500 px-4 py-2 text-4xl font-bold text-green-500 -rotate-12 z-20 bg-black/20 backdrop-blur-sm"
        >
          YES
        </motion.div>

        <motion.div 
          style={{ opacity: noOpacity }}
          className="absolute top-10 right-10 rounded-xl border-4 border-red-500 px-4 py-2 text-4xl font-bold text-red-500 rotate-12 z-20 bg-black/20 backdrop-blur-sm"
        >
          NO
        </motion.div>

        {/* Content */}
        <div className="absolute bottom-0 w-full p-6 text-white">
          <div className="mb-2 inline-block rounded-full bg-zinc-800/80 px-3 py-1 text-xs font-medium backdrop-blur-md border border-zinc-700">
            {category}
          </div>
          
          <h2 className="mb-4 text-3xl font-bold leading-tight shadow-black drop-shadow-lg">
            {question}
          </h2>

          <div className="flex items-center justify-between rounded-xl bg-zinc-900/60 p-4 backdrop-blur-md border border-zinc-800">
            <div className="text-center">
              <p className="text-xs text-zinc-400">Yes Pool</p>
              <p className="font-bold text-green-400">92%</p>
            </div>
            <div className="h-8 w-px bg-zinc-700" />
            <div className="text-center">
              <p className="text-xs text-zinc-400">Current Odds</p>
              <p className="text-xl font-bold">{odds}</p>
            </div>
            <div className="h-8 w-px bg-zinc-700" />
            <div className="text-center">
              <p className="text-xs text-zinc-400">No Pool</p>
              <p className="font-bold text-red-400">8%</p>
            </div>
          </div>
          
          <p className="mt-4 text-center text-sm text-zinc-500">
            Swipe Right for YES • Swipe Left for NO
          </p>
        </div>
      </div>
    </motion.div>
  );
}

