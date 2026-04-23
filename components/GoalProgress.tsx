"use client";

import { motion } from "framer-motion";
import { CLUB_STATS, CURRENT_GOALS, TARGET_GOALS } from "@/lib/goals";

export default function GoalProgress() {
  const totalWidth = 100;
  let accumulated = 0;

  return (
    <section className="px-4 py-16 max-w-4xl mx-auto">
      <motion.h2
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="text-2xl sm:text-3xl font-bold text-center mb-8"
        style={{ fontFamily: "var(--font-display)" }}
      >
        <span className="text-white/80">Le chemin vers </span>
        <span className="animate-shimmer">1000</span>
      </motion.h2>

      {/* Stacked bar */}
      <motion.div
        initial={{ opacity: 0, scaleX: 0 }}
        whileInView={{ opacity: 1, scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1 }}
        className="h-10 sm:h-12 rounded-full overflow-hidden flex border border-white/10 mb-6"
      >
        {CLUB_STATS.map((club) => {
          const width = (club.goals / TARGET_GOALS) * totalWidth;
          accumulated += width;
          return (
            <motion.div
              key={club.club}
              initial={{ width: 0 }}
              whileInView={{ width: `${width}%` }}
              viewport={{ once: true }}
              transition={{ duration: 1, delay: 0.2 }}
              className="h-full relative group cursor-pointer"
              style={{ backgroundColor: club.color }}
              title={`${club.club}: ${club.goals} buts`}
            >
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="text-[10px] sm:text-xs font-bold text-white drop-shadow-lg whitespace-nowrap">
                  {club.goals}
                </span>
              </div>
            </motion.div>
          );
        })}
        {/* Remaining */}
        <div
          className="h-full bg-white/5"
          style={{ width: `${totalWidth - accumulated}%` }}
        />
      </motion.div>

      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-3 sm:gap-4">
        {CLUB_STATS.map((club) => (
          <motion.div
            key={club.club}
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="flex items-center gap-2"
          >
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: club.color }}
            />
            <span className="text-xs sm:text-sm text-white/60">
              {club.club} ({club.goals})
            </span>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
