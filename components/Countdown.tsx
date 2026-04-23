"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { calculateCountdown, CURRENT_GOALS, TARGET_GOALS, GOALS_REMAINING, ESTIMATED_DATE } from "@/lib/goals";

function CountdownUnit({ value, label }: { value: number; label: string }) {
  const display = String(value).padStart(2, "0");

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <div className="bg-white/5 border border-white/10 rounded-xl px-3 py-3 sm:px-5 sm:py-4 md:px-6 md:py-5 min-w-[70px] sm:min-w-[90px] md:min-w-[110px] glow-gold">
          <AnimatePresence mode="popLayout">
            <motion.span
              key={value}
              initial={{ y: -20, opacity: 0, rotateX: -80 }}
              animate={{ y: 0, opacity: 1, rotateX: 0 }}
              exit={{ y: 20, opacity: 0, rotateX: 80 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="block text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold text-center"
              style={{
                fontFamily: "var(--font-display)",
                background: "linear-gradient(180deg, #F0D060 0%, #D4AF37 50%, #B8960C 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              {display}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>
      <span className="mt-2 text-[10px] sm:text-xs md:text-sm uppercase tracking-[0.2em] text-white/40 font-medium">
        {label}
      </span>
    </div>
  );
}

export default function Countdown() {
  const [countdown, setCountdown] = useState(calculateCountdown());
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const interval = setInterval(() => {
      setCountdown(calculateCountdown());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!mounted) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <div className="h-20 w-20 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
      </div>
    );
  }

  const estimatedDateStr = ESTIMATED_DATE.toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <section className="relative flex flex-col items-center justify-center min-h-[85vh] px-4 py-12">
      {/* Background effects */}
      <div className="absolute inset-0 bg-gradient-radial pointer-events-none" />
      <div className="absolute inset-0 bg-grid pointer-events-none opacity-50" />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="relative z-10 text-center"
      >
        {/* Title */}
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-sm sm:text-base md:text-lg uppercase tracking-[0.3em] text-white/50 mb-6 font-light"
        >
          Le 1000e but dans
        </motion.p>

        {/* Countdown */}
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="flex gap-2 sm:gap-3 md:gap-4 lg:gap-6 justify-center mb-8"
        >
          <CountdownUnit value={countdown.days} label="Jours" />
          <div className="flex items-center text-2xl sm:text-4xl md:text-5xl text-gold/40 font-light self-start mt-5 sm:mt-7 md:mt-8">:</div>
          <CountdownUnit value={countdown.hours} label="Heures" />
          <div className="flex items-center text-2xl sm:text-4xl md:text-5xl text-gold/40 font-light self-start mt-5 sm:mt-7 md:mt-8">:</div>
          <CountdownUnit value={countdown.minutes} label="Minutes" />
          <div className="flex items-center text-2xl sm:text-4xl md:text-5xl text-gold/40 font-light self-start mt-5 sm:mt-7 md:mt-8">:</div>
          <CountdownUnit value={countdown.seconds} label="Secondes" />
        </motion.div>

        {/* Goals counter */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
          className="mb-6"
        >
          <div className="inline-flex items-baseline gap-2">
            <span className="text-5xl sm:text-6xl md:text-8xl font-black animate-shimmer" style={{ fontFamily: "var(--font-display)" }}>
              {CURRENT_GOALS}
            </span>
            <span className="text-xl sm:text-2xl md:text-3xl text-white/30 font-light">/ {TARGET_GOALS}</span>
          </div>
          <p className="text-white/40 text-sm sm:text-base mt-2">
            Plus que <span className="text-gold font-semibold">{GOALS_REMAINING} buts</span> pour l&apos;histoire
          </p>
        </motion.div>

        {/* Progress bar */}
        <motion.div
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          transition={{ delay: 1, duration: 0.8 }}
          className="w-full max-w-md mx-auto mb-6"
        >
          <div className="h-2 sm:h-3 bg-white/5 rounded-full overflow-hidden border border-white/10">
            <div
              className="h-full progress-bar rounded-full"
              style={{ width: `${(CURRENT_GOALS / TARGET_GOALS) * 100}%` }}
            />
          </div>
          <div className="flex justify-between mt-2 text-xs text-white/30">
            <span>0</span>
            <span className="text-gold/60">{((CURRENT_GOALS / TARGET_GOALS) * 100).toFixed(1)}%</span>
            <span>1000</span>
          </div>
        </motion.div>

        {/* Estimated date */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.6 }}
          className="text-xs sm:text-sm text-white/25"
        >
          Date estimée : ~{estimatedDateStr}
        </motion.p>
      </motion.div>
    </section>
  );
}
