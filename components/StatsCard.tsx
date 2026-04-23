"use client";

import { motion } from "framer-motion";

interface StatsCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  delay?: number;
  highlight?: boolean;
}

export default function StatsCard({ label, value, subtitle, delay = 0, highlight = false }: StatsCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.5 }}
      whileHover={{ scale: 1.03, y: -4 }}
      className={`
        relative overflow-hidden rounded-2xl border p-5 sm:p-6 transition-all duration-300
        ${highlight
          ? "border-gold/30 bg-gold/5 glow-gold"
          : "border-white/10 bg-white/[0.02] hover:border-white/20"
        }
      `}
    >
      <p className="text-xs sm:text-sm uppercase tracking-wider text-white/40 mb-2">{label}</p>
      <p
        className={`text-2xl sm:text-3xl md:text-4xl font-bold ${highlight ? "text-gold" : "text-white/90"}`}
        style={{ fontFamily: "var(--font-display)" }}
      >
        {value}
      </p>
      {subtitle && (
        <p className="text-xs sm:text-sm text-white/30 mt-1">{subtitle}</p>
      )}
      {highlight && (
        <div className="absolute top-0 right-0 w-20 h-20 bg-gold/10 rounded-full -translate-y-1/2 translate-x-1/2 blur-xl" />
      )}
    </motion.div>
  );
}
