import Countdown from "@/components/Countdown";
import GoalProgress from "@/components/GoalProgress";
import StatsCard from "@/components/StatsCard";
import {
  CURRENT_GOALS,
  GOALS_REMAINING,
  CLUB_STATS,
  MILESTONE_GOALS,
} from "@/lib/goals";

export default function Home() {
  const totalAppearances = CLUB_STATS.reduce((acc, c) => acc + c.appearances, 0);
  const goalsPerMatch = (CURRENT_GOALS / totalAppearances).toFixed(2);
  const currentSeason = CLUB_STATS.find((c) => c.club === "Al Nassr");

  return (
    <>
      {/* Hero — Countdown */}
      <Countdown />

      {/* Quick Stats */}
      <section className="px-4 py-12 max-w-5xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
          <StatsCard
            label="Buts en carrière"
            value={CURRENT_GOALS}
            subtitle="Clubs + sélection"
            delay={0}
            highlight
          />
          <StatsCard
            label="Buts restants"
            value={GOALS_REMAINING}
            subtitle="pour le 1000e"
            delay={0.1}
            highlight
          />
          <StatsCard
            label="Ratio buts/match"
            value={goalsPerMatch}
            subtitle={`sur ${totalAppearances} matchs`}
            delay={0.2}
          />
          <StatsCard
            label="Saison actuelle"
            value={currentSeason?.goals || 0}
            subtitle="Al Nassr 2025/26"
            delay={0.3}
          />
        </div>
      </section>

      {/* Goal Progress Bar by Club */}
      <GoalProgress />

      {/* Milestones */}
      <section className="px-4 py-16 max-w-4xl mx-auto">
        <h2
          className="text-2xl sm:text-3xl font-bold text-center mb-10"
          style={{ fontFamily: "var(--font-display)" }}
        >
          <span className="text-white/80">Les </span>
          <span className="animate-shimmer">milestones</span>
        </h2>

        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-4 sm:left-6 top-0 bottom-0 w-px bg-gradient-to-b from-gold/40 via-gold/20 to-transparent" />

          <div className="space-y-6 sm:space-y-8">
            {MILESTONE_GOALS.map((milestone) => (
              <div key={milestone.number} className="relative pl-12 sm:pl-16">
                {/* Dot */}
                <div className="absolute left-2.5 sm:left-4 top-2 w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-gold/80 border-2 border-[#0A0A0A] shadow-[0_0_8px_rgba(212,175,55,0.4)]" />

                <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 sm:p-5 hover:border-gold/20 transition-colors">
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2">
                    <span className="text-lg sm:text-xl font-bold text-gold" style={{ fontFamily: "var(--font-display)" }}>
                      But #{milestone.number}
                    </span>
                    <span className="text-xs text-white/30 bg-white/5 px-2 py-0.5 rounded-full">
                      {new Date(milestone.date).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" })}
                    </span>
                  </div>
                  <p className="text-sm text-white/60 mb-1">
                    vs {milestone.opponent} — {milestone.competition}
                  </p>
                  <p className="text-xs text-white/30">{milestone.description}</p>
                </div>
              </div>
            ))}

            {/* Future 1000th goal */}
            <div className="relative pl-12 sm:pl-16">
              <div className="absolute left-2.5 sm:left-4 top-2 w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-gold animate-pulse border-2 border-[#0A0A0A] shadow-[0_0_12px_rgba(212,175,55,0.6)]" />
              <div className="bg-gold/5 border border-gold/20 rounded-xl p-4 sm:p-5 glow-gold">
                <span className="text-lg sm:text-xl font-bold text-gold" style={{ fontFamily: "var(--font-display)" }}>
                  But #1000
                </span>
                <p className="text-sm text-gold/60 mt-1">
                  L&apos;histoire est en marche...
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Share */}
      <section className="px-4 py-16 text-center">
        <p className="text-white/40 text-sm mb-4">Partagez le compte à rebours</p>
        <div className="flex justify-center gap-3">
          <a
            href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(
              `Plus que ${GOALS_REMAINING} buts avant le 1000e but de Cristiano Ronaldo ! Suivez le compte à rebours ici :`
            )}&url=${encodeURIComponent("https://to1000.com")}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 bg-white/5 border border-white/10 rounded-full text-sm text-white/70 hover:text-white hover:border-gold/30 transition-all"
          >
            Partager sur X
          </a>
          <a
            href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent("https://to1000.com")}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 bg-white/5 border border-white/10 rounded-full text-sm text-white/70 hover:text-white hover:border-gold/30 transition-all"
          >
            Partager sur Facebook
          </a>
        </div>
      </section>
    </>
  );
}
