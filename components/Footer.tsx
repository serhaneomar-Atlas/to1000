"use client";

import { LAST_UPDATED, CURRENT_GOALS } from "@/lib/goals";

export default function Footer() {
  return (
    <footer className="border-t border-white/5 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-white/30">
          <div className="flex items-center gap-4">
            <span
              className="font-bold text-sm"
              style={{
                background: "linear-gradient(135deg, #F0D060, #D4AF37)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              TO1000.com
            </span>
            <span>|</span>
            <span>Le compte à rebours du 1000e but de CR7</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Dernière mise à jour : {LAST_UPDATED}</span>
            <span>|</span>
            <span>{CURRENT_GOALS} buts vérifiés</span>
          </div>
        </div>
        <p className="text-center text-[10px] text-white/15 mt-4">
          Ce site n&apos;est pas affilié à Cristiano Ronaldo. Sources : ESPN, Transfermarkt, Wikipedia.
        </p>
      </div>
    </footer>
  );
}
